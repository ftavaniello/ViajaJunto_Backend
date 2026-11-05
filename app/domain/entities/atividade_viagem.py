from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from app.domain.entities.catalogo import AtividadeCatalogo
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.enums import StatusAtividade
from app.domain.errors import DadosInvalidos


@dataclass(frozen=True, kw_only=True)
class AtividadeViagem:
    viagem_id: int
    destino_viagem_id: int
    atividade: AtividadeCatalogo
    data: date
    hora_inicio: time | None = None
    duracao_minutos: int | None = None
    custo_previsto: Decimal = Decimal("0.00")
    status: StatusAtividade = StatusAtividade.PENDENTE
    realizada_em: datetime | None = None
    realizada_por_id: int | None = None
    id: int | None = None

    def __post_init__(self):
        if type(self.data) is not date:
            raise DadosInvalidos("Data da atividade é obrigatória")
        if self.hora_inicio is not None and (
            type(self.hora_inicio) is not time or self.hora_inicio.tzinfo is not None
        ):
            raise DadosInvalidos("Horário deve ser local, sem fuso")
        if self.duracao_minutos is not None and (
            type(self.duracao_minutos) is not int or not 1 <= self.duracao_minutos <= 2147483647
        ):
            raise DadosInvalidos("Duração deve ser um inteiro positivo de minutos")
        custo = self.custo_previsto
        if (
            not isinstance(custo, Decimal)
            or not custo.is_finite()
            or not (Decimal("0") <= custo <= Decimal("9999999999.99"))
        ):
            raise DadosInvalidos(
                "Custo deve ser um Decimal finito, não negativo e de até 12 dígitos"
            )
        if custo != custo.quantize(Decimal("0.01")):
            raise DadosInvalidos("Custo deve ter no máximo duas casas decimais")
        object.__setattr__(self, "custo_previsto", custo.quantize(Decimal("0.01")))
        try:
            object.__setattr__(self, "status", StatusAtividade(self.status))
        except (ValueError, TypeError) as error:
            raise DadosInvalidos("Status de atividade inválido") from error
        if self.status == StatusAtividade.CONCLUIDA and self.realizada_em is None:
            raise DadosInvalidos("Conclusão exige registro de data de comprovação")

    @property
    def catalogo_atividade_id(self) -> int | None:
        return self.atividade.id

    def validar_destino(self, destino: DestinoViagem) -> None:
        if (self.viagem_id, self.destino_viagem_id) != (destino.viagem_id, destino.id):
            raise DadosInvalidos("Atividade não pertence à parada informada")
        if self.atividade.destino.id != destino.destino_catalogo_id:
            raise DadosInvalidos("A atividade do catálogo deve pertencer ao destino da parada")
        if not destino.data_chegada <= self.data <= destino.data_saida:
            raise DadosInvalidos("Data da atividade deve estar dentro da estadia no destino")
