"""Constantes das regras de negócio decididas em docs/decisoes-de-produto.md."""

from app.domain.enums import PapelMembro

# Convites por email (RF18): link de uso único, ligado ao email convidado.
CONVITE_VALIDADE_DIAS = 7
PAPEL_INICIAL_CONVIDADO = PapelMembro.VISUALIZADOR

# Recuperação de senha (RF03)
RECUPERACAO_SENHA_VALIDADE_MINUTOS = 60

# Dinheiro e datas
MOEDA_PADRAO = "BRL"  # ISO 4217
FUSO_HORARIO_EXIBICAO_PADRAO = "America/Sao_Paulo"  # só para exibição

# Avaliações (RF22) e ranking de destinos (RF25)
NOTA_MINIMA = 1
NOTA_MAXIMA = 5
RANKING_PESO_PRIORI = 5  # "m" da média bayesiana: nº de avaliações para confiar no destino
