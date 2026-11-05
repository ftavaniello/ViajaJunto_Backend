from datetime import datetime

from app.domain.entities.token_recuperacao_senha import TokenRecuperacaoSenha
from app.domain.ports.token_recuperacao_senha_repository import TokenRecuperacaoSenhaRepository


class TokenRecuperacaoSenhaRepositoryMemory(TokenRecuperacaoSenhaRepository):
    def __init__(self):
        self.tokens: dict[str, TokenRecuperacaoSenha] = {}
        self.proximo_id = 1

    def salvar(self, token: TokenRecuperacaoSenha) -> TokenRecuperacaoSenha:
        if token.id is None:
            token.id = self.proximo_id
            self.proximo_id += 1

        self.tokens[token.token_hash] = token

        return token

    def buscar_por_hash(self, token_hash: str) -> TokenRecuperacaoSenha | None:
        return self.tokens.get(token_hash)

    def invalidar_pendentes(self, usuario_id: int, agora: datetime) -> None:
        for token in self.tokens.values():
            if token.usuario_id == usuario_id and token.usado_em is None:
                token.usado_em = agora
