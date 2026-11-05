"""Medição HTTP local reproduzível; grava apenas em schema descartável de banco _test."""

import argparse
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.support.banco_isolado import RAIZ, banco_isolado

CARGA = {
    "usuarios": 50,
    "viagens": 2000,
    "membros_viagem": 588,
    "destinos_catalogo": 50,
    "catalogo_atividades": 1000,
    "destinos_viagem": 2000,
    "atividades_viagem": 11000,
    "avaliacoes": 20000,
    "orcamentos": 2000,
}


def preparar(engine):
    comandos = [
        "INSERT INTO usuarios(id,nome,email,senha_hash) SELECT g,'Pessoa '||g,"
        "'pessoa'||g||'@example.com','hash-fora-da-medicao' FROM generate_series(1,50) g",
        "INSERT INTO destinos_catalogo(id,nome,pais_codigo) SELECT g,"
        "CASE WHEN g=1 THEN 'Roma' ELSE 'Cidade '||g END,'IT' FROM generate_series(1,50) g",
        "INSERT INTO catalogo_atividades(id,destino_catalogo_id,nome,categoria) "
        "SELECT g,(g-1)%50+1,'Atividade '||g,'cultura' FROM generate_series(1,1000) g",
        "INSERT INTO viagens(id,criador_id,nome,data_inicio,data_fim) SELECT g,(g-1)%50+1,"
        "'Viagem '||g,'2027-01-01','2027-01-10' FROM generate_series(1,2000) g",
        "INSERT INTO membros_viagem(viagem_id,usuario_id,papel) SELECT id,1,'editor' "
        "FROM viagens WHERE id<=600 AND criador_id<>1",
        "INSERT INTO destinos_viagem(id,viagem_id,destino_catalogo_id,ordem,"
        "data_chegada,data_saida) SELECT id,id,(id-1)%50+1,1,"
        "'2027-01-01','2027-01-10' FROM viagens",
        "INSERT INTO atividades_viagem(destino_viagem_id,catalogo_atividade_id,data,"
        "custo_previsto,status) SELECT p.id,p.destino_catalogo_id,'2027-01-02',10.25,'pendente' "
        "FROM destinos_viagem p CROSS JOIN generate_series(1,5) g",
        "INSERT INTO atividades_viagem(destino_viagem_id,catalogo_atividade_id,data,"
        "custo_previsto,status) SELECT 1,1,'2027-01-02',10.25,'pendente' "
        "FROM generate_series(1,1000)",
        "INSERT INTO orcamentos(viagem_id,limite_total) SELECT id,20000 FROM viagens",
        "INSERT INTO avaliacoes(usuario_id,catalogo_atividade_id,nota,comentario) "
        "SELECT (g-1)/1000+1,(g-1)%1000+1,(g-1)%5+1,'Comentário sintético' "
        "FROM generate_series(1,20000) g",
    ]
    with engine.begin() as conn:
        for sql in comandos:
            conn.execute(text(sql))
        for tabela, esperado in CARGA.items():
            assert conn.scalar(text(f"SELECT count(*) FROM {tabela}")) == esperado
            conn.execute(text(f"ANALYZE {tabela}"))


def requisitar(base, caminho, token):
    inicio = time.perf_counter()
    req = Request(base + caminho, headers={"Authorization": "Bearer " + token})
    try:
        with urlopen(req, timeout=15) as r:
            codigo, corpo = r.status, json.load(r)
        valido = codigo == 200
        if caminho.startswith(("/viagens?", "/catalogo/atividades")):
            valido = valido and len(corpo["itens"]) == 20
        if caminho.endswith("/orcamento"):
            valido = valido and corpo["total_planejado"] == "10301.25"
        if caminho == "/usuarios/resumo":
            valido = valido and corpo["total_usuarios"] == 50
        return (time.perf_counter() - inicio) * 1000, valido
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        return (time.perf_counter() - inicio) * 1000, False


def percentil(valores, p):
    return sorted(valores)[max(0, math.ceil(len(valores) * p) - 1)]


