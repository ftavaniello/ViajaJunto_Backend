from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    summary="Verifica a disponibilidade da API",
    description="Endpoint público de liveness check, usado por orquestradores e monitoramento.",
)
def health_check():
    return {"status": "ok"}