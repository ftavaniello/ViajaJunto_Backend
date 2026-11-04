"""Enriquecimento do catálogo por fornecedor externo, testado com um fornecedor falso."""
from dataclasses import replace
from decimal import Decimal

import pytest

from app.adapters.outbound.locais.provedor_locais_memory import ProvedorLocaisMemory
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.application.use_cases.enriquecer_catalogo import EnriquecerCatalogo
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade, FonteCatalogo
from app.domain.errors import (
    CredencialProvedorLocaisInvalida,
    DadosInvalidos,
    DestinoCatalogoNaoEncontrado,
    LimiteProvedorLocaisExcedido,
    ProvedorLocaisIndisponivel,
)
from app.domain.ports.provedor_locais import LocalExterno

CULTURA = CategoriaAtividade.CULTURA


def local(id_externo: str, nome: str, endereco: str | None = "Rua A, Orlando") -> LocalExterno:
    return LocalExterno(
        id_externo=id_externo,
        nome=nome,
        latitude=Decimal("28.538300"),
        longitude=Decimal("-81.379200"),
        endereco=endereco,
    )


@pytest.fixture
def contexto():
    catalogo = CatalogoRepositoryMemory()
    orlando = catalogo.salvar_destino(
        DestinoCatalogo(
            nome="Orlando",
            pais_codigo="US",
            latitude=Decimal("28.538336"),
            longitude=Decimal("-81.379234"),
        )
    )
    provedor = ProvedorLocaisMemory()
    provedor.locais[CULTURA] = [local("geo-1", "Museu de Arte"), local("geo-2", "Teatro")]
    uow = UnitOfWorkMemory()
    return EnriquecerCatalogo(catalogo, provedor, uow), catalogo, provedor, uow, orlando


def test_cria_atividades_ligadas_ao_destino_com_fonte_e_id_externo(contexto):
    caso, catalogo, provedor, uow, orlando = contexto

    resultado = caso.execute(orlando.id, "cultura", raio_metros=3_000, limite=10)

    assert (resultado.criadas, resultado.atualizadas, resultado.ignoradas) == (2, 0, 0)
    museu = catalogo.buscar_atividade_externa(FonteCatalogo.GEOAPIFY, "geo-1")
    assert museu.nome == "Museu de Arte"
    assert museu.destino.id == orlando.id
    assert museu.categoria == CULTURA
    assert museu.fonte == FonteCatalogo.GEOAPIFY
    assert museu.endereco == "Rua A, Orlando"
    # A busca usa as coordenadas do destino e os parâmetros pedidos.
    assert provedor.buscas == [(orlando.latitude, orlando.longitude, CULTURA, 3_000, 10)]
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_reexecutar_nao_duplica_e_atualiza_o_mesmo_registro(contexto):
    caso, catalogo, provedor, _, orlando = contexto
    caso.execute(orlando.id, CULTURA)
    id_original = catalogo.buscar_atividade_externa(FonteCatalogo.GEOAPIFY, "geo-1").id
    provedor.locais[CULTURA] = [local("geo-1", "Museu de Arte de Orlando", "Rua B")]

    resultado = caso.execute(orlando.id, CULTURA)

    assert (resultado.criadas, resultado.atualizadas) == (0, 1)
    assert len(catalogo.atividades) == 2
    atualizado = catalogo.buscar_atividade(id_original)
    assert atualizado.nome == "Museu de Arte de Orlando"
    assert atualizado.endereco == "Rua B"


def test_atualizacao_preserva_curadoria_categoria_e_destino(contexto):
    caso, catalogo, provedor, _, orlando = contexto
    caso.execute(orlando.id, CULTURA)
    museu = catalogo.buscar_atividade_externa(FonteCatalogo.GEOAPIFY, "geo-1")
    # A equipe curou a descrição, a foto e a categoria depois da importação.
    catalogo.atividades[museu.id] = replace(
        catalogo.atividades[museu.id],
        descricao="Texto da equipe",
        foto_url="https://example.com/museu.jpg",
        categoria=CategoriaAtividade.LAZER,
    )
    miami = catalogo.salvar_destino(
        DestinoCatalogo(
            nome="Miami", pais_codigo="US", latitude=Decimal("25.76"), longitude=Decimal("-80.19")
        )
    )

    caso.execute(miami.id, CULTURA)  # o mesmo local aparece buscando de outro destino

    atual = catalogo.buscar_atividade(museu.id)
    assert atual.descricao == "Texto da equipe"
    assert atual.foto_url == "https://example.com/museu.jpg"
    assert atual.categoria == CategoriaAtividade.LAZER
    assert atual.destino.id == orlando.id


