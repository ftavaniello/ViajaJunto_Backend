"""Prepara contas e cenários de demonstração em desenvolvimento.

Uso: python -m app.adapters.inbound.cli.seed_demo [--completo]

Sem argumentos mantém a conta inicial; --completo adiciona os cenários
colaborativos de docs/seed-demonstracao.md somente em APP_ENV=development.

Separado das migracoes: provisionar o schema nunca cria contas com senha
conhecida. O cadastro passa pelo caso de uso CriarUsuario, entao segue as mesmas
regras da API; se o email ja existir, a conta e mantida como esta (a senha nao e
redefinida).
"""

import argparse
import json
import sys
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app.application.use_cases.criar_usuario import CriarUsuario
from app.domain.errors import DadosInvalidos, EmailDuplicado
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import Settings, settings
from app.infrastructure.database import SessionLocal, engine
from app.infrastructure.dependencies import montar_criar_usuario
from app.infrastructure.seed_demonstracao import executar_seed_completo

NOME_DEMO = "Usuario Inicial"
EMAIL_DEMO = "usuario@viajajunto.com"
SENHA_DEMO = "changeme123"


def semear_usuario_demo(criar_usuario: CriarUsuario, config: Settings) -> str:
    """Retorna uma mensagem de resultado; nunca inclui a senha."""
    if not config.em_desenvolvimento:
        raise PermissionError(f"Seed de demonstração bloqueado em APP_ENV={config.APP_ENV}")

    try:
        criar_usuario.execute(nome=NOME_DEMO, email=EMAIL_DEMO, senha=SENHA_DEMO)
    except EmailDuplicado:
        return f"Conta de demonstração {EMAIL_DEMO} já existe; mantida sem alterações"
    return f"Conta de demonstração {EMAIL_DEMO} criada"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--completo", action="store_true", help="Cria os cenários colaborativos")
    parser.add_argument("--referencia", type=date.fromisoformat, help="Data base AAAA-MM-DD")
    args = parser.parse_args()
    if args.referencia and not args.completo:
        parser.error("--referencia exige --completo")
    if args.completo:
        return carregar_cenarios(args.referencia or date.today())
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


def carregar_cenarios(referencia: date) -> int:
    # Guard antes de abrir conexão; o serviço de composição também valida.
    if settings.APP_ENV != "development":
        print("Seed completo permitido somente em APP_ENV=development", file=sys.stderr)
        return 1
    try:
        with engine.begin() as connection:
            criado, manifesto = executar_seed_completo(settings, connection, referencia)
        if criado:
            get_total_usuarios_cache().invalidar()
        print("Seed completo criado." if criado else "Seed já executado; dados mantidos.")
        print(json.dumps(manifesto, ensure_ascii=False, indent=2))
    except (PermissionError, DadosInvalidos) as error:
        print(str(error), file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print(
            "Falha no banco; carga desfeita. Confira a conexão e execute alembic upgrade head.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
