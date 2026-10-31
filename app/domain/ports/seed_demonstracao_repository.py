from typing import Protocol

from app.domain.enums import PapelMembro


class SeedDemonstracaoRepository(Protocol):
    """Registro operacional da carga; não é uma API de colaboração."""

    def reservar(self, chave: str) -> dict | None: ...

    def vincular(self, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None: ...

    def concluir(self, chave: str, manifesto: dict) -> None: ...
