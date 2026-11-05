from datetime import date

import pytest

from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, StatusViagem
from app.domain.errors import DadosInvalidos
from app.domain.permissoes import AcaoViagem, PerfilViagem, perfil_na_viagem, pode


def _viagem(**extra) -> Viagem:
    campos = {
        "criador_id": 1,
        "nome": "Europa",
        "data_inicio": date(2027, 7, 1),
        "data_fim": date(2027, 7, 20),
    }
    campos.update(extra)
    return Viagem(**campos)


def test_viagem_nova_comeca_em_planejamento():
    assert _viagem().status == StatusViagem.PLANEJANDO


def test_viagem_aceita_inicio_e_fim_no_mesmo_dia():
    viagem = _viagem(data_inicio=date(2027, 7, 1), data_fim=date(2027, 7, 1))

    assert viagem.data_inicio == viagem.data_fim


def test_viagem_rejeita_fim_antes_do_inicio():
    with pytest.raises(DadosInvalidos):
        _viagem(data_inicio=date(2027, 7, 20), data_fim=date(2027, 7, 1))


def test_viagem_rejeita_datas_ausentes():
    with pytest.raises(DadosInvalidos):
        _viagem(data_inicio=None)


def test_viagem_rejeita_nome_vazio():
    with pytest.raises(DadosInvalidos):
        _viagem(nome="   ")


@pytest.mark.parametrize("status", ["confirmada", StatusViagem.CONCLUIDA])
def test_viagem_aceita_status_do_rf07(status):
    assert _viagem(status=status).status == StatusViagem(status)


@pytest.mark.parametrize("status", ["em_andamento", "cancelada", "qualquer"])
def test_viagem_rejeita_status_fora_do_rf07(status):
    with pytest.raises(DadosInvalidos):
        _viagem(status=status)


def test_descricao_vazia_vira_nula():
    assert _viagem(descricao="  ").descricao is None


def test_perfil_do_criador_independe_de_ser_membro():
    assert perfil_na_viagem(1, 1, None) == PerfilViagem.CRIADOR


def test_perfil_de_colaborador_vem_do_papel():
    assert perfil_na_viagem(1, 2, PapelMembro.EDITOR) == PerfilViagem.EDITOR
    assert perfil_na_viagem(1, 2, PapelMembro.VISUALIZADOR) == PerfilViagem.VISUALIZADOR


def test_quem_nao_participa_nao_tem_perfil_nem_permissao():
    assert perfil_na_viagem(1, 2, None) is None
    assert not any(pode(None, acao) for acao in AcaoViagem)


@pytest.mark.parametrize(
    ("perfil", "permitidas"),
    [
        (PerfilViagem.CRIADOR, set(AcaoViagem)),
        (PerfilViagem.EDITOR, {AcaoViagem.CONSULTAR, AcaoViagem.EDITAR}),
        (PerfilViagem.VISUALIZADOR, {AcaoViagem.CONSULTAR}),
    ],
)
def test_matriz_de_permissoes(perfil, permitidas):
    assert {acao for acao in AcaoViagem if pode(perfil, acao)} == permitidas
