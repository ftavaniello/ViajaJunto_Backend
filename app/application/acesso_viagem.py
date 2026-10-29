from app.domain.entities.viagem import Viagem
from app.domain.errors import AcessoNegado, ViagemNaoEncontrada
from app.domain.permissoes import AcaoViagem, PerfilViagem, perfil_na_viagem, pode
from app.domain.ports.membro_viagem_repository import MembroViagemRepository
from app.domain.ports.viagem_repository import ViagemRepository


class PoliticaAcessoViagem:
    """Ponto unico de autorizacao das operacoes sobre uma viagem e seus dados.

    Os casos de uso de viagem (e dos modulos seguintes: destinos, atividades,
    orcamento, membros) chamam `exigir` antes de ler ou alterar algo da viagem.
    """

    def __init__(self, viagens: ViagemRepository, membros: MembroViagemRepository):
        self.viagens = viagens
        self.membros = membros

    def perfil(self, viagem: Viagem, usuario_id: int) -> PerfilViagem | None:
        papel = None
        if usuario_id != viagem.criador_id:
            papel = self.membros.buscar_papel(viagem.id, usuario_id)
        return perfil_na_viagem(viagem.criador_id, usuario_id, papel)

    def exigir(self, viagem_id: int, usuario_id: int, acao: AcaoViagem) -> Viagem:
        """Retorna a viagem se o usuario pode executar `acao`; senao levanta erro.

        Quem nao participa da viagem recebe ViagemNaoEncontrada, como se ela nao
        existisse, para nao revelar ids de viagens alheias. Participantes sem a
        permissao recebem AcessoNegado.
        """
        viagem = self.viagens.buscar_por_id(viagem_id)
        if viagem is None:
            raise ViagemNaoEncontrada("Viagem não encontrada")

        perfil = self.perfil(viagem, usuario_id)
        if perfil is None:
            raise ViagemNaoEncontrada("Viagem não encontrada")
        if not pode(perfil, acao):
            raise AcessoNegado("Você não tem permissão para esta ação na viagem")
        return viagem
