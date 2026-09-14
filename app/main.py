from fastapi import FastAPI

from app.adapters.inbound.api.routes.health import router as health_router
from app.adapters.inbound.api.routes.usuario import router as usuario_router


app = FastAPI(
    title="ViajaJunto API",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(usuario_router)
