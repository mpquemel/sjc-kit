"""
Testes do S7 — gate de cinco camadas.

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S7
DEVE REPROVAR, RECUSAR ou DECLARAR NÃO AVALIADO:

  - peça com marcador residual          -> G3 REPROVA
  - seção obrigatória fora de ordem     -> G3 REPROVA
  - seção obrigatória ausente           -> G3 REPROVA
  - campo "a preencher" no corpo        -> G3 REPROVA
  - G1/G2 sem declaração                -> REPROVA (não "passa em branco")
  - G1/G2 com declaração                -> PASSA com autor e hora
  - revisor igual ao gerador            -> G5 REPROVA (sem independência)
  - revisor ausente                     -> G5 NAO_AVALIADO e bloqueia
  - transcrição declarada sem fonte     -> G4 NAO_AVALIADO e bloqueia
  - peça sem transcrição                -> G4 NAO_APLICAVEL, não bloqueia
  - peça vazia                          -> aborta
  - empate de gravidade                 -> todas as camadas declaradas
  - S6 reprovado                        -> entra no pior veredito

Nenhum teste exige revisor real: o revisor é injetado.
"""

import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s7_gate_cinco_camadas import S7GateCincoCamadas  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import (  # noqa: E402
    EstagioAbortado, PipelineContext, Stage)






# ---------------------------------------------------------------------------
# Peças de fixture
# ---------------------------------------------------------------------------

PECA = """# PEÇA

Processo nº 0000000-00.0000.8.00.0000

## I — DA TEMPESTIVIDADE

Recurso tempestivo, interposto dentro do prazo legal de quinze dias.

## II — DAS RAZÕES DE REFORMA

A sentença merece reforma porque o binômio necessidade e possibilidade não foi
observado na fixação dos alimentos, conforme art. 1.694 do Código Civil.

## III — DOS PEDIDOS

Requer o provimento do recurso para reduzir o valor fixado.
"""

DECL_OK = {
    "g1_legal": {"declarado_por": "operador", "em": "2026-11-02T15:00:00",
                 "texto": "conferi cabimento e prazo"},
    "g2_factual": {"declarado_por": "operador", "em": "2026-11-02T15:00:00",
                   "texto": "conferi cada fato na página dos autos"},
}


class RevisorFalso:
    """Revisor injetado. Modelo DIFERENTE do gerador por padrão."""

    def __init__(self, veredito="PASSA", modelo="revisor-x", itens=None):
        self.modelo = modelo
        self._veredito = veredito
        self._itens = itens or []

    def auditar(self, **kwargs):
        return {"veredito": self._veredito, "motivo": "laudo simulado",
                "itens": self._itens}


class RevisorQueFalha:
    modelo = "revisor-quebrado"

    def auditar(self, **kwargs):
        raise RuntimeError("provedor indisponível")


def contexto(peca_texto=PECA, declaracoes=None, gates=None,
             estrategia=None):
    ctx = PipelineContext(Path(tempfile.mkdtemp()), "familia")
    ctx.artefatos["S0"] = {
        "caso_id": "0" * 20, "pdf_path": "/tmp/falso.pdf",
        "arvore_path": None, "dominio_id": "familia",
        "perfil_atuacao": "ativo", "criado_em": "2026-11-02T00:00:00",
        "criado_por": "teste",
    }
    ctx.artefatos["S3"] = {
        "estrategia": estrategia or {"tese": "reduzir alimentos",
                                      "peca_cabivel": "apelacao"},
    }
    ctx.artefatos["S4"] = {"peca_texto": peca_texto}
    ctx.artefatos["S6"] = {"gates": gates or {"veredito": "PASSA",
                                             "reprovas": [],
                                             "advertencias": []}}
    if declaracoes is not None:
        ctx.artefatos["declaracoes_operador"] = declaracoes
    return ctx


def rodar(peca_texto=PECA, declaracoes=None, gates=None,
          revisor="default", estrategia=None):
    ctx = contexto(peca_texto, declaracoes, gates, estrategia)
    s7 = S7GateCincoCamadas()
    if revisor == "default":
        s7.revisor = RevisorFalso()
    else:
        s7.revisor = revisor
    return s7.executar(ctx)["gate_cinco_camadas"], ctx


def camada(saida, ident):
    return next(c for c in saida["camadas"] if c["id"] == ident)


# ---------------------------------------------------------------------------
# G3 — forma reprova de verdade
# ---------------------------------------------------------------------------

def t_peca_boa_passa_todas_as_camadas():
    s, _ = rodar(declaracoes=DECL_OK)
    assert s["veredito"] == "PASSA", f"{s['veredito']}: {s['camadas']}"
    assert s["pode_protocolar"] is True
    assert s["bloqueado"] is False


def t_marcador_residual_reprova():
    s, _ = rodar(peca_texto=PECA + "\nRequer o provimento. {{pedido_final}}",
                 declaracoes=DECL_OK)
    g3 = camada(s, "G3")
    assert g3["veredito"] == "REPROVA", g3
    assert any(d["tipo"] == "marcador_residual" for d in g3["defeitos"]), g3["defeitos"]
    assert s["veredito"] == "REPROVA"


def t_secao_fora_de_ordem_reprova():
    peca = """# PEÇA

## I — DOS PEDIDOS

Requer o provimento do recurso.

## II — DA TEMPESTIVIDADE

Tempestivo.

## III — DAS RAZÕES

A sentença merece reforma pelos motivos expostos.
"""
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g3 = camada(s, "G3")
    assert g3["veredito"] == "REPROVA", g3
    assert any(d["tipo"] == "secao_fora_de_ordem" for d in g3["defeitos"]), g3["defeitos"]


def t_secao_ausente_reprova():
    peca = """# PEÇA

## I — DA TEMPESTIVIDADE

Tempestivo, prazo observado.

## II — DAS RAZÕES

A sentença merece reforma pelos motivos expostos no corpo desta peça.
"""
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g3 = camada(s, "G3")
    assert g3["veredito"] == "REPROVA", g3
    assert any(d["tipo"] == "secao_ausente" for d in g3["defeitos"]), g3["defeitos"]


def t_campo_a_preencher_reprova():
    peca = PECA.replace("reduzir o valor fixado", "reduzir o valor a preencher")
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g3 = camada(s, "G3")
    assert g3["veredito"] == "REPROVA", g3
    assert any(d["tipo"] == "campo_a_preencher" for d in g3["defeitos"]), g3["defeitos"]


def t_g3_nao_verifica_numero_de_processo():
    """
    Decisão declarada em 02/11/2026: "Processo nº" é campo de S4, não de forma.
    G3 tem de ser reproduzível fora do pipeline — um revisor humano olhando a
    peça não sabe se o número faltou por omissão do operador ou porque o domínio
    não declara o campo. Misturar faria G3 reprovar peça correta de domínio que
    não usa identificador.
    """
    peca = PECA.replace("Processo nº 0000000-00.0000.8.00.0000", "")
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g3 = camada(s, "G3")
    assert g3["veredito"] == "PASSA", (
        f"G3 não pode reprovar por número de processo (é campo de S4): {g3['defeitos']}")


# ---------------------------------------------------------------------------
# G1 / G2 — sem declaração, reprova
# ---------------------------------------------------------------------------

def t_sem_declaracao_reprova_em_g1_e_g2():
    s, _ = rodar(declaracoes=None)
    assert camada(s, "G1")["veredito"] == "REPROVA", camada(s, "G1")
    assert camada(s, "G2")["veredito"] == "REPROVA", camada(s, "G2")
    assert s["veredito"] == "REPROVA"
    assert s["pode_protocolar"] is False


def t_declaracao_incompleta_nao_passa():
    """Declaração sem autor OU sem hora não é declaração: é intenção."""
    s, _ = rodar(declaracoes={"g1_legal": {"texto": "ok"}})
    assert camada(s, "G1")["veredito"] == "REPROVA", camada(s, "G1")


def t_declaracao_completa_passa_e_registra_autor():
    s, _ = rodar(declaracoes=DECL_OK)
    g1 = camada(s, "G1")
    assert g1["veredito"] == "PASSA", g1
    assert "operador" in g1["motivo"], g1["motivo"]
    assert s["declaracoes_registradas"].get("g1_legal"), s["declaracoes_registradas"]


def t_g1_lista_o_que_conferir_quando_falta():
    """Sem declaração, o relatório tem de dizer O QUE conferir, não só que falta."""
    s, _ = rodar(declaracoes=None)
    conferir = camada(s, "G1").get("conferir") or []
    assert conferir, "G1 sem declaração deve listar pontos a conferir"
    assert any("prazo" in c for c in conferir), conferir


def t_g1_g2_declaram_nao_automatizavel():
    s, _ = rodar(declaracoes=DECL_OK)
    assert camada(s, "G1")["automatizada"] is False
    assert camada(s, "G2")["automatizada"] is False
    assert set(s["nao_avaliaveis"]) >= {"G1", "G2"}, s["nao_avaliaveis"]


# ---------------------------------------------------------------------------
# G4 — transcrição só quando declarada
# ---------------------------------------------------------------------------

def t_peca_sem_transcricao_e_nao_aplicavel():
    s, _ = rodar(declaracoes=DECL_OK)
    g4 = camada(s, "G4")
    assert g4["veredito"] == "NAO_APLICAVEL", g4
    assert s["veredito"] == "PASSA", "NAO_APLICAVEL não pode bloquear"


def t_citacao_doutrinaria_nao_vira_transcricao():
    """
    Toda citação entre aspas virava G4 NAO_AVALIADO e bloqueava a peça. Citação
    doutrinária e transcrição de audiência têm o mesmo formato de aspas; só a
    segunda é conferível na linha exata.
    """
    peca = PECA + ('\n\nComo ensina a doutrina, "a fixação dos alimentos deve '
                   'observar o binômio necessidade e possibilidade".\n')
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g4 = camada(s, "G4")
    assert g4["veredito"] == "NAO_APLICAVEL", (
        f"citação doutrinária não é transcrição: {g4}")
    assert s["veredito"] == "PASSA", s["veredito"]


def t_transcricao_declarada_sem_fonte_bloqueia():
    peca = PECA + ('\n\nConforme a transcrição do termo de audiência, o '
                   'requerido afirmou que "não possui renda fixa no momento".\n')
    s, _ = rodar(peca_texto=peca, declaracoes=DECL_OK)
    g4 = camada(s, "G4")
    assert g4["veredito"] == "NAO_AVALIADO", g4
    assert "não foi executada" in g4["motivo"], g4["motivo"]
    assert s["veredito"] == "NAO_AVALIADO"
    assert s["bloqueado"] is True, "transcrição não conferida não autoriza protocolo"


# ---------------------------------------------------------------------------
# G5 — auditoria exige modelo independente
# ---------------------------------------------------------------------------

def t_sem_revisor_e_nao_avaliado_e_bloqueia():
    s, _ = rodar(declaracoes=DECL_OK, revisor=None)
    g5 = camada(s, "G5")
    assert g5["veredito"] == "NAO_AVALIADO", g5
    assert "revisor" in g5["motivo"].lower(), g5["motivo"]
    assert s["bloqueado"] is True


def t_revisor_igual_ao_gerador_reprova():
    """Medido: um modelo aprovou 11/11 que outro reprovou em 5/8."""
    est = {"tese": "x", "peca_cabivel": "apelacao", "modelo": {"modelo": "m1"}}
    s, _ = rodar(declaracoes=DECL_OK, estrategia=est,
                 revisor=RevisorFalso(modelo="m1"))
    g5 = camada(s, "G5")
    assert g5["veredito"] == "REPROVA", g5
    assert "mesmo modelo" in g5["motivo"], g5["motivo"]


def t_revisor_diferente_roda():
    est = {"tese": "x", "peca_cabivel": "apelacao", "modelo": {"modelo": "m1"}}
    s, _ = rodar(declaracoes=DECL_OK, estrategia=est,
                 revisor=RevisorFalso(modelo="m2"))
    g5 = camada(s, "G5")
    assert g5["veredito"] == "PASSA", g5
    assert g5["revisor"] == "m2", g5


def t_revisor_com_ressalvas_adverte():
    s, _ = rodar(declaracoes=DECL_OK,
                 revisor=RevisorFalso(veredito="ADVERTE", itens=["prova frágil"]))
    assert camada(s, "G5")["veredito"] == "ADVERTE"
    assert s["veredito"] == "ADVERTE"
    assert s["pode_protocolar"] is False, "ADVERTE não autoriza protocolo automático"


def t_revisor_que_falha_e_nao_avaliado_nao_passa():
    s, _ = rodar(declaracoes=DECL_OK, revisor=RevisorQueFalha())
    g5 = camada(s, "G5")
    assert g5["veredito"] == "NAO_AVALIADO", g5
    assert "RuntimeError" in g5["motivo"], g5["motivo"]


def t_revisor_com_veredito_inventado_e_nao_avaliado():
    s, _ = rodar(declaracoes=DECL_OK,
                 revisor=RevisorFalso(veredito="TALVEZ"))
    assert camada(s, "G5")["veredito"] == "NAO_AVALIADO", camada(s, "G5")


# ---------------------------------------------------------------------------
# Veredito final
# ---------------------------------------------------------------------------

def t_veredito_final_e_o_pior_nunca_media():
    s, _ = rodar(declaracoes=DECL_OK,
                 revisor=RevisorFalso(veredito="REPROVA"))
    assert s["veredito"] == "REPROVA", s["veredito"]
    assert s["bloqueado"] is True


def t_empate_declarado_em_todas_as_camadas():
    """Empate de gravidade deve ser visível: mais de uma camada bloqueando."""
    s, _ = rodar(declaracoes=None, revisor=None)
    piores = s["camadas_no_pior_veredito"]
    assert len(piores) > 1, f"empate não declarado: {piores}"
    assert s["pior_camada"] in piores, (s["pior_camada"], piores)


def t_s6_reprovado_entra_no_pior_veredito():
    s, _ = rodar(declaracoes=DECL_OK,
                 gates={"veredito": "REPROVA", "reprovas": ["prazo-conferir"],
                        "advertencias": []})
    assert s["veredito"] == "REPROVA", s["veredito"]
    assert any(c["id"] == "S6" for c in s["camadas"]), [c["id"] for c in s["camadas"]]


def t_aviso_de_responsabilidade_sempre_presente():
    s, _ = rodar(declaracoes=DECL_OK)
    aviso = s.get("aviso") or ""
    assert "responsabilidade" in aviso, f"aviso ausente: {aviso!r}"


# ---------------------------------------------------------------------------
# Falhas de entrada
# ---------------------------------------------------------------------------

def t_peca_vazia_aborta():
    ctx = contexto(peca_texto="   \n\n ")
    try:
        S7GateCincoCamadas().executar(ctx)
    except EstagioAbortado as e:
        assert "vazia" in str(e), e
        return
    raise AssertionError("peça vazia deve abortar o gate")


# ---------------------------------------------------------------------------
# Integração no runner
# ---------------------------------------------------------------------------

class S0Falso(Stage):
    id = "S0"
    nome = "entrada-falsa"
    depende_de = []  # type: ignore[assignment]
    entrada_obriga = []  # type: ignore[assignment]
    saida_obriga = ["caso_id", "pdf_path", "arvore_path", "dominio_id",
                    "perfil_atuacao", "criado_em", "criado_por"]  # type: ignore[assignment]
    campos_podem_ser_nulos = ["arvore_path", "criado_em", "criado_por",
                              "perfil_atuacao"]  # type: ignore[assignment]

    def executar(self, ctx):
        return dict(ctx.artefatos["S0"])


class S3Falso(Stage):
    id = "S3"
    nome = "estrategia-falsa"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["estrategia"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {"estrategia": {"tese": "reduzir", "peca_cabivel": "apelacao"}}


class S6Falso(Stage):
    id = "S6"
    nome = "gates-falsos"
    depende_de = ["S3"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["gates"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {"gates": {"veredito": "PASSA", "reprovas": [],
                          "advertencias": []}}


def t_integracao_s7_no_runner():
    ctx = contexto(declaracoes=DECL_OK)
    s7 = S7GateCincoCamadas()
    s7.revisor = RevisorFalso()
    res = Runner([S0Falso(), S3Falso(), S6Falso(), s7], ctx).rodar()
    assert res["parada"] == "fim", f"{res['parada']} em {res['estagio']}: {res['resultados']}"
    assert [r["estagio"] for r in res["resultados"]] == ["S0", "S3", "S6", "S7"]
    assert ctx.artefatos["S7"]["gate_cinco_camadas"]["veredito"] == "PASSA"


def t_integracao_s7_bloqueia_sem_declaracao():
    ctx = contexto(declaracoes=None)
    s7 = S7GateCincoCamadas()
    s7.revisor = RevisorFalso()
    Runner([S0Falso(), S3Falso(), S6Falso(), s7], ctx).rodar()
    saida = ctx.artefatos["S7"]["gate_cinco_camadas"]
    assert saida["pode_protocolar"] is False, saida["veredito"]


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

TESTES = [
    ("t_peca_boa_passa_todas_as_camadas", t_peca_boa_passa_todas_as_camadas),
    ("t_marcador_residual_reprova", t_marcador_residual_reprova),
    ("t_secao_fora_de_ordem_reprova", t_secao_fora_de_ordem_reprova),
    ("t_secao_ausente_reprova", t_secao_ausente_reprova),
    ("t_campo_a_preencher_reprova", t_campo_a_preencher_reprova),
    ("t_g3_nao_verifica_numero_de_processo", t_g3_nao_verifica_numero_de_processo),
    ("t_sem_declaracao_reprova_em_g1_e_g2", t_sem_declaracao_reprova_em_g1_e_g2),
    ("t_declaracao_incompleta_nao_passa", t_declaracao_incompleta_nao_passa),
    ("t_declaracao_completa_passa_e_registra_autor", t_declaracao_completa_passa_e_registra_autor),
    ("t_g1_lista_o_que_conferir_quando_falta", t_g1_lista_o_que_conferir_quando_falta),
    ("t_g1_g2_declaram_nao_automatizavel", t_g1_g2_declaram_nao_automatizavel),
    ("t_peca_sem_transcricao_e_nao_aplicavel", t_peca_sem_transcricao_e_nao_aplicavel),
    ("t_citacao_doutrinaria_nao_vira_transcricao", t_citacao_doutrinaria_nao_vira_transcricao),
    ("t_transcricao_declarada_sem_fonte_bloqueia", t_transcricao_declarada_sem_fonte_bloqueia),
    ("t_sem_revisor_e_nao_avaliado_e_bloqueia", t_sem_revisor_e_nao_avaliado_e_bloqueia),
    ("t_revisor_igual_ao_gerador_reprova", t_revisor_igual_ao_gerador_reprova),
    ("t_revisor_diferente_roda", t_revisor_diferente_roda),
    ("t_revisor_com_ressalvas_adverte", t_revisor_com_ressalvas_adverte),
    ("t_revisor_que_falha_e_nao_avaliado_nao_passa", t_revisor_que_falha_e_nao_avaliado_nao_passa),
    ("t_revisor_com_veredito_inventado_e_nao_avaliado", t_revisor_com_veredito_inventado_e_nao_avaliado),
    ("t_veredito_final_e_o_pior_nunca_media", t_veredito_final_e_o_pior_nunca_media),
    ("t_empate_declarado_em_todas_as_camadas", t_empate_declarado_em_todas_as_camadas),
    ("t_s6_reprovado_entra_no_pior_veredito", t_s6_reprovado_entra_no_pior_veredito),
    ("t_aviso_de_responsabilidade_sempre_presente", t_aviso_de_responsabilidade_sempre_presente),
    ("t_peca_vazia_aborta", t_peca_vazia_aborta),
    ("t_integracao_s7_no_runner", t_integracao_s7_no_runner),
    ("t_integracao_s7_bloqueia_sem_declaracao", t_integracao_s7_bloqueia_sem_declaracao),
]


if __name__ == "__main__":
    executar_e_sair("S7 GATE DE CINCO CAMADAS", TESTES)
