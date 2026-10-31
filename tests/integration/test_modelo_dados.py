"""Testes do modelo de dados contra o PostgreSQL (decisões D1–D10).

Cada teste prova uma regra registrada em docs/decisoes-de-produto.md. Como os
demais testes de integração, rodam no banco exclusivo de testes e falham quando
ele não está acessível (ver `db_session` em conftest.py).
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.adapters.outbound.persistence.avaliacao_model import AvaliacaoModel
from app.adapters.outbound.persistence.catalogo_model import (
    CatalogoAtividadeModel,
    DestinoCatalogoModel,
)
from app.adapters.outbound.persistence.notificacao_model import NotificacaoModel
from app.adapters.outbound.persistence.recuperacao_senha_model import (
    TokenRecuperacaoSenhaModel,
)
from app.adapters.outbound.persistence.roteiro_model import (
    AtividadeViagemModel,
    DestinoViagemModel,
)
from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import (
    MembroViagemModel,
    OrcamentoModel,
    ViagemModel,
)
from app.domain.entities.usuario import Usuario
from app.domain.enums import PapelMembro, StatusAtividade, TipoNotificacao

PREFIXO = "teste-"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _usuario(db, email: str | None = None) -> UsuarioModel:
    usuario = UsuarioModel(
        nome="Usuário de teste",
        email=email or f"{PREFIXO}{uuid.uuid4().hex}@example.com",
        senha_hash="hash",
    )
    db.add(usuario)
    db.commit()
    return usuario


def _viagem(db, criador: UsuarioModel, **extra) -> ViagemModel:
    campos = {
        "criador_id": criador.id,
        "nome": f"{PREFIXO}viagem",
        "data_inicio": date(2027, 1, 10),
        "data_fim": date(2027, 1, 20),
        "codigo_convite": uuid.uuid4().hex[:10].upper(),
        "codigo_convite_expira_em": _agora() + timedelta(days=7),
    }
    campos.update(extra)
    viagem = ViagemModel(**campos)
    db.add(viagem)
    db.commit()
    return viagem


def _catalogo(db) -> tuple[DestinoCatalogoModel, CatalogoAtividadeModel]:
    destino = DestinoCatalogoModel(nome=f"{PREFIXO}Lisboa", pais_codigo="PT")
    db.add(destino)
    db.commit()
    atividade = CatalogoAtividadeModel(
        destino_catalogo_id=destino.id, nome=f"{PREFIXO}Torre de Belém", categoria="cultura"
    )
    db.add(atividade)
    db.commit()
    return destino, atividade


def _roteiro(db, viagem, destino, atividade, realizada=True):
    parada = DestinoViagemModel(
        viagem_id=viagem.id,
        destino_catalogo_id=destino.id,
        ordem=1,
        data_chegada=date(2027, 1, 10),
        data_saida=date(2027, 1, 15),
    )
    db.add(parada)
    db.commit()
    ativ = AtividadeViagemModel(
        destino_viagem_id=parada.id,
        catalogo_atividade_id=atividade.id,
        data=date(2027, 1, 11),
        status=StatusAtividade.CONCLUIDA.value if realizada else "pendente",
        realizada_em=_agora() if realizada else None,
    )
    db.add(ativ)
    db.commit()
    return parada, ativ


@pytest.fixture(autouse=True)
def limpeza(db_session):
    """Remove o que os testes criam e que não depende de usuário (catálogo)."""
    yield
    db_session.rollback()
    db_session.execute(delete(ViagemModel).where(ViagemModel.nome.like(f"{PREFIXO}%")))
    db_session.execute(
        delete(CatalogoAtividadeModel).where(CatalogoAtividadeModel.nome.like(f"{PREFIXO}%"))
    )
    db_session.execute(
        delete(DestinoCatalogoModel).where(DestinoCatalogoModel.nome.like(f"{PREFIXO}%"))
    )
    db_session.commit()


# --- D1: identificador da viagem x código de convite -----------------------------------


def test_id_da_viagem_e_inteiro_e_distinto_do_codigo_de_convite(db_session):
    viagem = _viagem(db_session, _usuario(db_session), codigo_convite="ABCD234567")

    assert isinstance(viagem.id, int)
    assert viagem.codigo_convite == "ABCD234567"


def test_codigo_de_convite_e_unico(db_session):
    criador = _usuario(db_session)
    _viagem(db_session, criador, codigo_convite="DUPLICADO22")

    with pytest.raises(IntegrityError):
        _viagem(db_session, criador, codigo_convite="DUPLICADO22")


def test_periodo_da_viagem_nao_pode_terminar_antes_de_comecar(db_session):
    with pytest.raises(IntegrityError):
        _viagem(db_session, _usuario(db_session), data_fim=date(2027, 1, 1))


def test_moeda_deve_ter_tres_letras_e_padrao_e_brl(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    assert viagem.moeda == "BRL"
    assert viagem.status == "planejando"

    viagem.moeda = "BR"
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- D3: papéis ------------------------------------------------------------------------


def test_papel_de_membro_so_aceita_editor_ou_visualizador(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    membro = _usuario(db_session)

    db_session.add(MembroViagemModel(viagem_id=viagem.id, usuario_id=membro.id, papel="criador"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_usuario_nao_entra_duas_vezes_na_mesma_viagem(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    membro = _usuario(db_session)
    db_session.add(
        MembroViagemModel(
            viagem_id=viagem.id, usuario_id=membro.id, papel=PapelMembro.VISUALIZADOR.value
        )
    )
    db_session.commit()

    db_session.add(
        MembroViagemModel(
            viagem_id=viagem.id, usuario_id=membro.id, papel=PapelMembro.EDITOR.value
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_orcamento_e_unico_por_viagem_e_limite_nao_negativo(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    db_session.add(OrcamentoModel(viagem_id=viagem.id, limite_total=None))
    db_session.commit()

    db_session.add(OrcamentoModel(viagem_id=viagem.id, limite_total=100))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    viagem2 = _viagem(db_session, _usuario(db_session))
    db_session.add(OrcamentoModel(viagem_id=viagem2.id, limite_total=-1))
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- D2 e D3: avaliações e comprovação -------------------------------------------------


def test_avaliacao_unica_por_usuario_e_atividade_do_catalogo(db_session):
    usuario = _usuario(db_session)
    _, atividade = _catalogo(db_session)
    db_session.add(
        AvaliacaoModel(usuario_id=usuario.id, catalogo_atividade_id=atividade.id, nota=5)
    )
    db_session.commit()

    db_session.add(
        AvaliacaoModel(usuario_id=usuario.id, catalogo_atividade_id=atividade.id, nota=3)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("nota", [0, 6])
def test_nota_fora_de_1_a_5_e_rejeitada(db_session, nota):
    usuario = _usuario(db_session)
    _, atividade = _catalogo(db_session)

    db_session.add(
        AvaliacaoModel(usuario_id=usuario.id, catalogo_atividade_id=atividade.id, nota=nota)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_atividade_marcada_como_realizada_exige_data_da_comprovacao(db_session):
    usuario = _usuario(db_session)
    viagem = _viagem(db_session, usuario)
    destino, atividade = _catalogo(db_session)
    _, ativ = _roteiro(db_session, viagem, destino, atividade, realizada=False)

    ativ.status = StatusAtividade.CONCLUIDA.value
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- D6/D7: roteiro --------------------------------------------------------------------


def test_ordem_dos_destinos_e_unica_mas_permite_trocar_posicoes(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    destino, _ = _catalogo(db_session)
    a, b = (
        DestinoViagemModel(
            viagem_id=viagem.id,
            destino_catalogo_id=destino.id,
            ordem=ordem,
            data_chegada=date(2027, 1, 10),
            data_saida=date(2027, 1, 12),
        )
        for ordem in (1, 2)
    )
    db_session.add_all([a, b])
    db_session.commit()

    # Trocar 1 <-> 2 na mesma transação: só funciona porque a unicidade é adiada.
    a.ordem, b.ordem = 2, 1
    db_session.commit()
    # Nos testes o commit vira SAVEPOINT, que nao verifica constraints adiadas;
    # IMMEDIATE faz agora a verificacao que o COMMIT real faria.
    db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (a.ordem, b.ordem) == (2, 1)

    # Duplicar a posição continua proibido no commit.
    b.ordem = 2
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_permanencia_no_destino_nao_pode_terminar_antes_de_comecar(db_session):
    viagem = _viagem(db_session, _usuario(db_session))
    destino, _ = _catalogo(db_session)

    db_session.add(
        DestinoViagemModel(
            viagem_id=viagem.id,
            destino_catalogo_id=destino.id,
            ordem=1,
            data_chegada=date(2027, 1, 12),
            data_saida=date(2027, 1, 10),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_codigo_do_pais_deve_ser_iso_alfa2_em_maiusculas(db_session):
    db_session.add(DestinoCatalogoModel(nome=f"{PREFIXO}Porto", pais_codigo="pt"))
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- D10: efeitos das exclusões --------------------------------------------------------


def test_excluir_viagem_remove_o_roteiro_mas_preserva_catalogo_e_avaliacao(db_session):
    usuario = _usuario(db_session)
    viagem = _viagem(db_session, usuario)
    destino, atividade = _catalogo(db_session)
    parada, ativ = _roteiro(db_session, viagem, destino, atividade)
    avaliacao = AvaliacaoModel(
        usuario_id=usuario.id,
        catalogo_atividade_id=atividade.id,
        atividade_viagem_id=ativ.id,
        nota=4,
    )
    db_session.add(avaliacao)
    db_session.commit()
    parada_id, ativ_id, atividade_id, avaliacao_id = (
        parada.id, ativ.id, atividade.id, avaliacao.id
    )

    db_session.delete(viagem)
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(DestinoViagemModel, parada_id) is None
    assert db_session.get(AtividadeViagemModel, ativ_id) is None
    assert db_session.get(CatalogoAtividadeModel, atividade_id) is not None
    kept = db_session.get(AvaliacaoModel, avaliacao_id)
    assert kept is not None and kept.nota == 4
    assert kept.atividade_viagem_id is None


def test_excluir_viagem_preserva_a_notificacao_dos_membros(db_session):
    criador = _usuario(db_session)
    membro = _usuario(db_session)
    viagem = _viagem(db_session, criador)
    notificacao = NotificacaoModel(
        usuario_id=membro.id,
        tipo=TipoNotificacao.VIAGEM_EXCLUIDA.value,
        viagem_id=viagem.id,
        ator_id=criador.id,
        mensagem="A viagem foi excluída pelo criador.",
    )
    db_session.add(notificacao)
    db_session.commit()
    notificacao_id = notificacao.id

    db_session.delete(viagem)
    db_session.commit()
    db_session.expire_all()

    kept = db_session.get(NotificacaoModel, notificacao_id)
    assert kept is not None and kept.viagem_id is None


def test_excluir_conta_do_criador_remove_suas_viagens_e_anonimiza_avaliacoes(db_session):
    criador = _usuario(db_session)
    membro = _usuario(db_session)
    viagem = _viagem(db_session, criador)
    db_session.add(
        MembroViagemModel(
            viagem_id=viagem.id, usuario_id=membro.id, papel=PapelMembro.EDITOR.value
        )
    )
    _, atividade = _catalogo(db_session)
    avaliacao = AvaliacaoModel(usuario_id=criador.id, catalogo_atividade_id=atividade.id, nota=5)
    db_session.add(avaliacao)
    db_session.commit()
    viagem_id, avaliacao_id = viagem.id, avaliacao.id

    SQLAlchemyUsuarioRepository(db_session).deletar(criador.id)
    db_session.expire_all()

    assert db_session.get(ViagemModel, viagem_id) is None
    assert db_session.execute(
        select(MembroViagemModel).where(MembroViagemModel.viagem_id == viagem_id)
    ).first() is None
    kept = db_session.get(AvaliacaoModel, avaliacao_id)
    assert kept is not None and kept.usuario_id is None and kept.nota == 5


def test_excluir_conta_de_membro_remove_so_a_participacao(db_session):
    criador = _usuario(db_session)
    membro = _usuario(db_session)
    viagem = _viagem(db_session, criador)
    db_session.add(
        MembroViagemModel(
            viagem_id=viagem.id, usuario_id=membro.id, papel=PapelMembro.VISUALIZADOR.value
        )
    )
    db_session.commit()

    SQLAlchemyUsuarioRepository(db_session).deletar(membro.id)
    db_session.expire_all()

    assert db_session.get(ViagemModel, viagem.id) is not None
    assert db_session.execute(
        select(MembroViagemModel).where(MembroViagemModel.viagem_id == viagem.id)
    ).first() is None


def test_catalogo_em_uso_nao_pode_ser_excluido(db_session):
    usuario = _usuario(db_session)
    viagem = _viagem(db_session, usuario)
    destino, atividade = _catalogo(db_session)
    _roteiro(db_session, viagem, destino, atividade)

    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM destinos_catalogo WHERE id = :i"), {"i": destino.id})


# --- D9: recuperação de senha e notificações -------------------------------------------


def test_token_de_recuperacao_tem_hash_unico_e_some_com_a_conta(db_session):
    usuario = _usuario(db_session)
    hash_ = uuid.uuid4().hex + uuid.uuid4().hex  # 64 caracteres hex
    db_session.add(
        TokenRecuperacaoSenhaModel(
            usuario_id=usuario.id, token_hash=hash_, expira_em=_agora() + timedelta(hours=1)
        )
    )
    db_session.commit()

    db_session.add(
        TokenRecuperacaoSenhaModel(
            usuario_id=usuario.id, token_hash=hash_, expira_em=_agora() + timedelta(hours=1)
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    SQLAlchemyUsuarioRepository(db_session).deletar(usuario.id)
    assert db_session.execute(
        select(TokenRecuperacaoSenhaModel).where(TokenRecuperacaoSenhaModel.token_hash == hash_)
    ).first() is None


def test_tipo_de_notificacao_invalido_e_rejeitado(db_session):
    usuario = _usuario(db_session)
    db_session.add(NotificacaoModel(usuario_id=usuario.id, tipo="spam", mensagem="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


# --- usuario.criado_em -----------------------------------------------------------------


def test_usuario_recebe_criado_em_do_banco(db_session, email_teste):
    repo = SQLAlchemyUsuarioRepository(db_session)

    salvo = repo.salvar(Usuario(nome="Ana", email=email_teste, senha_hash="hash"))

    assert salvo.criado_em is not None
    assert abs(_agora() - salvo.criado_em) < timedelta(minutes=1)
