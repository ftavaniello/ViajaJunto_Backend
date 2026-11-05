from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.convite_viagem_model import ConviteViagemModel
from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.adapters.outbound.persistence.recuperacao_senha_model import TokenRecuperacaoSenhaModel
from app.adapters.outbound.persistence.roteiro_model import AtividadeViagemModel, DestinoViagemModel
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import MembroViagemModel, ViagemModel
from app.adapters.outbound.persistence.vinculos_conta_repository_sqlalchemy import (
    SQLAlchemyVinculosContaRepository,
)
from app.application.use_cases.excluir_usuario import ExcluirUsuario
from app.domain.enums import TipoNotificacao
from app.infrastructure.cache import get_total_usuarios_cache
from app.infrastructure.database import engine
from app.main import app
from tests.integration.test_avaliacoes_api import cenario as cenario
from tests.integration.test_avaliacoes_api import client as client


@pytest.mark.parametrize("papel", ["editor", "visualizador"])
def test_bloqueia_criador_com_qualquer_colaborador(client, cenario, db_session, papel):
    c = cenario
    db_session.execute(
        delete(MembroViagemModel).where(
            MembroViagemModel.usuario_id
            == c["usuarios"]["visualizador" if papel == "editor" else "editor"]
        )
    )
    db_session.commit()
    cache = Mock()
    app.dependency_overrides[get_total_usuarios_cache] = lambda: cache
    r = client.delete("/usuarios/me", headers=c["headers"]["criador"])
    assert r.status_code == 409
    assert "colaboradores" in r.json()["detail"]
    cache.invalidar.assert_not_called()
    # Inclusive a segunda viagem, sem membros, deve permanecer intacta.
    assert all(db_session.get(ViagemModel, i) for i in c["viagens"])
    assert all(db_session.get(AtividadeViagemModel, i) for i in c["atividades"])
    assert client.get("/usuarios/me", headers=c["headers"]["criador"]).status_code == 200


@pytest.mark.parametrize("papel", ["editor", "visualizador"])
def test_exclui_participante_preservando_planejamento_e_avaliacao(
    client,
    cenario,
    db_session,
    papel,
):
    c = cenario
    usuario_id = c["usuarios"][papel]
    review = AvaliacaoModel(
        usuario_id=usuario_id,
        catalogo_atividade_id=c["catalogo"][0],
        atividade_viagem_id=c["atividades"][0],
        nota=5,
        comentario="Ótima visita",
    )
    db_session.add(review)
    db_session.commit()
    review_id = review.id
    cache = Mock()
    app.dependency_overrides[get_total_usuarios_cache] = lambda: cache
    assert client.delete("/usuarios/me", headers=c["headers"][papel]).status_code == 204
    cache.invalidar.assert_called_once()
    db_session.expire_all()
    assert db_session.get(UsuarioModel, usuario_id) is None
    assert all(db_session.get(ViagemModel, i) for i in c["viagens"])
    assert all(db_session.get(AtividadeViagemModel, i) for i in c["atividades"])
    assert (
        db_session.scalar(
            select(MembroViagemModel.id).where(MembroViagemModel.usuario_id == usuario_id)
        )
        is None
    )
    review = db_session.get(AvaliacaoModel, review_id)
    assert (review.usuario_id, review.nota, review.comentario) == (None, 5, "Ótima visita")
    assert client.get("/usuarios/me", headers=c["headers"][papel]).status_code == 401
    publicas = client.get(f"/catalogo/atividades/{c['catalogo'][0]}/avaliacoes").json()
    assert publicas["itens"][0]["autor_nome"] is None


def test_exclui_criador_sem_membros_e_preserva_reviews(client, cenario, db_session):
    c = cenario
    db_session.execute(
        delete(MembroViagemModel).where(MembroViagemModel.viagem_id.in_(c["viagens"]))
    )
    review = AvaliacaoModel(
        usuario_id=c["usuarios"]["criador"],
        catalogo_atividade_id=c["catalogo"][0],
        atividade_viagem_id=c["atividades"][0],
        nota=4,
    )
    db_session.add(review)
    db_session.commit()
    review_id = review.id
    assert client.delete("/usuarios/me", headers=c["headers"]["criador"]).status_code == 204
    db_session.expire_all()
    assert all(db_session.get(ViagemModel, i) is None for i in c["viagens"])
    assert all(db_session.get(DestinoViagemModel, i) is None for i in c["paradas"])
    assert all(db_session.get(AtividadeViagemModel, i) is None for i in c["atividades"])
    review = db_session.get(AvaliacaoModel, review_id)
    assert (review.usuario_id, review.atividade_viagem_id, review.nota) == (None, None, 4)
    assert client.get("/usuarios/me", headers=c["headers"]["criador"]).status_code == 401


def test_falha_apos_delete_desfaz_conta_vinculos_e_autoria(client, cenario, db_session):
    c = cenario
    db_session.execute(
        delete(MembroViagemModel).where(MembroViagemModel.viagem_id.in_(c["viagens"]))
    )
    review = AvaliacaoModel(
        usuario_id=c["usuarios"]["criador"],
        catalogo_atividade_id=c["catalogo"][0],
        atividade_viagem_id=c["atividades"][0],
        nota=4,
    )
    db_session.add(review)
    db_session.commit()
    review_id = review.id
    cache = Mock()
    uow = SQLAlchemyUnitOfWork(db_session)
    uow.commit = Mock(side_effect=RuntimeError("falha antes de confirmar"))
    caso = ExcluirUsuario(
        SQLAlchemyUsuarioRepository(db_session),
        uow,
        SQLAlchemyVinculosContaRepository(db_session),
        cache,
    )
    with pytest.raises(RuntimeError, match="falha antes"):
        caso.execute(c["usuarios"]["criador"])
    db_session.expire_all()
    cache.invalidar.assert_not_called()
    review = db_session.get(AvaliacaoModel, review_id)
    assert (review.usuario_id, review.atividade_viagem_id) == (
        c["usuarios"]["criador"],
        c["atividades"][0],
    )
    assert all(db_session.get(ViagemModel, i) for i in c["viagens"])
    for i in c["atividades"]:
        assert db_session.get(AtividadeViagemModel, i).realizada_por_id == c["usuarios"]["criador"]
    assert client.get("/usuarios/me", headers=c["headers"]["criador"]).status_code == 200