def medir(base, caminho, token, amostras, concorrencia):
    for _ in range(5):
        _, ok = requisitar(base, caminho, token)
        if not ok:
            raise RuntimeError(f"Resposta inválida no aquecimento de {caminho}")
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concorrencia) as pool:
        resultados = list(pool.map(lambda _: requisitar(base, caminho, token), range(amostras)))
    duracao = time.perf_counter() - inicio
    valores = [r[0] for r in resultados]
    return dict(
        endpoint=caminho,
        concorrencia=concorrencia,
        requisicoes=amostras,
        erros=sum(not r[1] for r in resultados),
        p50_ms=round(percentil(valores, 0.5), 2),
        p95_ms=round(percentil(valores, 0.95), 2),
        p99_ms=round(percentil(valores, 0.99), 2),
        max_ms=round(max(valores), 2),
        requisicoes_segundo=round(amostras / duracao, 2),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amostras", type=int, default=100)
    parser.add_argument("--saida", type=Path, default=Path(".cache/desempenho-backend.json"))
    args = parser.parse_args()
    if args.amostras < 20:
        parser.error("Use pelo menos 20 amostras por cenário")
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url or not (make_url(url).database or "").endswith("_test"):
        parser.error("Defina TEST_DATABASE_URL para um banco terminado em _test")
    if os.getenv("APP_ENV") != "test":
        parser.error("Defina APP_ENV=test")
    # Precisa acontecer antes de importar configurações, Alembic env ou app.
    os.environ["DATABASE_URL"] = url
    from app.infrastructure.dependencies import get_token_service

    token = get_token_service().gerar_token(1, 0)
    with banco_isolado() as engine:
        preparar(engine)
        with engine.connect() as conn:
            postgres = conn.scalar(text("SELECT version()"))
        ambiente = dict(os.environ, DATABASE_URL=engine.url.render_as_string(hide_password=False))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            porta = sock.getsockname()[1]
        base = f"http://127.0.0.1:{porta}"
        processo = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "tests.performance.servidor_medicao:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(porta),
                "--no-access-log",
            ],
            cwd=RAIZ,
            env=ambiente,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            limite = time.monotonic() + 20
            while True:
                if processo.poll() is not None or time.monotonic() > limite:
                    raise RuntimeError("Servidor de medição não iniciou")
                try:
                    with urlopen(base + "/health", timeout=1) as r:
                        if r.status == 200:
                            break
                except (URLError, TimeoutError):
                    time.sleep(0.1)
            caminhos = [
                "/viagens?pagina=1&tamanho_pagina=20",
                "/viagens?pagina=10&tamanho_pagina=20",
                "/catalogo/atividades?tamanho_pagina=20",
                "/catalogo/atividades?nota_minima=4&tamanho_pagina=20",
                "/catalogo/atividades?localizacao=Roma&tamanho_pagina=20",
                "/viagens/1/orcamento",
                "/usuarios/resumo",
            ]
            resultados = [
                medir(base, caminho, token, args.amostras, concorrencia)
                for concorrencia in (1, 5)
                for caminho in caminhos
            ]
            relatorio = dict(
                data_utc=datetime.now(timezone.utc).isoformat(),
                dataset=CARGA,
                ambiente=dict(
                    python=platform.python_version(),
                    cpu=platform.processor(),
                    so=platform.platform(),
                    cpus_logicas=os.cpu_count(),
                    postgresql=postgres,
                    transporte="HTTP TCP loopback, urllib sem pool de keep-alive",
                    servidor="uvicorn, 1 worker",
                    cache_usuarios="BYPASS",
                ),
                aquecimento_por_cenario=5,
                percentil="nearest rank",
                resultados=resultados,
                limitacoes=[
                    "Sem navegador, frontend, rede externa, TLS ou balanceador",
                    "Carga fechada: novo pedido após resposta, sem taxa de chegada fixa",
                    "Instância local e dataset sintético; não é capacidade de produção",
                    "JWT real; login, bcrypt e envio de email fora da medição",
                    "Buffers e pool aquecidos; não mede partida a frio",
                ],
            )
            args.saida.parent.mkdir(parents=True, exist_ok=True)
            args.saida.write_text(
                json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(resultados, ensure_ascii=False, indent=2))
            if any(r["erros"] for r in resultados):
                raise SystemExit("Medição contém erros; consulte o relatório")
        finally:
            processo.terminate()
            try:
                processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait(timeout=5)


if __name__ == "__main__":
    main()
