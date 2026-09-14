from fastapi import APIRouter, HTTPException

from app.adapters.inbound.api.schemas.usuario_schema import (
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.criar_usuario import CriarUsuario


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)

repository = UsuarioRepositoryMemory()
criar_usuario = CriarUsuario(repository)


@router.post("", response_model=UsuarioResponse, status_code=201)
def criar(request: CriarUsuarioRequest):
    try:
        usuario = criar_usuario.execute(
            nome=request.nome,
            email=request.email,
            senha_hash=request.senha_hash,
        )

        return UsuarioResponse(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )