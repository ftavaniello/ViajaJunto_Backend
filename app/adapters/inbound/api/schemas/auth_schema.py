from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["livia@example.com"])
    senha: str = Field(examples=["senhaSegura123"])


class TokenResponse(BaseModel):
    access_token: str = Field(
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
        description="JWT a ser enviado no header 'Authorization: Bearer <access_token>' dos endpoints protegidos.",
    )
    token_type: str = Field(default="bearer", examples=["bearer"])