def test_local_repetido_na_resposta_conta_uma_vez(contexto):
    caso, catalogo, provedor, _, orlando = contexto
    provedor.locais[CULTURA] = [local("geo-1", "Museu"), local("geo-1", "Museu (de novo)")]

    resultado = caso.execute(orlando.id, CULTURA)

    assert (resultado.criadas, resultado.atualizadas) == (1, 0)
    assert catalogo.buscar_atividade_externa(FonteCatalogo.GEOAPIFY, "geo-1").nome == "Museu"


def test_local_invalido_e_ignorado_sem_cancelar_o_lote(contexto):
    caso, catalogo, provedor, uow, orlando = contexto
    provedor.locais[CULTURA] = [local("geo-1", "Museu"), local("geo-2", "   ")]

    resultado = caso.execute(orlando.id, CULTURA)

    assert (resultado.criadas, resultado.ignoradas) == (1, 1)
    assert uow.commits == 1


def test_registro_manual_com_mesmo_id_externo_nao_e_tocado(contexto):
    caso, catalogo, _, _, orlando = contexto
    manual = catalogo.salvar_atividade(
        AtividadeCatalogo(destino=orlando, nome="Curado", categoria=CULTURA, id_externo="geo-1")
    )

    caso.execute(orlando.id, CULTURA)

    assert catalogo.buscar_atividade(manual.id).nome == "Curado"
    assert catalogo.buscar_atividade_externa(FonteCatalogo.GEOAPIFY, "geo-1").id != manual.id


@pytest.mark.parametrize(
    "falha",
    [
        ProvedorLocaisIndisponivel("Geoapify não respondeu em 10 s"),
        LimiteProvedorLocaisExcedido("Limite atingido", 60),
        CredencialProvedorLocaisInvalida("Chave recusada"),
    ],
    ids=["indisponivel", "limite", "credencial"],
)
def test_falha_do_fornecedor_nao_grava_nem_abre_transacao(contexto, falha):
    caso, catalogo, provedor, uow, orlando = contexto
    provedor.falha = falha

    with pytest.raises(type(falha)):
        caso.execute(orlando.id, CULTURA)

    assert catalogo.atividades == {}
    assert (uow.commits, uow.rollbacks) == (0, 0)


def test_falha_ao_gravar_desfaz_o_lote(contexto):
    caso, catalogo, _, uow, orlando = contexto
    salvar = catalogo.salvar_atividade
    gravadas = []

    def salvar_e_falhar(atividade):
        if gravadas:
            raise RuntimeError("banco indisponível")
        gravadas.append(salvar(atividade))
        return gravadas[-1]

    catalogo.salvar_atividade = salvar_e_falhar

    with pytest.raises(RuntimeError):
        caso.execute(orlando.id, CULTURA)

    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_destino_inexistente(contexto):
    caso, _, provedor, _, _ = contexto

    with pytest.raises(DestinoCatalogoNaoEncontrado):
        caso.execute(999, CULTURA)
    assert provedor.buscas == []


def test_destino_sem_coordenadas_nao_consulta_o_fornecedor(contexto):
    caso, catalogo, provedor, _, _ = contexto
    sem_mapa = catalogo.salvar_destino(DestinoCatalogo(nome="Sem mapa", pais_codigo="BR"))

    with pytest.raises(DadosInvalidos, match="latitude e longitude"):
        caso.execute(sem_mapa.id, CULTURA)
    assert provedor.buscas == []


@pytest.mark.parametrize(
    "parametros",
    [
        {"categoria": "inexistente"},
        {"raio_metros": 99},
        {"raio_metros": 50_001},
        {"limite": 0},
        {"limite": 101},
    ],
)
def test_parametros_invalidos_nao_consultam_o_fornecedor(contexto, parametros):
    caso, _, provedor, _, orlando = contexto

    with pytest.raises(DadosInvalidos):
        caso.execute(**{"destino_id": orlando.id, "categoria": CULTURA, **parametros})
    assert provedor.buscas == []
