from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.application.use_cases.consultar_destinos_catalogo import (
    ConsultarDestinoCatalogo,
    ListarDestinosCatalogo,
)
from app.application.use_cases.importar_catalogo import ImportarCatalogo, LoteCatalogo
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.errors import DadosInvalidos, DestinoCatalogoNaoEncontrado


@pytest.fixture
def repository():
    repo = CatalogoRepositoryMemory()
    for nome, pais, categoria in [
        ("Lisboa", "PT", "cidade"),
        ("Porto", "PT", "cultural"),
        ("Florianópolis", "BR", "praia"),
        ("Serra 100%", "BR", "natureza"),
    ]:
        repo.salvar_destino(DestinoCatalogo(nome=nome, pais_codigo=pais, categoria=categoria))
    return repo


@pytest.mark.parametrize(
    ("filtros", "esperados"),
    [
        ({"nome": "LISBOA"}, ["Lisboa"]),
        ({"pais_codigo": "pt"}, ["Lisboa", "Porto"]),
        ({"categoria": "praia"}, ["Florianópolis"]),
        ({"nome": "serra", "pais_codigo": "br", "categoria": "natureza"}, ["Serra 100%"]),
        ({"nome": "%"}, ["Serra 100%"]),
        ({"nome": "_"}, []),
        ({"nome": "inexistente"}, []),
    ],
)
def test_busca_destinos(repository, filtros, esperados):
    resultado = ListarDestinosCatalogo(repository).execute(**filtros)
    obtidos = [d.nome for d in resultado.itens]
    assert obtidos == esperados


def test_paginas_destinos_sem_repeticao(repository):
    caso = ListarDestinosCatalogo(repository)
    primeira = caso.execute(tamanho_pagina=2)
    segunda = caso.execute(pagina=2, tamanho_pagina=2)
    ultima = caso.execute(pagina=3, tamanho_pagina=2)
    ids = [d.id for d in primeira.itens + segunda.itens]
    assert ids == [1, 2, 3, 4]
    assert primeira.tem_proxima is True
    assert segunda.tem_proxima is False
    assert ultima.itens == []
    assert ultima.tem_proxima is False


@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": 0},
        {"pagina": True},
        {"tamanho_pagina": 0},
        {"tamanho_pagina": 101},
        {"categoria": "hotel"},
        {"pais_codigo": "BRA"},
        {"pais_codigo": "12"},
        {"nome": "x" * 256},
    ],
)
def test_busca_invalida_nao_acessa_repositorio(filtros):
    repo = Mock()
    caso = ListarDestinosCatalogo(repo)
    with pytest.raises(DadosInvalidos):
        caso.execute(**filtros)
    repo.listar_destinos.assert_not_called()


def test_consultar_destino_e_inexistente(repository):
    caso = ConsultarDestinoCatalogo(repository)
    assert caso.execute(1).nome == "Lisboa"
    with pytest.raises(DestinoCatalogoNaoEncontrado):
        caso.execute(999)


def test_consulta_vazia_e_falha_de_persistencia():
    vazio = ListarDestinosCatalogo(CatalogoRepositoryMemory()).execute()
    assert vazio.itens == []
    assert vazio.tem_proxima is False
    repo = Mock()
    repo.listar_destinos.side_effect = RuntimeError("banco indisponível")
    caso = ListarDestinosCatalogo(repo)
    with pytest.raises(RuntimeError):
        caso.execute()


def test_importar_apenas_destinos():
    repo, uow = CatalogoRepositoryMemory(), UnitOfWorkMemory()
    destino = DestinoCatalogo(nome="Praia", pais_codigo="BR", categoria="praia")
    lote = LoteCatalogo({"praia": destino}, [])
    total_atividades = ImportarCatalogo(repo, uow).execute(lote)
    assert total_atividades == 0
    assert repo.buscar_destino(1).categoria.value == "praia"
    assert repo.atividades == {}
    assert uow.commits == 1


def test_lote_sem_destinos_nao_grava():
    repo = Mock()
    caso = ImportarCatalogo(repo, UnitOfWorkMemory())
    lote = LoteCatalogo({}, [])
    with pytest.raises(DadosInvalidos):
        caso.execute(lote)
    repo.salvar_destino.assert_not_called()
