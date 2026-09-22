from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.token_service import TokenService
from app.domain.ports.usuario_repository import UsuarioRepository


class AutenticarUsuario:
    def __init__(
        self,
        repository: UsuarioRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ):
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def execute(self, email: str, senha: str) -> str:
        usuario = self.repository.buscar_por_email(email)

        credenciais_invalidas = usuario is None or not self.password_hasher.verificar(
            senha, usuario.senha_hash
        )

        if credenciais_invalidas:
            raise ValueError("Email ou senha inválidos")

        return self.token_service.gerar_token(usuario.id)
