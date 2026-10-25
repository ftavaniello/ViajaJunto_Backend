from typing import Protocol


class TotalUsuariosCache(Protocol):
    def ler(self) -> tuple[int | None, bool]:
        """Retorna o total e se o cache esta disponivel."""
        ...

    def gravar(self, total: int) -> bool:
        ...

    def invalidar(self) -> None:
        ...
