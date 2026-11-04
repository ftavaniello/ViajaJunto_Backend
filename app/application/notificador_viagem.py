from app.domain.entities.notificacao import Notificacao
from app.domain.entities.viagem import Viagem
from app.domain.enums import TipoNotificacao
from app.domain.ports.membro_viagem_repository import MembroViagemRepository
from app.domain.ports.notificacao_repository import NotificacaoRepository
from app.domain.ports.usuario_repository import UsuarioRepository


def descrever_mudancas(campos: list[tuple[str, bool]]) -> str:
    """Junta os nomes dos campos que mudaram: "a data", "a data e o horário"...

    Retorna "" quando nada mudou, e o caso de uso não gera aviso.
    """
    alterados = [nome for nome, mudou in campos if mudou]
    if len(alterados) <= 1:
        return "".join(alterados)
    return ", ".join(alterados[:-1]) + " e " + alterados[-1]


class NotificadorViagem:
    """Gera os avisos in-app de alterações relevantes numa viagem (RF21).

    Os casos de uso chamam `notificar` dentro do `with uow:` e antes do commit:
    as notificações entram na mesma transação da alteração, então um rollback
    desfaz as duas e nenhum aviso fala de algo que não aconteceu.
    Quem fez a alteração nunca é notificado.
    """

    def __init__(
        self,
        notificacoes: NotificacaoRepository,
        membros: MembroViagemRepository,
        usuarios: UsuarioRepository,
    ):
        self.notificacoes = notificacoes
        self.membros = membros
        self.usuarios = usuarios

    def participantes(self, viagem: Viagem) -> list[int]:
        """Criador e colaboradores atuais da viagem."""
        return [viagem.criador_id] + [m.usuario_id for m in self.membros.listar(viagem.id)]

    def notificar(
        self,
        viagem: Viagem,
        tipo: TipoNotificacao,
        ator_id: int,
        acao: str,
        destinatarios: list[int] | None = None,
    ) -> None:
        """Grava "<nome do ator> <acao>" para cada destinatário, menos o ator.

        Sem `destinatarios`, avisa todos os participantes da viagem.
        """
        if destinatarios is None:
            destinatarios = self.participantes(viagem)
        # dict.fromkeys remove repetidos mantendo a ordem.
        destinatarios = [d for d in dict.fromkeys(destinatarios) if d != ator_id]
        if not destinatarios:
            return
        mensagem = f"{self.usuarios.buscar_por_id(ator_id).nome} {acao}"
        self.notificacoes.adicionar(
            [
                Notificacao(
                    usuario_id=destinatario,
                    tipo=tipo,
                    mensagem=mensagem,
                    viagem_id=viagem.id,
                    ator_id=ator_id,
                )
                for destinatario in destinatarios
            ]
        )
