import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.outbound.cache.redis_total_usuarios_cache import RedisTotalUsuariosCache
from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.convite_viagem_model import ConviteViagemModel
from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import TipoNotificacao
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
from app.infrastructure.email import get_email_sender
from app.main import app

SENHA = "SenhaIntegrada123!"


@pytest.fixture
def api_integrada(db_session):
    email = EmailSenderMemory()
    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_email_sender] = lambda: email
    app.dependency_overrides[get_total_usuarios_cache] = lambda: RedisTotalUsuariosCache(None)
    try:
        with TestClient(app) as client:
            yield client, email
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


@pytest.fixture
def catalogo_integrado(db_session):
    repo = SQLAlchemyCatalogoRepository(db_session)
    destino = repo.salvar_destino(
        DestinoCatalogo(
            nome="Roma",
            pais_codigo="IT",
            latitude=Decimal("41.890200"),
            longitude=Decimal("12.492200"),
        )
    )
    atividade = repo.salvar_atividade(
        AtividadeCatalogo(
            destino=destino,
            nome="Coliseu",
            categoria="cultura",
            descricao="Anfiteatro em Roma",
        )
    )
    db_session.commit()
    return destino.id, atividade.id


@pytest.fixture(scope="session")
def senha_matriz():
    return BcryptPasswordHasher().hash(SENHA)


@pytest.fixture
def matriz(db_session, catalogo_integrado, email_teste, senha_matriz):
    usuarios, headers = {}, {}
    for papel in ("criador", "editor", "visualizador", "externo", "removido"):
        usuario = UsuarioModel(
            nome=papel,
            email=email_teste.replace("@", f"-{papel}@"),
            senha_hash=senha_matriz,
        )
        db_session.add(usuario)
        db_session.flush()
        usuarios[papel] = usuario.id
        headers[papel] = {
            "Authorization": "Bearer "
            + get_token_service().gerar_token(
                usuario.id,
                usuario.versao_sessao,
            )
        }
    headers.update(anonimo={}, invalido={"Authorization": "Bearer token-invalido"})
    viagens, paradas, atividades, convites = [], [], [], []
    agora = datetime.now(timezone.utc)
    for indice in range(2):
        viagem = ViagemModel(
            criador_id=usuarios["criador"],
            nome=f"Viagem privada {indice}",
            data_inicio=date(2027, 1, 1),
            data_fim=date(2027, 1, 10),
        )
        db_session.add(viagem)
        db_session.flush()
        parada = DestinoViagemModel(
            viagem_id=viagem.id,
            destino_catalogo_id=catalogo_integrado[0],
            ordem=1,
            data_chegada=date(2027, 1, 1),
            data_saida=date(2027, 1, 10),
            observacoes=f"Segredo da parada {indice}",
        )
        db_session.add(parada)
        db_session.flush()
        atividade = AtividadeViagemModel(
            destino_viagem_id=parada.id,
            catalogo_atividade_id=catalogo_integrado[1],
            data=date(2027, 1, 2),
            custo_previsto=100,
            status="concluida",
            realizada_em=agora,
            realizada_por_id=usuarios["criador"],
        )
        convite = ConviteViagemModel(
            viagem_id=viagem.id,
            email=email_teste.replace("@", "-externo@"),
            token_hash=hashlib.sha256(f"segredo-{indice}".encode()).hexdigest(),
            convidado_por_id=usuarios["criador"],
            expira_em=agora + timedelta(days=1),
        )
        db_session.add_all([atividade, convite])
        db_session.flush()
        viagens.append(viagem.id)
        paradas.append(parada.id)
        atividades.append(atividade.id)
        convites.append(convite.id)
    for papel in ("editor", "visualizador", "removido"):
        membro = MembroViagemModel(
            viagem_id=viagens[0],
            usuario_id=usuarios[papel],
            papel="editor" if papel == "editor" else "visualizador",
        )
        db_session.add(membro)
        db_session.flush()
        if papel == "removido":
            db_session.delete(membro)  # Token emitido antes da perda do vínculo.
    db_session.add(
        MembroViagemModel(
            viagem_id=viagens[1],
            usuario_id=usuarios["externo"],
            papel="editor",
        )
    )
    notificacoes = {}
    for papel, usuario_id in usuarios.items():
        n = NotificacaoModel(
            usuario_id=usuario_id,
            tipo=TipoNotificacao.VIAGEM_EXCLUIDA.value,
            mensagem=f"Privada de {papel}",
        )
        db_session.add(n)
        db_session.flush()
        notificacoes[papel] = n.id
    db_session.commit()
    return dict(
        usuarios=usuarios,
        headers=headers,
        viagem_id=viagens[0],
        outra_viagem=viagens[1],
        destino_id=paradas[0],
        outro_destino=paradas[1],
        atividade_id=atividades[0],
        outra_atividade=atividades[1],
        convite_id=convites[0],
        outro_convite=convites[1],
        membro_id=usuarios["editor"],
        catalogo=catalogo_integrado,
        notificacoes=notificacoes,
    )
