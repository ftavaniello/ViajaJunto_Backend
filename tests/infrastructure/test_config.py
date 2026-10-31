import pytest

from app.infrastructure.config import (
    JWT_SECRET_KEY_DEV,
    ConfiguracaoInvalida,
    carregar_settings,
    validar_settings,
)

SEGREDO_FORTE = "segredo-de-producao-com-mais-de-32-bytes-0123456789"


def test_desenvolvimento_sem_segredo_usa_chave_de_exemplo():
    config = carregar_settings({})

    assert config.APP_ENV == "development"
    assert config.JWT_SECRET_KEY == JWT_SECRET_KEY_DEV
    validar_settings(config)


def test_segredo_vazio_conta_como_ausente_em_desenvolvimento():
    config = carregar_settings({"APP_ENV": "test", "JWT_SECRET_KEY": ""})

    assert config.JWT_SECRET_KEY == JWT_SECRET_KEY_DEV


def test_producao_com_segredo_proprio_e_aceita():
    config = carregar_settings({"APP_ENV": "production", "JWT_SECRET_KEY": SEGREDO_FORTE})

    validar_settings(config)
    assert config.JWT_SECRET_KEY == SEGREDO_FORTE


@pytest.mark.parametrize(
    "env",
    [
        {"APP_ENV": "production"},
        {"APP_ENV": "production", "JWT_SECRET_KEY": ""},
        {"APP_ENV": "staging", "JWT_SECRET_KEY": JWT_SECRET_KEY_DEV},
        {"APP_ENV": "Production", "JWT_SECRET_KEY": "curto-demais"},
    ],
    ids=["ausente", "vazio", "chave-de-exemplo", "curto"],
)
def test_fora_do_desenvolvimento_exige_segredo_apropriado(env):
    with pytest.raises(ConfiguracaoInvalida):
        validar_settings(carregar_settings(env))


def test_mensagem_de_erro_nao_expoe_o_segredo():
    segredo_fraco = "segredo-fraco-123"

    with pytest.raises(ConfiguracaoInvalida) as erro:
        validar_settings(
            carregar_settings({"APP_ENV": "production", "JWT_SECRET_KEY": segredo_fraco})
        )

    assert segredo_fraco not in str(erro.value)


@pytest.mark.parametrize("valor", ["0", "-5"])
def test_expiracao_do_token_precisa_ser_positiva(valor):
    with pytest.raises(ConfiguracaoInvalida):
        validar_settings(carregar_settings({"JWT_EXPIRE_MINUTES": valor}))


def test_expiracao_nao_numerica_e_rejeitada():
    with pytest.raises(ConfiguracaoInvalida):
        carregar_settings({"JWT_EXPIRE_MINUTES": "uma-hora"})
