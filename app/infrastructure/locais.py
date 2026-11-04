from pathlib import Path

from app.adapters.outbound.locais.geoapify_provedor_locais import GeoapifyProvedorLocais
from app.domain.errors import CredencialProvedorLocaisInvalida
from app.domain.ports.provedor_locais import ProvedorLocais
from app.infrastructure.config import Settings


def criar_provedor_locais(config: Settings) -> ProvedorLocais:
    """Monta o fornecedor de locais; a chave vem de GEOAPIFY_API_KEY ou do arquivo."""
    chave = config.GEOAPIFY_API_KEY
    if not chave and config.GEOAPIFY_API_KEY_FILE:
        try:
            chave = Path(config.GEOAPIFY_API_KEY_FILE).read_text(encoding="utf-8").strip()
        except OSError:
            raise CredencialProvedorLocaisInvalida(
                "Não foi possível ler GEOAPIFY_API_KEY_FILE"
            ) from None
    if not chave:
        raise CredencialProvedorLocaisInvalida(
            "Configure GEOAPIFY_API_KEY (ou GEOAPIFY_API_KEY_FILE) para buscar locais"
        )
    return GeoapifyProvedorLocais(chave, timeout_segundos=config.LOCAIS_TIMEOUT_SECONDS)
