from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import CategoriaAtividade, FonteCatalogo


@dataclass(frozen=True)
class LocalExterno:
    """Local encontrado no fornecedor, já no vocabulário do catálogo."""

    id_externo: str
    nome: str
    latitude: Decimal
    longitude: Decimal
    endereco: str | None = None


class ProvedorLocais(ABC):
    """Busca locais num serviço externo (Geoapify hoje; outro fornecedor amanhã).

    Credenciais, URLs, formato da resposta e códigos HTTP ficam no adaptador. As
    falhas chegam como erros de domínio: ProvedorLocaisIndisponivel,
    LimiteProvedorLocaisExcedido ou CredencialProvedorLocaisInvalida.
    """

    @property
    @abstractmethod
    def fonte(self) -> FonteCatalogo:
        """Valor gravado em `fonte` nos registros vindos deste fornecedor."""
        pass

    @abstractmethod
    def buscar_proximos(
        self,
        latitude: Decimal,
        longitude: Decimal,
        categoria: CategoriaAtividade,
        raio_metros: int,
        limite: int,
    ) -> list[LocalExterno]:
        """Locais da categoria dentro do raio, mais próximos primeiro."""
        pass
