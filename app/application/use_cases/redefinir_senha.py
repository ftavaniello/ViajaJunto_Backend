from collections.abc import Callable
from datetime import datetime, timezone

from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.entities.usuario import Usuario
from app.domain.errors import TokenRecuperacaoInvalido
from app.domain.ports.password_hasher import PasswordHasher
from app.domain.ports.token_recuperacao_senha_repository import TokenRecuperacaoSenhaRepository
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.validation import validar_senha


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class RedefinirSenha:
    """Troca a senha usando o token recebido por email (RF03)."""

    def __init__(
        self,
        repository: UsuarioRepository,
        tokens: TokenRecuperacaoSenhaRepository,
        password_hasher: PasswordHasher,
        uow: UnitOfWork,
        relogio: Callable[[], datetime] = _agora_utc,
    ):
        self.repository = repository
        self.tokens = tokens
        self.password_hasher = password_hasher
        self.uow = uow
        self.relogio = relogio

    def execute(self, token: str, senha_nova: str) -> None:
        # Valida antes de consumir o token: senha recusada nao gasta o link.
        validar_senha(senha_nova)
        agora = self.relogio()

        with self.uow:
            registro = self.tokens.buscar_por_hash(TokenRecuperacaoSenha.calcular_hash(token))

            # Inexistente, expirado e ja usado recebem a mesma resposta.
            if registro is None or not registro.pode_ser_usado(agora):
                raise TokenRecuperacaoInvalido("Token de recuperação inválido ou expirado")

            usuario = self.repository.buscar_por_id(registro.usuario_id)
            if usuario is None:
                raise TokenRecuperacaoInvalido("Token de recuperação inválido ou expirado")

            registro.marcar_usado(agora)
            self.tokens.salvar(registro)
            self.tokens.invalidar_pendentes(usuario.id, agora)

            # Mesma regra da troca de senha (docs/sessoes-e-logout.md): nova versao de
            # sessao encerra todos os tokens de acesso emitidos com a senha antiga.
            self.repository.salvar(
                Usuario(
                    id=usuario.id,
                    nome=usuario.nome,
                    email=usuario.email,
                    senha_hash=self.password_hasher.hash(senha_nova),
                    versao_sessao=usuario.versao_sessao + 1,
                )
            )
            self.uow.commit()
