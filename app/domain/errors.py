class ErroNegocio(ValueError):
    """Falha esperada de negocio, independente de HTTP."""


class DadosInvalidos(ErroNegocio):
    pass


class EmailDuplicado(ErroNegocio):
    pass


class ContaComViagensCompartilhadas(ErroNegocio):
    """A exclusão da conta apagaria planejamento de outros participantes."""


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


class AtividadeCatalogoNaoEncontrada(ErroNegocio):
    pass


class DestinoCatalogoNaoEncontrado(ErroNegocio):
    pass


class DestinoViagemNaoEncontrado(ErroNegocio):
    pass


class AtividadeViagemNaoEncontrada(ErroNegocio):
    pass


class ConviteInvalido(ErroNegocio):
    """Link de convite inexistente ou expirado (mesma mensagem para os dois casos)."""


class ConviteJaAceito(ErroNegocio):
    """O convite e de uso unico e ja foi aceito."""


class ConviteDeOutroEmail(AcessoNegado):
    """O usuario logado nao e o dono do email convidado."""


class ConviteNaoEncontrado(ErroNegocio):
    """Convite pendente inexistente nesta viagem."""


class FalhaEnvioConvite(ErroNegocio):
    """O email do convite nao pode ser enviado; nada foi gravado."""


class MembroJaParticipa(ErroNegocio):
    """Usuario ja e o criador ou colaborador da viagem."""


class MembroNaoEncontrado(ErroNegocio):
    """Usuario nao e colaborador desta viagem."""


class NotificacaoNaoEncontrada(ErroNegocio):
    """Notificacao inexistente ou de outro usuario (mesma resposta para os dois casos)."""


class FalhaProvedorLocais(ErroNegocio):
    """O fornecedor externo de locais nao respondeu como esperado; nada foi gravado."""


class ProvedorLocaisIndisponivel(FalhaProvedorLocais):
    """Timeout, falha de rede, erro do servidor ou resposta ilegivel."""


class LimiteProvedorLocaisExcedido(FalhaProvedorLocais):
    """Cota ou limite de requisicoes do fornecedor atingido (HTTP 429)."""

    def __init__(self, mensagem: str, tentar_em_segundos: int | None = None):
        super().__init__(mensagem)
        self.tentar_em_segundos = tentar_em_segundos


class CredencialProvedorLocaisInvalida(FalhaProvedorLocais):
    """Chave do fornecedor ausente, invalida ou sem permissao (HTTP 401/403)."""
