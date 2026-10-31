"""Implementacoes falsas das portas, para testar casos de uso sem bibliotecas externas."""
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado, NaoAutenticado
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


class RepositorioComCorrida(UsuarioRepositoryMemory):
    """Simula outra requisicao gravando o mesmo email entre a checagem e o salvar.

    A checagem previa do caso de uso nao enxerga o concorrente; quem impede a
    duplicidade e a restricao de unicidade do repositorio (no banco, a constraint).
    """

    def buscar_por_email(self, email: str) -> Usuario | None:
        return None

    def salvar(self, usuario: Usuario) -> Usuario:
        # A unicidade continua valendo no armazenamento, como a constraint do banco.
        for outro in self.usuarios.values():
            if outro.email == usuario.email and outro.id != usuario.id:
                raise EmailDuplicado("Já existe um usuário com este email")
        return super().salvar(usuario)
