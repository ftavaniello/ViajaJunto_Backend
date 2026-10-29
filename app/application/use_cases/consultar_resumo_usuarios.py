from enum import Enum

from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.usuario_repository import UsuarioRepository


class OrigemTotal(str, Enum):
    HIT = "HIT"  # valor lido do cache
    MISS = "MISS"  # valor lido do banco e gravado no cache
    BYPASS = "BYPASS"  # valor lido do banco; cache indisponivel


class ConsultarResumoUsuarios:
    def __init__(self, repository: UsuarioRepository, cache: TotalUsuariosCache):
        self.repository = repository
        self.cache = cache

    def execute(self) -> tuple[int, OrigemTotal]:
        total, disponivel = self.cache.ler()
        if total is not None:
            return total, OrigemTotal.HIT
        total = self.repository.contar()
        if disponivel and self.cache.gravar(total):
            return total, OrigemTotal.MISS
        return total, OrigemTotal.BYPASS
