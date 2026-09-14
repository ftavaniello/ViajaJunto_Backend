from pydantic import BaseModel, EmailStr


class CriarUsuarioRequest(BaseModel):
    nome: str
    email: EmailStr
    senha_hash: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr