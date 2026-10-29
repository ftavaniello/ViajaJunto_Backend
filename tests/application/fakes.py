"""Implementacoes falsas das portas, para testar casos de uso sem bibliotecas externas."""
from app.domain.errors import NaoAutenticado
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.token_service import TokenService


class FakePasswordHasher(PasswordHasher):
    def hash(self, senha: str) -> str:
        return f"hash:{senha}"

    def verificar(self, senha: str, senha_hash: str) -> bool:
        return senha_hash == self.hash(senha)


class FakeTokenService(TokenService):
    def gerar_token(self, usuario_id: int) -> str:
        return f"token:{usuario_id}"

    def verificar_token(self, token: str) -> int:
        prefixo, _, usuario_id = token.partition(":")
        if prefixo != "token" or not usuario_id.isdigit():
            raise NaoAutenticado("Token inválido ou expirado")
        return int(usuario_id)
