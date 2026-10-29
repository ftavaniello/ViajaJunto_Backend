"""Vocabulário fechado do domínio.

Os valores aqui são os mesmos gravados no banco (colunas texto com CHECK) e
expostos na API. Ver docs/decisoes-de-produto.md.
"""

from enum import StrEnum


class PapelMembro(StrEnum):
    """Papel de um colaborador na viagem.

    O criador não é um membro: ele é identificado por `viagem.criador_id`.
    """

    EDITOR = "editor"
    VISUALIZADOR = "visualizador"


class StatusViagem(StrEnum):
    """Status definido pelos participantes (RF07); qualquer transição é permitida."""

    PLANEJANDO = "planejando"
    CONFIRMADA = "confirmada"
    CONCLUIDA = "concluida"


class StatusAtividade(StrEnum):
    PLANEJADA = "planejada"
    REALIZADA = "realizada"
    CANCELADA = "cancelada"


class CategoriaAtividade(StrEnum):
    ALIMENTACAO = "alimentacao"
    TRANSPORTE = "transporte"
    CULTURA = "cultura"
    LAZER = "lazer"
    COMPRAS = "compras"
    OUTROS = "outros"


class TipoNotificacao(StrEnum):
    MEMBRO_ENTROU = "membro_entrou"
    PAPEL_ALTERADO = "papel_alterado"
    MEMBRO_REMOVIDO = "membro_removido"
    VIAGEM_EXCLUIDA = "viagem_excluida"
