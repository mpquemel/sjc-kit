"""
Testes do S4 — redação com provedor injetável.

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S4
DEVE RECUSAR:

  - modelo não decidido no domínio        -> pausa, não default inventado
  - "a preencher" no lugar de decisão     -> tratado como NÃO decidido
  - sem provedor injetado                 -> pausa
  - peça não declarada pela estratégia    -> pausa
  - template inexistente                  -> erro de contrato
  - citação fora da lista de autoridades  -> registrada como não sustentada
  - bloco opcional ausente                -> não quebra a montagem
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s3_estrategia import S3Estrategia, documento  # noqa: E402
from core.pipeline.s4_redacao import S4Redacao, _eh_titulo  # noqa: E402
from core.pipeline.s5_citacoes import S5Citacoes  # noqa: E402
from core.pipeline.s6_gates import S6Gates  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import PipelineContext, Stage  # noqa: E402






# ---------------------------------------------------------------------------
# Provedores falsos — nenhum toca a rede
# ---------------------------------------------------------------------------

def _provedor_fixo(prompt, contexto):
    """Devolve sempre um texto sem citação. Determinístico, sem custo."""
    return (f"Texto do bloco {contexto['titulo']}. Sustenta-se no que consta "
            f"dos autos, sem invocar precedente não conferido.")


def _provedor_cita_inventado(prompt, contexto):
    """Cita um julgado que ninguém declarou como autoridade."""
    return "Conforme o REsp 9.876.543/SP, o pedido prospera."


ESTRATEGIA = {
    "polo_atuacao": "ativo",
    "gatilho": "sentenca-procedente-ou-improcedente",
    "peca_cabivel": "apelacao",
    "prazo_estimado": {"base_legal": "art. 1.003, §5º, do CPC",
                       "conferido": True},
    "precisa_humano": False,
}


def _ctx(estrategia=None, dominio="familia", **extra):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s4-")
    ctx = PipelineContext(Path(tmp), dominio)
    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": dominio,
        "polo_atuacao": "ativo",
    }
    ctx.artefatos["S3"] = {
        "caso_id": "00000000000000000000",
        "estrategia": estrategia or dict(ESTRATEGIA),
    }
    for k, v in extra.items():
        ctx.artefatos["S0"][k] = v
    return ctx


def _rodar(provedor=_provedor_fixo, estrategia=None, dominio="familia", **kw):
    s4 = S4Redacao()
    s4.provedor = provedor
    return s4.rodar(_ctx(estrategia, dominio, **kw))


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def t_comentario_nao_e_titulo():
    """
    `# motivo: ...` é justificativa de template, não cabeçalho. Lido como
    título de nível 1 dentro de bloco nível 3, encerrava o consumo no meio e
    deixava `{{preliminares}}` órfão. Medido em 02/11/2026: 3 de 4 blocos.
    """
    assert _eh_titulo("# motivo: apelação sem preliminar é cabível") is False
    assert _eh_titulo("### III — PRELIMINARES") is True
    assert _eh_titulo("## RECURSO DE APELAÇÃO") is True
    assert _eh_titulo("[OPCIONAL]") is False


def t_todos_os_blocos_sao_encontrados():
    """Template de apelação tem 4 blocos: 3 obrigatórios + 1 opcional."""
    s4 = S4Redacao()
    tpl = s4._carregar_template("familia", "apelacao")
    blocos = s4._dividir_blocos(tpl)
    assert len(blocos) == 4, [b["chave"] for b in blocos]
    obrig = [b for b in blocos if b["exigencia"] == "OBRIGATORIA"]
    assert len(obrig) == 3, [b["chave"] for b in obrig]


def t_modelo_nao_decidido_pausa():
    """
    O catálogo real de família traz `a preencher`. S4 tem de PAUSAR, não
    inventar default: o requisito é o rastro da escolha, não o valor.
    """
    r = _rodar()
    assert r.pausado, "S4 não pausou com modelo indefinido"
    assert "modelo" in r.motivo_pausa.lower(), r.motivo_pausa
    assert "apelacao" in r.motivo_pausa, r.motivo_pausa


def t_a_preencher_nao_e_decisao():
    """Campo preenchido com 'a preencher' é ausência escrita de forma educada."""
    s4 = S4Redacao()
    cfg = {"modelos": {"default": {"provider": "a preencher",
                                    "modelo": "a preencher",
                                    "motivo": "a preencher"}}}
    assert s4._modelo_decidido(cfg, "apelacao") is None

    cfg2 = {"modelos": {"por_peca": {"apelacao": {
        "provider": "local", "modelo": "m1", "motivo": "custo medido",
        "verificado_em": "2026-11-02"}}}}
    d = s4._modelo_decidido(cfg2, "apelacao")
    assert d and d["modelo"] == "m1", d


def t_sem_provedor_pausa():
    """
    Com modelo decidido mas sem provedor injetado, não há como redigir.

    A ordem das checagens importa e foi medida em 02/11/2026: com o modelo
    indefinido no domínio, o estágio pausa ANTES de olhar o provedor — e o
    teste que esperava "provedor" recebia "modelo". Correto é o estágio
    declarar a falta mais fundamental primeiro? Não: a falta de modelo é a que
    o OPERADOR resolve, e o provedor é configurada pelo operador também. Mas o
    teste precisa isolar a checagem que quer provar, então decide o modelo por
    injeção e deixa o provedor vazio.
    """
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s4-")
    ctx = PipelineContext(Path(tmp), "familia")
    ctx.artefatos["S0"] = {"caso_id": "0", "dominio_id": "familia",
                           "polo_atuacao": "ativo"}
    ctx.artefatos["S3"] = {"caso_id": "0", "estrategia": dict(ESTRATEGIA)}
    s4 = S4Redacao()
    s4.provedor = None
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    r = s4.rodar(ctx)
    assert r.pausado, "sem provedor deveria pausar"
    assert "provedor" in r.motivo_pausa.lower(), r.motivo_pausa


def t_peca_nao_declarada_pausa():
    r = _rodar(estrategia={"gatilho": "x", "peca_cabivel": ""})
    assert r.pausado, "sem peca_cabivel deveria pausar"
    assert "peca_cabivel" in r.motivo_pausa, r.motivo_pausa


def t_template_inexistente_e_erro_de_contrato():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s4-")
    ctx = PipelineContext(Path(tmp), "familia")
    ctx.artefatos["S0"] = {"caso_id": "0", "dominio_id": "familia",
                           "polo_atuacao": "ativo"}
    e = dict(ESTRATEGIA, peca_cabivel="peca-que-nao-existe")
    ctx.artefatos["S3"] = {"caso_id": "0", "estrategia": e}
    s4 = S4Redacao()
    s4.provedor = _provedor_fixo
    # modelo de família está indefinido; força pela injeção de config
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    r = s4.rodar(ctx)
    assert not r.ok and not r.pausado, f"esperava erro de contrato: {r.pausado}"
    assert any("template" in p for p in r.problemas), r.problemas


def t_peca_montada_preserva_assinatura_e_marcadores():
    s4 = S4Redacao()
    s4.provedor = _provedor_fixo
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    ctx = _ctx()
    r = s4.rodar(ctx)
    assert r.ok, r.problemas
    texto = r.saida["peca_texto"]
    assert "{{nome_operador}}" in texto, "assinatura perdida na montagem"
    assert "OAB/{{uf}}" in texto, "campo de OAB perdido"
    assert "[OBRIGATÓRIA]" not in texto, "marcador de template vazou para a peça"
    assert "# motivo:" not in texto, "comentário de template vazou para a peça"
    assert "{{preliminares}}" not in texto, "bloco opcional não foi preenchido"
    assert "EXCELENTÍSSIMO" in texto, "cabeçalho perdido"


def t_citacao_fora_das_autoridades_e_registrada():
    """
    Provedor cita julgado que ninguém declarou. O S4 NÃO apaga (esconderia) e
    NÃO libera (seria o defeito de origem): registra e força revisão humana.
    """
    s4 = S4Redacao()
    s4.provedor = _provedor_cita_inventado
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    r = s4.rodar(_ctx())
    assert r.ok, r.problemas
    red = r.saida["redacao"]
    assert red["citacoes_nao_sustentadas"], "citação órfã não foi registrada"
    assert red["precisa_humano"] is True
    chaves = [c["bloco"] for c in red["citacoes_nao_sustentadas"]]
    assert chaves, red["citacoes_nao_sustentadas"]


def t_provedor_limpo_nao_marca_revisao():
    s4 = S4Redacao()
    s4.provedor = _provedor_fixo
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    r = s4.rodar(_ctx())
    assert r.ok, r.problemas
    assert r.saida["redacao"]["citacoes_nao_sustentadas"] == []
    assert r.saida["redacao"]["precisa_humano"] is False


def t_rastro_por_bloco_existe():
    s4 = S4Redacao()
    s4.provedor = _provedor_fixo
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}
    r = s4.rodar(_ctx())
    blocos = r.saida["redacao"]["blocos"]
    assert len(blocos) == 4, len(blocos)
    for b in blocos:
        assert b["caracteres"] > 0, b
        assert "exigencia" in b


# ---------------------------------------------------------------------------
# Integração: S3 -> S4 -> S5 -> S6
# ---------------------------------------------------------------------------

def t_integracao_s3_s4_s5_s6():
    """
    O ciclo completo, com provedor e verificador falsos. A peça sai de S4,
    passa por S5 (offline, retendo) e por S6 (que reprova por prazo não
    conferido no catálogo real).
    """
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-ciclo-")
    ctx = PipelineContext(Path(tmp), "familia")

    class S0Falso(Stage):
        id = "S0"
        nome = "entrada-de-teste"
        depende_de = []  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["caso_id", "dominio_id", "polo_atuacao"]  # type: ignore[assignment]

        def executar(self, ctx):
            return dict(ctx.artefatos.get("S0") or {})

    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": "familia",
        "polo_atuacao": "ativo",
        "consulta_fonte": False,
    }

    s4 = S4Redacao()
    s4.provedor = _provedor_fixo
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste de integração"}}}


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

    res = Runner([S0Falso(), S1Falso(), S3Estrategia(), s4, S5Citacoes(), S6Gates()],
                 ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}"

    assert ctx.artefatos["S4"]["peca_texto"], "S4 não produziu peça"
    assert ctx.artefatos["S5"]["citacoes"]["retem"] is True, \
        "S5 deveria reter em modo offline"
    g = ctx.artefatos["S6"]["gates"]
    assert g["peca"] == "apelacao", g["peca"]
    assert g["veredito"] == "REPROVA", g["veredito"]


TESTES = [
    ("t_comentario_nao_e_titulo", t_comentario_nao_e_titulo),
    ("t_todos_os_blocos_sao_encontrados", t_todos_os_blocos_sao_encontrados),
    ("t_modelo_nao_decidido_pausa", t_modelo_nao_decidido_pausa),
    ("t_a_preencher_nao_e_decisao", t_a_preencher_nao_e_decisao),
    ("t_sem_provedor_pausa", t_sem_provedor_pausa),
    ("t_peca_nao_declarada_pausa", t_peca_nao_declarada_pausa),
    ("t_template_inexistente_e_erro_de_contrato", t_template_inexistente_e_erro_de_contrato),
    ("t_peca_montada_preserva_assinatura_e_marcadores",
     t_peca_montada_preserva_assinatura_e_marcadores),
    ("t_citacao_fora_das_autoridades_e_registrada",
     t_citacao_fora_das_autoridades_e_registrada),
    ("t_provedor_limpo_nao_marca_revisao", t_provedor_limpo_nao_marca_revisao),
    ("t_rastro_por_bloco_existe", t_rastro_por_bloco_existe),
    ("t_integracao_s3_s4_s5_s6", t_integracao_s3_s4_s5_s6),
]


if __name__ == "__main__":
    executar_e_sair("S4 REDAÇÃO", TESTES)
