class ErroNegocio(ValueError):
    """Falha esperada de negocio, independente de HTTP."""


class DadosInvalidos(ErroNegocio):
    pass


class EmailDuplicado(ErroNegocio):
    pass


class UsuarioNaoEncontrado(ErroNegocio):
    pass


class NaoAutenticado(ErroNegocio):
    pass


class ViagemNaoEncontrada(ErroNegocio):
    """Viagem inexistente ou sem acesso para o usuario (nao revela a existencia)."""


class AcessoNegado(ErroNegocio):
    """Participante da viagem sem permissao para a acao."""


class TokenRecuperacaoInvalido(ErroNegocio):
    """Token de recuperacao inexistente, expirado ou ja utilizado (mesma mensagem)."""
