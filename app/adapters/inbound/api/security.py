from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.pyjwt_token_service import PyJWTTokenService
from app.domain.entities.usuario import Usuario
from app.infrastructure.database import get_db

bearer_scheme = HTTPBearer(
    description="Token JWT obtido em POST /auth/login",
    auto_error=False,
)


def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    erro_nao_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise erro_nao_autorizado

    try:
        usuario_id = PyJWTTokenService().verificar_token(credentials.credentials)
    except ValueError:
        raise erro_nao_autorizado

    usuario = SQLAlchemyUsuarioRepository(db).buscar_por_id(usuario_id)

    if usuario is None:
        raise erro_nao_autorizado

    return usuario
