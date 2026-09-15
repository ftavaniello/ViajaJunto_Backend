import pytest

from app.domain.entities.usuario import Usuario


def test_cria_usuario_valido():
    usuario = Usuario(nome="Livia", email="livia@example.com", senha_hash="hash123")

    assert usuario.id is None
    assert usuario.nome == "Livia"
    assert usuario.email == "livia@example.com"
    assert usuario.senha_hash == "hash123"


@pytest.mark.parametrize(
    "nome,email,senha_hash",
    [
        ("", "livia@example.com", "hash123"),
        ("   ", "livia@example.com", "hash123"),
        ("Livia", "", "hash123"),
        ("Livia", "livia@example.com", ""),
    ],
)
def test_rejeita_campos_vazios(nome, email, senha_hash):
    with pytest.raises(ValueError):
        Usuario(nome=nome, email=email, senha_hash=senha_hash)
