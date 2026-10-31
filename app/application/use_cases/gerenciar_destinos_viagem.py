from dataclasses import replace
from datetime import date

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.destino_viagem import DestinoViagem, validar_reordenacao
from app.domain.entities.viagem import Viagem
from app.domain.errors import (
    DadosInvalidos,
    DestinoCatalogoNaoEncontrado,
    DestinoViagemNaoEncontrado,
)
from app.domain.permissoes import AcaoViagem
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository
from app.domain.ports.unit_of_work import UnitOfWork


class GerenciarDestinosViagem:
    def __init__(
        self,
        repository: DestinoViagemRepository,
        catalogo: CatalogoRepository,
        acesso: PoliticaAcessoViagem,
        uow: UnitOfWork,
    ):
        self.repository = repository
        self.catalogo = catalogo
        self.acesso = acesso
        self.uow = uow

    def listar(self, viagem_id: int, usuario_id: int) -> list[DestinoViagem]:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
        return self.repository.listar(viagem_id)

    def consultar(self, viagem_id: int, destino_id: int, usuario_id: int) -> DestinoViagem:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
        return self._destino(viagem_id, destino_id)

    def _destino(self, viagem_id: int, destino_id: int) -> DestinoViagem:
        destino = self.repository.buscar(viagem_id, destino_id)
        if destino is None:
            raise DestinoViagemNaoEncontrado("Destino não encontrado nesta viagem")
        return destino

    def _editar(self, viagem_id: int, usuario_id: int) -> Viagem:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EDITAR)
        self.repository.bloquear_roteiro(viagem_id)
        # Revalida contexto e datas após adquirir o bloqueio da viagem.
        return self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.EDITAR)

    def criar(
        self,
        viagem_id: int,
        usuario_id: int,
        destino_catalogo_id: int,
        data_chegada: date,
        data_saida: date,
        descricao: str | None = None,
        hospedagem: str | None = None,
        ordem: int | None = None,
    ) -> DestinoViagem:
        with self.uow:
            viagem = self._editar(viagem_id, usuario_id)
            catalogo = self.catalogo.buscar_destino(destino_catalogo_id)
            if catalogo is None:
                raise DestinoCatalogoNaoEncontrado("Destino não encontrado no catálogo")
            destinos = self.repository.listar(viagem_id)
            posicao = len(destinos) + 1 if ordem is None else ordem
            if type(posicao) is not int or not 1 <= posicao <= len(destinos) + 1:
                raise DadosInvalidos("Ordem de inserção fora do roteiro")
            novo = DestinoViagem(
                viagem_id=viagem_id,
                destino=catalogo,
                ordem=posicao,
                data_chegada=data_chegada,
                data_saida=data_saida,
                descricao=descricao,
                hospedagem=hospedagem,
            )
            novo.validar_periodo(viagem.data_inicio, viagem.data_fim)
            for destino in destinos:
                if destino.ordem >= posicao:
                    self.repository.salvar(replace(destino, ordem=destino.ordem + 1))
            salvo = self.repository.salvar(novo)
            self.uow.commit()
        return salvo

    def atualizar(
        self,
        viagem_id: int,
        destino_id: int,
        usuario_id: int,
        data_chegada: date | None = None,
        data_saida: date | None = None,
        descricao: str | None = None,
        hospedagem: str | None = None,
    ) -> DestinoViagem:
        with self.uow:
            viagem = self._editar(viagem_id, usuario_id)
            destino = self._destino(viagem_id, destino_id)
            atualizado = replace(
                destino,
                data_chegada=destino.data_chegada if data_chegada is None else data_chegada,
                data_saida=destino.data_saida if data_saida is None else data_saida,
                descricao=destino.descricao if descricao is None else descricao,
                hospedagem=destino.hospedagem if hospedagem is None else hospedagem,
            )
            atualizado.validar_periodo(viagem.data_inicio, viagem.data_fim)
            if any(
                not atualizado.data_chegada <= data <= atualizado.data_saida
                for data in self.repository.datas_atividades(destino_id)
            ):
                raise DadosInvalidos(
                    "As atividades existentes devem permanecer no período do destino"
                )
            salvo = self.repository.salvar(atualizado)
            self.uow.commit()
        return salvo

    def reordenar(
        self, viagem_id: int, usuario_id: int, destinos_ids: list[int]
    ) -> list[DestinoViagem]:
        with self.uow:
            self._editar(viagem_id, usuario_id)
            destinos = self.repository.listar(viagem_id)
            validar_reordenacao(destinos_ids, destinos)
            por_id = {destino.id: destino for destino in destinos}
            resultado = [
                self.repository.salvar(replace(por_id[id_], ordem=posicao))
                for posicao, id_ in enumerate(destinos_ids, start=1)
            ]
            self.uow.commit()
        return resultado

    def remover(self, viagem_id: int, destino_id: int, usuario_id: int) -> None:
        with self.uow:
            self._editar(viagem_id, usuario_id)
            destino = self._destino(viagem_id, destino_id)
            self.repository.deletar(destino)
            for posicao, restante in enumerate(self.repository.listar(viagem_id), start=1):
                if restante.ordem != posicao:
                    self.repository.salvar(replace(restante, ordem=posicao))
            self.uow.commit()
