"""Curadoria manual de lugares reais; dados operacionais são ilustrativos.

Referências e limites: docs/seed-demonstracao.md. Coordenadas representam
aproximadamente o centro da cidade, não a entrada de cada atração.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LugarSeed:
    chave: str
    nome: str
    # URL HTTP(S) externa; o sistema não armazena arquivos de imagem (D8).
    foto_url: str | None
    pais: str
    latitude: str
    longitude: str
    descricao: str
    # Nome, URL da foto, categoria, área, descrição curta, duração ilustrativa em minutos.
    atividades: tuple[tuple[str, str | None, str, str, str, int], ...]


LUGARES_REAIS = (
    LugarSeed(
        "orlando",
        "Orlando",
        "https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcRS4jUSQMdrj4BXXk-XTG0JHkdxxPyhvTh-2J7zB2y1hRCsk2TUb2Vn74LDkOfRSwSN9MQ8ZL-3cQX8ooc",  # noqa: E501
        "US",
        "28.538300",
        "-81.379200",
        "Destino da Flórida para parques e passeios; inclui atrações da região de Orlando.",
        (
            (
                "Magic Kingdom Park",
                "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9GcT-t0TyrJ29s6VU6igo8jMVZMSUZvgu5TGN-cA19GYrDql5hpn0y4xQ8UfeT5_LbDTAy9aUbLqHAk4svDs",  # noqa: E501
                "passeio",
                "Walt Disney World Resort",
                "Parque temático na região de Orlando.",
                480,
            ),
            (
                "Universal Studios Florida",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcR71hpbXyigfSIpfNZ40kWEtxj_Fpnkj7ujwyBsrugZvmYAyB2PN8NcSpJgfPSQ3zT8HT1O4gNDEzX__W0",  # noqa: E501
                "passeio",
                "Universal Orlando Resort",
                "Parque temático do Universal Orlando Resort.",
                480,
            ),
            (
                "Disney Springs",
                "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcR4fYpo6l3DaLU4X_HmkCmRehutCDyEAlIUfyRV5MqtAKzbYrQg4GTSdhemtKjcIot8F2eUAjZ5Zc6AMCk",  # noqa: E501
                "outro",
                "Lake Buena Vista",
                "Área de compras, gastronomia e entretenimento.",
                180,
            ),
            (
                "ICON Park",
                "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9GcRcjPN3LRweWifavM0TQZroYTJgkYRBkIf38pnrpDzsDBqKQk6bkrvwdI7ASmTNQgNt-svVuaSsNwVVZkQ",  # noqa: E501
                "passeio",
                "International Drive",
                "Complexo de entretenimento na região da International Drive.",
                120,
            ),
            (
                "East End Market",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcQl92pLVZ0iK9c4TYR0r3iT7FLt80V_ap6-V8btXDx4aPECyEJEA0XNb51Fgm_0hf0lU-_Yhbt24mr17Wk",  # noqa: E501
                "refeicao",
                "Audubon Park",
                "Mercado gastronômico no bairro Audubon Park.",
                90,
            ),
            (
                "Lake Eola Park",
                "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcQH6zWBvwul2O7smOOtevRb1OYx5DsvDwqd_OJ6N1xKsj2unON3-jV6DZbhjlAvU14CeKWSezyVvPbmrQU",  # noqa: E501
                "outro",
                "Downtown Orlando",
                "Parque urbano ao redor do Lake Eola.",
                90,
            ),
        ),
    ),
    LugarSeed(
        "miami",
        "Miami",
        "https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcTu6yRO92VM5JkHarTQb_SKyUoMsi9UyIDorNS86ERCzb4HxhP-W-YuAYS7UpBY0TJqv5JkhO6fv-Z4i4g",  # noqa: E501
        "US",
        "25.761700",
        "-80.191800",
        "Destino da Flórida com áreas culturais e parques urbanos; "
        "inclui praias da região de Miami Beach.",
        (
            (
                "Vizcaya Museum and Gardens",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcQAetXb5yOvw0WBKow3hX_NEBrsrNxuQH4yamessQWsIDpZjca1Mym6MFvJrwxZfeHgb-ylgxWk36LLr4k",  # noqa: E501
                "passeio",
                "Coconut Grove",
                "Museu e jardins históricos junto à Biscayne Bay.",
                180,
            ),
            (
                "South Beach",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcT3QVHesFenQUAIt5HgWK4O7iXiiyjXGwuFLdbE5Rh8FGxtlKtHfENixXodOC_9HaRoCSrY8I8gKeyOBxQ",  # noqa: E501
                "passeio",
                "Miami Beach",
                "Passeio pela região de praia de South Beach.",
                180,
            ),
            (
                "Bayside Marketplace",
                "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9GcT5R2yrCM7MWwzV9DmzjmlHEPvr3ZLpQXYCkrcBRiXLNBS7gII4F7Kxh4QPeniW1DiJU2XlZM0TssFOKL0",  # noqa: E501
                "outro",
                "Downtown Miami",
                "Área de lojas e restaurantes junto à baía.",
                120,
            ),
            (
                "Metromover",
                "https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcTmOHdhZsLBhlBjPDvxSvgv13YDzjTp3M4TJoPSct16rZTBqfrnUBSieEDMnhAs8DSj4Dsb1KPLa3gEc60",  # noqa: E501
                "transporte",
                "Downtown Miami",
                "Deslocamento pelo sistema elevado de transporte urbano.",
                45,
            ),
            (
                "Versailles Restaurant",
                "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcSm4OmMIzLkD49zlEnc9mskpqL8lcVTdzEwpIgxL-cJDNnPZctrZ8ZtmEbND-zJJH45rf3CjGktCfEaz6Y",  # noqa: E501
                "refeicao",
                "Little Havana",
                "Restaurante de culinária cubana em Miami.",
                90,
            ),
            (
                "Bayfront Park",
                "https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcTM9uzusTIvIoZWB27fhkdVHdsABuv05zh8RfXB9IXT2m4RHCOX-2foIHJKT_cl9XdvZr1wH4tUZ8A1sRg",  # noqa: E501
                "outro",
                "Downtown Miami",
                "Parque urbano junto à Biscayne Bay.",
                90,
            ),
        ),
    ),
    LugarSeed(
        "rio",
        "Rio de Janeiro",
        "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRfX_9u6fzIcxSlIP5ZmM1IavY-vmkD_IaxWB0SEGLVBOC5H3fd3mWBvO3L56mw1klptcbKNHn2Gr19pgU",  # noqa: E501
        "BR",
        "-22.906800",
        "-43.172900",
        "Cidade brasileira com paisagens de montanha, praias e patrimônio cultural.",
        (
            (
                "Cristo Redentor",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRfX_9u6fzIcxSlIP5ZmM1IavY-vmkD_IaxWB0SEGLVBOC5H3fd3mWBvO3L56mw1klptcbKNHn2Gr19pgU",  # noqa: E501
                "passeio",
                "Corcovado",
                "Monumento no alto do Corcovado.",
                180,
            ),
            (
                "Pão de Açúcar",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRsQ7cbeYKeQuiNQaDympVBuuxVxieSG6rzHCvpEARWpDQsM4jlL9IomdWbqOIz_hj5Ewil8Eq47L7YJro",  # noqa: E501
                "passeio",
                "Urca",
                "Passeio pela região do Pão de Açúcar e seu bondinho.",
                180,
            ),
            (
                "Feira Hippie de Ipanema",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcQ0UoFF_oX7MNUqgYVtcdu8O4QjnMmHKzF8zJ472yzT4FQTg6X4hRI85Pr3soStPljS0qo0a2VAdSzkw1E",  # noqa: E501
                "outro",
                "Praça General Osório",
                "Feira de artesanato e arte em Ipanema.",
                90,
            ),
            (
                "Confeitaria Colombo",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcQIgcWTIPFsxuL050eHB3svgzOAx6Gf9hAWky1jPIvx6p8zJN1XNGSjihRj-aH355rUPwt6aQ7VmLljQ1g",  # noqa: E501
                "refeicao",
                "Rua Gonçalves Dias, Centro",
                "Confeitaria histórica no centro da cidade.",
                90,
            ),
            (
                "Bonde de Santa Teresa",
                "https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcSgeu8-eZ-YZfJNjMPV7MzKHhV30vlyfs5KRtRw-UZ6VP8494rZuTHZ_BuddEaI2vbuqdopo-UnNkp218w",  # noqa: E501
                "transporte",
                "Santa Teresa",
                "Passeio de bonde pelo bairro de Santa Teresa.",
                60,
            ),
            (
                "Jardim Botânico do Rio de Janeiro",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRH9YHPk3jTshA8wvzFL_bAcJgpnd7G2nKhd8uVnUO2F1Zbivzv3mjjZKhId8O1r1K1uAZXX-PcAmVf3Ks",  # noqa: E501
                "outro",
                "Jardim Botânico",
                "Visita ao jardim botânico e suas coleções vegetais.",
                180,
            ),
        ),
    ),
    LugarSeed(
        "roma",
        "Roma",
        "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRcKZc5vmXDH3fI3cLjDIUK_DdcjCpmdGsr0qRDVZ1tmc0QxMBNSZPmCtgsDwGSrHqGu6DmNKsyC_UZqGU",  # noqa: E501
        "IT",
        "41.902800",
        "12.496400",
        "Capital italiana com monumentos antigos, praças e parques históricos.",
        (
            (
                "Coliseu",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcRcKZc5vmXDH3fI3cLjDIUK_DdcjCpmdGsr0qRDVZ1tmc0QxMBNSZPmCtgsDwGSrHqGu6DmNKsyC_UZqGU",  # noqa: E501
                "passeio",
                "Piazza del Colosseo",
                "Anfiteatro histórico da Roma antiga.",
                180,
            ),
            (
                "Fontana di Trevi",
                "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9GcR9xu-8dpvutL6mxVdv9D89GXuX383RNOu5BEdury49KfsBGGpxv3FMT4RA0OpPEXY-7anmAcuCQ4xcqws",  # noqa: E501
                "passeio",
                "Piazza di Trevi",
                "Visita à fonte monumental no centro de Roma.",
                60,
            ),
            (
                "Via del Corso",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcSi2ySVhCx9Mn3vI8ftLA40PC7JVM1xA7yFGh8GHYT_S7QS5TGR-FvF2tuPeMB0MPNomxLqNZP2hzHkZhc",  # noqa: E501
                "outro",
                "Centro histórico de Roma",
                "Passeio pela via comercial do centro histórico.",
                120,
            ),
            (
                "Trastevere",
                "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcS7NQ5DgdStpCv3ovsRe4KTxeVOIJWAJrmUJ6-kqcTihe68Qy91refuhOqXgC-Hbf3h8eS6C6w7L8i3ggs",  # noqa: E501
                "refeicao",
                "Trastevere",
                "Passeio gastronômico pelo bairro; não representa uma reserva.",
                120,
            ),
            (
                "Metrô de Roma",
                "https://encrypted-tbn3.gstatic.com/licensed-image?q=tbn:ANd9GcS9ONxzRFehR2EY9uwt5tdK4zCmt4k0OGmWKXMbFdA3Geq_WMERK8VzB6VfkNS3v4pmiz99dZTF8riih7Y",  # noqa: E501
                "transporte",
                "Roma",
                "Deslocamento urbano de metrô para o roteiro.",
                45,
            ),
            (
                "Villa Borghese",
                "https://encrypted-tbn1.gstatic.com/licensed-image?q=tbn:ANd9GcSD-8qrlhkL0FjTaocXd8igt-vTDPozTS1uWSc_3SFFW89_LGO2gFT-JYCXGElqoxBdSRYwqWWxbSXcEdA",  # noqa: E501
                "outro",
                "Pinciano",
                "Passeio pelo parque e seus jardins.",
                180,
            ),
        ),
    ),
)
