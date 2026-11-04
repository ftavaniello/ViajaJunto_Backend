"""Notificações in-app (RF21): quem recebe, quando gera e isolamento por usuário."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.adapters.outbound.email.email_sender_memory import EmailSenderMemory
from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.convite_viagem_repository_memory import (
    ConviteViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.notificacao_repository_memory import (
    NotificacaoRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import UsuarioRepositoryMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.notificador_viagem import NotificadorViagem, descrever_mudancas
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.excluir_viagem import ExcluirViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.application.use_cases.gerenciar_membros_viagem import GerenciarMembrosViagem
from app.application.use_cases.gerenciar_notificacoes import GerenciarNotificacoes
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.entities.convite_viagem import ConviteViagem
from app.domain.entities.destino_viagem import DestinoViagem
from app.domain.entities.notificacao import Notificacao
from app.domain.entities.usuario import Usuario
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, StatusAtividade, StatusViagem, TipoNotificacao
from app.domain.errors import AcessoNegado, DadosInvalidos, NotificacaoNaoEncontrada

AGORA = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
CRIADOR, EDITOR, VISUALIZADOR, CONVIDADO, ESTRANHO = 1, 2, 3, 4, 5
VIAGEM = 1


class Cenario:
    """Viagem "Europa" do criador, com editor e visualizador, e uma parada em Lisboa."""

    def __init__(self):
        self.usuarios = UsuarioRepositoryMemory()
        for nome in ("Ana", "Bruno", "Carla", "Diego", "Elisa"):
            self.usuarios.salvar(
                Usuario(nome=nome, email=f"{nome.lower()}@example.com", senha_hash="hash")
            )
        self.membros = MembroViagemRepositoryMemory()
        self.viagens = ViagemRepositoryMemory(self.membros)
        self.viagens.salvar(
            Viagem(
                nome="Europa",
                criador_id=CRIADOR,
                data_inicio=date(2027, 7, 1),
                data_fim=date(2027, 7, 20),
            )
        )
        self.membros.adicionar(VIAGEM, EDITOR, PapelMembro.EDITOR)
        self.membros.adicionar(VIAGEM, VISUALIZADOR, PapelMembro.VISUALIZADOR)

        self.catalogo = CatalogoRepositoryMemory()
        lisboa = self.catalogo.salvar_destino(DestinoCatalogo(nome="Lisboa", pais_codigo="PT"))
        self.museu = self.catalogo.salvar_atividade(
            AtividadeCatalogo(destino=lisboa, nome="Museu", categoria="cultura")
        )
        self.lisboa = lisboa
        self.destinos = DestinoViagemRepositoryMemory()
        self.parada = self.destinos.salvar(
            DestinoViagem(
                viagem_id=VIAGEM,
                destino=lisboa,
                ordem=1,
                data_chegada=date(2027, 7, 2),
                data_saida=date(2027, 7, 5),
            )
        )
        self.atividades = AtividadeViagemRepositoryMemory()
        self.notificacoes = NotificacaoRepositoryMemory()
        self.uow = UnitOfWorkMemory()
        self.acesso = PoliticaAcessoViagem(self.viagens, self.membros)
        self.notificador = NotificadorViagem(self.notificacoes, self.membros, self.usuarios)

    def caso_atividades(self, **portas) -> GerenciarAtividadesViagem:
        return GerenciarAtividadesViagem(
            portas.get("repository", self.atividades),
            self.destinos,
            self.catalogo,
            self.acesso,
            self.uow,
            agora=lambda: AGORA,
            notificador=self.notificador,
        )

    def caso_destinos(self) -> GerenciarDestinosViagem:
        return GerenciarDestinosViagem(
            self.destinos, self.catalogo, self.acesso, self.uow, notificador=self.notificador
        )

    def caso_membros(self) -> GerenciarMembrosViagem:
        return GerenciarMembrosViagem(
            self.viagens,
            self.membros,
            ConviteViagemRepositoryMemory(),
            self.usuarios,
            self.acesso,
            EmailSenderMemory(),
            self.uow,
            url_convite="http://front.test/convite",
            agora=lambda: AGORA,
            notificador=self.notificador,
        )

    def criar_atividade(self, usuario_id: int = CRIADOR, **campos):
        return self.caso_atividades().criar(
            **{
                "viagem_id": VIAGEM,
                "destino_id": self.parada.id,
                "usuario_id": usuario_id,
                "catalogo_atividade_id": self.museu.id,
                "data": date(2027, 7, 3),
                **campos,
            }
        )

    def destinatarios(self) -> list[int]:
        return sorted(n.usuario_id for n in self.notificacoes.notificacoes.values())


@pytest.fixture
def cenario():
    return Cenario()


# --- Destinatários ---------------------------------------------------------------


def test_alteracao_do_editor_avisa_criador_e_demais_membros_menos_ele(cenario):
    atividade = cenario.criar_atividade()
    cenario.notificacoes.notificacoes.clear()

    cenario.caso_atividades().atualizar(
        VIAGEM, cenario.parada.id, atividade.id, EDITOR, data=date(2027, 7, 4)
    )

    assert cenario.destinatarios() == [CRIADOR, VISUALIZADOR]
    aviso = cenario.notificacoes.do_usuario(CRIADOR)[0]
    assert aviso.tipo == TipoNotificacao.ATIVIDADE_ALTERADA
    assert aviso.viagem_id == VIAGEM and aviso.ator_id == EDITOR and not aviso.lida
    assert aviso.mensagem == (
        'Bruno alterou a data da atividade "Museu" em Lisboa (04/07/2027) na viagem "Europa".'
    )


def test_alteracao_do_criador_avisa_todos_os_colaboradores(cenario):
    cenario.criar_atividade(usuario_id=CRIADOR)

    assert cenario.destinatarios() == [EDITOR, VISUALIZADOR]
    assert cenario.notificacoes.do_usuario(EDITOR)[0].mensagem.startswith(
        'Ana adicionou a atividade "Museu"'
    )


def test_quem_nao_participa_nunca_recebe(cenario):
    cenario.criar_atividade()

    assert cenario.notificacoes.do_usuario(ESTRANHO) == []
    assert cenario.notificacoes.do_usuario(CRIADOR) == []


def test_viagem_sem_colaboradores_nao_gera_aviso(cenario):
    cenario.membros.remover_da_viagem(VIAGEM)

    cenario.criar_atividade()

    assert cenario.notificacoes.notificacoes == {}


# --- O que gera aviso -------------------------------------------------------------


def test_varias_mudancas_numa_atividade_geram_um_aviso_por_pessoa(cenario):
    atividade = cenario.criar_atividade()
    cenario.notificacoes.notificacoes.clear()

    cenario.caso_atividades().atualizar(
        VIAGEM,
        cenario.parada.id,
        atividade.id,
        CRIADOR,
        hora_inicio=time(10),
        status=StatusAtividade.CONFIRMADA,
    )

    assert cenario.destinatarios() == [EDITOR, VISUALIZADOR]
    assert "alterou o horário e o status para confirmada da atividade" in (
        cenario.notificacoes.do_usuario(EDITOR)[0].mensagem
    )


@pytest.mark.parametrize(
    "campos",
    [
        {},
        {"data": date(2027, 7, 3)},
        {"custo_previsto": Decimal("50.00")},
        {"duracao_minutos": 90},
    ],
    ids=["nada", "mesma-data", "custo", "duracao"],
)
def test_atualizacao_sem_mudanca_relevante_nao_avisa(cenario, campos):
    atividade = cenario.criar_atividade()
    cenario.notificacoes.notificacoes.clear()

    cenario.caso_atividades().atualizar(VIAGEM, cenario.parada.id, atividade.id, EDITOR, **campos)

    assert cenario.notificacoes.notificacoes == {}


def test_remover_atividade_avisa(cenario):
    atividade = cenario.criar_atividade()
    cenario.notificacoes.notificacoes.clear()

    cenario.caso_atividades().remover(VIAGEM, cenario.parada.id, atividade.id, EDITOR)

    assert cenario.destinatarios() == [CRIADOR, VISUALIZADOR]
    assert cenario.notificacoes.do_usuario(CRIADOR)[0].mensagem.startswith(
        'Bruno removeu a atividade "Museu"'
    )


def test_destinos_adicionar_mudar_datas_e_remover_avisam(cenario):
    caso = cenario.caso_destinos()

    novo = caso.criar(
        VIAGEM, EDITOR, cenario.lisboa.id, date(2027, 7, 10), date(2027, 7, 12)
    )
    caso.atualizar(VIAGEM, novo.id, EDITOR, data_saida=date(2027, 7, 13))
    caso.atualizar(VIAGEM, novo.id, EDITOR, hospedagem="Hotel Azul")  # não avisa
    caso.reordenar(VIAGEM, EDITOR, [novo.id, cenario.parada.id])  # não avisa
    caso.remover(VIAGEM, novo.id, EDITOR)

    mensagens = [n.mensagem for n in cenario.notificacoes.do_usuario(CRIADOR)]
    assert mensagens == [
        'Bruno adicionou o destino Lisboa (10/07/2027 a 12/07/2027) no roteiro da viagem "Europa".',
        "Bruno alterou as datas do destino Lisboa (10/07/2027 a 13/07/2027) "
        'no roteiro da viagem "Europa".',
        'Bruno removeu o destino Lisboa (10/07/2027 a 13/07/2027) no roteiro da viagem "Europa".',
    ]
    tipos = {n.tipo for n in cenario.notificacoes.notificacoes.values()}
    assert tipos == {TipoNotificacao.ROTEIRO_ALTERADO}
    assert cenario.notificacoes.do_usuario(EDITOR) == []


def test_atualizar_viagem_avisa_so_nome_datas_e_status(cenario):
    caso = AtualizarViagem(
        cenario.viagens, cenario.acesso, cenario.uow, cenario.destinos,
        notificador=cenario.notificador,
    )

    caso.execute(VIAGEM, CRIADOR, descricao="Só a descrição")
    assert cenario.notificacoes.notificacoes == {}

    caso.execute(VIAGEM, EDITOR, nome="Europa 2027", status=StatusViagem.CONFIRMADA)

    assert cenario.destinatarios() == [CRIADOR, VISUALIZADOR]
    aviso = cenario.notificacoes.do_usuario(CRIADOR)[0]
    assert aviso.tipo == TipoNotificacao.VIAGEM_ALTERADA
    assert aviso.mensagem == (
        'Bruno alterou o nome e o status para confirmada da viagem "Europa 2027" '
        "(01/07/2027 a 20/07/2027)."
    )


def test_excluir_viagem_avisa_os_colaboradores_e_o_aviso_sobrevive(cenario):
    ExcluirViagem(
        cenario.viagens, cenario.acesso, cenario.uow, notificador=cenario.notificador
    ).execute(VIAGEM, CRIADOR)

    assert cenario.viagens.buscar_por_id(VIAGEM) is None
    assert cenario.destinatarios() == [EDITOR, VISUALIZADOR]
    aviso = cenario.notificacoes.do_usuario(EDITOR)[0]
    assert aviso.tipo == TipoNotificacao.VIAGEM_EXCLUIDA
    assert aviso.mensagem == 'Ana excluiu a viagem "Europa" (01/07/2027 a 20/07/2027).'


def test_papel_alterado_e_removido_avisam_so_o_membro_afetado(cenario):
    caso = cenario.caso_membros()

    caso.alterar_papel(VIAGEM, CRIADOR, VISUALIZADOR, PapelMembro.VISUALIZADOR)  # sem mudança
    assert cenario.notificacoes.notificacoes == {}

    caso.alterar_papel(VIAGEM, CRIADOR, VISUALIZADOR, PapelMembro.EDITOR)
    caso.remover_membro(VIAGEM, CRIADOR, EDITOR)

    avisos = cenario.notificacoes.notificacoes.values()
    assert [(n.usuario_id, n.tipo, n.mensagem) for n in avisos] == [
        (
            VISUALIZADOR,
            TipoNotificacao.PAPEL_ALTERADO,
            'Ana alterou seu papel para editor na viagem "Europa".',
        ),
        (EDITOR, TipoNotificacao.MEMBRO_REMOVIDO, 'Ana removeu você da viagem "Europa".'),
    ]


def test_membro_removido_deixa_de_receber_avisos(cenario):
    cenario.caso_membros().remover_membro(VIAGEM, CRIADOR, EDITOR)
    cenario.notificacoes.notificacoes.clear()

    cenario.criar_atividade()

    assert cenario.destinatarios() == [VISUALIZADOR]


def test_membro_que_entra_avisa_os_demais_menos_ele(cenario):
    convites = ConviteViagemRepositoryMemory()
    caso = cenario.caso_membros()
    caso.convites = convites
    convite, token = ConviteViagem.emitir(VIAGEM, "diego@example.com", CRIADOR, AGORA)
    convites.salvar(convite)

    caso.aceitar_convite(token, CONVIDADO)

    assert cenario.destinatarios() == [CRIADOR, EDITOR, VISUALIZADOR]
    aviso = cenario.notificacoes.do_usuario(CRIADOR)[0]
    assert aviso.tipo == TipoNotificacao.MEMBRO_ENTROU
    assert aviso.mensagem == 'Diego entrou na viagem "Europa".'


# --- Somente alterações confirmadas -----------------------------------------------


def test_aviso_e_gravado_antes_do_commit_na_mesma_transacao(cenario):
    eventos = []
    cenario.uow.commit = lambda: eventos.append("commit")
    adicionar = cenario.notificacoes.adicionar
    cenario.notificacoes.adicionar = lambda itens: (eventos.append("notificar"), adicionar(itens))

    cenario.criar_atividade()

    assert eventos == ["notificar", "commit"]


def test_operacao_invalida_nao_gera_aviso(cenario):
    with pytest.raises(DadosInvalidos):
        cenario.criar_atividade(data=date(2027, 7, 19))  # fora do período da parada

    assert cenario.notificacoes.notificacoes == {}
    assert (cenario.uow.commits, cenario.uow.rollbacks) == (0, 1)


def test_sem_permissao_nao_gera_aviso(cenario):
    with pytest.raises(AcessoNegado):
        cenario.criar_atividade(usuario_id=VISUALIZADOR)

    assert cenario.notificacoes.notificacoes == {}


def test_falha_ao_gravar_a_alteracao_nao_gera_aviso(cenario):
    falho = Mock(wraps=cenario.atividades)
    falho.salvar.side_effect = RuntimeError("banco indisponível")

    with pytest.raises(RuntimeError):
        cenario.caso_atividades(repository=falho).criar(
            VIAGEM, cenario.parada.id, EDITOR, cenario.museu.id, date(2027, 7, 3)
        )

    assert cenario.notificacoes.notificacoes == {}
    assert (cenario.uow.commits, cenario.uow.rollbacks) == (0, 1)


# --- Caixa do usuário -------------------------------------------------------------


@pytest.fixture
def caixa():
    repo = NotificacaoRepositoryMemory()
    repo.adicionar(
        [
            Notificacao(usuario_id=usuario, tipo=TipoNotificacao.VIAGEM_ALTERADA, mensagem=texto)
            for usuario, texto in [
                (CRIADOR, "primeira"),
                (CRIADOR, "segunda"),
                (EDITOR, "do editor"),
                (CRIADOR, "terceira"),
            ]
        ]
    )
    return GerenciarNotificacoes(repo, UnitOfWorkMemory(), agora=lambda: AGORA), repo


def test_lista_so_as_do_usuario_com_nao_lidas_primeiro(caixa):
    caso, _ = caixa
    caso.marcar_lida(CRIADOR, 4)

    pagina = caso.listar(CRIADOR)

    assert [n.mensagem for n in pagina.itens] == ["segunda", "primeira", "terceira"]
    assert pagina.nao_lidas == 2 and not pagina.tem_proxima


def test_filtra_nao_lidas_e_pagina(caixa):
    caso, _ = caixa
    caso.marcar_lida(CRIADOR, 1)

    assert [n.mensagem for n in caso.listar(CRIADOR, somente_nao_lidas=True).itens] == [
        "terceira",
        "segunda",
    ]
    pagina = caso.listar(CRIADOR, pagina=1, tamanho_pagina=2)
    assert len(pagina.itens) == 2 and pagina.tem_proxima
    assert len(caso.listar(CRIADOR, pagina=2, tamanho_pagina=2).itens) == 1


@pytest.mark.parametrize(("pagina", "tamanho"), [(0, 20), (1, 0), (1, 101)])
def test_paginacao_invalida(caixa, pagina, tamanho):
    caso, _ = caixa
    with pytest.raises(DadosInvalidos):
        caso.listar(CRIADOR, pagina=pagina, tamanho_pagina=tamanho)


def test_marcar_lida_e_idempotente(caixa):
    caso, _ = caixa
    primeira = caso.marcar_lida(CRIADOR, 1)
    caso.agora = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)

    de_novo = caso.marcar_lida(CRIADOR, 1)

    assert primeira.lida_em == de_novo.lida_em == AGORA
    assert caso.contar_nao_lidas(CRIADOR) == 2


@pytest.mark.parametrize("notificacao_id", [3, 999], ids=["alheia", "inexistente"])
def test_nao_marca_notificacao_alheia_ou_inexistente(caixa, notificacao_id):
    caso, repo = caixa

    with pytest.raises(NotificacaoNaoEncontrada):
        caso.marcar_lida(CRIADOR, notificacao_id)

    assert not repo.notificacoes[3].lida


def test_marcar_todas_afeta_so_o_usuario(caixa):
    caso, _ = caixa

    assert caso.marcar_todas_lidas(CRIADOR) == 3
    assert caso.marcar_todas_lidas(CRIADOR) == 0
    assert caso.contar_nao_lidas(CRIADOR) == 0
    assert caso.contar_nao_lidas(EDITOR) == 1


def test_descrever_mudancas():
    assert descrever_mudancas([("a", False)]) == ""
    assert descrever_mudancas([("a", True), ("b", False)]) == "a"
    assert descrever_mudancas([("a", True), ("b", True), ("c", True)]) == "a, b e c"
