from abc import ABC, abstractmethod


class TokenService(ABC):

    @abstractmethod
    def gerar_token(self, usuario_id: int) -> str:
        pass

    @abstractmethod
    def verificar_token(self, token: str) -> int:
        """Retorna o id do usuário dono do token, ou levanta ValueError se inválido/expirado."""
        pass
