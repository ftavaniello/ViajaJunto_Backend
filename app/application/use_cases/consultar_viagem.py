from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.viagem import Viagem
from app.domain.permissoes import AcaoViagem


class ConsultarViagem:
    def __init__(self, acesso: PoliticaAcessoViagem):
        self.acesso = acesso

    def execute(self, viagem_id: int, usuario_id: int) -> Viagem:
        return self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
