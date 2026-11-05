from dataclasses import dataclass
from datetime import date

from app.domain.entities.catalogo import DestinoCatalogo, texto
from app.domain.errors import DadosInvalidos


@dataclass(frozen=True, kw_only=True)
class DestinoViagem:
    viagem_id: int
    destino: DestinoCatalogo
    ordem: int
    data_chegada: date
    data_saida: date
    descricao: str | None = None
    hospedagem: str | None = None
    id: int | None = None

    def __post_init__(self):
        if type(self.ordem) is not int or self.ordem < 1:
            raise DadosInvalidos("Ordem deve ser um inteiro positivo")
        if type(self.data_chegada) is not date or type(self.data_saida) is not date:
            raise DadosInvalidos("Datas de chegada e saída são obrigatórias")
        if self.data_saida < self.data_chegada:
            raise DadosInvalidos("Saída não pode ser anterior à chegada")
        object.__setattr__(self, "descricao", texto(self.descricao, "Descrição", 10000))
        object.__setattr__(self, "hospedagem", texto(self.hospedagem, "Hospedagem", 255))

    @property
    def destino_catalogo_id(self) -> int | None:
        return self.destino.id

    def validar_periodo(self, inicio: date, fim: date) -> None:
        if self.data_chegada < inicio or self.data_saida > fim:
            raise DadosInvalidos("O período do destino deve estar dentro das datas da viagem")


def validar_reordenacao(ids: list[int], destinos: list[DestinoViagem]) -> None:
    if any(type(id_) is not int for id_ in ids) or len(ids) != len(set(ids)):
        raise DadosInvalidos("A reordenação não pode conter IDs inválidos ou duplicados")
    if set(ids) != {destino.id for destino in destinos}:
        raise DadosInvalidos("Informe todos e somente os IDs dos destinos desta viagem")
