from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.adapters.outbound.security.bcrypt_password_hasher import BcryptPasswordHasher
from tests.integration.consolidacao.conftest import SENHA


def test_cadastro_convite_planejamento_orcamento_conclusao_avaliacao(
    api_integrada,
    catalogo_integrado,
    db_session,
    email_teste,
):
    client, email = api_integrada

    def chamar(metodo, url, status, auth=None, **kwargs):
        r = client.request(metodo, url, headers=auth or {}, **kwargs)
        assert r.status_code == status, r.text
        return r.json() if r.content else None

    usuarios, headers = {}, {}
    for papel in ("criador", "colaborador"):
        endereco = email_teste.replace("@", f"-{papel}@")
        usuarios[papel] = chamar(
            "POST",
            "/usuarios",
            201,
            json={
                "nome": papel,
                "email": endereco,
                "senha": SENHA,
            },
        )
        assert "senha" not in str(usuarios[papel])
        salvo = db_session.scalar(select(UsuarioModel).where(UsuarioModel.email == endereco))
        assert salvo.senha_hash != SENHA
        assert BcryptPasswordHasher().verificar(SENHA, salvo.senha_hash)
        token = chamar("POST", "/auth/login", 200, json={"email": endereco, "senha": SENHA})
        headers[papel] = {"Authorization": "Bearer " + token["access_token"]}
    dono, colaborador = headers["criador"], headers["colaborador"]
    viagem = chamar(
        "POST",
        "/viagens",
        201,
        dono,
        json={
            "nome": "Roma em grupo",
            "data_inicio": "2027-01-01",
            "data_fim": "2027-01-10",
        },
    )
    base = f"/viagens/{viagem['id']}"
    chamar("GET", base, 404, colaborador)
    chamar(
        "POST",
        base + "/convites",
        201,
        dono,
        json={
            "email": usuarios["colaborador"]["email"],
        },
    )
    assert len(email.enviados) == 1
    link = next(linha for linha in email.enviados[0].corpo.splitlines() if "?token=" in linha)
    segredo = parse_qs(urlparse(link).query)["token"][0]
    aceito = chamar("POST", "/viagens/convites/aceitar", 201, colaborador, json={"token": segredo})
    assert aceito["papel_usuario"] == "visualizador"
    chamar("PUT", base + "/orcamento", 403, colaborador, json={"valor_total": "1000"})
    membro = base + f"/membros/{usuarios['colaborador']['id']}"
    chamar("PATCH", membro, 200, dono, json={"papel": "editor"})
    parada = chamar(
        "POST",
        base + "/destinos",
        201,
        colaborador,
        json={
            "destino_catalogo_id": catalogo_integrado[0],
            "data_chegada": "2027-01-01",
            "data_saida": "2027-01-10",
        },
    )
    roteiro = base + f"/destinos/{parada['id']}/atividades"
    atividade = chamar(
        "POST",
        roteiro,
        201,
        colaborador,
        json={
            "catalogo_atividade_id": catalogo_integrado[1],
            "data": "2027-01-02",
            "custo_previsto": "150.25",
        },
    )
    resumo = chamar("PUT", base + "/orcamento", 200, colaborador, json={"valor_total": "1000.00"})
    assert (resumo["total_planejado"], resumo["saldo_disponivel"]) == ("150.25", "849.75")
    assert chamar("GET", base + "/orcamento", 200, dono) == resumo
    url = roteiro + f"/{atividade['id']}"
    chamar("PUT", url + "/avaliacao", 403, colaborador, json={"nota": 5})
    concluida = chamar("PATCH", url, 200, colaborador, json={"status": "concluida"})
    assert concluida["realizada_por_id"] == usuarios["colaborador"]["id"]
    assert concluida["realizada_em"] is not None
    chamar("PATCH", base, 200, dono, json={"status": "concluida"})
    review = chamar(
        "PUT",
        url + "/avaliacao",
        200,
        colaborador,
        json={"nota": 5, "comentario": "Visita excelente"},
    )
    publico = chamar("GET", f"/catalogo/atividades/{catalogo_integrado[1]}", 200)
    assert publico["reviews"] == [review]
    assert (publico["media_avaliacoes"], publico["total_avaliacoes"]) == (5, 1)
    assert "viagem_id" not in str(publico) and "@" not in str(publico)
    viagens = chamar("GET", "/viagens", 200, colaborador)
    assert viagens["itens"][0]["id"] == viagem["id"]
    assert viagens["itens"][0]["papel_usuario"] == "editor"
    notificacoes = chamar("GET", "/notificacoes", 200, dono)
    assert notificacoes["nao_lidas"] > 0
    # A mesma sessão deve perder acesso imediatamente após remoção.
    chamar("DELETE", membro, 204, dono)
    chamar("GET", base + "/orcamento", 404, colaborador)
    assert chamar("GET", "/viagens", 200, colaborador)["itens"] == []
    chamar("POST", "/auth/logout", 204, colaborador)
    chamar("GET", "/usuarios/me", 401, colaborador)
