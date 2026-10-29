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


class TokenRecuperacaoInvalido(ErroNegocio):
    """Token de recuperacao inexistente, expirado ou ja utilizado (mesma mensagem)."""
