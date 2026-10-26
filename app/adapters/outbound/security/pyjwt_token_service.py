from datetime import datetime, timedelta, timezone

import jwt

from app.domain.errors import NaoAutenticado
from app.domain.ports.token_service import TokenService
from app.infrastructure.config import settings


class PyJWTTokenService(TokenService):
    def gerar_token(self, usuario_id: int) -> str:
        expira_em = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        payload = {"sub": str(usuario_id), "exp": expira_em}

        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verificar_token(self, token: str) -> int:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["sub", "exp"]},
            )
            return int(payload["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
            raise NaoAutenticado("Token inválido ou expirado") from error
