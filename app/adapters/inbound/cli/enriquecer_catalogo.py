"""Busca locais no Geoapify e grava ou atualiza atividades de um destino do catálogo.

Uso (operadores com acesso ao servidor e ao banco):
    python -m app.adapters.inbound.cli.enriquecer_catalogo --destino 1 --categoria passeio
"""

import argparse

from app.application.use_cases.enriquecer_catalogo import EnriquecerCatalogo
from app.domain.enums import CategoriaAtividade
from app.domain.errors import (
    ErroNegocio,
    FalhaProvedorLocais,
    LimiteProvedorLocaisExcedido,
)
from app.infrastructure.config import settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.dependencies import montar_enriquecer_catalogo
from app.infrastructure.locais import criar_provedor_locais


def enriquecer(caso: EnriquecerCatalogo, args: argparse.Namespace) -> str:
    resultado = caso.execute(args.destino, args.categoria, args.raio, args.limite)
    return (
        f"Catálogo enriquecido: {resultado.criadas} criada(s), "
        f"{resultado.atualizadas} atualizada(s), {resultado.ignoradas} ignorada(s)."
    )


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Enriquece o catálogo com locais do Geoapify próximos a um destino."
    )
    parser.add_argument("--destino", type=int, required=True, help="ID do destino do catálogo.")
    parser.add_argument(
        "--categoria",
        required=True,
        choices=[c.value for c in CategoriaAtividade],
        help="Categoria das atividades a buscar.",
    )
    parser.add_argument("--raio", type=int, default=5_000, help="Raio da busca em metros.")
    parser.add_argument("--limite", type=int, default=20, help="Máximo de locais (1 a 100).")
    args = parser.parse_args(argv)
    try:
        provedor = criar_provedor_locais(settings)
        with SessionLocal() as db:
            mensagem = enriquecer(montar_enriquecer_catalogo(db, provedor), args)
    except LimiteProvedorLocaisExcedido as error:
        espera = (
            f" Tente novamente em {error.tentar_em_segundos} s."
            if error.tentar_em_segundos
            else ""
        )
        parser.exit(2, f"Nada foi gravado: {error}.{espera}\n")
    except FalhaProvedorLocais as error:
        parser.exit(2, f"Nada foi gravado: {error}.\n")
    except ErroNegocio as error:
        parser.exit(1, f"Nada foi gravado: {error}.\n")
    print(mensagem)


if __name__ == "__main__":
    main()
