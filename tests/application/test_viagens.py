from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.consultar_viagem import ConsultarViagem
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.excluir_viagem import ExcluirViagem
from app.application.use_cases.listar_viagens import ListarViagens
from app.domain.enums import PapelMembro, StatusViagem
from app.domain.errors import AcessoNegado, DadosInvalidos, ViagemNaoEncontrada
from app.domain.permissoes import AcaoViagem, PerfilViagem

CRIADOR, EDITOR, VISUALIZADOR, ESTRANHO = 1, 2, 3, 4


@pytest.fixture
def membros() -> MembroViagemRepositoryMemory:
    return MembroViagemRepositoryMemory()


@pytest.fixture
def viagens(membros) -> ViagemRepositoryMemory:
    return ViagemRepositoryMemory(membros)


@pytest.fixture
def acesso(viagens, membros) -> PoliticaAcessoViagem:
    return PoliticaAcessoViagem(viagens, membros)


@pytest.fixture
def viagem_id(viagens, membros) -> int:
    viagem = CriarViagem(viagens, UnitOfWorkMemory()).execute(
        criador_id=CRIADOR, nome="Europa", descricao=None,
        data_inicio=date(2027, 7, 1), data_fim=date(2027, 7, 20),
    )
    membros.adicionar(viagem.id, EDITOR, PapelMembro.EDITOR)
    membros.adicionar(viagem.id, VISUALIZADOR, PapelMembro.VISUALIZADOR)
    return viagem.id


def test_criar_viagem_registra_criador_status_e_convite(viagens):
    agora = datetime(2026, 10, 29, tzinfo=timezone.utc)
    uow = UnitOfWorkMemory()

    viagem = CriarViagem(viagens, uow, agora=lambda: agora).execute(
        criador_id=CRIADOR, nome="Europa", descricao="Férias",
        data_inicio=date(2027, 7, 1), data_fim=date(2027, 7, 20),
    )

    assert viagem.id is not None
    assert viagem.criador_id == CRIADOR
    assert viagem.status == StatusViagem.PLANEJANDO
    assert viagem.codigo_convite
    assert viagem.codigo_convite_expira_em == agora + timedelta(days=7)
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_criar_viagem_com_periodo_invalido_nao_grava(viagens):
    uow = UnitOfWorkMemory()

    with pytest.raises(DadosInvalidos):
        CriarViagem(viagens, uow).execute(
            criador_id=CRIADOR, nome="Europa", descricao=None,
            data_inicio=date(2027, 7, 20), data_fim=date(2027, 7, 1),
        )

    assert viagens.viagens == {}
    assert uow.commits == 0


@pytest.mark.parametrize(
    ("usuario_id", "perfil"),
    [
        (CRIADOR, PerfilViagem.CRIADOR),
        (EDITOR, PerfilViagem.EDITOR),
        (VISUALIZADOR, PerfilViagem.VISUALIZADOR),
        (ESTRANHO, None),
    ],
)
def test_politica_identifica_o_perfil(acesso, viagens, viagem_id, usuario_id, perfil):
    assert acesso.perfil(viagens.buscar_por_id(viagem_id), usuario_id) == perfil


def test_politica_esconde_viagem_de_quem_nao_participa(acesso, viagem_id):
    with pytest.raises(ViagemNaoEncontrada):
        acesso.exigir(viagem_id, ESTRANHO, AcaoViagem.CONSULTAR)


def test_politica_trata_viagem_inexistente_como_nao_encontrada(acesso):
    with pytest.raises(ViagemNaoEncontrada):
        acesso.exigir(999, CRIADOR, AcaoViagem.CONSULTAR)


def test_politica_nega_acao_fora_do_papel(acesso, viagem_id):
    with pytest.raises(AcessoNegado):
        acesso.exigir(viagem_id, VISUALIZADOR, AcaoViagem.EDITAR)


@pytest.mark.parametrize("usuario_id", [CRIADOR, EDITOR, VISUALIZADOR])
def test_participantes_consultam_a_viagem(acesso, viagem_id, usuario_id):
    assert ConsultarViagem(acesso).execute(viagem_id, usuario_id).id == viagem_id


def test_consulta_por_quem_nao_participa_e_negada(acesso, viagem_id):
    with pytest.raises(ViagemNaoEncontrada):
        ConsultarViagem(acesso).execute(viagem_id, ESTRANHO)


