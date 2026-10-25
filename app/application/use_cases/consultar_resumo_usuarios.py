from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.usuario_repository import UsuarioRepository


class ConsultarResumoUsuarios:
    def __init__(self, repository: UsuarioRepository, cache: TotalUsuariosCache):
        self.repository = repository
        self.cache = cache

    def execute(self) -> tuple[int, str]:
        total, disponivel = self.cache.ler()
        if total is not None:
            return total, "HIT"
        total = self.repository.contar()
        if disponivel and self.cache.gravar(total):
            return total, "MISS"
        return total, "BYPASS"
