from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.notificador_viagem import NotificadorViagem
from app.domain.entities.convite_viagem import ConviteViagem
from app.domain.entities.viagem import Viagem
from app.domain.enums import PapelMembro, TipoNotificacao
from app.domain.errors import (
    ConviteDeOutroEmail,
    ConviteInvalido,
    ConviteJaAceito,
    ConviteNaoEncontrado,
    DadosInvalidos,
    FalhaEnvioConvite,
    MembroJaParticipa,
    MembroNaoEncontrado,
)
from app.domain.membro_viagem import ParticipanteViagem
from app.domain.participacao_viagem import ParticipacaoViagem
from app.domain.permissoes import AcaoViagem, PerfilViagem
from app.domain.ports.convite_viagem_repository import ConviteViagemRepository
from app.domain.ports.email_sender import EmailSender, FalhaEnvioEmail, MensagemEmail
from app.domain.ports.membro_viagem_repository import MembroViagemRepository
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.ports.viagem_repository import ViagemRepository
from app.domain.regras import CONVITE_VALIDADE_DIAS, PAPEL_INICIAL_CONVIDADO


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class GerenciarMembrosViagem:
    """Convites por email (RF18) e gestao de colaboradores (RF20 / RN04).

    O criador convida um email; o convidado recebe um link de uso unico e, ao
    aceitar com a conta daquele email, entra na viagem como
    PAPEL_INICIAL_CONVIDADO. So o criador promove ou rebaixa depois. Remocoes e
    trocas de papel valem na proxima requisicao porque `PoliticaAcessoViagem`
    le o papel do banco.
    """

    def __init__(
        self,
        viagens: ViagemRepository,
        membros: MembroViagemRepository,
        convites: ConviteViagemRepository,
        usuarios: UsuarioRepository,
        acesso: PoliticaAcessoViagem,
        email_sender: EmailSender,
        uow: UnitOfWork,
        url_convite: str,
        agora: Callable[[], datetime] = _agora_utc,
        notificador: NotificadorViagem | None = None,
    ):
        self.viagens = viagens
        self.membros = membros
        self.convites = convites
        self.usuarios = usuarios
        self.acesso = acesso
        self.email_sender = email_sender
        self.uow = uow
        self.url_convite = url_convite
        self.agora = agora
        self.notificador = notificador

    def convidar(self, viagem_id: int, usuario_id: int, email: str) -> ConviteViagem:
        with self.uow:
            viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.GERENCIAR_MEMBROS)
            convite, valor = ConviteViagem.emitir(viagem_id, email, usuario_id, self.agora())

            convidado = self.usuarios.buscar_por_email(convite.email)
            if convidado is not None and self._participa(viagem, convidado.id):
                raise MembroJaParticipa("Este usuário já participa da viagem")

            # Reenviar para o mesmo email invalida o link anterior.
            self.convites.remover_pendentes(viagem_id, convite.email)
            salvo = self.convites.salvar(convite)

            # Envia antes do commit: se o email falhar, o convite nao fica gravado
            # sem que ninguem tenha o link.
            criador = self.usuarios.buscar_por_id(usuario_id)
            try:
                self.email_sender.enviar(self._mensagem(convite.email, criador.nome, viagem, valor))
            except FalhaEnvioEmail as error:
                raise FalhaEnvioConvite(
                    "Não foi possível enviar o email do convite; tente novamente"
                ) from error
            self.uow.commit()
        return salvo

    def listar_convites(self, viagem_id: int, usuario_id: int) -> list[ConviteViagem]:
        self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.GERENCIAR_MEMBROS)
        return self.convites.listar_pendentes(viagem_id, self.agora())

    def cancelar_convite(self, viagem_id: int, usuario_id: int, convite_id: int) -> None:
        with self.uow:
            self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.GERENCIAR_MEMBROS)
            convite = self.convites.buscar(viagem_id, convite_id)
            if convite is None or convite.aceito:
                raise ConviteNaoEncontrado("Convite pendente não encontrado nesta viagem")
            self.convites.remover(convite_id)
            self.uow.commit()

    def aceitar_convite(self, token: str, usuario_id: int) -> ParticipacaoViagem:
        # A viagem vem do convite localizado pelo token secreto, nunca de um id
        # informado pelo usuario.
        agora = self.agora()
        with self.uow:
            convite = self.convites.buscar_por_hash(ConviteViagem.calcular_hash(token))
            if convite is None:
                raise ConviteInvalido("Convite inválido ou expirado")
            if convite.aceito:
                raise ConviteJaAceito("Este convite já foi utilizado")
            if convite.expirado(agora):
                raise ConviteInvalido("Convite inválido ou expirado")

            usuario = self.usuarios.buscar_por_id(usuario_id)
            if not convite.destinado_a(usuario.email):
                raise ConviteDeOutroEmail(
                    "Este convite foi enviado para outro email; "
                    "entre com a conta do email convidado"
                )

            viagem = self.viagens.buscar_por_id(convite.viagem_id)
            if self._participa(viagem, usuario_id):
                raise MembroJaParticipa("Você já participa desta viagem")

            self.membros.adicionar(viagem.id, usuario_id, PAPEL_INICIAL_CONVIDADO)
            convite.marcar_aceito(agora)
            self.convites.salvar(convite)
            # O novo membro ja esta na lista de participantes, mas e o ator e nao recebe.
            self._avisar(
                viagem, TipoNotificacao.MEMBRO_ENTROU, usuario_id,
                f'entrou na viagem "{viagem.nome}".',
            )
            self.uow.commit()
        return ParticipacaoViagem(viagem, PAPEL_INICIAL_CONVIDADO)

    def listar_membros(self, viagem_id: int, usuario_id: int) -> list[ParticipanteViagem]:
        viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
        participantes = [
            self._participante(viagem.criador_id, PerfilViagem.CRIADOR, viagem.criado_em)
        ]
        participantes += [
            self._participante(m.usuario_id, PerfilViagem(m.papel.value), m.entrou_em)
            for m in self.membros.listar(viagem_id)
        ]
        return participantes

    def alterar_papel(
        self, viagem_id: int, usuario_id: int, membro_id: int, papel: PapelMembro | str
    ) -> ParticipanteViagem:
        try:
            papel = PapelMembro(papel)
        except ValueError as error:
            raise DadosInvalidos("Papel inválido: use editor ou visualizador") from error

        with self.uow:
            viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.GERENCIAR_MEMBROS)
            if membro_id == viagem.criador_id:
                raise DadosInvalidos("O papel do criador da viagem não pode ser alterado")
            papel_anterior = self._exigir_membro(viagem_id, membro_id)
            self.membros.alterar_papel(viagem_id, membro_id, papel)
            membro = next(m for m in self.membros.listar(viagem_id) if m.usuario_id == membro_id)
            if papel != papel_anterior:
                self._avisar(
                    viagem, TipoNotificacao.PAPEL_ALTERADO, usuario_id,
                    f'alterou seu papel para {papel.value} na viagem "{viagem.nome}".',
                    destinatarios=[membro_id],
                )
            self.uow.commit()
        return self._participante(membro_id, PerfilViagem(membro.papel.value), membro.entrou_em)

    def remover_membro(self, viagem_id: int, usuario_id: int, membro_id: int) -> None:
        with self.uow:
            viagem = self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.GERENCIAR_MEMBROS)
            if membro_id == viagem.criador_id:
                raise DadosInvalidos("O criador não pode ser removido da viagem")
            self._exigir_membro(viagem_id, membro_id)
            self.membros.remover(viagem_id, membro_id)
            self._avisar(
                viagem, TipoNotificacao.MEMBRO_REMOVIDO, usuario_id,
                f'removeu você da viagem "{viagem.nome}".',
                destinatarios=[membro_id],
            )
            self.uow.commit()

    def _participa(self, viagem: Viagem, usuario_id: int) -> bool:
        return (
            usuario_id == viagem.criador_id
            or self.membros.buscar_papel(viagem.id, usuario_id) is not None
        )

    def _exigir_membro(self, viagem_id: int, membro_id: int) -> PapelMembro:
        papel = self.membros.buscar_papel(viagem_id, membro_id)
        if papel is None:
            raise MembroNaoEncontrado("Colaborador não encontrado nesta viagem")
        return papel

    def _avisar(
        self,
        viagem: Viagem,
        tipo: TipoNotificacao,
        ator_id: int,
        acao: str,
        destinatarios: list[int] | None = None,
    ) -> None:
        if self.notificador is not None:
            self.notificador.notificar(viagem, tipo, ator_id, acao, destinatarios)

    def _participante(
        self, usuario_id: int, perfil: PerfilViagem, entrou_em: datetime | None
    ) -> ParticipanteViagem:
        usuario = self.usuarios.buscar_por_id(usuario_id)
        return ParticipanteViagem(
            usuario_id=usuario_id,
            nome=usuario.nome,
            email=usuario.email,
            perfil=perfil,
            entrou_em=entrou_em,
        )

    def _mensagem(
        self, destinatario: str, nome_criador: str, viagem: Viagem, valor: str
    ) -> MensagemEmail:
        link = f"{self.url_convite}?{urlencode({'token': valor})}"
        corpo = (
            f"{nome_criador} convidou você para a viagem \"{viagem.nome}\" no ViajaJunto.\n\n"
            f"Para aceitar e entrar na viagem, acesse:\n{link}\n\n"
            f"Se ainda não tem conta, cadastre-se com este email ({destinatario}) "
            "antes de aceitar: o convite só vale para ele.\n\n"
            f"O link vale por {CONVITE_VALIDADE_DIAS} dias e só pode ser usado uma vez. "
            "Se você não esperava este convite, ignore este email."
        )
        return MensagemEmail(
            destinatario=destinatario,
            assunto=f"Convite para a viagem {viagem.nome} - ViajaJunto",
            corpo=corpo,
        )
