import pytest

from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.domain.errors import NaoAutenticado

SEGREDO = "segredo-de-teste-com-32-bytes-ou-mais"
OUTRO_SEGREDO = "outro-segredo-de-teste-com-32-bytes-ou-mais"


def test_token_gerado_e_verificado_com_o_mesmo_segredo():
    token_service = PyJWTTokenService(secret_key=SEGREDO)

    token = token_service.gerar_token(42)

    assert token_service.verificar_token(token) == 42


def test_token_assinado_com_outro_segredo_e_rejeitado():
    token = PyJWTTokenService(secret_key=OUTRO_SEGREDO).gerar_token(42)

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


def test_token_expirado_e_rejeitado():
    token_service = PyJWTTokenService(secret_key=SEGREDO, expire_minutes=-1)

    with pytest.raises(NaoAutenticado):
        token_service.verificar_token(token_service.gerar_token(42))
