from app.domain.errors import ContaComViagensCompartilhadas
from app.domain.ports.total_usuarios_cache import TotalUsuariosCache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository
from app.domain.ports.vinculos_conta_repository import VinculosContaRepository


class ExcluirUsuario:
    def __init__(
        self,
        repository: UsuarioRepository,
        uow: UnitOfWork,
        vinculos: VinculosContaRepository,
        cache: TotalUsuariosCache | None = None,
    ):
        self.cache = cache
        self.repository = repository
        self.uow = uow
        self.vinculos = vinculos

    def execute(self, usuario_id: int) -> None:
        with self.uow:
            if self.vinculos.bloquear_e_verificar_colaboradores(usuario_id):
                raise ContaComViagensCompartilhadas(
                    "Não é possível excluir a conta enquanto você for criador de viagens "
                    "com colaboradores. Resolva essas viagens antes de excluir a conta."
                )
            # Cascatas permitidas explicitamente: viagens próprias sem colaboradores,
            # participações em outras viagens, tokens e notificações da conta.
            # Avaliações e referências de autoria são preservadas com autor nulo.
            self.repository.deletar(usuario_id)
            self.uow.commit()

        if self.cache is not None:
            self.cache.invalidar()
