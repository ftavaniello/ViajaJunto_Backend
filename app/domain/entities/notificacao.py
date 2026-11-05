from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import TipoNotificacao


@dataclass
class Notificacao:
    """Aviso in-app (RF21) para um único destinatário.

    A mensagem é gravada pronta, para continuar legível depois que a viagem ou o
    autor deixarem de existir (`viagem_id` e `ator_id` viram nulos).
    """

    usuario_id: int
    tipo: TipoNotificacao
    mensagem: str
    viagem_id: int | None = None
    ator_id: int | None = None
    lida_em: datetime | None = None
    criado_em: datetime | None = None
    id: int | None = None

    @property
    def lida(self) -> bool:
        return self.lida_em is not None
