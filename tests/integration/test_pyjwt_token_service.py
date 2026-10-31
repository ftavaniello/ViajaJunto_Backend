from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.domain.errors import NaoAutenticado

SEGREDO = "segredo-de-teste-com-32-bytes-ou-mais"
OUTRO_SEGREDO = "outro-segredo-de-teste-com-32-bytes-ou-mais"


def _exp() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=5)


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


@pytest.mark.parametrize(
    "payload",
    [
        {"exp": "AGORA"},  # sem sub
        {"sub": "42"},  # sem exp
        {"sub": "abc", "exp": "AGORA"},
        {"sub": "-1", "exp": "AGORA"},
        {"sub": "0", "exp": "AGORA"},
        {"sub": " 42 ", "exp": "AGORA"},
        {"sub": "1_000", "exp": "AGORA"},
        {"sub": "", "exp": "AGORA"},
        {"sub": 42, "exp": "AGORA"},  # sub precisa ser string (RFC 7519)
        {"sub": "42", "exp": "amanha"},
    ],
    ids=[
        "sem-sub", "sem-exp", "sub-texto", "sub-negativo", "sub-zero", "sub-com-espacos",
        "sub-com-underscore", "sub-vazio", "sub-inteiro", "exp-invalido",
    ],
)
def test_claims_obrigatorias_ausentes_ou_invalidas_sao_rejeitadas(payload):
    # jti/ver validos: o teste isola a validacao de sub e exp.
    payload = {"jti": "abc", "ver": 0, **payload}
    if payload.get("exp") == "AGORA":
        payload = {**payload, "exp": _exp()}
    token = jwt.encode(payload, SEGREDO, algorithm="HS256")

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


def test_token_com_outro_algoritmo_e_rejeitado():
    payload = {"sub": "42", "exp": _exp(), "jti": "abc", "ver": 0}
    token = jwt.encode(payload, SEGREDO, algorithm="HS512")

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


def test_token_sem_assinatura_alg_none_e_rejeitado():
    payload = {"sub": "42", "exp": _exp(), "jti": "abc", "ver": 0}
    token = jwt.encode(payload, None, algorithm="none")

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


@pytest.mark.parametrize("token", ["", "nao-e-um-jwt", "a.b.c", "Bearer x.y.z"])
def test_token_malformado_e_rejeitado(token):
    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)


def test_token_sem_jti_e_rejeitado():
    # Formato anterior ao logout: nao pode ser revogado, entao nao e aceito.
    expira = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode({"sub": "42", "exp": expira}, SEGREDO, algorithm="HS256")

    with pytest.raises(NaoAutenticado):
        PyJWTTokenService(secret_key=SEGREDO).verificar_token(token)
