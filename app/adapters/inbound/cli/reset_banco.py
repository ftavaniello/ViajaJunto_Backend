"""Apaga os dados locais e reaplica migrações e seed. Pare a API antes.

Uso: python -m app.adapters.inbound.cli.reset_banco --confirmar
Execute pelo serviço api do Docker Compose; veja docs/reset-banco.md.
"""

import argparse
import sys

from alembic.util.exc import CommandError
from sqlalchemy.exc import SQLAlchemyError

from app.domain.errors import ErroNegocio
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.config import settings
from app.infrastructure.reset_banco import resetar_banco


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirmar",
        action="store_true",
        required=True,
        help="Confirma a exclusão de todos os dados do banco local viajajunto",
    )
    args = parser.parse_args()
    try:
        manifesto = resetar_banco(settings, confirmar=args.confirmar)
    except PermissionError as error:
        print(error, file=sys.stderr)
        return 1
    except (SQLAlchemyError, CommandError, ErroNegocio):
        print(
            "Falha no reset; alterações desfeitas. Confira a conexão, pare a API "
            "e tente novamente.",
            file=sys.stderr,
        )
        return 1
    get_total_usuarios_cache().invalidar()
    print("Banco local viajajunto recriado com migrações e seed atualizado.")
    print(
        f"Usuários: {len(manifesto['usuarios'])}; destinos: {len(manifesto['destinos_catalogo'])}; "
        f"atividades: {len(manifesto['atividades_catalogo'])}."
    )
    print("Inicie a API e faça login novamente no Swagger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
