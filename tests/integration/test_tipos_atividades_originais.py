from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.adapters.outbound.persistence.catalogo_model import CatalogoAtividadeModel
from app.adapters.outbound.persistence.catalogo_repository_sqlalchemy import (
    SQLAlchemyCatalogoRepository,
)
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.viagem_model import ViagemModel
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.infrastructure.database import get_db
from app.infrastructure.dependencies import get_token_service
from app.main import app
from tests.support.banco_isolado import banco_isolado, config_migracao, migrar

ANTIGAS = ["alimentacao", "cultura", "lazer", "compras", "outros", "transporte"]
NOVAS = ["refeicao", "passeio", "passeio", "outro", "outro", "transporte"]


def test_migracao_preserva_registros_vinculos_custos_e_reviews(banco_de_testes):
    with banco_isolado("a7d3e8c25f61") as engine:
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO usuarios(id,nome,email,senha_hash) "
                    "VALUES (1,'Ana','tipos@example.com','hash')"
                )
            )
            c.execute(
                text(
                    "INSERT INTO viagens(id,criador_id,nome,data_inicio,data_fim) "
                    "VALUES (1,1,'Roma','2027-01-01','2027-01-10')"
                )
            )
            c.execute(
                text("INSERT INTO destinos_catalogo(id,nome,pais_codigo) VALUES (1,'Roma','IT')")
            )
            c.execute(
                text(
                    "INSERT INTO destinos_viagem(id,viagem_id,destino_catalogo_id,ordem,"
                    "data_chegada,data_saida) VALUES (1,1,1,1,'2027-01-01','2027-01-10')"
                )
            )
            c.execute(text("INSERT INTO orcamentos(viagem_id,limite_total) VALUES (1,1000)"))
            for i, categoria in enumerate(ANTIGAS, 1):
                c.execute(
                    text(
                        "INSERT INTO catalogo_atividades(id,destino_catalogo_id,nome,"
                        "categoria,fonte,id_externo) VALUES (:i,1,:n,:c,'manual',:e)"
                    ),
                    {"i": i, "n": f"Local {i}", "c": categoria, "e": f"origem-{i}"},
                )
                c.execute(
                    text(
                        "INSERT INTO atividades_viagem(id,destino_viagem_id,"
                        "catalogo_atividade_id,data,custo_previsto) "
                        "VALUES (:i,1,:i,'2027-01-02',:v)"
                    ),
                    {"i": i, "v": i * 10},
                )
                c.execute(
                    text(
                        "INSERT INTO avaliacoes(id,usuario_id,catalogo_atividade_id,"
                        "atividade_viagem_id,nota,comentario) VALUES (:i,1,:i,:i,4,'Preservado')"
                    ),
                    {"i": i},
                )
            tabelas = [
                "usuarios",
                "viagens",
                "destinos_viagem",
                "atividades_viagem",
                "avaliacoes",
                "orcamentos",
            ]
            antes = {t: list(c.execute(text(f"SELECT * FROM {t} ORDER BY id"))) for t in tabelas}
            catalogo_antes = list(
                c.execute(
                    text(
                        "SELECT id,nome,fonte,id_externo,criado_em "
                        "FROM catalogo_atividades ORDER BY id"
                    )
                )
            )
        migrar(engine)
        with engine.connect() as c:
            assert (
                list(c.scalars(text("SELECT categoria FROM catalogo_atividades ORDER BY id")))
                == NOVAS
            )
            assert {
                t: list(c.execute(text(f"SELECT * FROM {t} ORDER BY id"))) for t in tabelas
            } == antes
            assert (
                list(
                    c.execute(
                        text(
                            "SELECT id,nome,fonte,id_externo,criado_em "
                            "FROM catalogo_atividades ORDER BY id"
                        )
                    )
                )
                == catalogo_antes
            )
            assert c.scalar(text("SELECT sum(custo_previsto) FROM atividades_viagem")) == 210
            with pytest.raises(IntegrityError):
                with c.begin_nested():
                    c.execute(text("UPDATE catalogo_atividades SET categoria='cultura' WHERE id=1"))
        # Hospedagem nova pode ser criada e também preservada em downgrade canônico.
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO catalogo_atividades(id,destino_catalogo_id,nome,categoria) "
                    "VALUES (7,1,'Hotel','hospedagem')"
                )
            )
        config = config_migracao()
        with engine.begin() as c:
            config.attributes["connection"] = c
            command.downgrade(config, "a7d3e8c25f61")
            assert list(
                c.scalars(text("SELECT categoria FROM catalogo_atividades ORDER BY id"))
            ) == [
                "alimentacao",
                "cultura",
                "cultura",
                "outros",
                "outros",
                "transporte",
                "outros",
            ]
        migrar(engine)
        with engine.connect() as c:
            assert c.scalar(text("SELECT count(*) FROM catalogo_atividades")) == 7
            assert c.scalar(text("SELECT count(*) FROM avaliacoes")) == 6


def test_api_filtra_hospedagem_e_inclui_custo_no_resumo(db_session, email_teste):
    repo = SQLAlchemyCatalogoRepository(db_session)
    destino = repo.salvar_destino(DestinoCatalogo(nome="Roma", pais_codigo="IT"))
    hotel = repo.salvar_atividade(
        AtividadeCatalogo(
            destino=destino,
            nome="Hotel",
            categoria=CategoriaAtividade.HOSPEDAGEM,
        )
    )
    usuario = UsuarioModel(nome="Ana", email=email_teste, senha_hash="hash")
    db_session.add(usuario)
    db_session.flush()
    viagem = ViagemModel(
        criador_id=usuario.id, nome="Roma", data_inicio=date(2027, 1, 1), data_fim=date(2027, 1, 10)
    )
    db_session.add(viagem)
    db_session.commit()
    token = get_token_service().gerar_token(usuario.id, usuario.versao_sessao)
    headers = {"Authorization": "Bearer " + token}
    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as client:
            r = client.get("/catalogo/atividades", params={"categoria": "hospedagem"})
            assert r.status_code == 200
            assert [a["id"] for a in r.json()["itens"]] == [hotel.id]
            parada = client.post(
                f"/viagens/{viagem.id}/destinos",
                headers=headers,
                json={
                    "destino_catalogo_id": destino.id,
                    "data_chegada": "2027-01-01",
                    "data_saida": "2027-01-10",
                },
            )
            assert parada.status_code == 201
            r = client.post(
                f"/viagens/{viagem.id}/destinos/{parada.json()['id']}/atividades",
                headers=headers,
                json={
                    "catalogo_atividade_id": hotel.id,
                    "data": "2027-01-02",
                    "custo_previsto": "99.90",
                },
            )
            assert r.status_code == 201
            resumo = client.get(f"/viagens/{viagem.id}/orcamento", headers=headers).json()
            assert resumo["total_planejado"] == "99.90"
            assert [c["categoria"] for c in resumo["categorias"]] == [
                c.value for c in CategoriaAtividade
            ]
            assert (
                next(c for c in resumo["categorias"] if c["categoria"] == "hospedagem")[
                    "total_planejado"
                ]
                == "99.90"
            )
            for antiga in ANTIGAS[:-1]:
                assert (
                    client.get("/catalogo/atividades", params={"categoria": antiga}).status_code
                    == 422
                )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)
    assert (
        db_session.scalar(
            select(CatalogoAtividadeModel.id).where(CatalogoAtividadeModel.id == hotel.id)
        )
        == hotel.id
    )
