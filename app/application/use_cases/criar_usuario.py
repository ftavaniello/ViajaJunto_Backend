from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.validation import validar_email, validar_nome, validar_senha


class CriarUsuario:
    def __init__(self, repository: UsuarioRepository, password_hasher: PasswordHasher,
                 cache: TotalUsuariosCache | None = None):
        self.cache = cache
        self.repository = repository
        self.password_hasher = password_hasher

    def execute(self, nome: str, email: str, senha: str) -> Usuario:
        validar_nome(nome)
        validar_email(email)
        validar_senha(senha)
        usuario_existente = self.repository.buscar_por_email(email)

        if usuario_existente:
            raise EmailDuplicado("Já existe um usuário com este email")

        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=self.password_hasher.hash(senha),
        )

        salvo = self.repository.salvar(usuario)
        if self.cache is not None:
            self.cache.invalidar()
        return salvo
