from decimal import Decimal

from app.domain.enums import CategoriaAtividade, FonteCatalogo
from app.domain.ports.provedor_locais import LocalExterno, ProvedorLocais


class ProvedorLocaisMemory(ProvedorLocais):
    """Fornecedor falso: devolve os locais cadastrados por categoria e registra as buscas.

    `falha` simula o fornecedor fora do ar: a exceção é levantada na busca.
    """

    def __init__(self, fonte: FonteCatalogo = FonteCatalogo.GEOAPIFY):
        self._fonte = fonte
        self.locais: dict[CategoriaAtividade, list[LocalExterno]] = {}
        self.buscas: list[tuple] = []
        self.falha: Exception | None = None

    @property
    def fonte(self) -> FonteCatalogo:
        return self._fonte

    def buscar_proximos(
        self,
        latitude: Decimal,
        longitude: Decimal,
        categoria: CategoriaAtividade,
        raio_metros: int,
        limite: int,
    ) -> list[LocalExterno]:
        self.buscas.append((latitude, longitude, categoria, raio_metros, limite))
        if self.falha is not None:
            raise self.falha
        return self.locais.get(categoria, [])[:limite]
