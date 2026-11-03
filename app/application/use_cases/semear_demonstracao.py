"""Carga única de usuários e roteiros, sem dependências de infraestrutura."""

from datetime import date, timedelta

from app.application.use_cases.criar_usuario import CriarUsuario
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.semear_destinos_reais import SemearDestinosReais
from app.domain.errors import DadosInvalidos
from app.domain.ports.seed_demonstracao_repository import SeedDemonstracaoRepository
from app.domain.ports.usuario_repository import UsuarioRepository

CHAVE_SEED = "dados-iniciais-v2"
SENHA_SEED = "DemoViaja123!"
PAPEIS = ("criador", "editor", "visualizador", "externo", "vazio", "descartavel")
EMAILS_SEED = {papel: f"{papel}.demo@example.com" for papel in PAPEIS}
NOMES_SEED = dict(
    zip(
        PAPEIS,
        (
            "Ana Souza",
            "Bruno Lima",
            "Carla Santos",
            "Diego Alves",
            "Elisa Costa",
            "Felipe Rocha",
        ),
        strict=True,
    )
)


class SemearDemonstracao:
    """Commits individuais são savepoints; o chamador confirma a carga inteira."""

    def __init__(
        self,
        registro: SeedDemonstracaoRepository,
        usuarios: UsuarioRepository,
        criar_usuario: CriarUsuario,
        criar_viagem: CriarViagem,
        roteiros: SemearDestinosReais,
    ):
        self.registro = registro
        self.usuarios = usuarios
        self.criar_usuario = criar_usuario
        self.criar_viagem = criar_viagem
        self.roteiros = roteiros

    def execute(self, referencia: date) -> tuple[bool, dict]:
        existente = self.registro.reservar(CHAVE_SEED)
        if existente is not None:
            return False, existente
        if any(self.usuarios.buscar_por_email(email) for email in EMAILS_SEED.values()):
            raise DadosInvalidos(
                "Email reservado do seed já existe. Bancos com a carga antiga precisam "
                "ser reinicializados explicitamente; nenhum dado foi alterado."
            )
        usuarios = {
            papel: self.criar_usuario.execute(NOMES_SEED[papel], email, SENHA_SEED).id
            for papel, email in EMAILS_SEED.items()
        }
        manifesto = dict(
            self.roteiros.execute(usuarios, referencia),
            chave=CHAVE_SEED,
            referencia=referencia.isoformat(),
            usuarios=usuarios,
        )
        self._viagens_vazias(manifesto, referencia)
        self.registro.concluir(CHAVE_SEED, manifesto)
        return True, manifesto

    def _viagens_vazias(self, manifesto: dict, referencia: date) -> None:
        usuarios = manifesto["usuarios"]
        planos = [("propria-editor", "Roma com amigos", usuarios["editor"], 45)]
        temas = ("Férias em Orlando", "Praias de Miami", "Rio em família", "Descobrindo Roma")
        planos.extend(
            (
                f"paginacao-{i:02}",
                f"{temas[(i - 1) % 4]} — roteiro {i:02}",
                usuarios["criador"],
                150 + i,
            )
            for i in range(1, 22)
        )
        for chave, nome, dono, dias in planos:
            inicio = referencia + timedelta(days=dias)
            viagem = self.criar_viagem.execute(
                dono,
                nome,
                "Planejamento aberto para organizar os próximos passeios.",
                inicio,
                inicio + timedelta(days=7),
            )
            manifesto["viagens"][chave] = viagem.id
