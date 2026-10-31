from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha


class TokenRecuperacaoSenhaRepository(ABC):
    @abstractmethod
    def salvar(self, token: TokenRecuperacaoSenha) -> TokenRecuperacaoSenha:
        pass

    @abstractmethod
    def buscar_por_hash(self, token_hash: str) -> TokenRecuperacaoSenha | None:
        """Busca o token e o reserva ate o fim da transacao.

        Duas redefinicoes simultaneas com o mesmo link nao podem ambas ve-lo como
        nao usado: a segunda espera a primeira terminar.
        """
        pass

    @abstractmethod
    def invalidar_pendentes(self, usuario_id: int, agora: datetime) -> None:
        """Inutiliza os tokens ainda nao usados do usuario (so o link mais novo vale)."""
        pass
