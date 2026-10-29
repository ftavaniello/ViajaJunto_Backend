from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado
from app.domain.ports.usuario_repository import UsuarioRepository


class SQLAlchemyUsuarioRepository(UsuarioRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def salvar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            model = UsuarioModel(
                nome=usuario.nome,
                email=usuario.email,
                senha_hash=usuario.senha_hash,
                versao_sessao=usuario.versao_sessao,
            )
            self.db.add(model)
        else:
            model = self.db.get(UsuarioModel, usuario.id)
            model.nome = usuario.nome
            model.email = usuario.email
            model.senha_hash = usuario.senha_hash
            model.versao_sessao = usuario.versao_sessao

        try:
            # flush envia o INSERT/UPDATE sem confirmar: gera o id e expoe violacoes
            # de constraint ainda dentro da transacao da operacao.
            self.db.flush()
        except IntegrityError as error:
            # A unicidade do email e garantida pelo banco; a verificacao previa no
            # caso de uso nao elimina a condicao de corrida entre requisicoes.
            raise EmailDuplicado("Já existe um usuário com este email") from error
        self.db.refresh(model)

        return self._to_entity(model)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        model = self.db.get(UsuarioModel, usuario_id)

        return self._to_entity(model) if model else None

    def buscar_por_email(self, email: str) -> Usuario | None:
        model = self.db.query(UsuarioModel).filter(UsuarioModel.email == email).first()

        return self._to_entity(model) if model else None

    def contar(self) -> int:
        return self.db.scalar(select(func.count()).select_from(UsuarioModel))

    def deletar(self, usuario_id: int) -> None:
        model = self.db.get(UsuarioModel, usuario_id)

        if model is not None:
            self.db.delete(model)
            self.db.flush()

    @staticmethod
    def _to_entity(model: UsuarioModel) -> Usuario:
        return Usuario(
            id=model.id,
            nome=model.nome,
            email=model.email,
            senha_hash=model.senha_hash,
            criado_em=model.criado_em,
            versao_sessao=model.versao_sessao,
        )
