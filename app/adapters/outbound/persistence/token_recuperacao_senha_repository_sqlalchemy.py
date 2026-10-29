from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.recuperacao_senha_model import TokenRecuperacaoSenhaModel
from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.ports.token_recuperacao_senha_repository import TokenRecuperacaoSenhaRepository


class SQLAlchemyTokenRecuperacaoSenhaRepository(TokenRecuperacaoSenhaRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def salvar(self, token: TokenRecuperacaoSenha) -> TokenRecuperacaoSenha:
        if token.id is None:
            model = TokenRecuperacaoSenhaModel(
                usuario_id=token.usuario_id,
                token_hash=token.token_hash,
                expira_em=token.expira_em,
                usado_em=token.usado_em,
            )
            self.db.add(model)
        else:
            model = self.db.get(TokenRecuperacaoSenhaModel, token.id)
            model.usado_em = token.usado_em

        self.db.flush()

        return self._to_entity(model)

    def buscar_por_hash(self, token_hash: str) -> TokenRecuperacaoSenha | None:
        # FOR UPDATE: uma segunda redefinicao com o mesmo token espera esta transacao
        # e depois ja encontra usado_em preenchido.
        model = self.db.scalar(
            select(TokenRecuperacaoSenhaModel)
            .where(TokenRecuperacaoSenhaModel.token_hash == token_hash)
            .with_for_update()
        )

        return self._to_entity(model) if model else None

    def invalidar_pendentes(self, usuario_id: int, agora: datetime) -> None:
        self.db.execute(
            update(TokenRecuperacaoSenhaModel)
            .where(
                TokenRecuperacaoSenhaModel.usuario_id == usuario_id,
                TokenRecuperacaoSenhaModel.usado_em.is_(None),
            )
            .values(usado_em=agora)
        )

    @staticmethod
    def _to_entity(model: TokenRecuperacaoSenhaModel) -> TokenRecuperacaoSenha:
        return TokenRecuperacaoSenha(
            id=model.id,
            usuario_id=model.usuario_id,
            token_hash=model.token_hash,
            expira_em=model.expira_em,
            usado_em=model.usado_em,
        )
