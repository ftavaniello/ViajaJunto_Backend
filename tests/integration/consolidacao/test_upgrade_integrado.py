from decimal import Decimal

from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.infrastructure.database import Base
from tests.support.banco_isolado import banco_isolado, config_migracao, migrar


def test_migracoes_em_base_vazia_criam_todas_as_tabelas_sem_seed(banco_de_testes):
    with banco_isolado() as engine:
        assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM usuarios")) == 0
            assert conn.scalar(text("SELECT count(*) FROM viagens")) == 0
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == (
                ScriptDirectory.from_config(config_migracao()).get_current_head()
            )
        migrar(engine)  # Segunda aplicação não apaga nem duplica dados.


def test_upgrade_v1_para_head_preserva_planejamento_e_reviews(banco_de_testes):
    with banco_isolado("a3f1c9d27b45") as engine:
        with engine.begin() as c:
            usuario = c.scalar(
                text(
                    "INSERT INTO usuarios(nome,email,senha_hash) "
                    "VALUES ('Ana','upgrade@example.com','hash preservado') RETURNING id"
                )
            )
            membro = c.scalar(
                text(
                    "INSERT INTO usuarios(nome,email,senha_hash) "
                    "VALUES ('Bruno','membro@example.com','outro hash') RETURNING id"
                )
            )
            viagem = c.scalar(
                text(
                    "INSERT INTO viagens(criador_id,nome,data_inicio,data_fim,"
                    "status,codigo_convite,codigo_convite_expira_em) VALUES "
                    "(:u,'Roma antiga','2027-01-01','2027-01-10','em_andamento',"
                    "'CODIGOLEGADO',now()+interval '1 day') RETURNING id"
                ),
                {"u": usuario},
            )
            c.execute(
                text(
                    "INSERT INTO membros_viagem(viagem_id,usuario_id,papel) VALUES (:v,:u,'editor')"
                ),
                {"v": viagem, "u": membro},
            )
            destino = c.scalar(
                text(
                    "INSERT INTO destinos_catalogo(nome,pais_codigo,"
                    "google_place_id) VALUES ('Roma','IT','origem-legada') RETURNING id"
                )
            )
            atividade = c.scalar(
                text(
                    "INSERT INTO catalogo_atividades(destino_catalogo_id,"
                    "nome,categoria,google_place_id) VALUES (:d,'Coliseu','cultura',"
                    "'atividade-legada') RETURNING id"
                ),
                {"d": destino},
            )
            parada = c.scalar(
                text(
                    "INSERT INTO destinos_viagem(viagem_id,destino_catalogo_id,"
                    "ordem,data_chegada,data_saida,observacoes) VALUES "
                    "(:v,:d,1,'2027-01-01','2027-01-10','Anotação particular') RETURNING id"
                ),
                {"v": viagem, "d": destino},
            )
            ocorrencia = c.scalar(
                text(
                    "INSERT INTO atividades_viagem(destino_viagem_id,"
                    "catalogo_atividade_id,data,custo_previsto,status,"
                    "realizada_em,realizada_por_id) "
                    "VALUES (:p,:a,'2027-01-02',150.25,'realizada',now(),:u) RETURNING id"
                ),
                {"p": parada, "a": atividade, "u": usuario},
            )
            c.execute(
                text("INSERT INTO orcamentos(viagem_id,limite_total) VALUES (:v,1000)"),
                {"v": viagem},
            )
            review = c.scalar(
                text(
                    "INSERT INTO avaliacoes(usuario_id,catalogo_atividade_id,"
                    "atividade_viagem_id,nota,comentario) VALUES "
                    "(:u,:a,:o,5,'Excelente') RETURNING id"
                ),
                {"u": membro, "a": atividade, "o": ocorrencia},
            )
            comprovacao = c.scalar(
                text("SELECT realizada_em FROM atividades_viagem WHERE id=:i"), {"i": ocorrencia}
            )
        migrar(engine)
        with engine.connect() as c:
            assert (
                c.scalar(text("SELECT senha_hash FROM usuarios WHERE id=:i"), {"i": usuario})
                == "hash preservado"
            )
            assert (
                c.scalar(text("SELECT status FROM viagens WHERE id=:i"), {"i": viagem})
                == "confirmada"
            )
            assert tuple(
                c.execute(
                    text("SELECT usuario_id,papel FROM membros_viagem WHERE viagem_id=:i"),
                    {"i": viagem},
                ).one()
            ) == (membro, "editor")
            assert (
                c.scalar(text("SELECT observacoes FROM destinos_viagem WHERE id=:i"), {"i": parada})
                == "Anotação particular"
            )
            assert tuple(
                c.execute(
                    text(
                        "SELECT status,custo_previsto,realizada_em,realizada_por_id "
                        "FROM atividades_viagem WHERE id=:i"
                    ),
                    {"i": ocorrencia},
                ).one()
            ) == (
                "concluida",
                Decimal("150.25"),
                comprovacao,
                usuario,
            )
            assert c.scalar(
                text("SELECT limite_total FROM orcamentos WHERE viagem_id=:i"), {"i": viagem}
            ) == Decimal("1000.00")
            assert tuple(
                c.execute(
                    text(
                        "SELECT usuario_id,atividade_viagem_id,nota,comentario "
                        "FROM avaliacoes WHERE id=:i"
                    ),
                    {"i": review},
                ).one()
            ) == (
                membro,
                ocorrencia,
                5,
                "Excelente",
            )
            assert tuple(
                c.execute(
                    text("SELECT id_externo,fonte,categoria FROM destinos_catalogo WHERE id=:i"),
                    {"i": destino},
                ).one()
            ) == ("origem-legada", "manual", "cidade")
        migrar(engine)
        with engine.connect() as c:
            assert c.scalar(text("SELECT count(*) FROM avaliacoes")) == 1
