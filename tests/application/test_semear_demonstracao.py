from datetime import date

from app.adapters.outbound.persistence.atividade_viagem_repository_memory import (
    AtividadeViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.catalogo_repository_memory import CatalogoRepositoryMemory
from app.adapters.outbound.persistence.destino_viagem_repository_memory import (
    DestinoViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.membro_viagem_repository_memory import (
    MembroViagemRepositoryMemory,
)
from app.adapters.outbound.persistence.unit_of_work_memory import UnitOfWorkMemory
from app.adapters.outbound.persistence.usuario_repository_memory import UsuarioRepositoryMemory
from app.adapters.outbound.persistence.viagem_repository_memory import ViagemRepositoryMemory
from app.application.acesso_viagem import PoliticaAcessoViagem
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.application.use_cases.semear_demonstracao import SemearDemonstracao
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
    catalogo, destinos = CatalogoRepositoryMemory(), DestinoViagemRepositoryMemory()
    atividades, uow = AtividadeViagemRepositoryMemory(), UnitOfWorkMemory()
    acesso = PoliticaAcessoViagem(viagens, membros)
    caso = SemearDemonstracao(
        RegistroMemory(membros),
        usuarios,
        CriarUsuario(usuarios, FakePasswordHasher(), uow),
        catalogo,
        CriarViagem(viagens, uow),
        AtualizarViagem(viagens, acesso, uow, destinos),
        GerenciarDestinosViagem(destinos, catalogo, acesso, uow),
        GerenciarAtividadesViagem(atividades, destinos, catalogo, acesso, uow),
    )
    criado, manifesto = caso.execute(date(2027, 1, 15))
    assert criado
    assert usuarios.contar() == 6
    assert (
        membros.buscar_papel(manifesto["viagens"]["compartilhada"], manifesto["usuarios"]["editor"])
        == PapelMembro.EDITOR
    )
    antes = uow.commits
    repetido, mesmo_manifesto = caso.execute(date(2030, 1, 1))
    assert not repetido
    assert mesmo_manifesto == manifesto
    assert uow.commits == antes
