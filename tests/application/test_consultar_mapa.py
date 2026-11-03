from datetime import date
from decimal import Decimal

import pytest

from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.paradas_participante_repository_memory import (
    ParadasParticipanteRepositoryMemory,
)
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.consultar_mapa import ConsultarMapaViagem, ConsultarPaisesVisitados
from app.domain.entities.catalogo import DestinoCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, StatusViagem
from app.domain.errors import ViagemNaoEncontrada

HOJE = date(2026, 11, 3)
ANA, BRUNO, CARLA = 1, 2, 3


@pytest.fixture
def contexto():
    membros = MembroViagemRepositoryMemory()
    viagens = ViagemRepositoryMemory(membros)
    destinos = DestinoViagemRepositoryMemory()
    lisboa = DestinoCatalogo(
        id=1, nome="Lisboa", pais_codigo="PT", latitude=Decimal("38.7223"),
        longitude=Decimal("-9.1393"),
    )
    porto = DestinoCatalogo(id=2, nome="Porto", pais_codigo="PT")
    rio = DestinoCatalogo(id=3, nome="Rio", pais_codigo="BR")
    tokyo = DestinoCatalogo(id=4, nome="Tóquio", pais_codigo="JP")

    def viagem(criador, status, inicio, fim, paradas):
        v = viagens.salvar(
            Viagem(nome="V", criador_id=criador, data_inicio=inicio, data_fim=fim, status=status)
        )
        for ordem, (destino, chegada) in enumerate(paradas, start=1):
            destinos.salvar(
                DestinoViagem(
                    viagem_id=v.id, destino=destino, ordem=ordem,
                    data_chegada=chegada, data_saida=chegada,
                )
            )
        return v.id

    passada = viagem(ANA, StatusViagem.CONCLUIDA, date(2026, 1, 1), date(2026, 1, 20), [
        (lisboa, date(2026, 1, 2)), (porto, date(2026, 1, 10)),
    ])
    futura = viagem(ANA, StatusViagem.CONFIRMADA, date(2027, 3, 1), date(2027, 3, 10), [
        (tokyo, date(2027, 3, 2)),
    ])
    plano = viagem(ANA, StatusViagem.PLANEJANDO, date(2025, 1, 1), date(2025, 1, 5), [
        (rio, date(2025, 1, 2)),
    ])
    compartilhada = viagem(BRUNO, StatusViagem.CONCLUIDA, date(2025, 6, 1), date(2025, 6, 9), [
        (rio, date(2025, 6, 2)), (lisboa, date(2025, 6, 5)),
    ])
    membros.adicionar(compartilhada, ANA, PapelMembro.VISUALIZADOR)
    paises = ConsultarPaisesVisitados(
        ParadasParticipanteRepositoryMemory(viagens, destinos), hoje=lambda: HOJE
    )
    mapa = ConsultarMapaViagem(destinos, PoliticaAcessoViagem(viagens, membros))
    ids = {"passada": passada, "futura": futura, "plano": plano, "compartilhada": compartilhada}
    return paises, mapa, ids


def test_paises_do_usuario_aplicam_criterio_e_nao_repetem(contexto):
    paises, *_ = contexto

    resultado = paises.execute(ANA)

    # JP é viagem futura; o BR da viagem "planejando" só conta pela viagem compartilhada.
    assert [(p.pais_codigo, p.total_viagens) for p in resultado] == [("BR", 1), ("PT", 2)]
    pt = resultado[1]
    assert (pt.primeira_visita, pt.ultima_visita) == (date(2025, 6, 5), date(2026, 1, 10))


def test_cada_usuario_ve_somente_os_proprios_paises(contexto):
    paises, *_ = contexto

    assert [p.pais_codigo for p in paises.execute(BRUNO)] == ["BR", "PT"]
    assert paises.execute(CARLA) == []


def test_mapa_retorna_paradas_na_ordem_com_coordenadas(contexto):
    _, mapa, ids = contexto

    paradas = mapa.execute(ids["passada"], ANA)

    assert [(p.ordem, p.destino.nome) for p in paradas] == [(1, "Lisboa"), (2, "Porto")]
    assert paradas[0].destino.latitude == Decimal("38.7223")
    assert paradas[1].destino.latitude is None


def test_mapa_de_viagem_compartilhada_e_negado_a_quem_nao_participa(contexto):
    _, mapa, ids = contexto

    assert len(mapa.execute(ids["compartilhada"], ANA)) == 2
    with pytest.raises(ViagemNaoEncontrada):
        mapa.execute(ids["passada"], CARLA)
    with pytest.raises(ViagemNaoEncontrada):
        mapa.execute(999, ANA)
