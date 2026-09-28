from fastapi import FastAPI

from app.adapters.inbound.api.routes.auth import router as auth_router
from app.adapters.inbound.api.routes.health import router as health_router
from app.adapters.inbound.api.routes.usuario import router as usuario_router

app = FastAPI(
    title="ViajaJunto API",
    description=(
        "API do ViajaJunto, aplicação de planejamento colaborativo de viagens. "
        "Exceto `POST /usuarios` (cadastro) e `POST /auth/login`, todos os "
        "endpoints exigem um token JWT no header `Authorization: Bearer <token>` "
        "(use o botão **Authorize** acima com o token retornado pelo login)."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "Autenticação", "description": "Login e emissão de tokens JWT."},
        {"name": "Usuarios", "description": "Cadastro e dados do usuário autenticado."},
        {"name": "Health", "description": "Verificação de disponibilidade da API."},
    ],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(usuario_router)

#ola