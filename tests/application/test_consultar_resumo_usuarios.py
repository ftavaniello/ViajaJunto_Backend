from unittest.mock import Mock

from app.application.use_cases.consultar_resumo_usuarios import ConsultarResumoUsuarios


def test_hit_zero_nao_consulta_banco():
    repository = Mock()
    cache = Mock()
    cache.ler.return_value = (0, True)
    assert ConsultarResumoUsuarios(repository, cache).execute() == (0, "HIT")
    repository.contar.assert_not_called()
    cache.gravar.assert_not_called()


def test_miss_consulta_e_preenche_cache():
    repository = Mock()
    repository.contar.return_value = 3
    cache = Mock()
    cache.ler.return_value = (None, True)
    cache.gravar.return_value = True
    assert ConsultarResumoUsuarios(repository, cache).execute() == (3, "MISS")
    repository.contar.assert_called_once()
    cache.gravar.assert_called_once_with(3)


def test_cache_indisponivel_usa_banco():
    repository = Mock()
    repository.contar.return_value = 3
    cache = Mock()
    cache.ler.return_value = (None, False)
    assert ConsultarResumoUsuarios(repository, cache).execute() == (3, "BYPASS")
    cache.gravar.assert_not_called()


def test_falha_ao_gravar_nao_perde_resposta_do_banco():
    repository = Mock()
    repository.contar.return_value = 3
    cache = Mock()
    cache.ler.return_value = (None, True)
    cache.gravar.return_value = False
    assert ConsultarResumoUsuarios(repository, cache).execute() == (3, "BYPASS")
