from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.domain.errors import NaoAutenticado

SEGREDO = "segredo-de-teste-com-32-bytes-ou-mais"
OUTRO_SEGREDO = "outro-segredo-de-teste-com-32-bytes-ou-mais"


def test_token_gerado_e_verificado_com_o_mesmo_segredo():
    token_service = PyJWTTokenService(secret_key=SEGREDO)

    dados = token_service.verificar_token(token_service.gerar_token(42, versao_sessao=3))

    assert dados.usuario_id == 42
    assert dados.versao_sessao == 3
    assert dados.jti
    assert dados.expira_em > datetime.now(timezone.utc)


def test_cada_token_tem_jti_proprio():
    token_service = PyJWTTokenService(secret_key=SEGREDO)

    primeiro = token_service.verificar_token(token_service.gerar_token(42, 0))
    segundo = token_service.verificar_token(token_service.gerar_token(42, 0))

    assert primeiro.jti != segundo.jti


def test_token_assinado_com_outro_segredo_e_rejeitado():
    token = PyJWTTokenService(secret_key=OUTRO_SEGREDO).gerar_token(42, 0)

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


def test_token_expirado_e_rejeitado():
    token_service = PyJWTTokenService(secret_key=SEGREDO, expire_minutes=-1)

    with pytest.raises(NaoAutenticado):
        token_service.verificar_token(token_service.gerar_token(42, 0))


def test_token_sem_jti_e_rejeitado():
    # Formato anterior ao logout: nao pode ser revogado, entao nao e aceito.
    expira = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode({"sub": "42", "exp": expira}, SEGREDO, algorithm="HS256")

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)
