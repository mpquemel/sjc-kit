# =============================================================================
# TEMPLATE DE PEÇA — esqueleto com blocos [OBRIGATÓRIA].
#
# Regras que o validador aplica a este arquivo:
#   1. Todo bloco marcado [OBRIGATÓRIA] precisa aparecer na peça gerada.
#      Bloco obrigatório ausente = REPROVA no portão de forma. Não é aviso.
#   2. Bloco não marcado pode ser omitido, mas sua omissão é registrada no
#      relatório de gates com o motivo declarado em `# motivo:`.
#   3. Marcador `{{campo}}` só pode referenciar campo existente em
#      core/casos/models.py ou em dominios/<id>/dominio.yaml. Campo
#      inexistente = REPROVA na validação do template (antes de rodar).
#
# Não use formatação visual (negrito, cor, tabela complexa) como argumento.
# A estrutura carrega o argumento. Leitor de tela não vê ênfase.
# =============================================================================

# {{orgao_julgador}}

{{cliente}}, já qualificado nos autos do processo
{{identificador_externo}}, por seu procurador que ao final subscreve, vem
respeitosamente à presença de Vossa Excelência apresentar

## {{titulo_peca}}

pelas razões de fato e de direito a seguir expostas.

## I — DOS FATOS

[OBRIGATÓRIA]

{{fatos}}

## II — DO DIREITO

[OBRIGATÓRIA]

{{fundamentacao}}

## III — DOS PEDIDOS

[OBRIGATÓRIA]

Diante do exposto, requer:

{{pedidos}}

## IV — DO VALOR

[OPCIONAL]
# motivo: peças não condenatórias dispensam valor da causa

Termos em que,
pede deferimento.

{{local}}, {{data}}.

{{nome_operador}}
{{oab_operador}}
