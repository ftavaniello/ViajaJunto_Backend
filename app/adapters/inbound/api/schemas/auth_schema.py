from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["livia@example.com"])
    senha: str = Field(examples=["senhaSegura123"])


class TokenResponse(BaseModel):
    access_token: str = Field(
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
        description="""JWT a ser enviado no header 'Authorization:
        Bearer <access_token>' dos endpoints protegidos.""",
    )
    token_type: str = Field(default="bearer", examples=["bearer"])


class SolicitarRecuperacaoSenhaRequest(BaseModel):
    email: EmailStr = Field(examples=["livia@example.com"])


class MensagemResponse(BaseModel):
    detail: str = Field(
        examples=[
            "Se o email estiver cadastrado, enviaremos um link para redefinir a senha."
        ]
    )


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(
        min_length=1,
        examples=["kW3v0d5o2Xc6m8bq1yQpZ4tA7nR9sLfH0jUeGiVaYxM"],
        description="Código recebido no email de recuperação (parâmetro `token` do link).",
    )
    senha_nova: str = Field(min_length=8, examples=["novaSenhaForte456"])
