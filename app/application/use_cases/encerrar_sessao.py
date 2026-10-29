from app.domain.ports.token_revogado_repository import TokenRevogadoRepository
from app.domain.ports.token_service import TokenService
from app.domain.ports.unit_of_work import UnitOfWork


class EncerrarSessao:
    """Logout: revoga no servidor o token usado, ate a expiracao dele.

    Qualquer copia do token passa a ser recusada; as demais sessoes do usuario
    (outros logins) continuam validas.
    """

    def __init__(self, token_service: TokenService, tokens_revogados: TokenRevogadoRepository,
                 uow: UnitOfWork):
        self.token_service = token_service
        self.tokens_revogados = tokens_revogados
        self.uow = uow

    def execute(self, token: str) -> None:
        dados = self.token_service.verificar_token(token)

        with self.uow:
            self.tokens_revogados.revogar(dados.jti, dados.usuario_id, dados.expira_em)
            self.uow.commit()
