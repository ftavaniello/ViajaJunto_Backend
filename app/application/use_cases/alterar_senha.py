from app.domain.entities.usuario import Usuario
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.usuario_repository import UsuarioRepository


class AlterarSenha:
    def __init__(self, repository: UsuarioRepository, password_hasher: PasswordHasher):
        self.repository = repository
        self.password_hasher = password_hasher

    def execute(self, usuario_id: int, senha_atual: str, senha_nova: str) -> None:
        usuario = self.repository.buscar_por_id(usuario_id)

        if usuario is None:
            raise ValueError("Usuário não encontrado")

        if not self.password_hasher.verificar(senha_atual, usuario.senha_hash):
            raise ValueError("Senha atual incorreta")

        usuario_atualizado = Usuario(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            senha_hash=self.password_hasher.hash(senha_nova),
        )

        self.repository.salvar(usuario_atualizado)
