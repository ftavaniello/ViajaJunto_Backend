from dataclasses import replace
from datetime import date
from decimal import Decimal

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
from app.adapters.outbound.persistence.orcamento_repository_memory import (
    OrcamentoRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_orcamento_viagem import GerenciarOrcamentoViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, StatusAtividade
from app.domain.errors import AcessoNegado, DadosInvalidos, ViagemNaoEncontrada

CRIADOR, EDITOR, VISUALIZADOR, ESTRANHO = 1, 2, 3, 4


@pytest.fixture
def contexto():
    membros = MembroViagemRepositoryMemory()
    viagens = ViagemRepositoryMemory(membros)
    for nome in ("Europa", "Outra"):
        viagens.salvar(
            Viagem(
                nome=nome,
                criador_id=CRIADOR,
                data_inicio=date(2027, 7, 1),
                data_fim=date(2027, 7, 20),
            )
        )
    membros.adicionar(1, EDITOR, PapelMembro.EDITOR)
    membros.adicionar(1, VISUALIZADOR, PapelMembro.VISUALIZADOR)
    catalogo = CatalogoRepositoryMemory()
    lisboa = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    catalogo.salvar_atividade(AtividadeCatalogo(destino=lisboa, nome="Museu", categoria="cultura"))
    catalogo.salvar_atividade(AtividadeCatalogo(destino=lisboa, nome="Barco", categoria="lazer"))
    destinos = DestinoViagemRepositoryMemory()
    for viagem_id in (1, 2):
        destinos.salvar(
            DestinoViagem(
                viagem_id=viagem_id,
                destino=lisboa,
                ordem=1,
                data_chegada=date(2027, 7, 2),
                data_saida=date(2027, 7, 5),
            )
        )
    acesso = PoliticaAcessoViagem(viagens, membros)
    atividades = AtividadeViagemRepositoryMemory()
    orcamentos = OrcamentoRepositoryMemory(atividades)
    uow = UnitOfWorkMemory()
    roteiro = GerenciarAtividadesViagem(atividades, destinos, catalogo, acesso, UnitOfWorkMemory())
    return GerenciarOrcamentoViagem(orcamentos, acesso, uow), roteiro, atividades, uow


def adicionar(roteiro, custo, catalogo_id=1, viagem_id=1):
    return roteiro.criar(
        viagem_id=viagem_id,
        destino_id=viagem_id,
        usuario_id=CRIADOR,
        catalogo_atividade_id=catalogo_id,
        data=date(2027, 7, 3),
        custo_previsto=Decimal(custo),
    )


def por_categoria(resumo):
    return {c.categoria.value: c for c in resumo.categorias}


def test_viagem_sem_orcamento_nem_atividades(contexto):
    caso, *_ = contexto

    resumo = caso.consultar_resumo(1, CRIADOR)

    assert resumo.orcamento_total is None
    assert resumo.total_planejado == Decimal("0.00")
    assert resumo.saldo_disponivel is None


@pytest.mark.parametrize("usuario", [CRIADOR, EDITOR])
def test_criador_e_editor_definem_orcamento(contexto, usuario):
    caso, roteiro, _, uow = contexto
    adicionar(roteiro, "200", catalogo_id=1)
    adicionar(roteiro, "100", catalogo_id=2)

    resumo = caso.definir(1, usuario, Decimal("1000"))

    assert (resumo.orcamento_total, resumo.total_planejado, resumo.saldo_disponivel) == (
        Decimal("1000.00"),
        Decimal("300.00"),
        Decimal("700.00"),
    )
    assert por_categoria(resumo)["cultura"].percentual_orcamento == Decimal("20.00")
    assert por_categoria(resumo)["lazer"].percentual_planejado == Decimal("33.33")
    assert uow.commits == 1


def test_orcamento_e_unico_e_editavel(contexto):
    caso, *_ = contexto
    caso.definir(1, CRIADOR, Decimal("1000"))

    caso.definir(1, EDITOR, Decimal("1500.50"))

    assert caso.consultar_resumo(1, VISUALIZADOR).orcamento_total == Decimal("1500.50")
    assert list(caso.repository.orcamentos) == [1]


def test_orcamentos_e_custos_sao_isolados_por_viagem(contexto):
    caso, roteiro, *_ = contexto
    adicionar(roteiro, "50")
    adicionar(roteiro, "999", viagem_id=2)
    caso.definir(2, CRIADOR, Decimal("10"))

    resumo = caso.consultar_resumo(1, CRIADOR)

    assert resumo.orcamento_total is None
    assert resumo.total_planejado == Decimal("50.00")


def test_visualizador_consulta_mas_nao_edita(contexto):
    caso, _, _, uow = contexto
    caso.definir(1, CRIADOR, Decimal("100"))

    assert caso.consultar_resumo(1, VISUALIZADOR).orcamento_total == Decimal("100.00")
    with pytest.raises(AcessoNegado):
        caso.definir(1, VISUALIZADOR, Decimal("1"))
    assert caso.consultar_resumo(1, CRIADOR).orcamento_total == Decimal("100.00")
    assert uow.rollbacks == 1


def test_estranho_nao_ve_nem_edita(contexto):
    caso, *_ = contexto

    with pytest.raises(ViagemNaoEncontrada):
        caso.consultar_resumo(1, ESTRANHO)
    with pytest.raises(ViagemNaoEncontrada):
        caso.definir(1, ESTRANHO, Decimal("1"))
    with pytest.raises(ViagemNaoEncontrada):
        caso.consultar_resumo(99, CRIADOR)


def test_valor_invalido_nao_grava(contexto):
    caso, _, _, uow = contexto

    with pytest.raises(DadosInvalidos):
        caso.definir(1, CRIADOR, Decimal("-1"))
    assert caso.consultar_resumo(1, CRIADOR).orcamento_total is None
    assert uow.commits == 0


def test_resumo_reflete_inclusao_edicao_e_remocao_de_atividades(contexto):
    caso, roteiro, *_ = contexto
    caso.definir(1, CRIADOR, Decimal("1000"))

    museu = adicionar(roteiro, "300")
    assert caso.consultar_resumo(1, CRIADOR).saldo_disponivel == Decimal("700.00")

    roteiro.atualizar(1, 1, museu.id, EDITOR, custo_previsto=Decimal("450.25"))
    resumo = caso.consultar_resumo(1, CRIADOR)
    assert resumo.saldo_disponivel == Decimal("549.75")
    assert por_categoria(resumo)["cultura"].total_planejado == Decimal("450.25")

    roteiro.remover(1, 1, museu.id, EDITOR)
    resumo = caso.consultar_resumo(1, CRIADOR)
    assert resumo.total_planejado == Decimal("0.00")
    assert resumo.saldo_disponivel == Decimal("1000.00")


def test_atividades_canceladas_legadas_nao_entram_no_total(contexto):
    caso, roteiro, atividades, _ = contexto
    legada = adicionar(roteiro, "80")
    atividades.salvar(replace(legada, status=StatusAtividade.CANCELADA))
    adicionar(roteiro, "20", catalogo_id=2)

    assert caso.consultar_resumo(1, CRIADOR).total_planejado == Decimal("20.00")


def test_estouro_e_orcamento_zero(contexto):
    caso, roteiro, *_ = contexto
    adicionar(roteiro, "150")

    resumo = caso.definir(1, CRIADOR, Decimal("100"))
    assert resumo.saldo_disponivel == Decimal("-50.00")
    assert resumo.orcamento_excedido is True

    resumo = caso.definir(1, CRIADOR, Decimal("0"))
    assert resumo.orcamento_total == Decimal("0.00")
    assert resumo.percentual_consumido is None
    assert resumo.orcamento_excedido is True
