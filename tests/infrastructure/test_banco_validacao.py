from unittest.mock import Mock

import pytest

from tests.support import banco_isolado as suporte


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg2://teste:teste@localhost/viajajunto",
        "sqlite:///:memory:",
    ],
)
def test_validador_recusa_destino_que_nao_e_postgresql_de_testes(monkeypatch, url):
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    fabrica = Mock()
    monkeypatch.setattr(suporte, "create_engine", fabrica)
    with pytest.raises(ValueError, match="_test"):
        with suporte.banco_isolado():
            pytest.fail("Não deve criar schema")
    fabrica.assert_not_called()
