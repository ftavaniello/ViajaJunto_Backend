"""Cenários reproduzíveis criados pelas mesmas regras dos fluxos da API."""

from datetime import date, time, timedelta
from decimal import Decimal

from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import (
    CategoriaAtividade,
    CategoriaDestino,
    PapelMembro,
    StatusAtividade,
    StatusViagem,
)
from app.domain.errors import DadosInvalidos
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.seed_demonstracao_repository import SeedDemonstracaoRepository
from app.domain.ports.usuario_repository import UsuarioRepository

CHAVE_SEED = "demonstracao-completa-v1"
SENHA_SEED = "DemoViaja123!"
PAPEIS = ("criador", "editor", "visualizador", "externo", "vazio", "descartavel")
EMAILS_SEED = {papel: f"{papel}.demo@example.com" for papel in PAPEIS}


class SemearDemonstracao:
    """O chamador fornece uma transação externa envolvendo toda a execução.

    Os commits individuais são savepoints. O registro só é concluído junto com
    os dados, inclusive se ocorrer falha após um cadastro.
    """

    def __init__(
        self,
        registro: SeedDemonstracaoRepository,
        usuarios: UsuarioRepository,
        criar_usuario: CriarUsuario,
        catalogo: CatalogoRepository,
        criar_viagem: CriarViagem,
        atualizar_viagem: AtualizarViagem,
        destinos: GerenciarDestinosViagem,
        atividades: GerenciarAtividadesViagem,
    ):
        self.registro = registro
        self.usuarios = usuarios
        self.criar_usuario = criar_usuario
        self.catalogo = catalogo
        self.criar_viagem = criar_viagem
        self.atualizar_viagem = atualizar_viagem
        self.destinos = destinos
        self.atividades = atividades

    def execute(self, referencia: date) -> tuple[bool, dict]:
        existente = self.registro.reservar(CHAVE_SEED)
        if existente is not None:
            return False, existente
        # Nunca apropriar contas existentes nem redefinir suas senhas/permissões.
        if any(self.usuarios.buscar_por_email(email) for email in EMAILS_SEED.values()):
            raise DadosInvalidos("Email reservado do seed já existe; nenhuma carga foi realizada")
        manifesto = {
            "chave": CHAVE_SEED,
            "referencia": referencia.isoformat(),
            "usuarios": {},
            "viagens": {},
            "destinos_catalogo": {},
            "atividades_catalogo": {},
            "paradas": {},
            "atividades_roteiro": {},
        }
        self._criar_usuarios(manifesto)
        lugares, atividades = self._criar_catalogo(manifesto)
        self._criar_viagens(manifesto, referencia, lugares, atividades)
        self.registro.concluir(CHAVE_SEED, manifesto)
        return True, manifesto

    def _criar_usuarios(self, manifesto: dict) -> None:
        for papel, email in EMAILS_SEED.items():
            usuario = self.criar_usuario.execute(f"Demo {papel}", email, SENHA_SEED)
            manifesto["usuarios"][papel] = usuario.id

    def _criar_catalogo(
        self,
        manifesto: dict,
    ) -> tuple[list[DestinoCatalogo], list[list[AtividadeCatalogo]]]:
        lugares, atividades = [], []
        nomes = ("Lisboa", "Porto", "Rio de Janeiro", "Paraty")
        for i in range(24):
            nome = nomes[i] if i < len(nomes) else f"Destino fictício {i + 1:02}"
            lugar = self.catalogo.salvar_destino(
                DestinoCatalogo(
                    nome=f"[Demo] {nome}",
                    pais_codigo="PT" if i < 2 else "BR",
                    categoria=list(CategoriaDestino)[i % 4],
                    descricao="Dados fictícios para testes manuais; sem referência comercial.",
                )
            )
            lugares.append(lugar)
            manifesto["destinos_catalogo"][f"destino-{i + 1:02}"] = lugar.id
            por_lugar = []
            for j, categoria in enumerate(CategoriaAtividade):
                atividade = self.catalogo.salvar_atividade(
                    AtividadeCatalogo(
                        destino=lugar,
                        nome=f"[Demo] {categoria.value} {i + 1:02}",
                        categoria=categoria,
                        descricao="Atividade fictícia de demonstração.",
                        endereco=f"Rua de Exemplo, {j + 1}",
                    )
                )
                por_lugar.append(atividade)
                manifesto["atividades_catalogo"][f"destino-{i + 1:02}-{categoria.value}"] = (
                    atividade.id
                )
            atividades.append(por_lugar)
        return lugares, atividades

    def _criar_viagens(
        self,
        manifesto: dict,
        referencia: date,
        lugares: list[DestinoCatalogo],
        atividades: list[list[AtividadeCatalogo]],
    ) -> None:
        dono = manifesto["usuarios"]["criador"]
        planos = [
            ("compartilhada", dono, 30, StatusViagem.CONFIRMADA),
            ("passada", dono, -30, StatusViagem.CONCLUIDA),
            ("privada", manifesto["usuarios"]["externo"], 60, StatusViagem.PLANEJANDO),
            ("propria-editor", manifesto["usuarios"]["editor"], 70, StatusViagem.PLANEJANDO),
            ("descartavel", manifesto["usuarios"]["descartavel"], 80, StatusViagem.PLANEJANDO),
        ] + [(f"paginacao-{i:02}", dono, 90 + i, StatusViagem.PLANEJANDO) for i in range(1, 22)]
        for chave, criador, deslocamento, status in planos:
            inicio = referencia + timedelta(days=deslocamento)
            viagem = self.criar_viagem.execute(
                criador,
                f"[Demo] {chave}",
                "Cenário de testes manuais",
                inicio,
                inicio + timedelta(days=8),
            )
            self.atualizar_viagem.execute(viagem.id, criador, status=status)
            manifesto["viagens"][chave] = viagem.id
            if chave == "compartilhada":
                for papel in PapelMembro:
                    self.registro.vincular(viagem.id, manifesto["usuarios"][papel.value], papel)
            if not chave.startswith("paginacao"):
                self._criar_roteiro(
                    manifesto, chave, viagem.id, criador, inicio, lugares, atividades
                )

    def _criar_roteiro(
        self,
        manifesto: dict,
        chave: str,
        viagem_id: int,
        criador: int,
        inicio: date,
        lugares: list[DestinoCatalogo],
        atividades: list[list[AtividadeCatalogo]],
    ) -> None:
        for i in range(3):
            parada = self.destinos.criar(
                viagem_id,
                criador,
                lugares[i].id,
                inicio + timedelta(days=i * 2),
                inicio + timedelta(days=i * 2 + 2),
                descricao="Anotações privadas do roteiro",
                hospedagem="Hotel fictício" if i == 0 else None,
            )
            identificador = f"{chave}-parada-{i + 1}"
            manifesto["paradas"][identificador] = parada.id
            if i == 2:
                continue
            for j, estado in enumerate(
                (
                    StatusAtividade.PENDENTE,
                    StatusAtividade.CONFIRMADA,
                    StatusAtividade.CONCLUIDA,
                )
            ):
                atividade = self.atividades.criar(
                    viagem_id,
                    parada.id,
                    criador,
                    atividades[i][j].id,
                    parada.data_chegada,
                    hora_inicio=(time(14) if j == 0 else time(9)) if j != 2 else None,
                    duracao_minutos=60 if j != 2 else None,
                    custo_previsto=Decimal(("0.00", "45.50", "120.00")[j]),
                    status=estado,
                )
                manifesto["atividades_roteiro"][f"{identificador}-{estado.value}"] = atividade.id
