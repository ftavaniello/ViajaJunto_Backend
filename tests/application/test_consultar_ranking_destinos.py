import pytest

from app.adapters.outbound.persistence.avaliacoes_destino_repository_memory import (
    AvaliacoesDestinoRepositoryMemory,
)
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.application.use_cases.consultar_ranking_destinos import ConsultarRankingDestinos
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.errors import DadosInvalidos


@pytest.fixture
def contexto():
    catalogo = CatalogoRepositoryMemory()
    lisboa = catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    rio = catalogo.salvar_destino(DestinoCatalogo(nome="Rio", pais_codigo="BR"))
    catalogo.salvar_destino(DestinoCatalogo(nome="Paris", pais_codigo="FR"))  # sem avaliações
    for destino, nome in ((lisboa, "Museu"), (lisboa, "Elétrico"), (rio, "Cristo")):
        catalogo.salvar_atividade(
            AtividadeCatalogo(destino=destino, nome=nome, categoria="passeio")
        )
    avaliacoes = AvaliacoesDestinoRepositoryMemory(catalogo)
    return ConsultarRankingDestinos(avaliacoes), avaliacoes


def nomes(ranking):
    return [i.destino.nome for i in ranking.itens]


def test_agrega_notas_de_todas_as_atividades_do_destino(contexto):
    caso, avaliacoes = contexto
    for atividade_id, nota in ((1, 5), (2, 3), (3, 4)):
        avaliacoes.avaliar(atividade_id, nota)

    ranking = caso.execute()

    lisboa = next(i for i in ranking.itens if i.destino.nome == "Lisboa")
    assert (lisboa.total_avaliacoes, str(lisboa.media_avaliacoes)) == (2, "4.00")
    assert "Paris" not in nomes(ranking)


def test_nova_avaliacao_atualiza_o_ranking(contexto):
    caso, avaliacoes = contexto
    avaliacoes.avaliar(1, 3)
    avaliacoes.avaliar(3, 4)
    assert nomes(caso.execute()) == ["Rio", "Lisboa"]

    for _ in range(3):
        avaliacoes.avaliar(2, 5)

    assert nomes(caso.execute()) == ["Lisboa", "Rio"]


@pytest.mark.parametrize("limite", [0, 51, -1, True, 1.5])
def test_limite_invalido(contexto, limite):
    caso, _ = contexto

    with pytest.raises(DadosInvalidos):
        caso.execute(limite)


def test_limite_restringe_quantidade(contexto):
    caso, avaliacoes = contexto
    avaliacoes.avaliar(1, 5)
    avaliacoes.avaliar(3, 4)

    assert nomes(caso.execute(1)) == ["Lisboa"]
