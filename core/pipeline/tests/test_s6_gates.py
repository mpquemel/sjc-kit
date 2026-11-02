"""
Testes do S6 — o estágio que reprova.

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o
gate DEVE recusar:

  - apelação sem bloco de razões            -> REPROVA
  - bloco de razões com menos de 3 parágrafos -> REPROVA
  - peça vazia                              -> aborta, não PASSA
  - regra em prosa sem avaliador            -> NAO_AVALIADO, nunca PASSA
  - prazo com marca de conferência          -> REPROVA a peça inteira
  - regra de outro tipo de peça             -> NAO_APLICAVEL (não conta)
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s3_estrategia import S3Estrategia, documento  # noqa: E402
from core.pipeline.s6_gates import S6Gates  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import PipelineContext  # noqa: E402






# ---------------------------------------------------------------------------
# Peças de trabalho
# ---------------------------------------------------------------------------

PECA_APELACAO_BOA = """\
# APELAÇÃO

## RAZÕES DE APELAÇÃO

### I — SÍNTESE DA DECISÃO RECORRIDA

A sentença julgou procedente o pedido, condenando o apelante ao pagamento de
alimentos no valor de 30% dos rendimentos.

### II — RAZÕES PARA REFORMA

O apelante sustenta que o percentual fixado compromete sua subsistência. Nos
termos do art. 1.694, §1º, do Código Civil, a fixação deve observar o binômio
necessidade e possibilidade — e o apelante comprova despesa médica continuada.

"Ante o exposto, julgo procedente o pedido para fixar os alimentos em trinta
por cento dos rendimentos líquidos do requerido."

Ainda que se reconheça a necessidade do alimentando, o percentual adotado
desconsidera a capacidade contributiva efetiva, comprovada pelos holerites de
fls. 88/92.

### III — DOS PEDIDOS

Requer o provimento para redução do percentual.
"""

PECA_SEM_RAZOES = """\
# APELAÇÃO

## RAZÕES DE APELAÇÃO

### I — SÍNTESE DA DECISÃO RECORRIDA

A sentença julgou procedente o pedido.

### II — DOS PEDIDOS

Requer o provimento do recurso.
"""

PECA_RAZOES_FRACA = """\
# APELAÇÃO

### II — RAZÕES PARA REFORMA

A sentença está errada. O juiz não apreciou bem as provas.

### IV — DOS PEDIDOS

Requer o provimento.
"""

PECA_AGRAVO = """\
# AGRAVO DE INSTRUMENTO

### DAS RAZÕES DE INCONFORMIDADE

O agravante impugna a decisão que fixou alimentos provisórios em 40% dos
rendimentos, sem sequer mencionar a possibilidade do alimentante.

### DOS PEDIDOS

