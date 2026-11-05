from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DadosToken:
    """Conteudo verificado de um token de acesso.

    `jti` identifica a sessao (permite revogar so este token) e `versao_sessao`
    e a versao das sessoes do usuario na emissao (permite revogar todas de uma vez).
    """

    usuario_id: int
    jti: str
    versao_sessao: int
    expira_em: datetime


class TokenService(ABC):
    @abstractmethod
    def gerar_token(self, usuario_id: int, versao_sessao: int) -> str:
        pass

    @abstractmethod
    def verificar_token(self, token: str) -> DadosToken:
        """Retorna os dados do token, ou levanta NaoAutenticado se inválido/expirado."""
        pass
