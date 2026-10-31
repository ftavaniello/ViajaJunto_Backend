from app.domain.entities.usuario import Usuario
from app.domain.errors import DadosInvalidos, UsuarioNaoEncontrado
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.validation import validar_senha


class AlterarSenha:
    def __init__(self, repository: UsuarioRepository, password_hasher: PasswordHasher,
                 uow: UnitOfWork):
        self.repository = repository
        self.password_hasher = password_hasher
        self.uow = uow

    def execute(self, usuario_id: int, senha_atual: str, senha_nova: str) -> None:
        usuario = self.repository.buscar_por_id(usuario_id)

        if usuario is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado")

        if not self.password_hasher.verificar(senha_atual, usuario.senha_hash):
            raise DadosInvalidos("Senha atual incorreta")

        validar_senha(senha_nova)

        # Nova versao de sessao: todos os tokens emitidos antes da troca, inclusive
        # o usado nesta requisicao, deixam de valer. O usuario precisa logar de novo.
        usuario_atualizado = Usuario(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            senha_hash=self.password_hasher.hash(senha_nova),
            criado_em=usuario.criado_em,
            versao_sessao=usuario.versao_sessao + 1,
        )

        with self.uow:
            self.repository.salvar(usuario_atualizado)
            self.uow.commit()
