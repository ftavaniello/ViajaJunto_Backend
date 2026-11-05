from tests.support.verificar_ci import auditar


def test_relatorio_sem_modulo_ou_com_skip_falha(tmp_path):
    relatorio = tmp_path / "junit.xml"
    relatorio.write_text(
        '<testsuite><testcase classname="tests.integration.test_a" '
        'name="caso"><skipped/></testcase></testsuite>'
    )
    erros = auditar(relatorio, {"tests.integration.test_a", "tests.integration.test_b"})
    assert len(erros) == 2
    assert any("não executado" in e for e in erros)
    assert any("ignorada" in e for e in erros)


def test_relatorio_com_falha_nao_e_aprovado(tmp_path):
    relatorio = tmp_path / "junit.xml"
    relatorio.write_text(
        '<testsuite><testcase classname="tests.integration.test_a" '
        'name="caso"><error/></testcase></testsuite>'
    )
    assert auditar(relatorio, {"tests.integration.test_a"})


def test_relatorio_com_todos_os_modulos_executados(tmp_path):
    relatorio = tmp_path / "junit.xml"
    relatorio.write_text(
        '<testsuite><testcase classname="tests.integration.test_a" name="caso"/></testsuite>'
    )
    assert auditar(relatorio, {"tests.integration.test_a"}) == []
