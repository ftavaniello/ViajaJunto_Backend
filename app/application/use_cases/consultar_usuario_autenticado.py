from app.domain.entities.usuario import Usuario
from app.domain.errors import NaoAutenticado
from app.domain.ports.token_revogado_repository import TokenRevogadoRepository
from app.domain.ports.token_service import TokenService
from app.domain.ports.usuario_repository import UsuarioRepository


class ConsultarUsuarioAutenticado:
    def __init__(self, repository: UsuarioRepository, token_service: TokenService,
                 tokens_revogados: TokenRevogadoRepository):
        self.repository = repository
        self.token_service = token_service
        self.tokens_revogados = tokens_revogados

    def execute(self, token: str | None) -> Usuario:
        if not token:
            raise NaoAutenticado("Token inválido ou expirado")
        dados = self.token_service.verificar_token(token)
        if self.tokens_revogados.esta_revogado(dados.jti):
            raise NaoAutenticado("Token inválido ou expirado")
        usuario = self.repository.buscar_por_id(dados.usuario_id)
        # Conta excluida ou sessoes encerradas por troca de senha.
        if usuario is None or usuario.versao_sessao != dados.versao_sessao:
            raise NaoAutenticado("Token inválido ou expirado")
        return usuario
