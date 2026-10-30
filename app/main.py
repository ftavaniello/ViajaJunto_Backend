from fastapi import FastAPI

from app.adapters.inbound.api.errors import tratar_erro_negocio
from app.adapters.inbound.api.routes.auth import router as auth_router
from app.adapters.inbound.api.routes.catalogo import router as catalogo_router
from app.adapters.inbound.api.routes.health import router as health_router
from app.adapters.inbound.api.routes.usuario import router as usuario_router
from app.adapters.inbound.api.routes.viagem import router as viagem_router
from app.domain.errors import ErroNegocio

app = FastAPI(
    title="ViajaJunto API",
    description=(
        "API do ViajaJunto, aplicação de planejamento colaborativo de viagens. "
        "Exceto `POST /usuarios` (cadastro), `POST /auth/login`, "
        "`POST /auth/recuperar-senha`, `POST /auth/redefinir-senha`, `/health` "
        "e as consultas públicas em `/catalogo/atividades`, os demais "
        "endpoints exigem um token JWT no header `Authorization: Bearer <token>` "
        "(use o botão **Authorize** acima com o token retornado pelo login)."
    ),
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Autenticação",
            "description": "Login, logout, emissão de tokens JWT e recuperação de senha.",
        },
        {"name": "Usuarios", "description": "Cadastro e dados do usuário autenticado."},
        {
            "name": "Viagens",
            "description": "Viagens do usuário; acesso restrito ao criador e colaboradores.",
        },
        {"name": "Catálogo", "description": "Consulta pública de atividades e locais."},
        {"name": "Health", "description": "Verificação de disponibilidade da API."},
    ],
)

app.add_exception_handler(ErroNegocio, tratar_erro_negocio)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(usuario_router)
app.include_router(viagem_router)
app.include_router(catalogo_router)
