"""Curadoria manual de lugares reais; dados operacionais são ilustrativos.

Referências e limites: docs/seed-destinos-reais.md. Coordenadas representam
aproximadamente o centro da cidade, não a entrada de cada atração.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LugarSeed:
    chave: str
    nome: str
    pais: str
    latitude: str
    longitude: str
    descricao: str
    # Nome, categoria, área, descrição curta, duração ilustrativa em minutos.
    atividades: tuple[tuple[str, str, str, str, int], ...]


LUGARES_REAIS = (
    LugarSeed(
        "orlando",
        "Orlando",
        "US",
        "28.538300",
        "-81.379200",
        "Destino da Flórida para parques e passeios; inclui atrações da região de Orlando.",
        (
            (
                "Magic Kingdom Park",
                "lazer",
                "Walt Disney World Resort",
                "Parque temático na região de Orlando.",
                480,
            ),
            (
                "Universal Studios Florida",
                "lazer",
                "Universal Orlando Resort",
                "Parque temático do Universal Orlando Resort.",
                480,
            ),
            (
                "Disney Springs",
                "compras",
                "Lake Buena Vista",
                "Área de compras, gastronomia e entretenimento.",
                180,
            ),
            (
                "ICON Park",
                "lazer",
                "International Drive",
                "Complexo de entretenimento na região da International Drive.",
                120,
            ),
            (
                "East End Market",
                "alimentacao",
                "Audubon Park",
                "Mercado gastronômico no bairro Audubon Park.",
                90,
            ),
            (
                "Lake Eola Park",
                "outros",
                "Downtown Orlando",
                "Parque urbano ao redor do Lake Eola.",
                90,
            ),
        ),
    ),
    LugarSeed(
        "miami",
        "Miami",
        "US",
        "25.761700",
        "-80.191800",
        "Destino da Flórida com áreas culturais e parques urbanos; "
        "inclui praias da região de Miami Beach.",
        (
            (
                "Vizcaya Museum and Gardens",
                "cultura",
                "Coconut Grove",
                "Museu e jardins históricos junto à Biscayne Bay.",
                180,
            ),
            (
                "South Beach",
                "lazer",
                "Miami Beach",
                "Passeio pela região de praia de South Beach.",
                180,
            ),
            (
                "Bayside Marketplace",
                "compras",
                "Downtown Miami",
                "Área de lojas e restaurantes junto à baía.",
                120,
            ),
            (
                "Metromover",
                "transporte",
                "Downtown Miami",
                "Deslocamento pelo sistema elevado de transporte urbano.",
                45,
            ),
            (
                "Versailles Restaurant",
                "alimentacao",
                "Little Havana",
                "Restaurante de culinária cubana em Miami.",
                90,
            ),
            (
                "Bayfront Park",
                "outros",
                "Downtown Miami",
                "Parque urbano junto à Biscayne Bay.",
                90,
            ),
        ),
    ),
    LugarSeed(
        "rio",
        "Rio de Janeiro",
        "BR",
        "-22.906800",
        "-43.172900",
        "Cidade brasileira com paisagens de montanha, praias e patrimônio cultural.",
        (
            ("Cristo Redentor", "cultura", "Corcovado", "Monumento no alto do Corcovado.", 180),
            (
                "Pão de Açúcar",
                "lazer",
                "Urca",
                "Passeio pela região do Pão de Açúcar e seu bondinho.",
                180,
            ),
            (
                "Feira Hippie de Ipanema",
                "compras",
                "Praça General Osório",
                "Feira de artesanato e arte em Ipanema.",
                90,
            ),
            (
                "Confeitaria Colombo",
                "alimentacao",
                "Rua Gonçalves Dias, Centro",
                "Confeitaria histórica no centro da cidade.",
                90,
            ),
            (
                "Bonde de Santa Teresa",
                "transporte",
                "Santa Teresa",
                "Passeio de bonde pelo bairro de Santa Teresa.",
                60,
            ),
            (
                "Jardim Botânico do Rio de Janeiro",
                "outros",
                "Jardim Botânico",
                "Visita ao jardim botânico e suas coleções vegetais.",
                180,
            ),
        ),
    ),
    LugarSeed(
        "roma",
        "Roma",
        "IT",
        "41.902800",
        "12.496400",
        "Capital italiana com monumentos antigos, praças e parques históricos.",
        (
            (
                "Coliseu",
                "cultura",
                "Piazza del Colosseo",
                "Anfiteatro histórico da Roma antiga.",
                180,
            ),
            (
                "Fontana di Trevi",
                "lazer",
                "Piazza di Trevi",
                "Visita à fonte monumental no centro de Roma.",
                60,
            ),
            (
                "Via del Corso",
                "compras",
                "Centro histórico de Roma",
                "Passeio pela via comercial do centro histórico.",
                120,
            ),
            (
                "Trastevere",
                "alimentacao",
                "Trastevere",
                "Passeio gastronômico pelo bairro; não representa uma reserva.",
                120,
            ),
            (
                "Metrô de Roma",
                "transporte",
                "Roma",
                "Deslocamento urbano de metrô para o roteiro.",
                45,
            ),
            ("Villa Borghese", "outros", "Pinciano", "Passeio pelo parque e seus jardins.", 180),
        ),
    ),
)
