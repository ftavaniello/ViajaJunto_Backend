from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.ports.catalogo_repository import CatalogoRepository


class SQLAlchemyCatalogoRepository(CatalogoRepository):
    def __init__(self, db: Session):
        self.db = db

    def reservar_carga_inicial(self) -> bool:
        # Lock transacional exclusivo para serializar seeds de múltiplas instâncias.
        # A UnitOfWork libera o lock ao confirmar ou desfazer a carga.
        self.db.execute(select(func.pg_advisory_xact_lock(202620, 1)))
        possui_destinos = self.db.scalar(select(select(DestinoCatalogoModel.id).exists()))
        possui_atividades = self.db.scalar(select(select(CatalogoAtividadeModel.id).exists()))
        return not possui_destinos and not possui_atividades

    def salvar_destino(self, destino: DestinoCatalogo) -> DestinoCatalogo:
        model = DestinoCatalogoModel(
            **{
                campo: getattr(destino, campo)
                for campo in (
                    "nome",
                    "pais_codigo",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "google_place_id",
                )
            }
        )
        self.db.add(model)
        self.db.flush()
        return self._destino(model)

    def salvar_atividade(self, atividade: AtividadeCatalogo) -> AtividadeCatalogo:
        model = CatalogoAtividadeModel(
            destino_catalogo_id=atividade.destino.id,
            **{
                campo: getattr(atividade, campo)
                for campo in (
                    "nome",
                    "descricao",
                    "categoria",
                    "endereco",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "google_place_id",
                    "fonte",
                )
            },
        )
        self.db.add(model)
        self.db.flush()
        return self._atividade(model, atividade.destino)

    def buscar_atividade(self, atividade_id: int) -> AtividadeCatalogo | None:
        resultado = self.db.execute(
            select(CatalogoAtividadeModel, DestinoCatalogoModel)
            .join(DestinoCatalogoModel)
            .where(CatalogoAtividadeModel.id == atividade_id)
        ).first()
        return self._atividade(resultado[0], self._destino(resultado[1])) if resultado else None

    def listar_atividades(
        self,
        nome: str | None,
        categoria: CategoriaAtividade | None,
        localizacao: str | None,
        destino_catalogo_id: int | None,
        limite: int,
        deslocamento: int,
    ) -> list[AtividadeCatalogo]:
        consulta = select(CatalogoAtividadeModel, DestinoCatalogoModel).join(DestinoCatalogoModel)
        # autoescape impede que % e _ fornecidos pelo cliente virem curingas SQL.
        if nome:
            consulta = consulta.where(CatalogoAtividadeModel.nome.icontains(nome, autoescape=True))
        if categoria:
            consulta = consulta.where(CatalogoAtividadeModel.categoria == categoria.value)
        if destino_catalogo_id:
            consulta = consulta.where(
                CatalogoAtividadeModel.destino_catalogo_id == destino_catalogo_id
            )
        if localizacao:
            consulta = consulta.where(
                or_(
                    DestinoCatalogoModel.nome.icontains(localizacao, autoescape=True),
                    DestinoCatalogoModel.pais_codigo.icontains(localizacao, autoescape=True),
                    CatalogoAtividadeModel.endereco.icontains(localizacao, autoescape=True),
                )
            )
        resultados = self.db.execute(
            consulta.order_by(CatalogoAtividadeModel.id).limit(limite).offset(deslocamento)
        )
        return [self._atividade(a, self._destino(d)) for a, d in resultados]

    @staticmethod
    def _destino(model: DestinoCatalogoModel) -> DestinoCatalogo:
        return DestinoCatalogo(
            **{
                campo: getattr(model, campo)
                for campo in (
                    "id",
                    "nome",
                    "pais_codigo",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "google_place_id",
                )
            }
        )

    @staticmethod
    def _atividade(model: CatalogoAtividadeModel, destino: DestinoCatalogo) -> AtividadeCatalogo:
        return AtividadeCatalogo(
            destino=destino,
            **{
                campo: getattr(model, campo)
                for campo in (
                    "id",
                    "nome",
                    "descricao",
                    "categoria",
                    "endereco",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "google_place_id",
                    "fonte",
                )
            },
        )
