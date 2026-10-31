"""Cria a conta de demonstracao em ambientes de desenvolvimento.

Uso: python -m app.adapters.inbound.cli.seed_demo

Separado das migracoes: provisionar o schema nunca cria contas com senha
conhecida. O cadastro passa pelo caso de uso CriarUsuario, entao segue as mesmas
regras da API; se o email ja existir, a conta e mantida como esta (a senha nao e
redefinida).
"""
import sys

from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.errors import EmailDuplicado
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import Settings, settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.dependencies import montar_criar_usuario

NOME_DEMO = "Usuario Inicial"
EMAIL_DEMO = "usuario@viajajunto.com"
SENHA_DEMO = "changeme123"


def semear_usuario_demo(criar_usuario: CriarUsuario, config: Settings) -> str:
    """Retorna uma mensagem de resultado; nunca inclui a senha."""
    if not config.em_desenvolvimento:
        raise PermissionError(
            f"Seed de demonstração bloqueado em APP_ENV={config.APP_ENV}"
        )

    try:
        criar_usuario.execute(nome=NOME_DEMO, email=EMAIL_DEMO, senha=SENHA_DEMO)
    except EmailDuplicado:
        return f"Conta de demonstração {EMAIL_DEMO} já existe; mantida sem alterações"
    return f"Conta de demonstração {EMAIL_DEMO} criada"


def main() -> int:
    db = SessionLocal()
    try:
        criar_usuario = montar_criar_usuario(db, get_total_usuarios_cache())
        print(semear_usuario_demo(criar_usuario, settings))
    except PermissionError as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
