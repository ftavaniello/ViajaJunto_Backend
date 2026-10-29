from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.use_cases.consultar_usuario_autenticado import ConsultarUsuarioAutenticado
from app.domain.entities.usuario import Usuario
from app.infrastructure.dependencies import get_consultar_usuario_autenticado

bearer_scheme = HTTPBearer(
    description="Token JWT obtido em POST /auth/login",
    auto_error=False,
)


def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    consultar: ConsultarUsuarioAutenticado = Depends(get_consultar_usuario_autenticado),
) -> Usuario:
    return consultar.execute(credentials.credentials if credentials else None)
