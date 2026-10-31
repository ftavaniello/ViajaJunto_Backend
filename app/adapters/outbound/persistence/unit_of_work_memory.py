from app.domain.ports.unit_of_work import UnitOfWork


class UnitOfWorkMemory(UnitOfWork):
    """Conta commits e rollbacks; nao desfaz alteracoes do repositorio em memoria."""

    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self._pendente = False

    def __enter__(self) -> "UnitOfWorkMemory":
        self._pendente = True
        return self

    def commit(self) -> None:
        self.commits += 1
        self._pendente = False

    def rollback(self) -> None:
        # So conta rollback que de fato descarta trabalho nao confirmado.
        if self._pendente:
            self.rollbacks += 1
        self._pendente = False
