from app.application.acesso_viagem import PoliticaAcessoViagem
from app.domain.entities.avaliacao import Avaliacao, ReviewPublico, exigir_realizacao
from app.domain.errors import AtividadeViagemNaoEncontrada
from app.domain.permissoes import AcaoViagem
from app.domain.ports.atividade_viagem_repository import AtividadeViagemRepository
from app.domain.ports.avaliacao_repository import AvaliacaoRepository
from app.domain.ports.destino_viagem_repository import DestinoViagemRepository
from app.domain.ports.unit_of_work import UnitOfWork


class AvaliarAtividadeViagem:
    def __init__(
        self,
        atividades: AtividadeViagemRepository,
        destinos: DestinoViagemRepository,
        acesso: PoliticaAcessoViagem,
        avaliacoes: AvaliacaoRepository,
        uow: UnitOfWork,
    ):
        self.atividades = atividades
        self.destinos = destinos
        self.acesso = acesso
        self.avaliacoes = avaliacoes
        self.uow = uow

    def execute(
        self,
        viagem_id: int,
        destino_id: int,
        atividade_id: int,
        usuario_id: int,
        nota: int,
        comentario: str | None = None,
    ) -> ReviewPublico:
        with self.uow:
            self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
            self.destinos.bloquear_roteiro(viagem_id)
            self.acesso.exigir(viagem_id, usuario_id, AcaoViagem.CONSULTAR)
            atividade = self.atividades.buscar(viagem_id, destino_id, atividade_id)
            if atividade is None:
                raise AtividadeViagemNaoEncontrada("Atividade não encontrada nesta parada")
            exigir_realizacao(atividade)
            avaliacao = Avaliacao(
                usuario_id=usuario_id,
                catalogo_atividade_id=atividade.catalogo_atividade_id,
                atividade_viagem_id=atividade.id,
                nota=nota,
                comentario=comentario,
            )
            review = self.avaliacoes.salvar(avaliacao)
            self.uow.commit()
        return review
