import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.domain.errors import NaoAutenticado
from app.domain.ports.token_service import DadosToken, TokenService


class PyJWTTokenService(TokenService):
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def gerar_token(self, usuario_id: int, versao_sessao: int) -> str:
        agora = datetime.now(timezone.utc)
        payload = {
            "sub": str(usuario_id),
            "iat": agora,
            "exp": agora + timedelta(minutes=self.expire_minutes),
            "jti": uuid.uuid4().hex,
            "ver": versao_sessao,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verificar_token(self, token: str) -> DadosToken:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                # Tokens sem jti/ver (emitidos antes do logout existir) nao sao revogaveis.
                options={"require": ["sub", "exp", "jti", "ver"]},
            )
            return DadosToken(
                usuario_id=_usuario_id_do_sub(payload["sub"]),
                jti=str(payload["jti"]),
                versao_sessao=int(payload["ver"]),
                expira_em=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
            raise NaoAutenticado("Token inválido ou expirado") from error


def _usuario_id_do_sub(sub: object) -> int:
    # Emitimos sempre str(id) positivo; int() aceitaria " 42 ", "-1" ou "1_000".
    if not isinstance(sub, str) or not (sub.isascii() and sub.isdigit()) or int(sub) <= 0:
        raise NaoAutenticado("Token inválido ou expirado")
    return int(sub)
