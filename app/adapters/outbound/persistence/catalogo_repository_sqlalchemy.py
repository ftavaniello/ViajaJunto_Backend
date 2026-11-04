from dataclasses import replace
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade, CategoriaDestino, FonteCatalogo
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
                    "categoria",
                    "descricao",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "id_externo",
                    "fonte",
                )
            }
        )
        self.db.add(model)
        self.db.flush()
        return self._destino(model)

    def buscar_destino(self, destino_id: int) -> DestinoCatalogo | None:
        model = self.db.get(DestinoCatalogoModel, destino_id)
        return self._destino(model) if model is not None else None

    def listar_destinos(
        self,
        nome: str | None,
        pais_codigo: str | None,
        categoria: CategoriaDestino | None,
        limite: int,
        deslocamento: int,
    ) -> list[DestinoCatalogo]:
        consulta = select(DestinoCatalogoModel)
        if nome:
            consulta = consulta.where(DestinoCatalogoModel.nome.icontains(nome, autoescape=True))
        if pais_codigo:
            consulta = consulta.where(DestinoCatalogoModel.pais_codigo == pais_codigo)
        if categoria:
            consulta = consulta.where(DestinoCatalogoModel.categoria == categoria.value)
        models = self.db.scalars(
            consulta.order_by(DestinoCatalogoModel.id).limit(limite).offset(deslocamento)
        )
        return [self._destino(model) for model in models]

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
                    "id_externo",
                    "fonte",
                )
            },
        )
        self.db.add(model)
        self.db.flush()
        return self._atividade(model, atividade.destino)

    def buscar_atividade_externa(
        self, fonte: FonteCatalogo, id_externo: str
    ) -> AtividadeCatalogo | None:
        consulta, _ = self._consulta_publica()
        linha = self.db.execute(
            consulta.where(
                CatalogoAtividadeModel.fonte == fonte.value,
                CatalogoAtividadeModel.id_externo == id_externo,
            )
        ).first()
        return self._atividade_publica(*linha) if linha else None

    def atualizar_atividade(self, atividade: AtividadeCatalogo) -> AtividadeCatalogo:
        model = self.db.get(CatalogoAtividadeModel, atividade.id)
        # O id e o destino não mudam: avaliações e roteiros continuam ligados ao registro.
        for campo in (
            "nome",
            "descricao",
            "categoria",
            "endereco",
            "latitude",
            "longitude",
            "foto_url",
        ):
            setattr(model, campo, getattr(atividade, campo))
        self.db.flush()
        return self._atividade(model, atividade.destino)

    @staticmethod
    def _consulta_publica():
        resumo = (
            select(
                AvaliacaoModel.catalogo_atividade_id.label("atividade_id"),
                func.avg(AvaliacaoModel.nota).label("media"),
                func.count(AvaliacaoModel.id).label("total"),
            )
            .group_by(AvaliacaoModel.catalogo_atividade_id)
            .subquery()
        )
        consulta = (
            select(
                CatalogoAtividadeModel,
                DestinoCatalogoModel,
                resumo.c.media,
                func.coalesce(resumo.c.total, 0),
            )
            .join(DestinoCatalogoModel)
            .outerjoin(resumo, resumo.c.atividade_id == CatalogoAtividadeModel.id)
        )
        return consulta, resumo

    def buscar_atividade(self, atividade_id: int) -> AtividadeCatalogo | None:
        consulta, _ = self._consulta_publica()
        linha = self.db.execute(consulta.where(CatalogoAtividadeModel.id == atividade_id)).first()
        return self._atividade_publica(*linha) if linha else None

    def listar_atividades(
        self,
        nome: str | None,
        categoria: CategoriaAtividade | None,
        localizacao: str | None,
        destino_catalogo_id: int | None,
        limite: int,
        deslocamento: int,
        nota_minima: Decimal | None = None,
    ) -> list[AtividadeCatalogo]:
        consulta, resumo = self._consulta_publica()
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
        if nota_minima is not None:
            consulta = consulta.where(resumo.c.media >= nota_minima)
        resultados = self.db.execute(
            consulta.order_by(CatalogoAtividadeModel.id).limit(limite).offset(deslocamento)
        )
        return [self._atividade_publica(*linha) for linha in resultados]

    @classmethod
    def _atividade_publica(
        cls,
        atividade: CatalogoAtividadeModel,
        destino: DestinoCatalogoModel,
        media: Decimal | None,
        total: int,
    ) -> AtividadeCatalogo:
        return replace(
            cls._atividade(atividade, cls._destino(destino)),
            media_avaliacoes=media,
            total_avaliacoes=total,
        )

    @staticmethod
    def _destino(model: DestinoCatalogoModel) -> DestinoCatalogo:
        return DestinoCatalogo(
            **{
                campo: getattr(model, campo)
                for campo in (
                    "id",
                    "nome",
                    "pais_codigo",
                    "categoria",
                    "descricao",
                    "latitude",
                    "longitude",
                    "foto_url",
                    "id_externo",
                    "fonte",
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
                    "id_externo",
                    "fonte",
                )
            },
        )
