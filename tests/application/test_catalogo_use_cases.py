from unittest.mock import Mock

import pytest

from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.application.use_cases.consultar_catalogo import (
    ConsultarAtividadeCatalogo,
    ListarAtividadesCatalogo,
)
from app.application.use_cases.importar_catalogo import ImportarCatalogo, LoteCatalogo
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.errors import AtividadeCatalogoNaoEncontrada, DadosInvalidos


@pytest.fixture
def repository():
    repo = CatalogoRepositoryMemory()
    lisboa = repo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    porto = repo.salvar_destino(DestinoCatalogo(nome="Porto", pais_codigo="PT"))
    for nome, categoria, destino, endereco in [
        ("Museu Nacional", "cultura", lisboa, "Rua Azul"),
        ("Museu do Porto", "cultura", porto, None),
        ("Restaurante", "alimentacao", lisboa, "Rua Verde"),
        ("Passeio 100%", "lazer", lisboa, None),
    ]:
        repo.salvar_atividade(
            AtividadeCatalogo(
                destino=destino,
                nome=nome,
                categoria=categoria,
                endereco=endereco,
            )
        )
    return repo


@pytest.mark.parametrize(
    ("filtros", "nomes"),
    [
        ({"nome": "MUSEU"}, ["Museu Nacional", "Museu do Porto"]),
        ({"categoria": CategoriaAtividade.ALIMENTACAO}, ["Restaurante"]),
        ({"localizacao": "LISBOA", "nome": "museu"}, ["Museu Nacional"]),
        ({"localizacao": "azul"}, ["Museu Nacional"]),
        ({"destino_catalogo_id": 2}, ["Museu do Porto"]),
        ({"nome": "%"}, ["Passeio 100%"]),
        ({"nome": "inexistente"}, []),
    ],
)
def test_filtros(repository, filtros, nomes):
    resultado = ListarAtividadesCatalogo(repository).execute(**filtros)
    nomes_obtidos = [a.nome for a in resultado.itens]
    assert nomes_obtidos == nomes


def test_paginacao_estavel(repository):
    caso = ListarAtividadesCatalogo(repository)
    primeira = caso.execute(tamanho_pagina=2)
    segunda = caso.execute(pagina=2, tamanho_pagina=2)
    terceira = caso.execute(pagina=3, tamanho_pagina=2)
    assert [a.id for a in primeira.itens + segunda.itens] == [1, 2, 3, 4]
    assert primeira.tem_proxima is True
    assert segunda.tem_proxima is False
    assert terceira.itens == []
    assert terceira.tem_proxima is False


@pytest.mark.parametrize(
    "filtros",
    [
        {"pagina": 0},
        {"tamanho_pagina": 101},
        {"tamanho_pagina": 0},
        {"categoria": "invalida"},
        {"destino_catalogo_id": -1},
        {"nome": "x" * 256},
    ],
)
def test_filtros_invalidos_nao_consultam_porta(filtros):
    repo = Mock()
    caso_em_teste = ListarAtividadesCatalogo(repo)
    with pytest.raises(DadosInvalidos):
        caso_em_teste.execute(**filtros)
    repo.listar_atividades.assert_not_called()


def test_detalhe_e_inexistente(repository):
    caso = ConsultarAtividadeCatalogo(repository)
    assert caso.execute(1).nome == "Museu Nacional"
    with pytest.raises(AtividadeCatalogoNaoEncontrada):
        caso.execute(999)


def test_importacao_confirma_lote():
    repo, uow = CatalogoRepositoryMemory(), UnitOfWorkMemory()
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT")
    atividade = AtividadeCatalogo(destino=destino, nome="Museu", categoria="cultura")
    assert (
        ImportarCatalogo(repo, uow).execute(
            LoteCatalogo(
                {"lisboa": destino},
                [("lisboa", atividade)],
            )
        )
        == 1
    )
    assert repo.buscar_atividade(1).destino.id == 1
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_importacao_desfaz_em_falha():
    repo, uow = Mock(), UnitOfWorkMemory()
    repo.salvar_atividade.side_effect = RuntimeError("falha de persistência")
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT")
    atividade = AtividadeCatalogo(destino=destino, nome="Museu", categoria="cultura")
    caso_em_teste = ImportarCatalogo(repo, uow)
    entrada_teste_0 = LoteCatalogo({"lisboa": destino}, [("lisboa", atividade)])
    with pytest.raises(RuntimeError):
        caso_em_teste.execute(entrada_teste_0)
    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_destino_ausente_impede_importacao():
    repo, uow = Mock(), UnitOfWorkMemory()
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT")
    atividade = AtividadeCatalogo(destino=destino, nome="Museu", categoria="cultura")
    caso_em_teste = ImportarCatalogo(repo, uow)
    entrada_teste_0 = LoteCatalogo({"lisboa": destino}, [("porto", atividade)])
    with pytest.raises(DadosInvalidos):
        caso_em_teste.execute(entrada_teste_0)
    repo.salvar_destino.assert_not_called()


def test_falha_de_busca_nao_e_ocultada():
    repo = Mock()
    repo.listar_atividades.side_effect = RuntimeError("offline")
    caso_em_teste = ListarAtividadesCatalogo(repo)
    with pytest.raises(RuntimeError):
        caso_em_teste.execute()


@pytest.fixture
def lote_seed():
    destino = DestinoCatalogo(nome="Lisboa", pais_codigo="PT")
    atividade = AtividadeCatalogo(destino=destino, nome="Museu", categoria="cultura")
    return LoteCatalogo({"lisboa": destino}, [("lisboa", atividade)])


def test_seed_repetido_nao_duplica(lote_seed):
    repo, uow = CatalogoRepositoryMemory(), UnitOfWorkMemory()
    caso = ImportarCatalogo(repo, uow)
    assert caso.execute(lote_seed, apenas_se_vazio=True) == 1
    antes = (dict(repo.destinos), dict(repo.atividades))
    assert caso.execute(lote_seed, apenas_se_vazio=True) == 0
    assert (repo.destinos, repo.atividades) == antes
    assert uow.commits == 2


def test_seed_preserva_catalogo_existente(repository, lote_seed):
    antes = (dict(repository.destinos), dict(repository.atividades))
    assert (
        ImportarCatalogo(repository, UnitOfWorkMemory()).execute(
            lote_seed,
            apenas_se_vazio=True,
        )
        == 0
    )
    assert (repository.destinos, repository.atividades) == antes


def test_seed_nao_duplica_destinos_preexistentes(lote_seed):
    repo = CatalogoRepositoryMemory()
    destino = repo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
    assert (
        ImportarCatalogo(repo, UnitOfWorkMemory()).execute(
            lote_seed,
            apenas_se_vazio=True,
        )
        == 0
    )
    assert repo.destinos == {destino.id: destino}
    assert repo.atividades == {}


def test_seed_com_falha_nao_confirma(lote_seed):
    repo, uow = Mock(), UnitOfWorkMemory()
    repo.reservar_carga_inicial.return_value = True
    repo.salvar_atividade.side_effect = RuntimeError("falha no seed")
    caso_em_teste = ImportarCatalogo(repo, uow)
    with pytest.raises(RuntimeError):
        caso_em_teste.execute(lote_seed, apenas_se_vazio=True)
    assert (uow.commits, uow.rollbacks) == (0, 1)
