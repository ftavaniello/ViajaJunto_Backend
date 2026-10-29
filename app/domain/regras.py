"""Constantes das regras de negócio decididas em docs/decisoes-de-produto.md."""

from app.domain.enums import PapelMembro

# Convites (RF18)
CODIGO_CONVITE_TAMANHO = 10
# Sem I, O, 0 e 1 para evitar confusão ao ditar/digitar o código.
CODIGO_CONVITE_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODIGO_CONVITE_VALIDADE_DIAS = 7
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
