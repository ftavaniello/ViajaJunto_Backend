from datetime import date

import pytest
from sqlalchemy import event

from app.adapters.outbound.persistence.catalogo_model import CatalogoAtividadeModel
from app.adapters.outbound.persistence.viagem_model import ViagemModel


@pytest.mark.parametrize("rota,limite", [("/viagens", 5), ("/catalogo/atividades", 2)])
def test_pagina_maior_nao_causa_consultas_por_item(api_integrada, matriz, db_session, rota, limite):
    for indice in range(20):
        db_session.add(
            ViagemModel(
                criador_id=matriz["usuarios"]["criador"],
                nome=f"Extra {indice}",
                data_inicio=date(2027, 1, 1),
                data_fim=date(2027, 1, 10),
            )
        )
        db_session.add(
            CatalogoAtividadeModel(
                destino_catalogo_id=matriz["catalogo"][0],
                nome=f"Extra {indice}",
                categoria="passeio",
            )
        )
    db_session.commit()
    contagens = []
    for tamanho in (1, 20):
        consultas = []
        conexao = db_session.connection()

        def registrar(conn, cursor, statement, params, context, many):
            if statement.lstrip().upper().startswith("SELECT"):
                consultas.append(statement)

        event.listen(conexao, "before_cursor_execute", registrar)
        try:
            r = api_integrada[0].get(
                rota, params={"tamanho_pagina": tamanho}, headers=matriz["headers"]["criador"]
            )
            assert r.status_code == 200
            assert len(r.json()["itens"]) == tamanho
            contagens.append(len(consultas))
        finally:
            event.remove(conexao, "before_cursor_execute", registrar)
    assert contagens[0] == contagens[1]
    assert 0 < contagens[1] <= limite