def test_exige_autenticacao_e_documenta_conflito(client):
    assert client.delete("/usuarios/me").status_code == 401
    assert "409" in app.openapi()["paths"]["/usuarios/me"]["delete"]["responses"]


@pytest.mark.parametrize("novo_vinculo", ["viagem", "membro"])
def test_protecao_impede_novos_vinculos_concorrentes(banco_de_testes, novo_vinculo):
    # Dados confirmados para duas conexões independentes. Somente o banco _test
    # configurado em conftest; limpeza restrita aos ids gerados por este teste.
    with engine.begin() as conn:
        ids = [
            conn.scalar(
                insert(UsuarioModel)
                .values(
                    nome="Concorrência",
                    email=f"{uuid4().hex}@example.com",
                    senha_hash="hash",
                )
                .returning(UsuarioModel.id)
            )
            for _ in range(2)
        ]
        viagem_id = conn.scalar(
            insert(ViagemModel)
            .values(
                criador_id=ids[0],
                nome="Roteiro",
                data_inicio=date(2027, 1, 1),
                data_fim=date(2027, 1, 2),
            )
            .returning(ViagemModel.id)
        )
    try:
        with Session(engine) as exclusao:
            guard = SQLAlchemyVinculosContaRepository(exclusao)
            assert guard.bloquear_e_verificar_colaboradores(ids[0]) is False
            with engine.connect() as concorrente:
                tx = concorrente.begin()
                concorrente.execute(text("SET LOCAL lock_timeout = '300ms'"))
                with pytest.raises(OperationalError) as erro:
                    if novo_vinculo == "membro":
                        concorrente.execute(
                            insert(MembroViagemModel).values(
                                viagem_id=viagem_id,
                                usuario_id=ids[1],
                                papel="editor",
                            )
                        )
                    else:
                        concorrente.execute(
                            insert(ViagemModel).values(
                                criador_id=ids[0],
                                nome="Nova",
                                data_inicio=date(2027, 1, 1),
                                data_fim=date(2027, 1, 2),
                            )
                        )
                assert erro.value.orig.pgcode == "55P03"  # lock_not_available
                tx.rollback()
            exclusao.rollback()
        # Após liberar os locks, novos membros podem entrar e a verificação bloqueia.
        with engine.begin() as conn:
            conn.execute(
                insert(MembroViagemModel).values(
                    viagem_id=viagem_id,
                    usuario_id=ids[1],
                    papel="visualizador",
                )
            )
        with Session(engine) as exclusao:
            assert (
                SQLAlchemyVinculosContaRepository(exclusao).bloquear_e_verificar_colaboradores(
                    ids[0]
                )
                is True
            )
    finally:
        with engine.begin() as conn:
            conn.execute(delete(UsuarioModel).where(UsuarioModel.id.in_(ids)))


def test_exclusao_limpa_tokens_convites_e_notificacoes(client, cenario, db_session):
    c = cenario
    dono, outro = c["usuarios"]["criador"], c["usuarios"]["externo"]
    db_session.execute(
        delete(MembroViagemModel).where(MembroViagemModel.viagem_id.in_(c["viagens"]))
    )
    agora = datetime.now(timezone.utc)
    convite = ConviteViagemModel(
        viagem_id=c["viagens"][0],
        email="convite@example.com",
        token_hash=uuid4().hex * 2,
        convidado_por_id=dono,
        expira_em=agora + timedelta(days=1),
    )
    recuperacao = TokenRecuperacaoSenhaModel(
        usuario_id=dono,
        token_hash=uuid4().hex * 2,
        expira_em=agora + timedelta(hours=1),
    )
    # Uma notificação de outro destinatário conserva o histórico e perde as FKs.
    historico = NotificacaoModel(
        usuario_id=outro,
        ator_id=dono,
        viagem_id=c["viagens"][0],
        tipo=TipoNotificacao.VIAGEM_EXCLUIDA.value,
        mensagem="Histórico preservado",
    )
    propria = NotificacaoModel(
        usuario_id=dono,
        ator_id=outro,
        tipo=TipoNotificacao.VIAGEM_EXCLUIDA.value,
        mensagem="Notificação própria",
    )
    db_session.add_all([convite, recuperacao, historico, propria])
    db_session.commit()
    convite_id, recuperacao_id, historico_id, propria_id = (
        convite.id,
        recuperacao.id,
        historico.id,
        propria.id,
    )
    assert client.delete("/usuarios/me", headers=c["headers"]["criador"]).status_code == 204
    db_session.expire_all()
    assert db_session.get(ConviteViagemModel, convite_id) is None
    assert db_session.get(TokenRecuperacaoSenhaModel, recuperacao_id) is None
    assert db_session.get(NotificacaoModel, propria_id) is None
    historico = db_session.get(NotificacaoModel, historico_id)
    assert historico.ator_id is None and historico.viagem_id is None
    assert historico.mensagem == "Histórico preservado"
