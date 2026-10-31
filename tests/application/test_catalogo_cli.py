import io
import json
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import ValidationError

from app.adapters.inbound.cli import importar_catalogo as cli
from app.domain.errors import DadosInvalidos


def lote_json():
    return json.dumps(
        {
            "destinos": {"cidade": {"nome": "Lisboa", "pais_codigo": "PT"}},
            "atividades": [{"destino": "cidade", "nome": "Museu", "categoria": "cultura"}],
        }
    )


def test_cli_recebe_json_pela_entrada_padrao(monkeypatch, capsys):
    caso = Mock()
    caso.execute.return_value = 1
    monkeypatch.setattr(cli.sys, "argv", ["importar_catalogo"])
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(lote_json()))
    monkeypatch.setattr(cli, "SessionLocal", MagicMock())
    monkeypatch.setattr(cli, "montar_importar_catalogo", Mock(return_value=caso))
    cli.main()
    lote = caso.execute.call_args.args[0]
    assert lote.atividades[0][1].nome == "Museu"
    assert caso.execute.call_args.kwargs == {"apenas_se_vazio": False}
    assert "1 atividade(s) importada(s)." in capsys.readouterr().out


def test_cli_seed_seleciona_apenas_exemplo_fixo(monkeypatch, capsys):
    caso = Mock()
    caso.execute.return_value = 0
    monkeypatch.setattr(cli.sys, "argv", ["importar_catalogo", "--se-vazio", "--exemplo"])
    monkeypatch.setattr(cli, "SessionLocal", MagicMock())
    monkeypatch.setattr(cli, "montar_importar_catalogo", Mock(return_value=caso))
    cli.main()
    assert len(caso.execute.call_args.args[0].atividades) == 2
    assert caso.execute.call_args.kwargs == {"apenas_se_vazio": True}
    assert "Seed ignorado" in capsys.readouterr().out


@pytest.mark.parametrize("caminho", ["../../.env", "/etc/passwd", "C:/Windows/win.ini"])
def test_cli_rejeita_caminhos_sem_abrir_banco(monkeypatch, caminho):
    sessao = Mock()
    monkeypatch.setattr(cli.sys, "argv", ["importar_catalogo", caminho])
    monkeypatch.setattr(cli, "SessionLocal", sessao)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    sessao.assert_not_called()


def test_cli_json_invalido_nao_invoca_caso_de_uso():
    caso = Mock()
    with pytest.raises(ValidationError):
        cli.importar_json("../../.env", caso)
    caso.execute.assert_not_called()


def test_cli_destino_ausente_nao_invoca_caso_de_uso():
    caso = Mock()
    conteudo = json.dumps(
        {
            "destinos": {},
            "atividades": [{"destino": "ausente", "nome": "Museu", "categoria": "cultura"}],
        }
    )
    with pytest.raises(DadosInvalidos):
        cli.importar_json(conteudo, caso)
    caso.execute.assert_not_called()
