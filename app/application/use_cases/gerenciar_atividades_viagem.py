from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import TypeVar

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.enums import StatusAtividade
from app.domain.errors import (
    AtividadeCatalogoNaoEncontrada,
    AtividadeViagemNaoEncontrada,
    DadosInvalidos,
    DestinoViagemNaoEncontrado,
)
from app.domain.permissoes import AcaoViagem
from app.domain.ports.atividade_viagem_repository import AtividadeViagemRepository
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository
from app.domain.ports.unit_of_work import UnitOfWork

T = TypeVar("T")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class GerenciarAtividadesViagem:
    def __init__(
        self,
        repository: AtividadeViagemRepository,
        destinos: DestinoViagemRepository,
        catalogo: CatalogoRepository,
        acesso: PoliticaAcessoViagem,
        uow: UnitOfWork,
        agora: Callable[[], datetime] = _agora_utc,
    ):
        self.repository = repository
        self.destinos = destinos
        self.catalogo = catalogo
        self.acesso = acesso
        self.uow = uow
        self.agora = agora

    def _contexto(
        self, viagem_id: int, destino_id: int, usuario_id: int, editar: bool = False
    ) -> DestinoViagem:
        acao = AcaoViagem.EDITAR if editar else AcaoViagem.CONSULTAR
        self.acesso.exigir(viagem_id, usuario_id, acao)
        if editar:
            self.destinos.bloquear_roteiro(viagem_id)
            self.acesso.exigir(viagem_id, usuario_id, acao)
        destino = self.destinos.buscar(viagem_id, destino_id)
        if destino is None:
            raise DestinoViagemNaoEncontrado("Destino não encontrado nesta viagem")
        return destino

    def _atividade(self, viagem_id: int, destino_id: int, atividade_id: int) -> AtividadeViagem:
        atividade = self.repository.buscar(viagem_id, destino_id, atividade_id)
        if atividade is None:
            raise AtividadeViagemNaoEncontrada("Atividade não encontrada nesta parada")
        return atividade

    def listar(self, viagem_id: int, destino_id: int, usuario_id: int) -> list[AtividadeViagem]:
        self._contexto(viagem_id, destino_id, usuario_id)
        return self.repository.listar(viagem_id, destino_id)

    def consultar(
        self, viagem_id: int, destino_id: int, atividade_id: int, usuario_id: int
    ) -> AtividadeViagem:
        self._contexto(viagem_id, destino_id, usuario_id)
        return self._atividade(viagem_id, destino_id, atividade_id)

    @staticmethod
    def _status_novo(status: StatusAtividade | str) -> StatusAtividade:
        try:
            resultado = StatusAtividade(status)
        except (ValueError, TypeError) as error:
            raise DadosInvalidos("Status de atividade inválido") from error
        if resultado == StatusAtividade.CANCELADA:
            raise DadosInvalidos(
                "Cancelada é um status legado; use pendente, confirmada ou concluida"
            )
        return resultado

    def criar(
        self,
        viagem_id: int,
        destino_id: int,
        usuario_id: int,
        catalogo_atividade_id: int,
        data: date,
        hora_inicio: time | None = None,
        duracao_minutos: int | None = None,
        custo_previsto: Decimal = Decimal("0.00"),
        status: StatusAtividade = StatusAtividade.PENDENTE,
    ) -> AtividadeViagem:
        with self.uow:
            destino = self._contexto(viagem_id, destino_id, usuario_id, editar=True)
            catalogo = self.catalogo.buscar_atividade(catalogo_atividade_id)
            if catalogo is None:
                raise AtividadeCatalogoNaoEncontrada("Atividade não encontrada no catálogo")
            status = self._status_novo(status)
            concluida = status == StatusAtividade.CONCLUIDA
            nova = AtividadeViagem(
                viagem_id=viagem_id,
                destino_viagem_id=destino_id,
                atividade=catalogo,
                data=data,
                hora_inicio=hora_inicio,
                duracao_minutos=duracao_minutos,
                custo_previsto=custo_previsto,
                status=status,
                realizada_em=self.agora() if concluida else None,
                realizada_por_id=usuario_id if concluida else None,
            )
            nova.validar_destino(destino)
            salva = self.repository.salvar(nova)
            self.uow.commit()
        return salva

    def atualizar(
        self,
        viagem_id: int,
        destino_id: int,
        atividade_id: int,
        usuario_id: int,
        data: date | None = None,
        hora_inicio: time | None = None,
        duracao_minutos: int | None = None,
        custo_previsto: Decimal | None = None,
        status: StatusAtividade | None = None,
        limpar_hora: bool = False,
        limpar_duracao: bool = False,
    ) -> AtividadeViagem:
        with self.uow:
            destino = self._contexto(viagem_id, destino_id, usuario_id, editar=True)
            atual = self._atividade(viagem_id, destino_id, atividade_id)
            novo_status = atual.status if status is None else self._status_novo(status)
            realizada_em, realizada_por_id = self._comprovacao(atual, novo_status, usuario_id)
            nova = replace(
                atual,
                data=atual.data if data is None else data,
                hora_inicio=self._valor_opcional(atual.hora_inicio, hora_inicio, limpar_hora),
                duracao_minutos=self._valor_opcional(
                    atual.duracao_minutos, duracao_minutos, limpar_duracao
                ),
                custo_previsto=atual.custo_previsto if custo_previsto is None else custo_previsto,
                status=novo_status,
                realizada_em=realizada_em,
                realizada_por_id=realizada_por_id,
            )
            nova.validar_destino(destino)
            salva = self.repository.salvar(nova)
            self.uow.commit()
        return salva

    @staticmethod
    def _valor_opcional(atual: T | None, novo: T | None, limpar: bool) -> T | None:
        if limpar:
            return None
        return atual if novo is None else novo

    def _comprovacao(
        self, atual: AtividadeViagem, status: StatusAtividade, usuario_id: int
    ) -> tuple[datetime | None, int | None]:
        if status == atual.status:
            return atual.realizada_em, atual.realizada_por_id
        if status != StatusAtividade.CONCLUIDA:
            return None, None
        return self.agora(), usuario_id

    def remover(self, viagem_id: int, destino_id: int, atividade_id: int, usuario_id: int) -> None:
        with self.uow:
            self._contexto(viagem_id, destino_id, usuario_id, editar=True)
            atividade = self._atividade(viagem_id, destino_id, atividade_id)
            self.repository.deletar(atividade)
            self.uow.commit()
