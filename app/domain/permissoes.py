"""Matriz de permissões por viagem (RN06 / RNF03).

Fonte única de "quem pode o quê" numa viagem; os casos de uso consultam esta
matriz por meio de `PoliticaAcessoViagem` em vez de repetir a regra.
"""

from enum import StrEnum

from app.domain.enums import PapelMembro


class PerfilViagem(StrEnum):
    """Relação do usuário com a viagem: o criador ou o papel de colaborador."""

    CRIADOR = "criador"
    EDITOR = PapelMembro.EDITOR.value
    VISUALIZADOR = PapelMembro.VISUALIZADOR.value


class AcaoViagem(StrEnum):
    CONSULTAR = "consultar"
    EDITAR = "editar"  # dados gerais, status e planejamento (destinos, atividades, orçamento)
    EXCLUIR = "excluir"
    GERENCIAR_MEMBROS = "gerenciar_membros"


PERMISSOES: dict[PerfilViagem, frozenset[AcaoViagem]] = {
    PerfilViagem.CRIADOR: frozenset(AcaoViagem),
    PerfilViagem.EDITOR: frozenset({AcaoViagem.CONSULTAR, AcaoViagem.EDITAR}),
    PerfilViagem.VISUALIZADOR: frozenset({AcaoViagem.CONSULTAR}),
}


def perfil_na_viagem(
    criador_id: int, usuario_id: int, papel_membro: PapelMembro | None
) -> PerfilViagem | None:
    """Perfil do usuário na viagem, ou None se ele não participa dela."""
    if usuario_id == criador_id:
        return PerfilViagem.CRIADOR
    if papel_membro is None:
        return None
    return PerfilViagem(papel_membro.value)


def pode(perfil: PerfilViagem | None, acao: AcaoViagem) -> bool:
    return perfil is not None and acao in PERMISSOES[perfil]
