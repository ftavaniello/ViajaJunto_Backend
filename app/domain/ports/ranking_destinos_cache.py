from typing import Protocol

from app.domain.ranking_destinos import RankingDestinos


class RankingDestinosCache(Protocol):
    def ler(self) -> tuple[RankingDestinos | None, bool, str | None]:
        """Resultado, disponibilidade e versão usada para impedir gravações obsoletas."""
        ...

    def gravar(self, ranking: RankingDestinos, versao: str) -> bool: ...

    def invalidar(self) -> None: ...
