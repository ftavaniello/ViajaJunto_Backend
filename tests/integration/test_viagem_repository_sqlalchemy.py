from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.adapters.outbound.persistence.membro_viagem_repository_sqlalchemy import (
    SQLAlchemyMembroViagemRepository,
)
from app.adapters.outbound.persistence.unit_of_work_sqlalchemy import SQLAlchemyUnitOfWork
from app.adapters.outbound.persistence.usuario_repository_sqlalchemy import (
    SQLAlchemyUsuarioRepository,
)
from app.adapters.outbound.persistence.viagem_model import (
    MembroViagemModel,
    OrcamentoModel,
    ViagemModel,
)
from app.adapters.outbound.persistence.viagem_repository_sqlalchemy import (
    SQLAlchemyViagemRepository,
)
from app.application.use_cases.criar_viagem import CriarViagem
from app.domain.entities.usuario import Usuario
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, StatusViagem


def _usuario(db, email: str) -> int:
    return SQLAlchemyUsuarioRepository(db).salvar(
        Usuario(nome="Livia", email=email, senha_hash="hash")
    ).id


def _criar(db, criador_id: int, nome: str = "Europa", inicio=date(2027, 7, 1)) -> Viagem:
    return CriarViagem(SQLAlchemyViagemRepository(db), SQLAlchemyUnitOfWork(db)).execute(
        criador_id=criador_id, nome=nome, descricao="Férias",
        data_inicio=inicio, data_fim=date(2027, 7, 20),
    )


def _membro(db, viagem_id: int, usuario_id: int, papel: PapelMembro) -> None:
    db.add(MembroViagemModel(viagem_id=viagem_id, usuario_id=usuario_id, papel=papel.value))
    db.flush()


def test_salvar_e_buscar_viagem(db_session, email_teste):
    criador_id = _usuario(db_session, email_teste)

    viagem = _criar(db_session, criador_id)
    encontrada = SQLAlchemyViagemRepository(db_session).buscar_por_id(viagem.id)

    assert encontrada.nome == "Europa"
    assert encontrada.descricao == "Férias"
    assert encontrada.criador_id == criador_id
    assert encontrada.status == StatusViagem.PLANEJANDO
    assert encontrada.codigo_convite == viagem.codigo_convite
    assert encontrada.criado_em is not None


def test_atualizar_viagem_grava_status(db_session, email_teste):
    repository = SQLAlchemyViagemRepository(db_session)
    viagem = _criar(db_session, _usuario(db_session, email_teste))
    viagem.status = StatusViagem.CONFIRMADA

    repository.salvar(viagem)

    assert repository.buscar_por_id(viagem.id).status == StatusViagem.CONFIRMADA


def test_banco_rejeita_status_fora_do_rf07(db_session, email_teste):
    viagem = _criar(db_session, _usuario(db_session, email_teste))
    model = db_session.get(ViagemModel, viagem.id)
    model.status = "em_andamento"

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_listar_por_participante_inclui_viagens_como_membro(db_session, email_teste):
    criador_id = _usuario(db_session, email_teste)
    colaborador_id = _usuario(db_session, email_teste.replace("@", "-colab@"))
    repository = SQLAlchemyViagemRepository(db_session)
    propria = _criar(db_session, colaborador_id, "Própria", inicio=date(2027, 7, 5))
    compartilhada = _criar(db_session, criador_id, "Compartilhada")
    _criar(db_session, criador_id, "Privada")
    _membro(db_session, compartilhada.id, colaborador_id, PapelMembro.VISUALIZADOR)

    ids = [p.viagem.id for p in repository.listar_por_participante(colaborador_id, 20, 0)]

    assert ids == [compartilhada.id, propria.id]  # ordenadas por data de início


def test_buscar_papel_do_membro(db_session, email_teste):
    criador_id = _usuario(db_session, email_teste)
    editor_id = _usuario(db_session, email_teste.replace("@", "-editor@"))
    viagem = _criar(db_session, criador_id)
    _membro(db_session, viagem.id, editor_id, PapelMembro.EDITOR)
    membros = SQLAlchemyMembroViagemRepository(db_session)

    assert membros.buscar_papel(viagem.id, editor_id) == PapelMembro.EDITOR
    assert membros.buscar_papel(viagem.id, criador_id) is None


def test_deletar_viagem_remove_membros_e_orcamento(db_session, email_teste):
    criador_id = _usuario(db_session, email_teste)
    editor_id = _usuario(db_session, email_teste.replace("@", "-editor@"))
    viagem = _criar(db_session, criador_id)
    _membro(db_session, viagem.id, editor_id, PapelMembro.EDITOR)
    db_session.add(OrcamentoModel(viagem_id=viagem.id))
    db_session.flush()

    SQLAlchemyViagemRepository(db_session).deletar(viagem.id)
    db_session.expire_all()

    assert db_session.get(ViagemModel, viagem.id) is None
    assert db_session.scalars(
        select(MembroViagemModel).where(MembroViagemModel.viagem_id == viagem.id)
    ).all() == []
    assert db_session.scalars(
        select(OrcamentoModel).where(OrcamentoModel.viagem_id == viagem.id)
    ).all() == []


def test_exclusao_sem_commit_e_desfeita(db_session, email_teste):
    viagem = _criar(db_session, _usuario(db_session, email_teste))
    repository = SQLAlchemyViagemRepository(db_session)

    with SQLAlchemyUnitOfWork(db_session):
        repository.deletar(viagem.id)
        # sem commit: sair do bloco desfaz a exclusao

    assert repository.buscar_por_id(viagem.id) is not None


def test_listagem_paginada_com_vinculo_do_criador_e_multiplos_membros(db_session, email_teste):
    criador = _usuario(db_session, email_teste)
    editor = _usuario(db_session, email_teste.replace("@", "-editor@"))
    primeira = _criar(db_session, criador)
    segunda = _criar(db_session, editor)
    _membro(db_session, primeira.id, criador, PapelMembro.VISUALIZADOR)
    _membro(db_session, primeira.id, editor, PapelMembro.EDITOR)
    _membro(db_session, segunda.id, criador, PapelMembro.VISUALIZADOR)
    repository = SQLAlchemyViagemRepository(db_session)

    assert [p.viagem.id for p in repository.listar_por_participante(criador, 10, 0)] == [
        primeira.id, segunda.id,
    ]
    pagina = repository.listar_por_participante(criador, 1, 1)
    assert len(pagina) == 1
    assert pagina[0].viagem.id == segunda.id
    assert pagina[0].papel_membro == PapelMembro.VISUALIZADOR
    assert repository.listar_por_participante(criador, 1, 2) == []