Requer o provimento.
"""


def _ctx(peca_texto, estrategia=None, dominio="familia"):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s6-")
    ctx = PipelineContext(Path(tmp), dominio)
    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": dominio,
        "polo_atuacao": "ativo",
    }
    ctx.artefatos["S3"] = {
        "caso_id": "00000000000000000000",
        "estrategia": estrategia or {
            "polo_atuacao": "ativo",
            "gatilho": "sentenca-procedente-ou-improcedente",
            "peca_cabivel": "apelacao",
            "prazo_estimado": {"base": "art. 1.003, §5º, do CPC",
                               "conferido": True, "data_limite": None},
            "precisa_humano": False,
        },
    }
    if peca_texto is not None:
        ctx.artefatos["S0"]["peca_texto"] = peca_texto
    return ctx


def _rodar(peca_texto, **kw):
    return S6Gates().rodar(_ctx(peca_texto, **kw))


def _gates(r):
    assert r.ok and not r.pausado, f"gate não rodou: {r.problemas or r.motivo_pausa}"
    return r.saida["gates"]


def _regra(g, rid):
    for a in g["regras_avaliadas"]:
        if a["id"] == rid:
            return a
    raise AssertionError(f"regra {rid} não apareceu no relatório")


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def t_peca_boa_passa_no_que_e_verificavel():
    g = _gates(_rodar(PECA_APELACAO_BOA))
    assert _regra(g, "apelacao-sem-razoes-de-reforma")["veredito"] == "PASSA", \
        _regra(g, "apelacao-sem-razoes-de-reforma")["motivo"]
    assert _regra(g, "apelacao-sem-impugnacao-especifica")["veredito"] == "PASSA", \
        _regra(g, "apelacao-sem-impugnacao-especifica")["motivo"]


def t_apelacao_sem_bloco_de_razoes_reprova():
    g = _gates(_rodar(PECA_SEM_RAZOES))
    r = _regra(g, "apelacao-sem-razoes-de-reforma")
    assert r["veredito"] == "REPROVA", f"gate deixou passar: {r['veredito']}"
    assert "não tem bloco" in r["motivo"], r["motivo"]
    assert g["veredito"] == "REPROVA", g["veredito"]
    assert g["pode_protocolar"] is False


def t_razoes_com_poucos_paragrafos_reprova():
    g = _gates(_rodar(PECA_RAZOES_FRACA))
    r = _regra(g, "apelacao-sem-razoes-de-reforma")
    assert r["veredito"] == "REPROVA", f"1 parágrafo passou: {r['veredito']}"
    assert "1 parágrafo" in r["motivo"], r["motivo"]


def t_peca_vazia_aborta():
    r = _rodar("   \n\n  ")
    assert r.pausado, "peça vazia deveria abortar/pausar, não PASSA"
    assert "vazia" in r.motivo_pausa.lower(), r.motivo_pausa


def t_regra_sem_avaliador_e_nao_avaliado():
    """
    As 4 regras em prosa do catálogo de família não são executáveis por
    programa hoje. Elas NÃO podem sair PASSA — bateria verde com metade não
    executada é mentira com aparência de método.
    """
    g = _gates(_rodar(PECA_APELACAO_BOA))
    r = _regra(g, "alimentos-sem-binomio")
    assert r["veredito"] == "NAO_AVALIADO", f"prosa virou {r['veredito']}"
    assert "sem avaliador" in r["motivo"], r["motivo"]
    assert "alimentos-sem-binomio" in g["nao_avaliadas"]


def t_veredito_da_peca_nao_e_passa_com_nao_avaliada():
    """
    Pior veredito vence. Peça com tudo PASSA mas uma regra NAO_AVALIADO não
    pode sair PASSA: quem lê precisa saber que a bateria foi incompleta.
    """
    g = _gates(_rodar(PECA_APELACAO_BOA))
    assert g["veredito"] != "PASSA", \
        f"veredito {g['veredito']} com {len(g['nao_avaliadas'])} regra(s) não avaliada(s)"
    assert g["pode_protocolar"] is False


def t_prazo_nao_conferido_reprova_peca_inteira():
    estrategia = {
        "polo_atuacao": "ativo",
        "gatilho": "sentenca-procedente-ou-improcedente",
        "peca_cabivel": "apelacao",
        "prazo_estimado": {"base": "art. 1.003, §5º, do CPC — CONFERIR",
                           "conferido": False, "data_limite": None},
        "precisa_humano": True,
    }
    g = _gates(_rodar(PECA_APELACAO_BOA, estrategia=estrategia))
    r = _regra(g, "prazo-conferir-marca")
    assert r["veredito"] == "REPROVA", f"prazo não conferido virou {r['veredito']}"
    assert g["veredito"] == "REPROVA", g["veredito"]


def t_prazo_conferido_passa():
    g = _gates(_rodar(PECA_APELACAO_BOA))
    r = _regra(g, "prazo-conferir-marca")
    assert r["veredito"] == "PASSA", r["motivo"]


def t_regra_de_outra_peca_nao_e_aplicavel():
    """Gate de apelação não julga agravo."""
    g = _gates(_rodar(PECA_AGRAVO, estrategia={
        "polo_atuacao": "ativo",
        "gatilho": "decisao-interlocutoria-alimentos",
        "peca_cabivel": "agravo-instrumento",
        "prazo_estimado": {"base": "art. 1.015 do CPC", "conferido": True,
                           "data_limite": None},
        "precisa_humano": False,
    }))
    r = _regra(g, "apelacao-sem-razoes-de-reforma")
    assert r["veredito"] == "NAO_APLICAVEL", f"gate cruzado: {r['veredito']}"


def t_impugnacao_generica_adverte():
    g = _gates(_rodar(PECA_RAZOES_FRACA))
    r = _regra(g, "apelacao-sem-impugnacao-especifica")
    assert r["veredito"] == "ADVERTE", f"sem referência à decisão virou {r['veredito']}"


def t_integracao_s3_para_s6_no_runner():
    """S3 decide apelação; S6 recebe a peça e reprova por prazo não conferido."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s36-")
    ctx = PipelineContext(Path(tmp), "familia")
    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": "familia",
        "polo_atuacao": "ativo",
        "peca_texto": PECA_APELACAO_BOA,
    }
    from core.pipeline.stage import Stage

    class S0Falso(Stage):
        """S0 mínimo. O DAG exige que a dependência declarada exista."""
        id = "S0"
        nome = "entrada-de-teste"
        depende_de = []  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["caso_id", "dominio_id", "polo_atuacao",
                        "peca_texto"]  # type: ignore[assignment]

        def executar(self, ctx):
            # S0 é a fonte do caso: devolver {} faz o runner validar saída
            # vazia e falhar em S0, não em S3.
            return dict(ctx.artefatos.get("S0") or {})

    # `documentos` vem do S1Falso, não do S0: declarar nos dois colide de chave
    # e o contrato recusa — comportamento correto.

    # S6 declara dependência de S4 (de onde vem a peça em produção). Dependência
    # declarada tem de existir no DAG, senão o runner levanta DAGInvalido. O
    # teste inclui S4 — que pausa por modelo indefinido em família — e por isso
    # injeta provedor e config.
    from core.pipeline.s4_redacao import S4Redacao

    s4 = S4Redacao()
    s4.provedor = lambda prompt, contexto: "Texto do bloco, sem citação."
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}


    class S1Falso(Stage):
        """S1 mínimo: `documentos` nasce no S1, não no S0.

        S3 declara `depende_de = ["S0", "S1"]` porque é o S1 que produz os
        documentos tipados. Sem S1 no DAG de teste, o runner recusa o grafo
        por dependência inexistente — comportamento correto, não defeito.
        """
        id = "S1"
        nome = "conversao-de-teste"
        depende_de = ["S0"]  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["documentos"]  # type: ignore[assignment]

        def executar(self, ctx):
            return {"documentos": [documento("sentenca", resultado="procedente",
                                             texto="Julgo procedente o pedido.")]}

    res = Runner([S0Falso(), S1Falso(), S3Estrategia(), s4, S6Gates()], ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}"
    gates = ctx.artefatos["S6"]["gates"]
    assert gates["peca"] == "apelacao", gates["peca"]
    assert gates["veredito"] == "REPROVA", \
        f"prazo [CONFERIR] do catálogo real deveria reprovar; veio {gates['veredito']}"


