from app.domain.entities.usuario import Usuario
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.usuario_repository import UsuarioRepository


class CriarUsuario:
    def __init__(self, repository: UsuarioRepository, password_hasher: PasswordHasher):
        self.repository = repository
        self.password_hasher = password_hasher

    def execute(self, nome: str, email: str, senha: str) -> Usuario:
        usuario_existente = self.repository.buscar_por_email(email)

        if usuario_existente:
            raise ValueError("Já existe um usuário com este email")

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=self.password_hasher.hash(senha),
        )

        return self.repository.salvar(usuario)