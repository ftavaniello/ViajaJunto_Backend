from datetime import date
from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro
from app.domain.errors import (
    AcessoNegado,
    DadosInvalidos,
    DestinoCatalogoNaoEncontrado,
    DestinoViagemNaoEncontrado,
    ViagemNaoEncontrada,
)


@pytest.fixture
def contexto():
    membros = MembroViagemRepositoryMemory()
    viagens = ViagemRepositoryMemory(membros)
    for nome in ("Europa", "Outra"):
        viagens.salvar(
            Viagem(
                criador_id=1, nome=nome, data_inicio=date(2027, 7, 1), data_fim=date(2027, 7, 20)
            )
        )
    membros.adicionar(1, 2, PapelMembro.EDITOR)
    membros.adicionar(1, 3, PapelMembro.VISUALIZADOR)
    catalogo = CatalogoRepositoryMemory()
    catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT", descricao="Pública"))
    repo, uow = DestinoViagemRepositoryMemory(), UnitOfWorkMemory()
    acesso = PoliticaAcessoViagem(viagens, membros)
    caso = GerenciarDestinosViagem(repo, catalogo, acesso, uow)
    return caso, repo, catalogo, uow, viagens, acesso


def criar(caso, **campos):
    return caso.criar(
        **{
            "viagem_id": 1,
            "usuario_id": 1,
            "destino_catalogo_id": 1,
            "data_chegada": date(2027, 7, 2),
            "data_saida": date(2027, 7, 5),
            **campos,
        }
    )


@pytest.mark.parametrize("usuario", [1, 2])
def test_criador_editor_inserem_e_reordenam(contexto, usuario):
    caso, repo, _, _, _, _ = contexto
    primeira = criar(caso, usuario_id=usuario)
    segunda = criar(caso, usuario_id=usuario, ordem=1)
    assert [d.id for d in caso.listar(1, usuario)] == [segunda.id, primeira.id]
    resultado = caso.reordenar(1, usuario, [primeira.id, segunda.id])
    assert [(d.id, d.ordem) for d in resultado] == [(primeira.id, 1), (segunda.id, 2)]
    assert len(repo.destinos) == 2


@pytest.mark.parametrize("usuario", [1, 2, 3])
def test_participantes_consultam(contexto, usuario):
    caso, *_ = contexto
    destino = criar(caso)
    assert caso.consultar(1, destino.id, usuario).id == destino.id
    assert len(caso.listar(1, usuario)) == 1


@pytest.mark.parametrize("acao", ["criar", "atualizar", "remover", "reordenar"])
@pytest.mark.parametrize("usuario,erro", [(3, AcessoNegado), (4, ViagemNaoEncontrada)])
def test_sem_permissao_nao_altera(contexto, acao, usuario, erro):
    caso, repo, *_ = contexto
    destino = criar(caso)
    antes = dict(repo.destinos)
    argumentos = {
        "criar": (1, usuario, 1, date(2027, 7, 2), date(2027, 7, 5)),
        "atualizar": (1, destino.id, usuario),
        "remover": (1, destino.id, usuario),
        "reordenar": (1, usuario, [destino.id]),
    }
    operacao = getattr(caso, acao)
    with pytest.raises(erro):
        operacao(*argumentos[acao])
    assert repo.destinos == antes


def test_destino_de_outra_viagem_e_ocultado(contexto):
    caso, *_ = contexto
    destino = criar(caso, viagem_id=2)
    with pytest.raises(DestinoViagemNaoEncontrado):
        caso.consultar(1, destino.id, 1)


@pytest.mark.parametrize(
    "campos",
    [
        {"ordem": 2},
        {"data_chegada": date(2027, 6, 30)},
        {"data_saida": date(2027, 7, 21)},
        {"data_saida": date(2027, 7, 1)},
    ],
)
def test_insercao_invalida_nao_grava(contexto, campos):
    caso, repo, *_ = contexto
    with pytest.raises(DadosInvalidos):
        criar(caso, **campos)
    assert repo.destinos == {}


def test_catalogo_inexistente(contexto):
    caso, *_ = contexto
    with pytest.raises(DestinoCatalogoNaoEncontrado):
        criar(caso, destino_catalogo_id=999)


def test_atualizacao_preserva_catalogo_e_campos_omitidos(contexto):
    caso, _, catalogo, *_ = contexto
    destino = criar(caso, descricao="Privada", hospedagem="Hotel")
    atualizado = caso.atualizar(1, destino.id, 2, descricao="Nova")
    assert atualizado.data_chegada == destino.data_chegada
    assert atualizado.hospedagem == "Hotel"
    assert catalogo.buscar_destino(1).descricao == "Pública"
    limpo = caso.atualizar(1, destino.id, 1, descricao="", hospedagem="")
    assert limpo.descricao is None
    assert limpo.hospedagem is None


def test_reduzir_periodo_nao_deixa_atividades_fora(contexto):
    caso, repo, *_ = contexto
    destino = criar(caso)
    repo.atividades[destino.id] = [date(2027, 7, 3)]
    valor_data_chegada = date(2027, 7, 4)
    with pytest.raises(DadosInvalidos):
        caso.atualizar(1, destino.id, 1, data_chegada=valor_data_chegada)
    assert repo.buscar(1, destino.id) == destino


@pytest.mark.parametrize("ids", [[1, 1], [1], [1, 999]])
def test_reordenacao_invalida_preserva_ordem(contexto, ids):
    caso, repo, *_ = contexto
    criar(caso)
    criar(caso)
    antes = dict(repo.destinos)
    with pytest.raises(DadosInvalidos):
        caso.reordenar(1, 1, ids)
    assert repo.destinos == antes


def test_exclusao_remove_atividades_e_compacta(contexto):
    caso, repo, catalogo, *_ = contexto
    primeira = criar(caso)
    segunda = criar(caso)
    repo.atividades[primeira.id] = [date(2027, 7, 3)]
    caso.remover(1, primeira.id, 1)
    assert primeira.id not in repo.atividades
    assert [(d.id, d.ordem) for d in caso.listar(1, 1)] == [(segunda.id, 1)]
    assert catalogo.buscar_destino(1) is not None


def test_viagem_nao_pode_encolher_excluindo_destino(contexto):
    caso, repo, _, _, viagens, acesso = contexto
    criar(caso)
    atualizar = AtualizarViagem(viagens, acesso, UnitOfWorkMemory(), repo)
    valor_data_fim = date(2027, 7, 4)
    with pytest.raises(DadosInvalidos):
        atualizar.execute(1, 1, data_fim=valor_data_fim)
    assert viagens.buscar_por_id(1).data_fim == date(2027, 7, 20)


def test_falha_de_gravacao_desfaz_transacao(contexto):
    caso, repo, catalogo, _, _, acesso = contexto
    falho = Mock(wraps=repo)
    falho.salvar.side_effect = RuntimeError("falha no banco")
    uow = UnitOfWorkMemory()
    caso = GerenciarDestinosViagem(falho, catalogo, acesso, uow)
    with pytest.raises(RuntimeError):
        criar(caso)
    assert (uow.commits, uow.rollbacks) == (0, 1)
