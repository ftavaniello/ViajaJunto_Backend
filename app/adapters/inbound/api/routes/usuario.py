from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.inbound.api.schemas.usuario_schema import (
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.application.use_cases.criar_usuario import CriarUsuario
from app.infrastructure.database import get_db


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
)


@router.post("", response_model=UsuarioResponse, status_code=201)
def criar(request: CriarUsuarioRequest, db: Session = Depends(get_db)):
    try:
        repository = SQLAlchemyUsuarioRepository(db)
        criar_usuario = CriarUsuario(repository)

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