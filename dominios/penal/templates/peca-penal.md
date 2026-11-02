# =============================================================================
# DOMÍNIO PENAL — TEMPLATE DE PEÇA. ESQUELETO.
#
# Um template penal tem blocos que o civil não tem. A lista abaixo é o teste do
# núcleo: se algum destes blocos exigir campo novo em core/casos/models.py com
# nome penal-específico, o núcleo vazou para o domínio.
#
# Bloco declarado vazio, não preenchido. A ordem dos blocos é a ordem da peça —
# em penal a ordem pode decidir a leitura (preliminar de nulidade antes do
# mérito, sempre; tese subsidiária nunca antes da principal).
# =============================================================================

# {{orgao_julgador}}

{{cliente}}, já qualificado nos autos do processo
{{identificador_externo}}, por seu procurador que ao final subscreve, vem
respeitosamente à presença de Vossa Excelência apresentar

## {{titulo_peca}}

## I — SÍNTESE PROCESSUAL

[OBRIGATÓRIA]
# a preencher — data da denúncia, imputação, fase atual, decisão impugnada

## II — PRELIMINARES

[OBRIGATÓRIA]
# a preencher — nulidades na ordem em que prejudicam: competência, citação,
# prova ilícita, cadeia de custódia, cerceamento. Cada uma com o prejuízo
# demonstrado — nulidade sem prejuízo é pedido que o juiz nega por preguiça.
# motivo: blocos obrigatórios porque preliminar omitida não se recupera em recurso seguinte

## III — DO MÉRITO

[OBRIGATÓRIA]
# a preencher — impugnação ponto a ponto da prova de acusação, com referência
# à peça e ao id onde cada elemento aparece

## IV — SUBSIDIÁRIO

[OPCIONAL]
# motivo: nem toda peça tem tese subsidiária; omitido é registrado no relatório
# a preencher — dosimetria, regime, substituição, prescrição

## V — DOS PEDIDOS

[OBRIGATÓRIA]
# a preencher — pedido certo e determinado, na ordem de preferência

Termos em que,
pede deferimento.

{{local}}, {{data}}.

{{nome_operador}}
{{oab_operador}}

# -----------------------------------------------------------------------------
# CAMPOS QUE O TEMPLATE EXIGE DO NÚCLEO (o teste de acoplamento em concreto)
# Se algum destes não existir hoje no modelo de caso, o campo é GENÉRICO e deve
# entrar em core/casos/models.py — nunca um campo com nome de área:
#   orgao_julgador        ✔ genérico
#   cliente               ✔ genérico
#   identificador_externo ✔ genérico
#   titulo_peca           ✔ genérico
#   decisao_impugnada     ? verificar — provavelmente genérico, como "documento_alvo"
#   fase_processual       ? verificar — genérico, se aceitar "instrução", "sentença"
#   local, data           ✔ genérico
#   nome_operador, oab    ✔ genérico
# -----------------------------------------------------------------------------
