"""Implementacoes falsas das portas, para testar casos de uso sem bibliotecas externas."""
from datetime import datetime, timezone

from app.domain.errors import NaoAutenticado
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.token_service import DadosToken, TokenService

EXPIRA_EM = datetime(2100, 1, 1, tzinfo=timezone.utc)


class FakePasswordHasher(PasswordHasher):
    def hash(self, senha: str) -> str:
        return f"hash:{senha}"

    def verificar(self, senha: str, senha_hash: str) -> bool:
        return senha_hash == self.hash(senha)


class FakeTokenService(TokenService):
    """Token no formato `token:<usuario_id>:<versao_sessao>:<jti>`; cada emissao tem jti novo."""

    def __init__(self):
        self.emitidos = 0

    def gerar_token(self, usuario_id: int, versao_sessao: int) -> str:
        self.emitidos += 1
        return f"token:{usuario_id}:{versao_sessao}:jti{self.emitidos}"

    def verificar_token(self, token: str) -> DadosToken:
        partes = token.split(":")
        if len(partes) != 4 or partes[0] != "token" or not all(
            parte.isdigit() for parte in partes[1:3]
        ):
            raise NaoAutenticado("Token inválido ou expirado")
        return DadosToken(
            usuario_id=int(partes[1]),
            versao_sessao=int(partes[2]),
            jti=partes[3],
            expira_em=EXPIRA_EM,
        )
