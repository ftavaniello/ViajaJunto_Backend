import uuid

import pytest
from sqlalchemy import text

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.infrastructure.database import SessionLocal


@pytest.fixture
def email_teste() -> str:
    return f"teste-{uuid.uuid4().hex}@example.com"


@pytest.fixture
def db_session():
    session = SessionLocal()

    try:
        session.execute(text("SELECT 1"))
    except Exception:
        session.close()
        pytest.skip(
            "PostgreSQL indisponível - suba com `docker compose up -d db` "
            "para rodar os testes de integração."
        )

    yield session

    session.rollback()
    session.query(UsuarioModel).filter(UsuarioModel.email.like("teste-%")).delete()
    session.commit()
    session.close()
