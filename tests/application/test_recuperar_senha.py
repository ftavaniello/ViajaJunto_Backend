"""Recuperacao de senha por email (RF03). Ver docs/recuperacao-de-senha.md."""
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.token_recuperacao_senha_repository_memory import (
    TokenRecuperacaoSenhaRepositoryMemory,
)
from app.adapters.outbound.persistence.token_revogado_repository_memory import (
    TokenRevogadoRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.consultar_usuario_autenticado import ConsultarUsuarioAutenticado
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.redefinir_senha import RedefinirSenha
from app.application.use_cases.solicitar_recuperacao_senha import SolicitarRecuperacaoSenha
from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.errors import DadosInvalidos, NaoAutenticado, TokenRecuperacaoInvalido
from tests.application.fakes import FakePasswordHasher, FakeTokenService

URL = "http://front.local/redefinir-senha"
INICIO = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


class Relogio:
    def __init__(self):
        self.agora = INICIO

    def __call__(self) -> datetime:
        return self.agora

    def avancar(self, **delta) -> None:
        self.agora += timedelta(**delta)


class Cenario:
    def __init__(self, falhar_envio: bool = False):
        self.repository = UsuarioRepositoryMemory()
        self.tokens = TokenRecuperacaoSenhaRepositoryMemory()
        self.email = EmailSenderMemory(falhar=falhar_envio)
        self.password_hasher = FakePasswordHasher()
        self.token_service = FakeTokenService()
        self.relogio = Relogio()
        self.uow = UnitOfWorkMemory()
        CriarUsuario(self.repository, self.password_hasher, UnitOfWorkMemory()).execute(
            nome="Livia", email="livia@example.com", senha="senha123"
        )

    def solicitar(self, email: str = "livia@example.com") -> None:
        SolicitarRecuperacaoSenha(
            self.repository, self.tokens, self.email, UnitOfWorkMemory(),
            url_redefinicao=URL, relogio=self.relogio,
        ).execute(email)

    def redefinir(self, token: str, senha_nova: str = "senhaNova456") -> None:
        RedefinirSenha(
            self.repository, self.tokens, self.password_hasher, self.uow, relogio=self.relogio
        ).execute(token, senha_nova)

    def token_do_ultimo_email(self) -> str:
        link = next(
            linha for linha in self.email.enviados[-1].corpo.splitlines()
            if linha.startswith(URL)
        )
        return parse_qs(urlparse(link).query)["token"][0]

    def login(self, senha: str) -> str:
        return AutenticarUsuario(
            self.repository, self.password_hasher, self.token_service
        ).execute(email="livia@example.com", senha=senha)


# --- solicitacao ---------------------------------------------------------------------


def test_solicitacao_envia_email_com_link_para_o_usuario():
    cenario = Cenario()

    cenario.solicitar()

    assert len(cenario.email.enviados) == 1
    mensagem = cenario.email.enviados[0]
    assert mensagem.destinatario == "livia@example.com"
    token = cenario.token_do_ultimo_email()
    assert token in mensagem.corpo
    assert "60 minutos" in mensagem.corpo


def test_solicitacao_grava_so_o_hash_do_token_com_validade_de_60_minutos():
    cenario = Cenario()

    cenario.solicitar()

    token = cenario.token_do_ultimo_email()
    [registro] = cenario.tokens.tokens.values()
    assert registro.token_hash == TokenRecuperacaoSenha.calcular_hash(token)
    assert registro.token_hash != token
    assert registro.usuario_id == 1
    assert registro.expira_em == INICIO + timedelta(minutes=60)
    assert registro.usado_em is None


def test_tokens_sao_imprevisiveis():
    cenario = Cenario()

    valores = set()
    for _ in range(5):
        cenario.solicitar()
        valores.add(cenario.token_do_ultimo_email())

    assert len(valores) == 5
    assert all(len(valor) >= 43 for valor in valores)  # 32 bytes em base64url


def test_email_nao_cadastrado_nao_envia_nada_nem_levanta_erro():
    cenario = Cenario()

    cenario.solicitar("ninguem@example.com")

    assert cenario.email.enviados == []
    assert cenario.tokens.tokens == {}


def test_nova_solicitacao_invalida_o_link_anterior():
    cenario = Cenario()
    cenario.solicitar()
    primeiro = cenario.token_do_ultimo_email()
    cenario.solicitar()
    segundo = cenario.token_do_ultimo_email()

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(primeiro)
    cenario.redefinir(segundo)


def test_falha_de_envio_nao_propaga_e_e_registrada_no_log(caplog):
    cenario = Cenario(falhar_envio=True)

    with caplog.at_level(logging.ERROR):
        cenario.solicitar()

    assert cenario.email.enviados == []
    assert "Falha ao enviar email de recuperacao do usuario 1" in caplog.text
    # O valor do token nao vai para o log, so o hash fica no repositorio.
    [registro] = cenario.tokens.tokens.values()
    assert registro.token_hash not in caplog.text


def test_falha_de_envio_permite_pedir_novo_link():
    cenario = Cenario(falhar_envio=True)
    cenario.solicitar()

    cenario.email.falhar = False
    cenario.solicitar()
    cenario.redefinir(cenario.token_do_ultimo_email())

    assert cenario.login("senhaNova456")


# --- redefinicao ---------------------------------------------------------------------


def test_redefinicao_troca_a_senha_e_confirma_a_transacao():
    cenario = Cenario()
    cenario.solicitar()

    cenario.redefinir(cenario.token_do_ultimo_email())

    assert cenario.uow.commits == 1
    usuario = cenario.repository.buscar_por_id(1)
    assert cenario.password_hasher.verificar("senhaNova456", usuario.senha_hash)
    assert not cenario.password_hasher.verificar("senha123", usuario.senha_hash)
    with pytest.raises(NaoAutenticado):
        cenario.login("senha123")
    assert cenario.login("senhaNova456")


def test_redefinicao_encerra_todas_as_sessoes():
    cenario = Cenario()
    token_acesso = cenario.login("senha123")
    cenario.solicitar()

    cenario.redefinir(cenario.token_do_ultimo_email())

    consultar = ConsultarUsuarioAutenticado(
        cenario.repository, cenario.token_service, TokenRevogadoRepositoryMemory()
    )
    with pytest.raises(NaoAutenticado):
        consultar.execute(token_acesso)
    assert consultar.execute(cenario.login("senhaNova456")).id == 1


def test_token_reutilizado_e_recusado():
    cenario = Cenario()
    cenario.solicitar()
    token = cenario.token_do_ultimo_email()
    cenario.redefinir(token)

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(token, senha_nova="outraSenha789")

    assert cenario.login("senhaNova456")


def test_token_vencido_e_recusado():
    cenario = Cenario()
    cenario.solicitar()
    cenario.relogio.avancar(minutes=60)

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(cenario.token_do_ultimo_email())

    assert cenario.login("senha123")


def test_token_ainda_vale_no_ultimo_minuto():
    cenario = Cenario()
    cenario.solicitar()
    cenario.relogio.avancar(minutes=59, seconds=59)

    cenario.redefinir(cenario.token_do_ultimo_email())

    assert cenario.login("senhaNova456")


@pytest.mark.parametrize("token", ["", "token-inventado", "a" * 43])
def test_token_invalido_e_recusado(token):
    cenario = Cenario()
    cenario.solicitar()

    with pytest.raises(TokenRecuperacaoInvalido, match="inválido ou expirado"):
        cenario.redefinir(token)

    assert cenario.uow.commits == 0
    assert cenario.login("senha123")


def test_hash_gravado_nao_serve_como_token():
    cenario = Cenario()
    cenario.solicitar()
    [registro] = cenario.tokens.tokens.values()

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(registro.token_hash)


def test_senha_nova_invalida_nao_gasta_o_token():
    cenario = Cenario()
    cenario.solicitar()
    token = cenario.token_do_ultimo_email()

    with pytest.raises(DadosInvalidos):
        cenario.redefinir(token, senha_nova="curta")

    cenario.redefinir(token)
    assert cenario.login("senhaNova456")


def test_token_de_conta_excluida_e_recusado():
    cenario = Cenario()
    cenario.solicitar()
    cenario.repository.deletar(1)

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(cenario.token_do_ultimo_email())


def test_troca_por_link_inutiliza_outros_links_pendentes():
    cenario = Cenario()
    cenario.solicitar()
    token = cenario.token_do_ultimo_email()
    # Link emitido por fora do fluxo normal (ex.: corrida entre duas solicitacoes).
    outro, valor_outro = TokenRecuperacaoSenha.emitir(1, INICIO, 60)
    cenario.tokens.salvar(outro)

    cenario.redefinir(token)

    with pytest.raises(TokenRecuperacaoInvalido):
        cenario.redefinir(valor_outro)
