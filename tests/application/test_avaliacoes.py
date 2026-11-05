from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.avaliacao_repository_memory import AvaliacaoRepositoryMemory
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import UsuarioRepositoryMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.avaliar_atividade_viagem import AvaliarAtividadeViagem
from app.application.use_cases.consultar_catalogo import (
    ConsultarAtividadeCatalogo,
    ListarAtividadesCatalogo,
)
from app.domain.entities.atividade_viagem import AtividadeViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.usuario import Usuario
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro
from app.domain.errors import (
    AcessoNegado,
    AtividadeViagemNaoEncontrada,
    DadosInvalidos,
    ViagemNaoEncontrada,
)


@pytest.fixture
def contexto():
    usuarios, membros = UsuarioRepositoryMemory(), MembroViagemRepositoryMemory()
    for nome in ("criador", "editor", "visualizador", "externo"):
        usuarios.salvar(Usuario(nome=nome, email=f"{nome}@example.com", senha_hash="hash"))
    avaliacoes = AvaliacaoRepositoryMemory(usuarios)
    catalogo = CatalogoRepositoryMemory(avaliacoes)
    lugar = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    atividade = catalogo.salvar_atividade(
        AtividadeCatalogo(destino=lugar, nome="Museu", categoria="passeio")
    )
    catalogo.salvar_atividade(
        AtividadeCatalogo(destino=lugar, nome="Sem reviews", categoria="passeio")
    )
    viagens = ViagemRepositoryMemory(membros)
    viagens.salvar(
        Viagem(
            criador_id=1, nome="Viagem", data_inicio=date(2027, 1, 1), data_fim=date(2027, 1, 10)
        )
    )
    membros.adicionar(1, 2, PapelMembro.EDITOR)
    membros.adicionar(1, 3, PapelMembro.VISUALIZADOR)
    atividades, destinos, uow = (
        AtividadeViagemRepositoryMemory(),
        DestinoViagemRepositoryMemory(),
        UnitOfWorkMemory(),
    )
    atividades.salvar(
        AtividadeViagem(
            viagem_id=1,
            destino_viagem_id=1,
            atividade=atividade,
            data=date(2027, 1, 2),
            status="concluida",
            realizada_em=datetime.now(timezone.utc),
            realizada_por_id=1,
        )
    )
    caso = AvaliarAtividadeViagem(
        atividades, destinos, PoliticaAcessoViagem(viagens, membros), avaliacoes, uow
    )
    return caso, atividades, avaliacoes, catalogo, uow


@pytest.mark.parametrize("usuario_id", [1, 2, 3])
def test_participantes_avaliam_inclusive_visualizador(contexto, usuario_id):
    caso, _, _, _, uow = contexto
    review = caso.execute(1, 1, 1, usuario_id, 4)
    assert review.autor_nome in ("criador", "editor", "visualizador")
    assert review.nota == 4
    assert uow.commits == 1


def test_nao_participante_nao_avalia(contexto):
    caso, _, avaliacoes, _, uow = contexto
    with pytest.raises(ViagemNaoEncontrada):
        caso.execute(1, 1, 1, 4, 5)
    assert avaliacoes.reviews == {}
    assert uow.commits == 0


@pytest.mark.parametrize("status", ["pendente", "confirmada", "cancelada"])
def test_nao_concluida_nao_avalia(contexto, status):
    caso, atividades, _, _, uow = contexto
    atividades.salvar(replace(atividades.buscar(1, 1, 1), status=status, realizada_em=None))
    with pytest.raises(AcessoNegado):
        caso.execute(1, 1, 1, 1, 5)
    assert uow.commits == 0


def test_contexto_cruzado_nao_avalia(contexto):
    caso = contexto[0]
    with pytest.raises(AtividadeViagemNaoEncontrada):
        caso.execute(1, 2, 1, 1, 5)


def test_repeticao_por_outra_ocorrencia_atualiza_mesma_avaliacao(contexto):
    caso, atividades, avaliacoes, catalogo, _ = contexto
    primeiro = caso.execute(1, 1, 1, 1, 5, "Bom")
    outra = atividades.salvar(replace(atividades.buscar(1, 1, 1), id=None))
    segundo = caso.execute(1, 1, outra.id, 1, 3)
    assert primeiro.id == segundo.id
    assert primeiro.criado_em == segundo.criado_em
    assert segundo.comentario is None
    assert len(avaliacoes.reviews) == 1
    assert catalogo.buscar_atividade(1).media_avaliacoes == 3


def test_media_filtro_inclusivo_e_detalhe(contexto):
    caso, _, avaliacoes, catalogo, _ = contexto
    caso.execute(1, 1, 1, 1, 5)
    caso.execute(1, 1, 1, 2, 4)
    consulta = ListarAtividadesCatalogo(catalogo)
    assert [a.id for a in consulta.execute(nota_minima=Decimal("4.5")).itens] == [1]
    assert consulta.execute(nota_minima=Decimal("4.51")).itens == []
    detalhe = ConsultarAtividadeCatalogo(catalogo, avaliacoes).execute(1)
    assert detalhe.atividade.total_avaliacoes == 2
    assert detalhe.atividade.media_avaliacoes == Decimal("4.5")
    assert [r.nota for r in detalhe.reviews] == [4, 5]
    pagina = ConsultarAtividadeCatalogo(catalogo, avaliacoes).listar_avaliacoes(1, tamanho_pagina=1)
    assert pagina.tem_proxima
    assert pagina.itens[0].nota == 4


@pytest.mark.parametrize("nota", [True, "4", float("nan"), float("inf"), Decimal("NaN"), 0, 6])
def test_filtro_invalido_nao_chama_porta(nota):
    repo = Mock()
    with pytest.raises(DadosInvalidos):
        ListarAtividadesCatalogo(repo).execute(nota_minima=nota)
    repo.listar_atividades.assert_not_called()


def test_falha_persistencia_nao_confirma(contexto):
    caso, _, _, _, uow = contexto
    caso.avaliacoes = Mock()
    caso.avaliacoes.salvar.side_effect = RuntimeError("Falha")
    with pytest.raises(RuntimeError):
        caso.execute(1, 1, 1, 1, 5)
    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_cache_invalidado_somente_depois_do_commit(contexto):
    caso, _, _, _, uow = contexto
    caso.cache = Mock()
    caso.cache.invalidar.side_effect = lambda: (
        pytest.fail("Invalidou antes do commit") if uow.commits == 0 else None
    )
    caso.execute(1, 1, 1, 1, 5)
    caso.cache.invalidar.assert_called_once()


def test_falha_commit_nao_invalida_cache(contexto, monkeypatch):
    caso, _, _, _, uow = contexto
    caso.cache = Mock()

    def falhar():
        raise RuntimeError("commit falhou")

    monkeypatch.setattr(uow, "commit", falhar)
    with pytest.raises(RuntimeError, match="commit falhou"):
        caso.execute(1, 1, 1, 1, 5)
    caso.cache.invalidar.assert_not_called()
