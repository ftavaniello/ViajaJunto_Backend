from pydantic import BaseModel, EmailStr, Field


class CriarUsuarioRequest(BaseModel):
    nome: str = Field(examples=["Livia Bampi"])
    email: EmailStr = Field(examples=["livia@example.com"])
    senha: str = Field(
        min_length=8,
        examples=["senhaSegura123"],
        description="Senha em texto puro; o backend a converte em hash antes de persistir.",
    )


class UsuarioResponse(BaseModel):
    id: int = Field(examples=[1])
    nome: str = Field(examples=["Livia Bampi"])
    email: EmailStr = Field(examples=["livia@example.com"])


class AtualizarUsuarioRequest(BaseModel):
    nome: str | None = Field(
        default=None,
        min_length=1,
        examples=["Livia Bampi"],
        description="Campos omitidos (ou nulos) permanecem inalterados.",
    )
    email: EmailStr | None = Field(default=None, examples=["livia@example.com"])


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(examples=["senhaSegura123"])
    senha_nova: str = Field(min_length=8, examples=["novaSenhaForte456"])
