from datetime import date, datetime

from app.domain.enums import StatusViagem
from app.domain.errors import DadosInvalidos
from app.domain.validation import validar_nome


class Viagem:
    def __init__(
        self,
        criador_id: int,
        nome: str,
        data_inicio: date,
        data_fim: date,
        descricao: str | None = None,
        status: StatusViagem | str = StatusViagem.PLANEJANDO,
        codigo_convite: str | None = None,
        codigo_convite_expira_em: datetime | None = None,
        id: int | None = None,
        criado_em: datetime | None = None,
        atualizado_em: datetime | None = None,
    ):
        validar_nome(nome)
        if not isinstance(data_inicio, date) or not isinstance(data_fim, date):
            raise DadosInvalidos("Datas de início e fim são obrigatórias")
        if data_fim < data_inicio:
            raise DadosInvalidos("Data de fim não pode ser anterior à data de início")
        try:
            status = StatusViagem(status)
        except ValueError as error:
            raise DadosInvalidos("Status de viagem inválido") from error

        self.id = id
        self.criador_id = criador_id
        self.nome = nome
        # Descricao vazia equivale a nao ter descricao.
        self.descricao = (descricao.strip() or None) if descricao is not None else None
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.status = status
        self.codigo_convite = codigo_convite
        self.codigo_convite_expira_em = codigo_convite_expira_em
        self.criado_em = criado_em
        self.atualizado_em = atualizado_em
