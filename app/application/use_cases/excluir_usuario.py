from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository


class ExcluirUsuario:
    def __init__(self, repository: UsuarioRepository, uow: UnitOfWork,
                 cache: TotalUsuariosCache | None = None):
        self.cache = cache
        self.repository = repository
        self.uow = uow

    def execute(self, usuario_id: int) -> None:
        with self.uow:
            self.repository.deletar(usuario_id)
            self.uow.commit()

        if self.cache is not None:
            self.cache.invalidar()
