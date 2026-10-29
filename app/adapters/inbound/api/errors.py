from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.errors import ErroNegocio, NaoAutenticado, UsuarioNaoEncontrado


async def tratar_erro_negocio(request: Request, error: ErroNegocio) -> JSONResponse:
    # Mantem o contrato existente: email duplicado e dados invalidos retornam 400.
    status = 400
    headers = None
    if isinstance(error, NaoAutenticado):
        status = 401
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(error, UsuarioNaoEncontrado):
        status = 404
    return JSONResponse(status_code=status, content={"detail": str(error)}, headers=headers)
