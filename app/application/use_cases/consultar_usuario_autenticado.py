from app.domain.entities.usuario import Usuario
from app.domain.errors import NaoAutenticado
from app.domain.ports.token_service import TokenService
from app.domain.ports.usuario_repository import UsuarioRepository


class ConsultarUsuarioAutenticado:
    def __init__(self, repository: UsuarioRepository, token_service: TokenService):
        self.repository = repository
        self.token_service = token_service

    def execute(self, token: str | None) -> Usuario:
        if not token:
            raise NaoAutenticado("Token inválido ou expirado")
        usuario_id = self.token_service.verificar_token(token)
        usuario = self.repository.buscar_por_id(usuario_id)
        if usuario is None:
            raise NaoAutenticado("Token inválido ou expirado")
        return usuario
