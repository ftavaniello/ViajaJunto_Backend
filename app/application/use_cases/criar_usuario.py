from app.domain.entities.usuario import Usuario
from app.domain.ports.usuario_repository import UsuarioRepository


class CriarUsuario:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    def execute(self, nome: str, email: str, senha_hash: str) -> Usuario:
        usuario_existente = self.repository.buscar_por_email(email)

        if usuario_existente:
            raise ValueError("Já existe um usuário com este email")

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
        )

        return self.repository.salvar(usuario)