from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """Agrupa as gravacoes de um caso de uso: confirma todas ou desfaz todas.

    Uso: `with uow: ...; uow.commit()`. Sair do bloco sem `commit()` (inclusive
    por excecao) desfaz o que foi gravado.
    """

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # Depois de um commit nao ha nada pendente, entao o rollback nao tem efeito.
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass
