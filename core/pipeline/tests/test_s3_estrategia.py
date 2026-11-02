"""
Testes do S3 — o estágio que decide.

Regra herdada: teste que só produz sucesso não validou nada. O foco aqui são
os casos em que o S3 DEVE RECUSAR decidir:

  - nenhuma regra casa                    -> pausa, não invenção
  - regra casa mas peça não tem template  -> pausa, não peça fantasma
  - polo não declarado                    -> indefinido + precisa_humano
  - prazo com [CONFERIR]                  -> confianca baixa
  - tese não conferida                    -> separada, não silenciada
  - data de intimação ausente             -> data_limite null com motivo
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s3_estrategia import S3Estrategia, documento  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import PipelineContext  # noqa: E402






def _ctx(documentos, dominio="familia", polo="ativo", **extra):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s3-")
    ctx = PipelineContext(Path(tmp), dominio)
    base = {"caso_id": "00000000000000000000", "dominio_id": dominio,
            "documentos": documentos}
    if polo is not None:
        base["polo_atuacao"] = polo
    base.update(extra)
    ctx.artefatos["S0"] = base
    return ctx


def _rodar(documentos, **kw):
    return S3Estrategia().rodar(_ctx(documentos, **kw))


def _estrategia(r):
    assert r.ok and not r.pausado, f"não produziu estratégia: {r.problemas or r.motivo_pausa}"
    return r.saida["estrategia"]


# ---------------------------------------------------------------------------
# Casamento de gatilho
# ---------------------------------------------------------------------------

def t_sentenca_extintiva_escolhe_apelacao():
    doc = documento("sentenca", resultado="extinto_sem_resolucao",
                    texto="Extingo o processo sem resolução de mérito.")
    e = _estrategia(_rodar([doc]))
    assert e["peca_cabivel"] == "apelacao", f"peça errada: {e['peca_cabivel']}"
    assert e["gatilho"] == "sentenca-extincao-sem-resolucao"


def t_agravo_de_tutela():
    doc = documento("decisao_interlocutoria",
                    texto="Defiro a tutela provisória de urgência.")
    e = _estrategia(_rodar([doc]))
    assert e["peca_cabivel"] == "agravo-instrumento", e["peca_cabivel"]


def t_sentenca_de_merito_tambem_vira_apelacao():
    doc = documento("sentenca", resultado="procedente",
                    texto="Julgo procedente o pedido.")
    e = _estrategia(_rodar([doc]))
    assert e["peca_cabivel"] == "apelacao", e["peca_cabivel"]


def t_resultado_em_lista_casa():
    """O catálogo aceita lista de resultados em uma regra só."""
    for res in ("procedente", "improcedente", "parcialmente_procedente"):
        e = _estrategia(_rodar([documento("sentenca", resultado=res)]))
        assert e["peca_cabivel"] == "apelacao", f"{res} não casou"


def t_conteudo_nao_contem_exclui():
    """
    A palavra "sentença" citada dentro de uma decisão interlocutória não torna
    o documento uma sentença, e não pode desqualificar a regra correta.

    Histórico: a regra de alimentos declarava `nao_contem: [sentenca]`. O texto
    "Determino alimentos provisórios. Sentença proferida." era excluído da regra
    certa e caía na regra de cumprimento — que casava só por conter "alimentos".
    Correções: (1) tipo documental é `tipo_documento`, nunca substring;
    (2) cumprimento passou a exigir conjunção (alimentos E cumprimento).
    """
    doc = documento("decisao_interlocutoria",
                    texto="Determino alimentos provisórios. Sentença proferida.")
    e = _estrategia(_rodar([doc]))
    assert e["peca_cabivel"] == "agravo-instrumento", e["peca_cabivel"]
    assert e["gatilho"] == "decisao-interlocutoria-alimentos", \
        f"a menção incidental à palavra sentença sequestrou o caso: {e['gatilho']}"


def t_conteudo_contem_todos_exige_conjuncao():
    """Cumprimento de sentença de alimentos exige alimentos E cumprimento."""
    # Só "alimentos": NÃO é cumprimento de sentença.
    r = _rodar([documento("decisao_interlocutoria",
                          texto="Fixo alimentos provisórios em favor do filho.")])
    e = _estrategia(r)
    assert e["gatilho"] != "cumprimento-de-sentenca-alimentos", \
        f"conjunção ignorada: casou {e['gatilho']} só com 'alimentos'"

    # Alimentos E cumprimento: agora sim.
    r2 = _rodar([documento("decisao_interlocutoria",
                           texto="Iniciado o cumprimento de sentença de alimentos.")])
    e2 = _estrategia(r2)
    assert e2["peca_cabivel"] == "impugnacao-cumprimento", e2["peca_cabivel"]


def t_tipo_documento_errado_nao_casa():
    """
    Sentença cujo texto menciona "tutela" NÃO casa a regra de interlocutória.
    O comportamento correto é PAUSAR: não há regra para sentença em que a tutela
    aparece só como menção, e inventar uma seria pior que pausar.
    """
    doc = documento("sentenca", texto="Defiro a tutela de urgência.")
    r = _rodar([doc])
    assert r.pausado, f"deveria pausar; ok={r.ok} problemas={r.problemas}"
    assert "nenhuma regra" in r.motivo_pausa.lower(), r.motivo_pausa


# ---------------------------------------------------------------------------
# Recusas — o S3 não pode inventar decisão
# ---------------------------------------------------------------------------

def t_nenhuma_regra_casa_pausa():
    """Caso sem documento correspondente: pausa com motivo, não peça inventada."""
    doc = documento("despacho", texto="Intime-se a parte autora.")
    r = _rodar([doc])
    assert r.ok and r.pausado, f"deveria pausar: ok={r.ok} pausado={r.pausado}"
    assert "nenhuma regra" in r.motivo_pausa.lower(), r.motivo_pausa
    assert "fallback" in r.motivo_pausa.lower(), \
        "não declarou que o fallback não está implementado"


def t_sem_documentos_pausa():
    r = _rodar([])
    assert r.pausado, "lista vazia de documentos deveria pausar"


def t_peça_sem_template_pausa():
    """
    Se o catálogo aponta peça sem template, o S3 recusa — S4 não teria o que ler.
    Este teste usa um domínio temporário para não depender do catálogo real.
    """
    import shutil, tempfile
    tmp = Path(tempfile.mkdtemp(prefix="sjc-dom-fant-"))
    d = tmp / "dominios" / "fantasma"
    (d / "templates").mkdir(parents=True)
    (d / "estrategia.yaml").write_text(
        "regras:\n  - id: r1\n    gatilho:\n      tipo_documento: sentenca\n"
        "    peca_cabivel: peca_que_nao_existe\n", encoding="utf-8")
    (d / "dominio.yaml").write_text(
        "id: fantasma\nnome: f\n", encoding="utf-8")
    try:
        import core.pipeline.s3_estrategia as m
        original = m.RAIZ
        m.RAIZ = tmp
        try:
            r = _rodar([documento("sentenca")], dominio="fantasma")
        finally:
            m.RAIZ = original
        assert r.pausado, f"deveria pausar; ok={r.ok} problemas={r.problemas}"
        assert "template" in r.motivo_pausa, r.motivo_pausa
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_dominio_inexistente_falha_na_entrada():
    r = _rodar([documento("sentenca")], dominio="nao_existe")
    assert not r.ok and not r.pausado, "domínio inexistente deveria falhar"
    assert any("dominios/" in p for p in r.problemas), r.problemas


def t_polo_invalido_falha_na_entrada():
    r = _rodar([documento("sentenca", resultado="procedente")], polo="autor")
    assert not r.ok, "polo inválido deveria falhar na entrada"
    assert any("polo_atuacao" in p for p in r.problemas), r.problemas


# ---------------------------------------------------------------------------
# Polo: nunca inferido
# ---------------------------------------------------------------------------

def t_polo_ausente_vira_indefinido_e_pede_humano():
    doc = documento("sentenca", resultado="procedente")
    e = _estrategia(_rodar([doc], polo=None))
    assert e["polo_atuacao"] == "indefinido", e["polo_atuacao"]
    assert e["precisa_humano"] is True, "polo indefinido não forçou revisão humana"
    assert e["confianca"] == "baixa", e["confianca"]


def t_polo_nunca_inferido_do_documento():
    """
    Documento diz 'Maria, autora'. O S3 NÃO pode deduzir polo disso.
    """
    doc = documento("sentenca", resultado="procedente",
                    texto="Maria, autora, requereu alimentos.")
    e = _estrategia(_rodar([doc], polo=None))
    assert e["polo_atuacao"] == "indefinido", \
        f"polo foi inferido do texto: {e['polo_atuacao']}"


# ---------------------------------------------------------------------------
# Prazo
# ---------------------------------------------------------------------------

def t_prazo_conferir_rebaixa_confianca():
    """Base com [CONFERIR] -> confianca baixa e campo conferido=False."""
    doc = documento("sentenca", resultado="procedente")
    e = _estrategia(_rodar([doc]))
    prazo = e["prazo_estimado"]
    assert prazo is not None, "prazo ausente"
    assert prazo["conferido"] is False, \
        "a marca [CONFERIR] do catálogo de família não foi detectada"
    assert "[CONFERIR]" not in prazo["base_legal"], \
        "a marca vazou para a base_legal — não deve seguir para a peça"
    assert e["confianca"] == "baixa", \
        f"prazo não conferido deveria rebaixar confiança: {e['confianca']}"


def t_prazo_sem_intimacao_nao_calcula_data():
    doc = documento("sentenca", resultado="procedente")
    e = _estrategia(_rodar([doc]))
    p = e["prazo_estimado"]
    assert p["data_limite"] is None, "calculou data sem intimação conhecida"
    assert p["data_limite_motivo"], "omitir o motivo esconde a razão do null"


def t_prazo_nulo_quando_regra_nao_tem():
    """Regra sem prazo declarado devolve null, não prazo default."""
    import shutil, tempfile
    tmp = Path(tempfile.mkdtemp(prefix="sjc-dom-sp-"))
    d = tmp / "dominios" / "sem_prazo"
    (d / "templates").mkdir(parents=True)
    (d / "templates" / "peticao.md").write_text("[OBRIGATÓRIA]", encoding="utf-8")
    (d / "estrategia.yaml").write_text(
        "regras:\n  - id: r1\n    gatilho:\n      tipo_documento: despacho\n"
        "    peca_cabivel: peticao\n", encoding="utf-8")
    (d / "dominio.yaml").write_text("id: sem_prazo\n", encoding="utf-8")
    try:
        import core.pipeline.s3_estrategia as m
        original = m.RAIZ
        m.RAIZ = tmp
        try:
            e = _estrategia(_rodar([documento("despacho")], dominio="sem_prazo"))
        finally:
            m.RAIZ = original
        assert e["prazo_estimado"] is None, \
            f"inventou prazo: {e['prazo_estimado']}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Teses
# ---------------------------------------------------------------------------

def t_teses_nao_conferidas_sao_separadas():
    """
    As 5 teses de família têm verificado_em: null. Referenciá-las NÃO pode
    produzir tese 'conferida': separa e levanta precisa_humano.
    """
    doc = documento("decisao_interlocutoria",
                    texto="Fixos alimentos provisórios.")
    e = _estrategia(_rodar([doc]))
    assert e["teses"], f"tese não foi sugerida: {e.get('teses')}"
    assert all(t["conferida"] is False for t in e["teses"]), \
        "tese sem verificado_em foi marcada como conferida"
    assert e["teses_nao_conferidas"], "não separou as teses não conferidas"
    assert e["precisa_humano"] is True, \
        "tese não conferida não forçou revisão humana"


def t_tese_fantasma_e_reportada():
    """Tese referenciada que não existe no catálogo tem de aparecer."""
    import shutil, tempfile
    tmp = Path(tempfile.mkdtemp(prefix="sjc-dom-tf-"))
    d = tmp / "dominios" / "tese_fantasma"
    (d / "templates").mkdir(parents=True)
    (d / "templates" / "peticao.md").write_text("[OBRIGATÓRIA]", encoding="utf-8")
    (d / "estrategia.yaml").write_text(
        "regras:\n  - id: r1\n    gatilho:\n      tipo_documento: despacho\n"
        "    peca_cabivel: peticao\n    teses_sugeridas: [tese_que_nao_existe]\n",
        encoding="utf-8")
    (d / "tese-catalogo.yaml").write_text("teses: []\n", encoding="utf-8")
    (d / "dominio.yaml").write_text("id: tese_fantasma\n", encoding="utf-8")
    try:
        import core.pipeline.s3_estrategia as m
        original = m.RAIZ
        m.RAIZ = tmp
        try:
            e = _estrategia(_rodar([documento("despacho")], dominio="tese_fantasma"))
        finally:
            m.RAIZ = original
        assert any("tese_que_nao_existe" in t for t in e["teses_nao_conferidas"]), \
            f"tese fantasma silenciada: {e['teses_nao_conferidas']}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_tese_sem_fundamento_e_visivel():
    """Toda tese tem fundamento_normativo (invariante do contrato)."""
    doc = documento("decisao_interlocutoria", texto="Defiro tutela e guarda.")
    e = _estrategia(_rodar([doc]))
    for t in e["teses"]:
        assert t["fundamento_normativo"], \
            f"tese {t['tese']} sem fundamento normativo"


# ---------------------------------------------------------------------------
# Rastro da decisão (L1)
# ---------------------------------------------------------------------------

def t_alternativas_registradas_quando_duas_regras_casam():
    """
    Decisão de tutela que também menciona alimentos casa duas regras.
    A segunda tem de aparecer como alternativa — proibição explícita: 'S3 não
    produz saída sem justificar por que descartou alternativas'.
    """
    doc = documento("decisao_interlocutoria",
                    texto="Defiro a tutela e fixo alimentos provisórios.")
    e = _estrategia(_rodar([doc]))
    assert e["pecas_alternativas"], "nenhuma alternativa registrada"
    assert any(a["casou_nos_autos"] for a in e["pecas_alternativas"]), \
        f"nenhuma alternativa marcada como casada nos autos: {e['pecas_alternativas']}"


def t_justificativa_referencia_regra():
    doc = documento("sentenca", resultado="extinto_sem_resolucao")
    e = _estrategia(_rodar([doc]))
    assert e["gatilho"] in e["justificativa"], \
        f"justificativa não referencia a regra aplicada: {e['justificativa']}"


def t_modelo_nao_decidido_e_declarado():
    """Família não decidiu modelo: o campo diz isso, não inventa provider."""
    doc = documento("sentenca", resultado="procedente")
    e = _estrategia(_rodar([doc]))
    m = e["modelo_sugerido"]
    assert m["decidido"] is False, f"inventou modelo: {m}"
    assert "a preencher" in str(m["provider"]), m


# ---------------------------------------------------------------------------
# Integração com o runner
# ---------------------------------------------------------------------------

def t_s3_no_runner_registra_saida():
    """
    Integração real: S3 recebe o artefato de S0 pelo PipelineContext e a
    saída entra no manifesto com hash.

    A primeira versão deste teste usava um S0 sem herdar de Stage — o runner
    então não tinha `rodar()` para chamar e a falha aparecia em S0, não em S3.
    Defeito do teste: ele não estava testando a integração que dizia testar.
    """
    from core.pipeline.stage import Stage

    class S0(Stage):
        id = "S0"
        nome = "entrada-de-teste"
        depende_de = []  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["caso_id", "dominio_id", "documentos", "polo_atuacao"]  # type: ignore[assignment]
        # polo nulo é informação legítima, não ausência: o contrato manda
        # tratar como 'indefinido' e forçar revisão humana.
        campos_podem_ser_nulos = ["polo_atuacao"]  # type: ignore[assignment]

        def executar(self, ctx):
            return {"caso_id": "00000000000000000000", "dominio_id": "familia",
                    "documentos": [documento("sentenca", resultado="procedente")],
                    "polo_atuacao": None}

    import tempfile
    ctx = PipelineContext(Path(tempfile.mkdtemp(prefix="sjc-int-")), "familia")
    res = Runner([S0(), S3Estrategia()], ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}"
    saidas = [e for e in ctx.manifesto["estagios"] if e["evento"] == "saida"]
    assert any(s["estagio"] == "S3" for s in saidas), "S3 não registrou saída"
    assert all(len(s["hash_sha256"]) == 64 for s in saidas), "hash inválido"


TESTES = [
    ("t_sentenca_extintiva_escolhe_apelacao", t_sentenca_extintiva_escolhe_apelacao),
    ("t_agravo_de_tutela", t_agravo_de_tutela),
    ("t_sentenca_de_merito_tambem_vira_apelacao", t_sentenca_de_merito_tambem_vira_apelacao),
    ("t_resultado_em_lista_casa", t_resultado_em_lista_casa),
    ("t_conteudo_nao_contem_exclui", t_conteudo_nao_contem_exclui),
    ("t_conteudo_contem_todos_exige_conjuncao", t_conteudo_contem_todos_exige_conjuncao),
    ("t_tipo_documento_errado_nao_casa", t_tipo_documento_errado_nao_casa),
    ("t_nenhuma_regra_casa_pausa", t_nenhuma_regra_casa_pausa),
    ("t_sem_documentos_pausa", t_sem_documentos_pausa),
    ("t_peça_sem_template_pausa", t_peça_sem_template_pausa),
    ("t_dominio_inexistente_falha_na_entrada", t_dominio_inexistente_falha_na_entrada),
    ("t_polo_invalido_falha_na_entrada", t_polo_invalido_falha_na_entrada),
    ("t_polo_ausente_vira_indefinido_e_pede_humano", t_polo_ausente_vira_indefinido_e_pede_humano),
    ("t_polo_nunca_inferido_do_documento", t_polo_nunca_inferido_do_documento),
    ("t_prazo_conferir_rebaixa_confianca", t_prazo_conferir_rebaixa_confianca),
    ("t_prazo_sem_intimacao_nao_calcula_data", t_prazo_sem_intimacao_nao_calcula_data),
    ("t_prazo_nulo_quando_regra_nao_tem", t_prazo_nulo_quando_regra_nao_tem),
    ("t_teses_nao_conferidas_sao_separadas", t_teses_nao_conferidas_sao_separadas),
    ("t_tese_fantasma_e_reportada", t_tese_fantasma_e_reportada),
    ("t_tese_sem_fundamento_e_visivel", t_tese_sem_fundamento_e_visivel),
    ("t_alternativas_registradas_quando_duas_regras_casam", t_alternativas_registradas_quando_duas_regras_casam),
    ("t_justificativa_referencia_regra", t_justificativa_referencia_regra),
    ("t_modelo_nao_decidido_e_declarado", t_modelo_nao_decidido_e_declarado),
    ("t_s3_no_runner_registra_saida", t_s3_no_runner_registra_saida),
]


if __name__ == "__main__":
    executar_e_sair("S3 ESTRATÉGIA", TESTES)
