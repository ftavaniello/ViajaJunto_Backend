from datetime import datetime

from app.domain.ports.token_revogado_repository import TokenRevogadoRepository


class TokenRevogadoRepositoryMemory(TokenRevogadoRepository):
    def __init__(self):
        self.revogados: dict[str, tuple[int, datetime]] = {}

    def revogar(self, jti: str, usuario_id: int, expira_em: datetime) -> None:
        self.revogados[jti] = (usuario_id, expira_em)

    def esta_revogado(self, jti: str) -> bool:
        return jti in self.revogados
