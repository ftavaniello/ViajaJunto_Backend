from datetime import date

from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.avaliacao_repository_memory import AvaliacaoRepositoryMemory
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.orcamento_repository_memory import OrcamentoRepositoryMemory
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import UsuarioRepositoryMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.avaliar_atividade_viagem import AvaliarAtividadeViagem
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.application.use_cases.gerenciar_orcamento_viagem import GerenciarOrcamentoViagem
from app.application.use_cases.semear_demonstracao import SemearDemonstracao
from app.application.use_cases.semear_destinos_reais import SemearDestinosReais
from app.domain.enums import PapelMembro
from tests.application.fakes import FakePasswordHasher


class RegistroMemory:
    def __init__(self, membros):
        self.membros = membros
        self.manifestos = {}

    def reservar(self, chave):
        return self.manifestos.get(chave)

    def vincular(self, viagem_id, usuario_id, papel):
        self.membros.adicionar(viagem_id, usuario_id, papel)

    def concluir(self, chave, manifesto):
        self.manifestos[chave] = manifesto


def test_carga_e_reexecucao_sem_banco_ou_framework():
    usuarios, membros = UsuarioRepositoryMemory(), MembroViagemRepositoryMemory()
    viagens = ViagemRepositoryMemory(membros)
    reviews = AvaliacaoRepositoryMemory(usuarios)
    catalogo, destinos = CatalogoRepositoryMemory(reviews), DestinoViagemRepositoryMemory()
    atividades, uow = AtividadeViagemRepositoryMemory(), UnitOfWorkMemory()
    acesso = PoliticaAcessoViagem(viagens, membros)
    registro = RegistroMemory(membros)
    roteiros = SemearDestinosReais(
        registro,
        catalogo,
        CriarViagem(viagens, uow),
        AtualizarViagem(viagens, acesso, uow, destinos),
        GerenciarDestinosViagem(destinos, catalogo, acesso, uow),
        GerenciarAtividadesViagem(atividades, destinos, catalogo, acesso, uow),
        AvaliarAtividadeViagem(atividades, destinos, acesso, reviews, uow),
        GerenciarOrcamentoViagem(OrcamentoRepositoryMemory(atividades), acesso, uow),
    )
    caso = SemearDemonstracao(
        registro,
        usuarios,
        CriarUsuario(usuarios, FakePasswordHasher(), uow),
        CriarViagem(viagens, uow),
        roteiros,
    )
    criado, manifesto = caso.execute(date(2027, 1, 15))
    assert criado
    assert usuarios.contar() == 6
    assert (
        membros.buscar_papel(manifesto["viagens"]["florida"], manifesto["usuarios"]["editor"])
        == PapelMembro.EDITOR
    )
    antes = uow.commits
    repetido, mesmo_manifesto = caso.execute(date(2030, 1, 1))
    assert not repetido
    assert mesmo_manifesto == manifesto
    assert uow.commits == antes
