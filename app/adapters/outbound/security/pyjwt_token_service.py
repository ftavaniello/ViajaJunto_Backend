from datetime import datetime, timedelta, timezone

import jwt

from app.domain.errors import NaoAutenticado
from app.domain.ports.token_service import TokenService


class PyJWTTokenService(TokenService):
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def gerar_token(self, usuario_id: int) -> str:
        expira_em = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        payload = {"sub": str(usuario_id), "exp": expira_em}

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verificar_token(self, token: str) -> int:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "exp"]},
            )
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise NaoAutenticado("Token inválido ou expirado") from error

        return _usuario_id_do_sub(payload["sub"])


def _usuario_id_do_sub(sub: object) -> int:
    # Emitimos sempre str(id) positivo; int() aceitaria " 42 ", "-1" ou "1_000".
    if not isinstance(sub, str) or not (sub.isascii() and sub.isdigit()) or int(sub) <= 0:
        raise NaoAutenticado("Token inválido ou expirado")
    return int(sub)
