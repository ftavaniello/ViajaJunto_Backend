"""Uso: JSON via stdin ou --exemplo para o seed fixo de desenvolvimento."""

import argparse
import sys
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


def importar_json(
    conteudo: str,
    caso: ImportarCatalogo,
    apenas_se_vazio: bool = False,
) -> int:
    dados = ArquivoCatalogo.model_validate_json(conteudo)
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
    return caso.execute(LoteCatalogo(destinos, atividades), apenas_se_vazio=apenas_se_vazio)


def main():
    parser = argparse.ArgumentParser(description="Importa catálogo curado pela equipe autorizada")
    parser.add_argument(
        "--exemplo",
        action="store_true",
        help="Usa exclusivamente o arquivo fixo docs/catalogo-exemplo.json do projeto.",
    )
    parser.add_argument(
        "--se-vazio",
        action="store_true",
        help="Seed: importa somente se não houver destinos nem atividades no catálogo.",
    )
    args = parser.parse_args()
    try:
        if args.exemplo:
            # Caminho fixo derivado do código, nunca de argumentos fornecidos ao CLI.
            arquivo_exemplo = Path(__file__).resolve().parents[4] / "docs/catalogo-exemplo.json"
            conteudo = arquivo_exemplo.read_text(encoding="utf-8")
        else:
            if hasattr(sys.stdin, "reconfigure"):
                sys.stdin.reconfigure(encoding="utf-8")
            conteudo = sys.stdin.read()
        with SessionLocal() as db:
            total = importar_json(conteudo, montar_importar_catalogo(db), args.se_vazio)
    except IntegrityError:
        parser.exit(1, "Importação cancelada: referência externa duplicada ou vínculo inválido.\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Importação cancelada: {error}\n")
    if args.se_vazio and total == 0:
        print("Seed ignorado: o catálogo já contém dados.")
    else:
        print(f"{total} atividade(s) importada(s).")


if __name__ == "__main__":
    main()
