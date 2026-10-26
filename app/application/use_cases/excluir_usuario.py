from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.usuario_repository import UsuarioRepository


class ExcluirUsuario:
    def __init__(self, repository: UsuarioRepository,
                 cache: TotalUsuariosCache | None = None):
        self.cache = cache
        self.repository = repository

    def execute(self, usuario_id: int) -> None:
        self.repository.deletar(usuario_id)
        if self.cache is not None:
            self.cache.invalidar()
