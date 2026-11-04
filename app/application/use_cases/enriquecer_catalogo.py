from dataclasses import dataclass, replace

from app.domain.entities.catalogo import AtividadeCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos, DestinoCatalogoNaoEncontrado
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.provedor_locais import LocalExterno, ProvedorLocais
from app.domain.ports.unit_of_work import UnitOfWork

RAIO_MINIMO_METROS, RAIO_MAXIMO_METROS = 100, 50_000
LIMITE_MAXIMO = 100


@dataclass(frozen=True)
class ResultadoEnriquecimento:
    criadas: int
    atualizadas: int
    ignoradas: int


class EnriquecerCatalogo:
    """Abastece o catálogo de atividades com locais de um fornecedor externo.

    Entrada operacional, como o importador: sem endpoint de usuário, para não
    expor a cota nem a chave do fornecedor.

    Cada local é identificado por (fonte, id_externo): reexecutar atualiza o mesmo
    registro em vez de duplicar. A atualização mantém id, destino, categoria,
    descrição e foto, então avaliações, roteiros e a curadoria da equipe ficam
    preservados. Locais que somem do fornecedor não são apagados.
    """

    def __init__(
        self, repository: CatalogoRepository, provedor: ProvedorLocais, uow: UnitOfWork
    ):
        self.repository = repository
        self.provedor = provedor
        self.uow = uow

    def execute(
        self,
        destino_id: int,
        categoria: CategoriaAtividade | str,
        raio_metros: int = 5_000,
        limite: int = 20,
    ) -> ResultadoEnriquecimento:
        try:
            categoria = CategoriaAtividade(categoria)
        except ValueError as error:
            raise DadosInvalidos("Categoria de atividade inválida") from error
        if type(raio_metros) is not int or not (
            RAIO_MINIMO_METROS <= raio_metros <= RAIO_MAXIMO_METROS
        ):
            raise DadosInvalidos(
                f"Raio deve estar entre {RAIO_MINIMO_METROS} e {RAIO_MAXIMO_METROS} metros"
            )
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAXIMO:
            raise DadosInvalidos(f"Limite deve estar entre 1 e {LIMITE_MAXIMO}")

        destino = self.repository.buscar_destino(destino_id)
        if destino is None:
            raise DestinoCatalogoNaoEncontrado("Destino não encontrado no catálogo")
        if destino.latitude is None or destino.longitude is None:
            raise DadosInvalidos("O destino precisa de latitude e longitude para a busca")

        # Consulta externa fora da transação: não segura o banco esperando a rede, e
        # uma falha do fornecedor interrompe antes de gravar qualquer coisa.
        locais = self.provedor.buscar_proximos(
            destino.latitude, destino.longitude, categoria, raio_metros, limite
        )

        criadas = atualizadas = ignoradas = 0
        vistos: set[str] = set()
        with self.uow:
            for local in locais:
                # O mesmo local pode vir repetido na resposta; vale a primeira ocorrência.
                if local.id_externo in vistos:
                    continue
                vistos.add(local.id_externo)
                existente = self.repository.buscar_atividade_externa(
                    self.provedor.fonte, local.id_externo
                )
                try:
                    if existente is None:
                        self.repository.salvar_atividade(self._nova(destino, categoria, local))
                        criadas += 1
                    else:
                        self.repository.atualizar_atividade(self._atualizada(existente, local))
                        atualizadas += 1
                except DadosInvalidos:
                    ignoradas += 1
            self.uow.commit()
        return ResultadoEnriquecimento(criadas, atualizadas, ignoradas)

    def _nova(self, destino, categoria: CategoriaAtividade, local: LocalExterno):
        return AtividadeCatalogo(
            destino=destino,
            nome=local.nome,
            categoria=categoria,
            endereco=local.endereco,
            latitude=local.latitude,
            longitude=local.longitude,
            id_externo=local.id_externo,
            fonte=self.provedor.fonte,
        )

    @staticmethod
    def _atualizada(existente: AtividadeCatalogo, local: LocalExterno) -> AtividadeCatalogo:
        # replace revalida a entidade; dados externos inválidos levantam DadosInvalidos.
        return replace(
            existente,
            nome=local.nome,
            endereco=local.endereco,
            latitude=local.latitude,
            longitude=local.longitude,
        )
