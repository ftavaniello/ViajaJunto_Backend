"""Falha se módulos de integração não executaram ou se houve testes ignorados."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.support.banco_isolado import RAIZ


def auditar(arquivo: Path, modulos: set[str]) -> list[str]:
    casos = list(ET.parse(arquivo).getroot().iter("testcase"))
    erros = []
    for modulo in sorted(modulos):
        encontrados = [
            c
            for c in casos
            if c.get("classname", "") == modulo or c.get("classname", "").startswith(modulo + ".")
        ]
        if not encontrados:
            erros.append(f"Módulo de integração não executado: {modulo}")
    for caso in casos:
        if caso.find("failure") is not None or caso.find("error") is not None:
            erros.append(f"Teste falhou: {caso.get('classname')}.{caso.get('name')}")
        if caso.get("classname", "").startswith("tests.integration."):
            if caso.find("skipped") is not None:
                erros.append(f"Integração ignorada: {caso.get('classname')}.{caso.get('name')}")
    return erros


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relatorio", type=Path)
    args = parser.parse_args()
    modulos = {
        ".".join(p.relative_to(RAIZ).with_suffix("").parts)
        for p in (RAIZ / "tests/integration").rglob("test_*.py")
    }
    erros = auditar(args.relatorio, modulos)
    if erros:
        raise SystemExit("\n".join(erros))
    print(f"CI: {len(modulos)} módulos de integração executados, sem falhas ou skips")


if __name__ == "__main__":
    main()
