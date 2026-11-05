from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.convite_viagem_repository_memory import (
    ConviteViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import UsuarioRepositoryMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.gerenciar_membros_viagem import GerenciarMembrosViagem
from app.domain.entities.usuario import Usuario
from app.domain.enums import PapelMembro
from app.domain.errors import (
    AcessoNegado,
    ConviteDeOutroEmail,
    ConviteInvalido,
    ConviteJaAceito,
    ConviteNaoEncontrado,
    DadosInvalidos,
    FalhaEnvioConvite,
    MembroJaParticipa,
    MembroNaoEncontrado,
    ViagemNaoEncontrada,
)
from app.domain.permissoes import AcaoViagem, PerfilViagem

AGORA = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
URL_CONVITE = "http://front.test/convite"
CRIADOR, EDITOR, VISUALIZADOR, CONVIDADO, ESTRANHO = 1, 2, 3, 4, 5
EMAIL_CONVIDADO = "convidado@example.com"


class Relogio:
    def __init__(self):
        self.agora = AGORA

    def __call__(self) -> datetime:
        return self.agora


@pytest.fixture
def usuarios():
    repo = UsuarioRepositoryMemory()
    for nome in ("criador", "editor", "visualizador", "convidado", "estranho"):
        repo.salvar(Usuario(nome=nome, email=f"{nome}@example.com", senha_hash="hash"))
    return repo


@pytest.fixture
def membros():
    return MembroViagemRepositoryMemory()


@pytest.fixture
def viagens(membros):
    return ViagemRepositoryMemory(membros)


@pytest.fixture
def convites():
    return ConviteViagemRepositoryMemory()


@pytest.fixture
def email_sender():
    return EmailSenderMemory()


@pytest.fixture
def relogio():
    return Relogio()


@pytest.fixture
def uow():
    return UnitOfWorkMemory()


@pytest.fixture
def acesso(viagens, membros):
    return PoliticaAcessoViagem(viagens, membros)


@pytest.fixture
def caso(viagens, membros, convites, usuarios, acesso, email_sender, uow, relogio):
    return GerenciarMembrosViagem(
        viagens, membros, convites, usuarios, acesso, email_sender, uow,
        url_convite=URL_CONVITE, agora=relogio,
    )


@pytest.fixture
def viagem(viagens, membros):
    viagem = CriarViagem(viagens, UnitOfWorkMemory()).execute(
        criador_id=CRIADOR,
        nome="Floripa",
        descricao=None,
        data_inicio=date(2027, 1, 10),
        data_fim=date(2027, 1, 20),
    )
    membros.adicionar(viagem.id, EDITOR, PapelMembro.EDITOR)
    membros.adicionar(viagem.id, VISUALIZADOR, PapelMembro.VISUALIZADOR)
    return viagem


def token_enviado(email_sender: EmailSenderMemory) -> str:
    link = next(
        linha for linha in email_sender.enviados[-1].corpo.splitlines()
        if linha.startswith(URL_CONVITE)
    )
    return parse_qs(urlparse(link).query)["token"][0]


def convidar(caso, viagem, email=EMAIL_CONVIDADO) -> str:
    caso.convidar(viagem.id, CRIADOR, email)
    return token_enviado(caso.email_sender)


# --- Envio do convite -------------------------------------------------------


def test_criador_convida_por_email_e_link_leva_o_token(caso, viagem, email_sender, uow):
    convite = caso.convidar(viagem.id, CRIADOR, EMAIL_CONVIDADO)

    mensagem = email_sender.enviados[0]
    assert mensagem.destinatario == EMAIL_CONVIDADO
    assert "Floripa" in mensagem.assunto
    assert "criador convidou você" in mensagem.corpo
    assert convite.email == EMAIL_CONVIDADO
    assert convite.expira_em == AGORA + timedelta(days=7)
    assert uow.commits == 1
    # Só o hash fica gravado.
    assert convite.token_hash != token_enviado(email_sender)


def test_email_e_normalizado(caso, viagem, email_sender):
    convite = caso.convidar(viagem.id, CRIADOR, "  Convidado@Example.COM ")
    assert convite.email == EMAIL_CONVIDADO
    assert email_sender.enviados[0].destinatario == EMAIL_CONVIDADO


def test_pode_convidar_email_sem_conta(caso, viagem, email_sender):
    caso.convidar(viagem.id, CRIADOR, "novo@example.com")
    assert email_sender.enviados[0].destinatario == "novo@example.com"


@pytest.mark.parametrize("email", ["criador@example.com", "editor@example.com"])
def test_nao_convida_quem_ja_participa(caso, viagem, email_sender, email):
    with pytest.raises(MembroJaParticipa):
        caso.convidar(viagem.id, CRIADOR, email)
    assert email_sender.enviados == []


def test_email_invalido(caso, viagem):
    with pytest.raises(DadosInvalidos):
        caso.convidar(viagem.id, CRIADOR, "nao-e-email")


def test_reenviar_invalida_o_link_anterior(caso, viagem, convites):
    antigo = convidar(caso, viagem)
    novo = convidar(caso, viagem)

    assert len(convites.listar_pendentes(viagem.id, AGORA)) == 1
    with pytest.raises(ConviteInvalido):
        caso.aceitar_convite(antigo, CONVIDADO)
    caso.aceitar_convite(novo, CONVIDADO)


def test_falha_no_email_nao_grava_convite(caso, viagem, convites, uow):
    caso.email_sender = EmailSenderMemory(falhar=True)

    with pytest.raises(FalhaEnvioConvite):
        caso.convidar(viagem.id, CRIADOR, EMAIL_CONVIDADO)
    assert uow.commits == 0
    assert uow.rollbacks == 1


@pytest.mark.parametrize("usuario", [EDITOR, VISUALIZADOR])
def test_colaborador_nao_convida_nem_ve_convites(caso, viagem, email_sender, usuario):
    with pytest.raises(AcessoNegado):
        caso.convidar(viagem.id, usuario, EMAIL_CONVIDADO)
    with pytest.raises(AcessoNegado):
        caso.listar_convites(viagem.id, usuario)
    assert email_sender.enviados == []


def test_estranho_nao_convida(caso, viagem):
    with pytest.raises(ViagemNaoEncontrada):
        caso.convidar(viagem.id, ESTRANHO, EMAIL_CONVIDADO)


# --- Aceite -----------------------------------------------------------------


def test_aceitar_entra_na_viagem_como_visualizador(caso, membros, acesso, viagem, convites):
    token = convidar(caso, viagem)

    participacao = caso.aceitar_convite(token, CONVIDADO)

    assert participacao.viagem.id == viagem.id
    assert participacao.papel_membro == PapelMembro.VISUALIZADOR
    assert membros.buscar_papel(viagem.id, CONVIDADO) == PapelMembro.VISUALIZADOR
    assert convites.listar_pendentes(viagem.id, AGORA) == []
    acesso.exigir(viagem.id, CONVIDADO, AcaoViagem.CONSULTAR)
    with pytest.raises(AcessoNegado):
        acesso.exigir(viagem.id, CONVIDADO, AcaoViagem.EDITAR)


def test_aceite_repetido_e_recusado(caso, membros, viagem):
    token = convidar(caso, viagem)
    caso.aceitar_convite(token, CONVIDADO)

    with pytest.raises(ConviteJaAceito):
        caso.aceitar_convite(token, CONVIDADO)
    assert len([m for m in membros.listar(viagem.id) if m.usuario_id == CONVIDADO]) == 1


def test_link_usado_nao_serve_depois_de_remocao(caso, membros, viagem):
    token = convidar(caso, viagem)
    caso.aceitar_convite(token, CONVIDADO)
    caso.remover_membro(viagem.id, CRIADOR, CONVIDADO)

    with pytest.raises(ConviteJaAceito):
        caso.aceitar_convite(token, CONVIDADO)
    assert membros.buscar_papel(viagem.id, CONVIDADO) is None


def test_link_encaminhado_para_outra_conta_nao_funciona(caso, membros, viagem):
    token = convidar(caso, viagem)

    with pytest.raises(ConviteDeOutroEmail):
        caso.aceitar_convite(token, ESTRANHO)
    assert membros.buscar_papel(viagem.id, ESTRANHO) is None
    # O convite continua valendo para o dono do email.
    caso.aceitar_convite(token, CONVIDADO)


def test_email_da_conta_com_maiusculas_aceita(caso, usuarios, membros, viagem):
    usuarios.salvar(Usuario(nome="Bia", email="Bia@Example.com", senha_hash="hash"))
    bia = usuarios.buscar_por_email("Bia@Example.com")
    token = convidar(caso, viagem, "bia@example.com")

    caso.aceitar_convite(token, bia.id)
    assert membros.buscar_papel(viagem.id, bia.id) == PapelMembro.VISUALIZADOR


@pytest.mark.parametrize("token", ["", "inexistente", "x" * 43])
def test_token_inexistente(caso, viagem, token):
    with pytest.raises(ConviteInvalido):
        caso.aceitar_convite(token, CONVIDADO)


def test_convite_expirado(caso, membros, viagem, relogio):
    token = convidar(caso, viagem)
    relogio.agora = AGORA + timedelta(days=7)

    with pytest.raises(ConviteInvalido):
        caso.aceitar_convite(token, CONVIDADO)
    assert membros.buscar_papel(viagem.id, CONVIDADO) is None


def test_convite_vale_ate_antes_de_expirar(caso, membros, viagem, relogio):
    token = convidar(caso, viagem)
    relogio.agora = AGORA + timedelta(days=7) - timedelta(seconds=1)

    caso.aceitar_convite(token, CONVIDADO)
    assert membros.buscar_papel(viagem.id, CONVIDADO) == PapelMembro.VISUALIZADOR


def test_quem_ja_participa_nao_e_rebaixado_pelo_convite(caso, usuarios, membros, viagem, convites):
    # Convidado entra por outro caminho antes de usar o link (ex.: convite anterior).
    token = convidar(caso, viagem)
    membros.adicionar(viagem.id, CONVIDADO, PapelMembro.EDITOR)

    with pytest.raises(MembroJaParticipa):
        caso.aceitar_convite(token, CONVIDADO)
    assert membros.buscar_papel(viagem.id, CONVIDADO) == PapelMembro.EDITOR


def test_vinculo_duplicado_e_barrado_no_repositorio(membros, viagem):
    with pytest.raises(MembroJaParticipa):
        membros.adicionar(viagem.id, EDITOR, PapelMembro.VISUALIZADOR)
    assert membros.buscar_papel(viagem.id, EDITOR) == PapelMembro.EDITOR


# --- Convites pendentes ------------------------------------------------------


def test_criador_lista_e_cancela_convite(caso, viagem):
    token = convidar(caso, viagem)
    convidar(caso, viagem, "outro@example.com")

    pendentes = caso.listar_convites(viagem.id, CRIADOR)
    assert [c.email for c in pendentes] == [EMAIL_CONVIDADO, "outro@example.com"]

    caso.cancelar_convite(viagem.id, CRIADOR, pendentes[0].id)

    assert [c.email for c in caso.listar_convites(viagem.id, CRIADOR)] == ["outro@example.com"]
    with pytest.raises(ConviteInvalido):
        caso.aceitar_convite(token, CONVIDADO)


def test_lista_de_pendentes_ignora_aceitos_e_expirados(caso, viagem, relogio):
    caso.aceitar_convite(convidar(caso, viagem), CONVIDADO)
    convidar(caso, viagem, "outro@example.com")
    assert [c.email for c in caso.listar_convites(viagem.id, CRIADOR)] == ["outro@example.com"]

    relogio.agora = AGORA + timedelta(days=8)
    assert caso.listar_convites(viagem.id, CRIADOR) == []


def test_cancelar_convite_inexistente_aceito_ou_de_outra_viagem(caso, viagens, viagem):
    convidar(caso, viagem)
    aceito = caso.listar_convites(viagem.id, CRIADOR)[0]
    caso.aceitar_convite(token_enviado(caso.email_sender), CONVIDADO)
    outra = CriarViagem(viagens, UnitOfWorkMemory()).execute(
        CRIADOR, "Outra", None, date(2027, 1, 10), date(2027, 1, 20)
    )

    for viagem_id, convite_id in [(viagem.id, 999), (viagem.id, aceito.id), (outra.id, aceito.id)]:
        with pytest.raises(ConviteNaoEncontrado):
            caso.cancelar_convite(viagem_id, CRIADOR, convite_id)


@pytest.mark.parametrize("usuario", [EDITOR, VISUALIZADOR])
def test_colaborador_nao_cancela_convite(caso, viagem, usuario):
    convidar(caso, viagem)
    convite = caso.listar_convites(viagem.id, CRIADOR)[0]
    with pytest.raises(AcessoNegado):
        caso.cancelar_convite(viagem.id, usuario, convite.id)


# --- Listagem de membros -----------------------------------------------------


@pytest.mark.parametrize("usuario", [CRIADOR, EDITOR, VISUALIZADOR])
def test_participantes_listam_membros_com_criador_primeiro(caso, viagem, usuario):
    participantes = caso.listar_membros(viagem.id, usuario)
    assert [(p.usuario_id, p.perfil) for p in participantes] == [
        (CRIADOR, PerfilViagem.CRIADOR),
        (EDITOR, PerfilViagem.EDITOR),
        (VISUALIZADOR, PerfilViagem.VISUALIZADOR),
    ]
    assert participantes[1].nome == "editor"
    assert participantes[1].email == "editor@example.com"


def test_estranho_nao_lista_membros(caso, viagem):
    with pytest.raises(ViagemNaoEncontrada):
        caso.listar_membros(viagem.id, ESTRANHO)


# --- Alterar papel e remover -------------------------------------------------


def test_criador_promove_visualizador_e_acesso_muda_na_proxima_operacao(caso, acesso, viagem):
    with pytest.raises(AcessoNegado):
        acesso.exigir(viagem.id, VISUALIZADOR, AcaoViagem.EDITAR)

    participante = caso.alterar_papel(viagem.id, CRIADOR, VISUALIZADOR, PapelMembro.EDITOR)

    assert participante.perfil == PerfilViagem.EDITOR
    acesso.exigir(viagem.id, VISUALIZADOR, AcaoViagem.EDITAR)


def test_criador_rebaixa_editor_e_acesso_muda_na_proxima_operacao(caso, acesso, viagem):
    caso.alterar_papel(viagem.id, CRIADOR, EDITOR, "visualizador")
    with pytest.raises(AcessoNegado):
        acesso.exigir(viagem.id, EDITOR, AcaoViagem.EDITAR)


def test_criador_remove_membro_e_acesso_some_na_proxima_operacao(caso, acesso, viagem, uow):
    caso.remover_membro(viagem.id, CRIADOR, EDITOR)

    assert uow.commits == 1
    with pytest.raises(ViagemNaoEncontrada):
        acesso.exigir(viagem.id, EDITOR, AcaoViagem.CONSULTAR)


def test_removido_volta_com_novo_convite_como_visualizador(caso, membros, viagem):
    caso.remover_membro(viagem.id, CRIADOR, EDITOR)
    caso.aceitar_convite(convidar(caso, viagem, "editor@example.com"), EDITOR)
    assert membros.buscar_papel(viagem.id, EDITOR) == PapelMembro.VISUALIZADOR


@pytest.mark.parametrize("ator", [EDITOR, VISUALIZADOR])
def test_colaborador_nao_altera_papel_nem_remove(caso, membros, viagem, ator):
    # Escalada de privilégio: nem para si mesmo nem para outro.
    for alvo in (EDITOR, VISUALIZADOR):
        with pytest.raises(AcessoNegado):
            caso.alterar_papel(viagem.id, ator, alvo, PapelMembro.EDITOR)
        with pytest.raises(AcessoNegado):
            caso.remover_membro(viagem.id, ator, alvo)
    assert membros.buscar_papel(viagem.id, EDITOR) == PapelMembro.EDITOR
    assert membros.buscar_papel(viagem.id, VISUALIZADOR) == PapelMembro.VISUALIZADOR


def test_estranho_nao_gerencia_membros(caso, viagem):
    with pytest.raises(ViagemNaoEncontrada):
        caso.alterar_papel(viagem.id, ESTRANHO, EDITOR, PapelMembro.VISUALIZADOR)
    with pytest.raises(ViagemNaoEncontrada):
        caso.remover_membro(viagem.id, ESTRANHO, EDITOR)


def test_criador_nao_pode_ser_alterado_nem_removido(caso, acesso, viagem):
    with pytest.raises(DadosInvalidos):
        caso.alterar_papel(viagem.id, CRIADOR, CRIADOR, PapelMembro.VISUALIZADOR)
    with pytest.raises(DadosInvalidos):
        caso.remover_membro(viagem.id, CRIADOR, CRIADOR)
    acesso.exigir(viagem.id, CRIADOR, AcaoViagem.GERENCIAR_MEMBROS)


@pytest.mark.parametrize("papel", ["criador", "admin", ""])
def test_papel_invalido(caso, viagem, papel):
    with pytest.raises(DadosInvalidos):
        caso.alterar_papel(viagem.id, CRIADOR, EDITOR, papel)


def test_alvo_que_nao_e_membro(caso, viagem):
    with pytest.raises(MembroNaoEncontrado):
        caso.alterar_papel(viagem.id, CRIADOR, ESTRANHO, PapelMembro.EDITOR)
    with pytest.raises(MembroNaoEncontrado):
        caso.remover_membro(viagem.id, CRIADOR, ESTRANHO)
