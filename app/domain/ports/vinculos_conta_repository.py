from typing import Protocol


class VinculosContaRepository(Protocol):
    def bloquear_e_verificar_colaboradores(self, usuario_id: int) -> bool:
        """Protege conta e viagens criadas até o fim da transação.

        Impede novos vínculos concorrentes e informa se alguma viagem criada
        tem outro participante. Não altera nem exclui os vínculos.
        """
        ...
