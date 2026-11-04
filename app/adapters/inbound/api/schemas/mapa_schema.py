from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PaisVisitadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    pais_codigo: str = Field(
        description="ISO 3166-1 alfa-2 em maiúsculas, o código de região usado pelo jsVectorMap.",
        examples=["BR"],
    )
    primeira_visita: date = Field(description="Menor data de chegada entre as paradas no país.")
    ultima_visita: date = Field(description="Maior data de chegada já ocorrida no país.")
    total_viagens: int = Field(description="Viagens distintas com visita ao país.")


class PaisesVisitadosResponse(BaseModel):
    total: int
    paises: list[PaisVisitadoResponse] = Field(
        description="Sem repetição, ordenados pelo código do país."
    )


class PontoMapaResponse(BaseModel):
    parada_id: int = Field(description="ID da parada no roteiro (`destino_id` das rotas).")
    destino_catalogo_id: int
    ordem: int = Field(description="Posição na ordem de visita, a partir de 1.")
    nome: str
    pais_codigo: str
    latitude: float | None = Field(description="Graus decimais (WGS 84); nulo se desconhecida.")
    longitude: float | None = Field(description="Graus decimais (WGS 84); nulo se desconhecida.")
    data_chegada: date
    data_saida: date


class MapaViagemResponse(BaseModel):
    viagem_id: int
    paradas: list[PontoMapaResponse] = Field(
        description="Na ordem de visita (ordem e id). Ligue os pontos com coordenadas, "
        "nessa sequência, para desenhar o roteiro."
    )
