"""Composição operacional; uma transação externa protege a carga inteira."""

from datetime import date

from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.seed_demonstracao_repository_sqlalchemy import (
    SQLAlchemySeedDemonstracaoRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.semear_demonstracao import SemearDemonstracao
from app.infrastructure.config import Settings
from app.infrastructure.dependencies import (
    get_atualizar_viagem,
    get_criar_viagem,
    get_gerenciar_atividades_viagem,
    get_gerenciar_destinos_viagem,
)


def executar_seed_completo(
    config: Settings,
    connection: Connection,
    referencia: date,
) -> tuple[bool, dict]:
    if config.APP_ENV != "development":
        raise PermissionError("Seed completo permitido somente em APP_ENV=development")
    if not connection.in_transaction():
        raise RuntimeError("O seed exige uma transação externa")
    with connection.begin_nested():
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            usuarios = SQLAlchemyUsuarioRepository(db)
            caso = SemearDemonstracao(
                SQLAlchemySeedDemonstracaoRepository(db),
                usuarios,
                CriarUsuario(usuarios, BcryptPasswordHasher(), SQLAlchemyUnitOfWork(db)),
                SQLAlchemyCatalogoRepository(db),
                get_criar_viagem(db),
                get_atualizar_viagem(db),
                get_gerenciar_destinos_viagem(db),
                get_gerenciar_atividades_viagem(db),
            )
            resultado = caso.execute(referencia)
            db.commit()
            return resultado
