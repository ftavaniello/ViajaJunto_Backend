"""Monta os roteiros reais da carga inicial; transação controlada pelo seed completo."""

from datetime import date, time, timedelta
from decimal import Decimal

from app.application.dados_seed_destinos_reais import LUGARES_REAIS
from app.application.use_cases.atualizar_viagem import AtualizarViagem
from app.application.use_cases.avaliar_atividade_viagem import AvaliarAtividadeViagem
from app.application.use_cases.criar_viagem import CriarViagem
from app.application.use_cases.gerenciar_atividades_viagem import GerenciarAtividadesViagem
from app.application.use_cases.gerenciar_destinos_viagem import GerenciarDestinosViagem
from app.application.use_cases.gerenciar_orcamento_viagem import GerenciarOrcamentoViagem
from app.domain.entities.catalogo import AtividadeCatalogo, DestinoCatalogo
from app.domain.enums import PapelMembro, StatusAtividade, StatusViagem
from app.domain.ports.catalogo_repository import CatalogoRepository
from app.domain.ports.seed_demonstracao_repository import SeedDemonstracaoRepository


class SemearDestinosReais:
    def __init__(
        self,
        registro: SeedDemonstracaoRepository,
        catalogo: CatalogoRepository,
        criar_viagem: CriarViagem,
        atualizar_viagem: AtualizarViagem,
        destinos: GerenciarDestinosViagem,
        atividades: GerenciarAtividadesViagem,
        avaliacoes: AvaliarAtividadeViagem,
        orcamento: GerenciarOrcamentoViagem,
    ):
        self.registro = registro
        self.catalogo = catalogo
        self.criar_viagem = criar_viagem
        self.atualizar_viagem = atualizar_viagem
        self.destinos = destinos
        self.atividades = atividades
        self.avaliacoes = avaliacoes
        self.orcamento = orcamento

    def execute(self, usuarios: dict[str, int], referencia: date) -> dict:
        manifesto = {
            "destinos_catalogo": {},
            "atividades_catalogo": {},
            "viagens": {},
            "paradas": {},
            "atividades_roteiro": {},
            "avaliacoes": {},
        }
        lugares, atividades = self._catalogo(manifesto)
        planos = (
            (
                "florida",
                "Orlando e Miami em grupo",
                "criador",
                ("orlando", "miami"),
                30,
                "6000",
                True,
            ),
            (
                "rio",
                "Cultura e paisagens no Rio de Janeiro",
                "criador",
                ("rio",),
                -30,
                "1200",
                False,
            ),
            ("roma", "História e gastronomia em Roma", "criador", ("roma",), 60, "2000", False),
            ("roma-privada", "Roma: roteiro privado", "externo", ("roma",), 90, "500", False),
            ("descartavel", "Rio para descansar", "descartavel", ("rio",), 120, "1000", False),
        )
        for chave, nome, papel, cidades, dias, limite, compartilhar in planos:
            inicio = referencia + timedelta(days=dias)
            dono = usuarios[papel]
            viagem = self.criar_viagem.execute(
                dono,
                nome,
                "Roteiro ilustrativo. Valores em BRL para testes, sem preços oficiais.",
                inicio,
                inicio + timedelta(days=11),
            )
            self.atualizar_viagem.execute(
                viagem.id,
                dono,
                status=StatusViagem.CONCLUIDA if dias < 0 else StatusViagem.CONFIRMADA,
            )
            manifesto["viagens"][chave] = viagem.id
            avaliadores = [dono]
            if compartilhar:
                for papel_membro in PapelMembro:
                    membro = usuarios[papel_membro.value]
                    self.registro.vincular(viagem.id, membro, papel_membro)
                    avaliadores.append(membro)
            for i, cidade in enumerate(cidades):
                self._parada(
                    manifesto,
                    chave,
                    cidade,
                    viagem.id,
                    dono,
                    inicio + timedelta(days=i * 6),
                    lugares[cidade],
                    atividades[cidade],
                    avaliadores,
                )
            self.orcamento.definir(viagem.id, dono, Decimal(limite))
        return manifesto

    def _catalogo(self, manifesto: dict) -> tuple[dict, dict]:
        lugares, atividades = {}, {}
        for dado in LUGARES_REAIS:
            lugar = self.catalogo.salvar_destino(
                DestinoCatalogo(
                    nome=dado.nome,
                    pais_codigo=dado.pais,
                    descricao=dado.descricao,
                    latitude=Decimal(dado.latitude),
                    longitude=Decimal(dado.longitude),
                    foto_url=dado.foto_url,
                )
            )
            lugares[dado.chave] = lugar
            manifesto["destinos_catalogo"][dado.chave] = lugar.id
            atividades[dado.chave] = []
            for i, (nome, foto_url, categoria, area, descricao, _) in enumerate(dado.atividades):
                atividade = self.catalogo.salvar_atividade(
                    AtividadeCatalogo(
                        destino=lugar,
                        nome=nome,
                        categoria=categoria,
                        endereco=area,
                        descricao=descricao,
                        foto_url=foto_url,
                    )
                )
                atividades[dado.chave].append(atividade)
                manifesto["atividades_catalogo"][f"{dado.chave}-{i + 1}"] = atividade.id
        return lugares, atividades

    def _parada(
        self,
        manifesto: dict,
        chave: str,
        cidade: str,
        viagem_id: int,
        dono: int,
        chegada: date,
        lugar: DestinoCatalogo,
        atividades: list[AtividadeCatalogo],
        avaliadores: list[int],
    ) -> None:
        parada = self.destinos.criar(
            viagem_id,
            dono,
            lugar.id,
            chegada,
            chegada + timedelta(days=5),
            descricao="Passeios e deslocamentos organizados para a estadia.",
            hospedagem="Hospedagem na região central",
        )
        manifesto["paradas"][f"{chave}-{cidade}"] = parada.id
        dado = next(lugar for lugar in LUGARES_REAIS if lugar.chave == cidade)
        for i, catalogo in enumerate(atividades):
            estado = (
                StatusAtividade.CONCLUIDA,
                StatusAtividade.CONFIRMADA,
                StatusAtividade.PENDENTE,
            )[i % 3]
            custo = (
                "0" if catalogo.nome == "Metromover" else ("350", "250", "120", "80", "60", "0")[i]
            )
            ocorrencia = self.atividades.criar(
                viagem_id,
                parada.id,
                dono,
                catalogo.id,
                chegada + timedelta(days=i),
                hora_inicio=time(9 if i % 2 == 0 else 14),
                duracao_minutos=dado.atividades[i][5],
                custo_previsto=Decimal(custo),
                status=estado,
            )
            identificador = f"{chave}-{cidade}-{i + 1}"
            manifesto["atividades_roteiro"][identificador] = ocorrencia.id
            if estado == StatusAtividade.CONCLUIDA:
                for j, usuario_id in enumerate(avaliadores):
                    review = self.avaliacoes.execute(
                        viagem_id,
                        parada.id,
                        ocorrencia.id,
                        usuario_id,
                        nota=(5, 4, 3)[j % 3] if chave != "roma" else 3,
                        comentario=(
                            (
                                "Gostei do passeio e da organização do roteiro.",
                                "Valeu a visita; recomendo reservar tempo para as filas.",
                                "O lugar é interessante, mas prefiro um passeio mais tranquilo.",
                            )[j % 3]
                        ),
                    )
                    chave_review = f"{identificador}-{usuario_id}"
                    manifesto["avaliacoes"][chave_review] = review.id
