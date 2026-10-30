from dataclasses import dataclass, replace

from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.errors import DadosInvalidos
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class LoteCatalogo:
    destinos: dict[str, DestinoCatalogo]
    atividades: list[tuple[str, AtividadeCatalogo]]


class ImportarCatalogo:
    """Entrada operacional: somente operadores com acesso ao servidor e ao banco.

    A autorização é fornecida pelo acesso ao comando, não por um endpoint público.
    """

    def __init__(self, repository: CatalogoRepository, uow: UnitOfWork):
        self.repository = repository
        self.uow = uow

    def execute(self, lote: LoteCatalogo, apenas_se_vazio: bool = False) -> int:
        if not lote.destinos or not lote.atividades:
            raise DadosInvalidos("Informe destinos e atividades para importar")
        if any(chave not in lote.destinos for chave, _ in lote.atividades):
            raise DadosInvalidos("Atividade referencia destino ausente no lote")
        with self.uow:
            if apenas_se_vazio and not self.repository.reservar_carga_inicial():
                self.uow.commit()
                return 0
            destinos = {
                chave: self.repository.salvar_destino(destino)
                for chave, destino in lote.destinos.items()
            }
            for chave, atividade in lote.atividades:
                self.repository.salvar_atividade(replace(atividade, destino=destinos[chave]))
            self.uow.commit()
        return len(lote.atividades)
