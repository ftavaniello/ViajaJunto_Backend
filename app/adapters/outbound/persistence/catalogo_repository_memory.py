from dataclasses import replace

from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.ports.catalogo_repository import CatalogoRepository


class CatalogoRepositoryMemory(CatalogoRepository):
    def __init__(self):
        self.destinos: dict[int, DestinoCatalogo] = {}
        self.atividades: dict[int, AtividadeCatalogo] = {}

    def reservar_carga_inicial(self) -> bool:
        return not self.destinos and not self.atividades

    def salvar_destino(self, destino: DestinoCatalogo) -> DestinoCatalogo:
        destino = replace(destino, id=len(self.destinos) + 1)
        self.destinos[destino.id] = destino
        return destino

    def salvar_atividade(self, atividade: AtividadeCatalogo) -> AtividadeCatalogo:
        atividade = replace(atividade, id=len(self.atividades) + 1)
        self.atividades[atividade.id] = atividade
        return atividade

    def buscar_atividade(self, atividade_id: int) -> AtividadeCatalogo | None:
        return self.atividades.get(atividade_id)

    def listar_atividades(
        self,
        nome: str | None,
        categoria: CategoriaAtividade | None,
        localizacao: str | None,
        destino_catalogo_id: int | None,
        limite: int,
        deslocamento: int,
    ) -> list[AtividadeCatalogo]:
        itens = []
        for atividade in sorted(self.atividades.values(), key=lambda a: a.id):
            destino = atividade.destino
            if nome and nome.lower() not in atividade.nome.lower():
                continue
            if categoria and atividade.categoria != categoria:
                continue
            if destino_catalogo_id and destino.id != destino_catalogo_id:
                continue
            if localizacao and not any(
                localizacao.lower() in campo.lower()
                for campo in (
                    destino.nome,
                    destino.pais_codigo,
                    atividade.endereco or "",
                )
            ):
                continue
            itens.append(atividade)
        return itens[deslocamento : deslocamento + limite]
