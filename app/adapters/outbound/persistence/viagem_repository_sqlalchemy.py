from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro
from app.domain.participacao_viagem import ParticipacaoViagem
from app.domain.ports.viagem_repository import ViagemRepository


class SQLAlchemyViagemRepository(ViagemRepository):
    """Grava na transacao corrente da Session; quem confirma ou desfaz e a UnitOfWork."""

    def __init__(self, db: Session):
        self.db = db

    def salvar(self, viagem: Viagem) -> Viagem:
        if viagem.id is None:
            model = ViagemModel(
                criador_id=viagem.criador_id,
                codigo_convite=viagem.codigo_convite,
                codigo_convite_expira_em=viagem.codigo_convite_expira_em,
            )
            self.db.add(model)
        else:
            # criador e codigo de convite nao mudam por aqui.
            model = self.db.get(ViagemModel, viagem.id)

        model.nome = viagem.nome
        model.descricao = viagem.descricao
        model.data_inicio = viagem.data_inicio
        model.data_fim = viagem.data_fim
        model.status = viagem.status.value

        self.db.flush()
        self.db.refresh(model)

        return self._to_entity(model)

    def buscar_por_id(self, viagem_id: int) -> Viagem | None:
        model = self.db.get(ViagemModel, viagem_id)

        return self._to_entity(model) if model else None

    def listar_por_participante(
        self, usuario_id: int, limite: int, deslocamento: int
    ) -> list[ParticipacaoViagem]:
        # O vínculo único por (viagem, usuário) impede duplicação no JOIN.
        resultados = self.db.execute(
            select(ViagemModel, MembroViagemModel.papel)
            .outerjoin(MembroViagemModel, and_(
                MembroViagemModel.viagem_id == ViagemModel.id,
                MembroViagemModel.usuario_id == usuario_id,
            ))
            .where(or_(ViagemModel.criador_id == usuario_id, MembroViagemModel.id.is_not(None)))
            .order_by(ViagemModel.data_inicio, ViagemModel.id)
            .limit(limite)
            .offset(deslocamento)
        )
        return [
            ParticipacaoViagem(self._to_entity(model), PapelMembro(papel) if papel else None)
            for model, papel in resultados
        ]

    def deletar(self, viagem_id: int) -> None:
        model = self.db.get(ViagemModel, viagem_id)

        if model is not None:
            # Membros, roteiro e orcamento saem pelo ON DELETE CASCADE do banco.
            self.db.delete(model)
            self.db.flush()

    @staticmethod
    def _to_entity(model: ViagemModel) -> Viagem:
        return Viagem(
            id=model.id,
            criador_id=model.criador_id,
            nome=model.nome,
            descricao=model.descricao,
            data_inicio=model.data_inicio,
            data_fim=model.data_fim,
            status=model.status,
            codigo_convite=model.codigo_convite,
            codigo_convite_expira_em=model.codigo_convite_expira_em,
            criado_em=model.criado_em,
            atualizado_em=model.atualizado_em,
        )
