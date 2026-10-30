"""Uso: python -m app.adapters.inbound.cli.importar_catalogo arquivo.json."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError

from app.application.use_cases.importar_catalogo import ImportarCatalogo, LoteCatalogo
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.errors import DadosInvalidos
from app.infrastructure.database import SessionLocal
from app.infrastructure.dependencies import montar_importar_catalogo


class DestinoImportacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str
    pais_codigo: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    foto_url: str | None = None
    google_place_id: str | None = None


class AtividadeImportacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destino: str
    nome: str
    categoria: CategoriaAtividade
    descricao: str | None = None
    endereco: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    foto_url: str | None = None
    google_place_id: str | None = None


class ArquivoCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destinos: dict[str, DestinoImportacao]
    atividades: list[AtividadeImportacao]


def importar_arquivo(arquivo: Path, caso: ImportarCatalogo) -> int:
    dados = ArquivoCatalogo.model_validate(json.loads(arquivo.read_text(encoding="utf-8")))
    destinos = {chave: DestinoCatalogo(**d.model_dump()) for chave, d in dados.destinos.items()}
    atividades = []
    for atividade in dados.atividades:
        if atividade.destino not in destinos:
            raise DadosInvalidos("Destino ausente no lote")
        atividades.append(
            (
                atividade.destino,
                AtividadeCatalogo(
                    destino=destinos[atividade.destino],
                    **atividade.model_dump(exclude={"destino"}),
                ),
            )
        )
    return caso.execute(LoteCatalogo(destinos, atividades))


def main():
    parser = argparse.ArgumentParser(description="Importa catálogo curado pela equipe autorizada")
    parser.add_argument("arquivo", type=Path)
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            total = importar_arquivo(args.arquivo, montar_importar_catalogo(db))
    except IntegrityError:
        parser.exit(1, "Importação cancelada: referência externa duplicada ou vínculo inválido.\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Importação cancelada: {error}\n")
    print(f"{total} atividade(s) importada(s).")


if __name__ == "__main__":
    main()