TESTES = [
    ("t_peca_boa_passa_no_que_e_verificavel", t_peca_boa_passa_no_que_e_verificavel),
    ("t_apelacao_sem_bloco_de_razoes_reprova", t_apelacao_sem_bloco_de_razoes_reprova),
    ("t_razoes_com_poucos_paragrafos_reprova", t_razoes_com_poucos_paragrafos_reprova),
    ("t_peca_vazia_aborta", t_peca_vazia_aborta),
    ("t_regra_sem_avaliador_e_nao_avaliado", t_regra_sem_avaliador_e_nao_avaliado),
    ("t_veredito_da_peca_nao_e_passa_com_nao_avaliada",
     t_veredito_da_peca_nao_e_passa_com_nao_avaliada),
    ("t_prazo_nao_conferido_reprova_peca_inteira", t_prazo_nao_conferido_reprova_peca_inteira),
    ("t_prazo_conferido_passa", t_prazo_conferido_passa),
    ("t_regra_de_outra_peca_nao_e_aplicavel", t_regra_de_outra_peca_nao_e_aplicavel),
    ("t_impugnacao_generica_adverte", t_impugnacao_generica_adverte),
    ("t_integracao_s3_para_s6_no_runner", t_integracao_s3_para_s6_no_runner),
]


if __name__ == "__main__":
    executar_e_sair("S6 GATES", TESTES)
