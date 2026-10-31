from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
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
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro
from app.domain.errors import (
    AcessoNegado,
    AtividadeCatalogoNaoEncontrada,
    AtividadeViagemNaoEncontrada,
    DadosInvalidos,
    DestinoViagemNaoEncontrado,
    ViagemNaoEncontrada,
)

AGORA = datetime(2026, 10, 31, tzinfo=timezone.utc)


@pytest.fixture
def contexto():
    membros = MembroViagemRepositoryMemory()
    viagens = ViagemRepositoryMemory(membros)
    viagens.salvar(
        Viagem(
            nome="Europa", criador_id=1, data_inicio=date(2027, 7, 1), data_fim=date(2027, 7, 20)
        )
    )
    membros.adicionar(1, 2, PapelMembro.EDITOR)
    membros.adicionar(1, 3, PapelMembro.VISUALIZADOR)
    catalogo = CatalogoRepositoryMemory()
    cidade = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    outra = catalogo.salvar_destino(DestinoCatalogo(nome="Porto", pais_codigo="PT"))
    catalogo.salvar_atividade(AtividadeCatalogo(destino=cidade, nome="Museu", categoria="cultura"))
    catalogo.salvar_atividade(AtividadeCatalogo(destino=outra, nome="Passeio", categoria="lazer"))
    destinos = DestinoViagemRepositoryMemory()
    for ordem in (1, 2):
        destinos.salvar(
            DestinoViagem(
                viagem_id=1,
                destino=cidade,
                ordem=ordem,
                data_chegada=date(2027, 7, 2),
                data_saida=date(2027, 7, 5),
            )
        )
    repo, uow = AtividadeViagemRepositoryMemory(), UnitOfWorkMemory()
    caso = GerenciarAtividadesViagem(
        repo, destinos, catalogo, PoliticaAcessoViagem(viagens, membros), uow, agora=lambda: AGORA
    )
    return caso, repo, catalogo, uow


def criar(caso, **campos):
    return caso.criar(
        **{
            "viagem_id": 1,
            "destino_id": 1,
            "usuario_id": 1,
            "catalogo_atividade_id": 1,
            "data": date(2027, 7, 3),
            **campos,
        }
    )


@pytest.mark.parametrize("usuario", [1, 2])
def test_criador_editor_planejam_sem_alterar_catalogo(contexto, usuario):
    caso, _, catalogo, _ = contexto
    original = catalogo.buscar_atividade(1)
    nova = criar(caso, usuario_id=usuario, custo_previsto=Decimal("10.20"))
    salva = caso.atualizar(
        1, 1, nova.id, usuario, status="confirmada", custo_previsto=Decimal("20.30")
    )
    assert salva.status.value == "confirmada"
    assert salva.custo_previsto == Decimal("20.30")
    assert catalogo.buscar_atividade(1) == original
    caso.remover(1, 1, nova.id, usuario)
    assert caso.listar(1, 1, usuario) == []


@pytest.mark.parametrize("usuario", [1, 2, 3])
def test_participantes_consultam(contexto, usuario):
    caso, *_ = contexto
    nova = criar(caso)
    assert caso.consultar(1, 1, nova.id, usuario) == nova


@pytest.mark.parametrize("usuario,erro", [(3, AcessoNegado), (4, ViagemNaoEncontrada)])
@pytest.mark.parametrize("acao", ["criar", "atualizar", "remover"])
def test_sem_permissao_nao_altera(contexto, usuario, erro, acao):
    caso, repo, *_ = contexto
    nova = criar(caso)
    antes = dict(repo.atividades)
    argumentos = {
        "criar": (1, 1, usuario, 1, date(2027, 7, 3)),
        "atualizar": (1, 1, nova.id, usuario),
        "remover": (1, 1, nova.id, usuario),
    }
    operacao = getattr(caso, acao)
    with pytest.raises(erro):
        operacao(*argumentos[acao])
    assert repo.atividades == antes


def test_ordenacao_por_dia_hora_nulos_e_id(contexto):
    caso, *_ = contexto
    sem_hora = criar(caso)
    tarde = criar(caso, hora_inicio=time(15))
    cedo = criar(caso, hora_inicio=time(9))
    empate = criar(caso, hora_inicio=time(9))
    anterior = criar(caso, data=date(2027, 7, 2))
    ids = [a.id for a in caso.listar(1, 1, 1)]
    assert ids == [anterior.id, cedo.id, empate.id, tarde.id, sem_hora.id]


@pytest.mark.parametrize(
    "campos,erro",
    [
        ({"catalogo_atividade_id": 999}, AtividadeCatalogoNaoEncontrada),
        ({"catalogo_atividade_id": 2}, DadosInvalidos),
        ({"data": date(2027, 7, 6)}, DadosInvalidos),
        ({"status": "cancelada"}, DadosInvalidos),
        ({"destino_id": 999}, DestinoViagemNaoEncontrado),
    ],
)
def test_criacao_invalida(contexto, campos, erro):
    caso, repo, *_ = contexto
    with pytest.raises(erro):
        criar(caso, **campos)
    assert repo.atividades == {}


def test_id_de_outra_parada_nao_e_aceito(contexto):
    caso, *_ = contexto
    nova = criar(caso)
    with pytest.raises(AtividadeViagemNaoEncontrada):
        caso.consultar(1, 2, nova.id, 1)


def test_conclusao_reabertura_e_comprovacao(contexto):
    caso, *_ = contexto
    nova = criar(caso)
    concluida = caso.atualizar(1, 1, nova.id, 2, status="concluida")
    assert concluida.realizada_em == AGORA
    assert concluida.realizada_por_id == 2
    editada = caso.atualizar(1, 1, nova.id, 1, custo_previsto=Decimal("5.10"))
    assert (editada.realizada_em, editada.realizada_por_id) == (AGORA, 2)
    reaberta = caso.atualizar(1, 1, nova.id, 1, status="pendente")
    assert reaberta.realizada_em is None
    assert reaberta.realizada_por_id is None


def test_criacao_concluida_e_limpeza_de_opcionais(contexto):
    caso, *_ = contexto
    nova = criar(caso, status="concluida", hora_inicio=time(9), duracao_minutos=60)
    assert nova.realizada_por_id == 1
    limpa = caso.atualizar(1, 1, nova.id, 1, limpar_hora=True, limpar_duracao=True)
    assert limpa.hora_inicio is None
    assert limpa.duracao_minutos is None
    assert limpa.realizada_em == nova.realizada_em


def test_falha_de_gravacao_reverte_transacao(contexto):
    caso, repo, _, uow = contexto
    falho = Mock(wraps=repo)
    falho.salvar.side_effect = RuntimeError("falha de persistência")
    caso.repository = falho
    with pytest.raises(RuntimeError):
        criar(caso)
    assert (uow.commits, uow.rollbacks) == (0, 1)