def test_listar_traz_viagens_criadas_e_como_colaborador(viagens, membros, viagem_id):
    outra = CriarViagem(viagens, UnitOfWorkMemory()).execute(
        criador_id=ESTRANHO, nome="Japão", descricao=None,
        data_inicio=date(2027, 1, 1), data_fim=date(2027, 1, 10),
    )

    listar = ListarViagens(viagens)

    assert [v.id for v in listar.execute(CRIADOR)] == [viagem_id]
    assert [v.id for v in listar.execute(EDITOR)] == [viagem_id]
    assert [v.id for v in listar.execute(ESTRANHO)] == [outra.id]


@pytest.mark.parametrize("usuario_id", [CRIADOR, EDITOR])
def test_criador_e_editor_atualizam_dados_e_status(viagens, acesso, viagem_id, usuario_id):
    uow = UnitOfWorkMemory()

    viagem = AtualizarViagem(viagens, acesso, uow).execute(
        viagem_id, usuario_id, nome="Europa 2027", status=StatusViagem.CONFIRMADA,
    )

    assert viagem.nome == "Europa 2027"
    assert viagem.status == StatusViagem.CONFIRMADA
    assert viagem.data_inicio == date(2027, 7, 1)  # campos omitidos mantidos
    assert viagem.criador_id == CRIADOR
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_visualizador_nao_atualiza(viagens, acesso, viagem_id):
    with pytest.raises(AcessoNegado):
        AtualizarViagem(viagens, acesso, UnitOfWorkMemory()).execute(
            viagem_id, VISUALIZADOR, nome="Outro nome",
        )

    assert viagens.buscar_por_id(viagem_id).nome == "Europa"


def test_estranho_nao_atualiza(viagens, acesso, viagem_id):
    with pytest.raises(ViagemNaoEncontrada):
        AtualizarViagem(viagens, acesso, UnitOfWorkMemory()).execute(
            viagem_id, ESTRANHO, nome="Outro nome",
        )


def test_atualizar_valida_periodo_combinado_com_o_atual(viagens, acesso, viagem_id):
    with pytest.raises(DadosInvalidos):
        AtualizarViagem(viagens, acesso, UnitOfWorkMemory()).execute(
            viagem_id, CRIADOR, data_fim=date(2027, 6, 30),
        )

    assert viagens.buscar_por_id(viagem_id).data_fim == date(2027, 7, 20)


def test_atualizar_preserva_convite(viagens, acesso, viagem_id):
    codigo = viagens.buscar_por_id(viagem_id).codigo_convite

    viagem = AtualizarViagem(viagens, acesso, UnitOfWorkMemory()).execute(
        viagem_id, CRIADOR, descricao="Nova descrição",
    )

    assert viagem.codigo_convite == codigo


def test_falha_ao_gravar_atualizacao_desfaz_a_transacao(viagens, acesso, viagem_id):
    repository = Mock(wraps=viagens)
    repository.salvar.side_effect = RuntimeError("falha no banco")
    uow = UnitOfWorkMemory()

    with pytest.raises(RuntimeError):
        AtualizarViagem(repository, acesso, uow).execute(viagem_id, CRIADOR, nome="X")

    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_criador_exclui_viagem_e_colaboradores_perdem_acesso(viagens, acesso, viagem_id):
    uow = UnitOfWorkMemory()

    ExcluirViagem(viagens, acesso, uow).execute(viagem_id, CRIADOR)

    assert viagens.buscar_por_id(viagem_id) is None
    assert ListarViagens(viagens).execute(EDITOR) == []
    assert (uow.commits, uow.rollbacks) == (1, 0)


@pytest.mark.parametrize(
    ("usuario_id", "erro"),
    [(EDITOR, AcessoNegado), (VISUALIZADOR, AcessoNegado), (ESTRANHO, ViagemNaoEncontrada)],
)
def test_somente_criador_exclui(viagens, acesso, viagem_id, usuario_id, erro):
    uow = UnitOfWorkMemory()

    with pytest.raises(erro):
        ExcluirViagem(viagens, acesso, uow).execute(viagem_id, usuario_id)

    assert viagens.buscar_por_id(viagem_id) is not None
    assert uow.commits == 0


def test_falha_ao_excluir_desfaz_a_transacao(viagens, acesso, viagem_id):
    repository = Mock(wraps=viagens)
    repository.deletar.side_effect = RuntimeError("falha no banco")
    uow = UnitOfWorkMemory()

    with pytest.raises(RuntimeError):
        ExcluirViagem(repository, acesso, uow).execute(viagem_id, CRIADOR)

    assert (uow.commits, uow.rollbacks) == (0, 1)
