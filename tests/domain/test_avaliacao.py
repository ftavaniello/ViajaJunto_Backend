from types import SimpleNamespace

import pytest

from app.domain.entities.avaliacao import Avaliacao, exigir_realizacao
from app.domain.errors import AcessoNegado, DadosInvalidos


@pytest.mark.parametrize("nota", [0, 6, -1, True, False, 4.0, "5", None])
def test_nota_exige_inteiro_entre_um_e_cinco(nota):
    with pytest.raises(DadosInvalidos):
        Avaliacao(usuario_id=1, catalogo_atividade_id=2, atividade_viagem_id=3, nota=nota)


@pytest.mark.parametrize("nota", [1, 2, 3, 4, 5])
def test_nota_valida_e_normalizacao_de_comentario(nota):
    avaliacao = Avaliacao(
        usuario_id=1,
        catalogo_atividade_id=2,
        atividade_viagem_id=3,
        nota=nota,
        comentario="  Boa visita  ",
    )
    assert avaliacao.nota == nota
    assert avaliacao.comentario == "Boa visita"


@pytest.mark.parametrize("comentario", ["x" * 2001, 123, ["texto"]])
def test_comentario_invalido(comentario):
    with pytest.raises(DadosInvalidos):
        Avaliacao(
            usuario_id=1,
            catalogo_atividade_id=2,
            atividade_viagem_id=3,
            nota=5,
            comentario=comentario,
        )


@pytest.mark.parametrize("comentario", [None, "", "   "])
def test_comentario_opcional(comentario):
    avaliacao = Avaliacao(
        usuario_id=1, catalogo_atividade_id=2, atividade_viagem_id=3, nota=1, comentario=comentario
    )
    assert avaliacao.comentario is None


@pytest.mark.parametrize(
    "status,instante",
    [
        ("pendente", None),
        ("confirmada", None),
        ("cancelada", None),
        ("concluida", None),
    ],
)
def test_realizacao_exige_status_e_registro_de_conclusao(status, instante):
    with pytest.raises(AcessoNegado):
        exigir_realizacao(SimpleNamespace(status=status, realizada_em=instante))
