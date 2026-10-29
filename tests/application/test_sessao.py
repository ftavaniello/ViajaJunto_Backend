"""Politica de sessao (RF02): logout revoga o token no servidor e a troca de senha
encerra todas as sessoes do usuario. Ver docs/sessoes-e-logout.md."""
import pytest

from app.adapters.outbound.persistence.token_revogado_repository_memory import (
    TokenRevogadoRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import (
    UsuarioRepositoryMemory,
)
from app.application.use_cases.alterar_senha import AlterarSenha
from app.application.use_cases.atualizar_usuario import AtualizarUsuario
from app.application.use_cases.autenticar_usuario import AutenticarUsuario
from app.application.use_cases.consultar_usuario_autenticado import ConsultarUsuarioAutenticado
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.encerrar_sessao import EncerrarSessao
from app.domain.errors import NaoAutenticado
from tests.application.fakes import EXPIRA_EM, FakePasswordHasher, FakeTokenService


class Cenario:
    def __init__(self):
        self.repository = UsuarioRepositoryMemory()
        self.password_hasher = FakePasswordHasher()
        self.token_service = FakeTokenService()
        self.revogados = TokenRevogadoRepositoryMemory()
        self.uow = UnitOfWorkMemory()
        CriarUsuario(self.repository, self.password_hasher, UnitOfWorkMemory()).execute(
            nome="Livia", email="livia@example.com", senha="senha123"
        )

    def login(self, senha: str = "senha123") -> str:
        return AutenticarUsuario(
            self.repository, self.password_hasher, self.token_service
        ).execute(email="livia@example.com", senha=senha)

    def logout(self, token: str) -> None:
        EncerrarSessao(self.token_service, self.revogados, self.uow).execute(token)

    def autenticar(self, token: str):
        return ConsultarUsuarioAutenticado(
            self.repository, self.token_service, self.revogados
        ).execute(token)


def test_token_valido_autentica_o_usuario():
    cenario = Cenario()

    assert cenario.autenticar(cenario.login()).id == 1


def test_logout_revoga_o_token_e_confirma_a_transacao():
    cenario = Cenario()
    token = cenario.login()

    cenario.logout(token)

    assert cenario.uow.commits == 1
    jti = cenario.token_service.verificar_token(token).jti
    assert cenario.revogados.revogados[jti] == (1, EXPIRA_EM)


def test_token_copiado_antes_do_logout_deixa_de_autenticar():
    cenario = Cenario()
    token = cenario.login()
    copia = str(token)

    cenario.logout(token)

    with pytest.raises(NaoAutenticado):
        cenario.autenticar(copia)


def test_logout_nao_encerra_outras_sessoes_do_usuario():
    cenario = Cenario()
    token_notebook = cenario.login()
    token_celular = cenario.login()

    cenario.logout(token_notebook)

    assert cenario.autenticar(token_celular).id == 1


def test_novo_login_depois_do_logout_funciona():
    cenario = Cenario()
    cenario.logout(cenario.login())

    assert cenario.autenticar(cenario.login()).id == 1


def test_logout_com_token_invalido_nao_revoga_nada():
    cenario = Cenario()

    with pytest.raises(NaoAutenticado):
        cenario.logout("token-invalido")

    assert cenario.revogados.revogados == {}
    assert cenario.uow.commits == 0


def test_troca_de_senha_encerra_todas_as_sessoes():
    cenario = Cenario()
    token_atual = cenario.login()
    outro_token = cenario.login()

    AlterarSenha(cenario.repository, cenario.password_hasher, UnitOfWorkMemory()).execute(
        usuario_id=1, senha_atual="senha123", senha_nova="senhaNova456"
    )

    for token in (token_atual, outro_token):
        with pytest.raises(NaoAutenticado):
            cenario.autenticar(token)
    assert cenario.autenticar(cenario.login(senha="senhaNova456")).id == 1


def test_troca_de_senha_incorreta_nao_encerra_sessoes():
    cenario = Cenario()
    token = cenario.login()

    with pytest.raises(ValueError):
        AlterarSenha(cenario.repository, cenario.password_hasher, UnitOfWorkMemory()).execute(
            usuario_id=1, senha_atual="errada", senha_nova="senhaNova456"
        )

    assert cenario.autenticar(token).id == 1


def test_atualizar_perfil_nao_encerra_sessoes():
    cenario = Cenario()
    token = cenario.login()

    AtualizarUsuario(cenario.repository, UnitOfWorkMemory()).execute(
        usuario_id=1, nome="Livia Bampi", email=None
    )

    assert cenario.autenticar(token).nome == "Livia Bampi"


def test_conta_excluida_nao_autentica():
    cenario = Cenario()
    token = cenario.login()
    cenario.repository.deletar(1)

    with pytest.raises(NaoAutenticado):
        cenario.autenticar(token)


def test_sem_token_nao_autentica():
    with pytest.raises(NaoAutenticado):
        Cenario().autenticar(None)
