from app.domain.ports.usuario_repository import UsuarioRepository


class ExcluirUsuario:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    def execute(self, usuario_id: int) -> None:
        self.repository.deletar(usuario_id)
