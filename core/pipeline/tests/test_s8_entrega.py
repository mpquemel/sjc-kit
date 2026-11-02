"""
Testes do S8 — entrega (pacote pré-assinatura).

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S8
DEVE RECUSAR, RETER ou DECLARAR LIMITE:

  - pacote sai MESMO bloqueado       -> com o bloqueio escrito dentro
  - nunca assina, nunca protocola    -> campos falsos em todo manifesto
  - cadeia de hash adulterada        -> verificação aponta a primeira divergência
  - S7 ausente                       -> aborta (pacote sem veredito esconde recusa)
  - peça vazia                       -> aborta
  - citação sem S5                   -> relatório diz "ninguém conferiu", não "ok"
  - declaração ausente               -> registrada como ausência, não como aprovação
  - .docx com hierarquia real        -> Heading 1/2/3, não negrito

Nenhum teste depende de relógio real: o relógio é injetado.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s8_entrega import S8Entrega  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import (  # noqa: E402
    ErroDeContrato, EstagioAbortado, PipelineContext, Stage)






PECA = """# PEÇA

Processo nº 0000000-00.0000.8.00.0000

## I — DA TEMPESTIVIDADE

Recurso tempestivo, dentro do prazo de quinze dias.

## II — DAS RAZÕES

A sentença merece reforma pelos motivos expostos no corpo desta peça.

## III — DOS PEDIDOS

Requer o provimento do recurso.
"""

GATE_LIBERADO = {
    "camadas": [
        {"id": "G1", "nome": "legal", "automatizada": False,
         "veredito": "PASSA", "motivo": "declarado por operador"},
        {"id": "G3", "nome": "forma", "automatizada": True,
         "veredito": "PASSA", "motivo": "sem defeito"},
    ],
    "veredito": "PASSA", "pode_protocolar": True, "bloqueado": False,
    "camadas_no_pior_veredito": ["G1"],
}

GATE_BLOQUEADO = {
    "camadas": [
        {"id": "G3", "nome": "forma", "automatizada": True,
         "veredito": "REPROVA", "motivo": "1 marcador residual",
         "defeitos": [{"tipo": "marcador_residual", "linha": "4",
                       "achado": "{{pedido}}"}]},
    ],
    "veredito": "REPROVA", "pode_protocolar": False, "bloqueado": True,
    "camadas_no_pior_veredito": ["G3"],
}


def contexto(peca_texto=PECA, gate=GATE_LIBERADO, verificacao=None,
             declaracoes=None):
    ctx = PipelineContext(Path(tempfile.mkdtemp()), "familia")
    ctx.artefatos["S0"] = {
        "caso_id": "0" * 20, "pdf_path": "/tmp/falso.pdf", "arvore_path": None,
        "dominio_id": "familia", "perfil_atuacao": "ativo",
        "criado_em": "2026-11-02T00:00:00", "criado_por": "teste",
    }
    ctx.artefatos["S4"] = {"peca_texto": peca_texto}
    if verificacao is not None:
        ctx.artefatos["S5"] = {"verificacao": verificacao}
    if gate is not None:
        ctx.artefatos["S7"] = {"gate_cinco_camadas": gate}
    if declaracoes is not None:
        ctx.artefatos["declaracoes_operador"] = declaracoes
    return ctx


def entregar(**kwargs):
    ctx = contexto(**kwargs)
    s8 = kwargs.pop("s8", None) or S8Entrega()
    s8 = s8 if isinstance(s8, S8Entrega) else S8Entrega()
    s8.relogio = "2026-11-02T15:10:00+00:00"
    saida = s8.executar(ctx)["entrega"]
    return saida, ctx


def ler_auditoria(saida):
    caminho = Path(saida["pacote_dir"]) / "auditoria.jsonl"
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]


# ---------------------------------------------------------------------------
# Pacote
# ---------------------------------------------------------------------------

def t_pacote_traz_os_cinco_arquivos():
    s, _ = entregar()
    nomes = set(s["arquivos"])
    assert nomes == {"minuta.docx", "relatorio-citacoes.md", "vereditos.md",
                     "proveniencia.json", "declaracao-operador.json"}, nomes
    for nome in nomes:
        caminho = Path(s["pacote_dir"]) / nome
        assert caminho.exists() and caminho.stat().st_size > 0, nome


def t_docx_tem_hierarquia_de_verdade():
    """
    Cabeçalho Markdown vira Heading de verdade, não negrito maior: leitor de
    tela e sumário dependem da estrutura.
    """
    import docx

    s, _ = entregar()
    documento = docx.Document(str(Path(s["pacote_dir"]) / "minuta.docx"))
    titulos = [(p.style.name, p.text) for p in documento.paragraphs
               if p.style.name.startswith("Heading")]
    assert titulos, "nenhum cabeçalho virou Heading no .docx"
    assert any(t[0] == "Heading 1" for t in titulos), titulos
    assert any(t[0] == "Heading 2" for t in titulos), titulos
    assert any("TEMPESTIVIDADE" in t[1].upper() for t in titulos), titulos


def t_peca_bloqueada_ainda_entrega_com_bloqueio_escrito():
    """
    Excluir o pacote de peça reprovada empurraria o operador a burlar o gate
    para ter o arquivo. O pacote sai com a recusa escrita dentro.
    """
    s, _ = entregar(gate=GATE_BLOQUEADO)
    assert s["bloqueado"] is True
    assert s["veredito"] == "REPROVA"
    assert s["pode_protocolar"] is False
    vereditos = (Path(s["pacote_dir"]) / "vereditos.md").read_text(encoding="utf-8")
    assert "REPROVA" in vereditos, vereditos[:200]
    assert "marcador_residual" in vereditos, "o defeito tem de aparecer no relatório"


# ---------------------------------------------------------------------------
# Nunca assina, nunca protocola
# ---------------------------------------------------------------------------

def t_nunca_assina_nem_protocola():
    for gate in (GATE_LIBERADO, GATE_BLOQUEADO):
        s, _ = entregar(gate=gate)
        assert s["assinado"] is False, "S8 não pode assinar"
        assert s["protocolo"] is None, "S8 não pode protocolar"
        assert s["manifesto"]["assinado"] is False
        assert s["manifesto"]["protocolo"] is None


def t_aviso_de_peca_parada_registra_entrega_sem_protocolo():
    s, _ = entregar()
    assert "NÃO protocolada" in s["aviso_peca_parada"], s["aviso_peca_parada"]
    assert s["entregue_em"] == "2026-11-02T15:10:00+00:00"


# ---------------------------------------------------------------------------
# Cadeia de hash
# ---------------------------------------------------------------------------

def t_cadeia_de_auditoria_e_integra():
    s, _ = entregar()
    entradas = ler_auditoria(s)
    assert len(entradas) == s["manifesto"]["entradas_auditoria"], len(entradas)

    anterior = "0" * 64
    for i, registro in enumerate(entradas, 1):
        corpo = {k: v for k, v in registro.items() if k != "hash"}
        calculado = hashlib.sha256(
            json.dumps(corpo, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        assert calculado == registro["hash"], f"hash inválido na entrada {i}"
        assert registro["anterior"] == anterior, f"elo quebrado na entrada {i}"
        anterior = registro["hash"]

    assert anterior == s["manifesto"]["hash_final"], "hash final não confere"


def t_adulteracao_no_meio_quebra_a_cadeia():
    """Adulterar uma entrada do meio tem de ser detectável."""
    s, _ = entregar()
    caminho = Path(s["pacote_dir"]) / "auditoria.jsonl"
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    adulterada = json.loads(linhas[2])
    adulterada["evento"] = "arquivo_adulterado"
    linhas[2] = json.dumps(adulterada, ensure_ascii=False)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    entradas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]
    anterior, quebrou = "0" * 64, False
    for registro in entradas:
        corpo = {k: v for k, v in registro.items() if k != "hash"}
        calculado = hashlib.sha256(
            json.dumps(corpo, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        if calculado != registro["hash"] or registro["anterior"] != anterior:
            quebrou = True
        anterior = registro["hash"]
    assert quebrou, "adulteração passou despercebida"


def t_manifesto_declara_o_limite_da_cadeia():
    s, _ = entregar()
    limite = s["manifesto"].get("limite_declarado") or ""
    assert ".docx" in limite, f"limite da cadeia não declarado: {limite!r}"
    assert s["manifesto"]["cadeia_verificavel"] is True


# ---------------------------------------------------------------------------
# Citações
# ---------------------------------------------------------------------------

def t_sem_s5_relatorio_diz_que_ninguem_conferiu():
    s, _ = entregar(verificacao=None)
    texto = (Path(s["pacote_dir"]) / "relatorio-citacoes.md").read_text(encoding="utf-8")
    assert "S5 não rodou" in texto, texto[:300]
    assert "ninguém" in texto.lower(), texto[:300]


def t_vacuidade_de_citacao_aparece_no_relatorio():
    s, _ = entregar(verificacao={"total": 0, "retem": True,
                                 "motivo": "sem citação extraível",
                                 "citacoes": []})
    texto = (Path(s["pacote_dir"]) / "relatorio-citacoes.md").read_text(encoding="utf-8")
    assert "vacuidade" in texto.lower(), texto[:300]
    assert s["citacoes"] == {"total": 0, "retem": True}, s["citacoes"]


def t_citacoes_com_estado_aparecem_uma_a_uma():
    s, _ = entregar(verificacao={
        "total": 1, "retem": True, "motivo": "tribunal não determinado",
        "citacoes": [{"referencia": "Súmula 593/STJ", "tribunal": "STJ",
                      "estado": "nao_avaliado", "motivo": "sem consulta"}],
    })
    texto = (Path(s["pacote_dir"]) / "relatorio-citacoes.md").read_text(encoding="utf-8")
    assert "Súmula 593/STJ" in texto, texto[:400]
    assert "nao_avaliado" in texto, texto[:400]


# ---------------------------------------------------------------------------
# Declaração do operador
# ---------------------------------------------------------------------------

def t_declaracao_ausente_registrada_como_ausencia():
    s, _ = entregar(declaracoes=None)
    dados = json.loads((Path(s["pacote_dir"]) /
                        "declaracao-operador.json").read_text(encoding="utf-8"))
    assert dados["g1_legal"] is None and dados["g2_factual"] is None, dados
    assert "ninguém declarou" in dados["nota"], dados["nota"]


def t_declaracao_presente_entra_no_pacote_com_autor():
    decl = {"g1_legal": {"declarado_por": "operador", "em": "2026-11-02T15:00:00"},
            "g2_factual": None}
    s, _ = entregar(declaracoes=decl)
    dados = json.loads((Path(s["pacote_dir"]) /
                        "declaracao-operador.json").read_text(encoding="utf-8"))
    assert dados["g1_legal"]["declarado_por"] == "operador", dados
    assert dados["g2_factual"] is None, "G2 ausente não pode virar aprovação"


# ---------------------------------------------------------------------------
# Proveniência
# ---------------------------------------------------------------------------

def t_proveniencia_cobre_todos_os_artefatos():
    """Todo artefato do caso tem de aparecer, e a declaração com origem distinta.

    A versão anterior comparava contra o contexto SEM declarações e exigia a
    chave `declaracoes_operador` no resultado — exigia proveniência de artefato
    que não existia no caso. Corrigido: o teste agora entrega declarações, e é
    a origem do artefato que se compara, não a mera presença da chave.
    """
    decl = {"g1_legal": {"declarado_por": "operador", "em": "2026-11-02T15:00:00"},
            "g2_factual": {"declarado_por": "operador", "em": "2026-11-02T15:00:00"}}
    s, ctx = entregar(declaracoes=decl)
    dados = json.loads((Path(s["pacote_dir"]) /
                        "proveniencia.json").read_text(encoding="utf-8"))
    assert set(dados["estagios"]) == set(ctx.artefatos), (
        f"artefato fora da proveniência: {set(ctx.artefatos) ^ set(dados['estagios'])}")
    assert dados["estagios"]["declaracoes_operador"]["origem"] != \
        dados["estagios"]["S0"]["origem"], "origem da declaração tem de ser distinguida"


# ---------------------------------------------------------------------------
# Falhas de entrada
# ---------------------------------------------------------------------------

def t_sem_s7_aborta():
    ctx = contexto(gate=None)
    s8 = S8Entrega()
    s8.relogio = "2026-11-02T15:10:00+00:00"
    try:
        s8.executar(ctx)
    except EstagioAbortado as e:
        assert "S7" in str(e), e
        return
    raise AssertionError("pacote sem veredito de S7 deve abortar")


def t_peca_vazia_aborta():
    ctx = contexto(peca_texto="   \n\n ")
    s8 = S8Entrega()
    s8.relogio = "2026-11-02T15:10:00+00:00"
    try:
        s8.executar(ctx)
    except EstagioAbortado as e:
        assert "vazia" in str(e), e
        return
    raise AssertionError("peça vazia deve abortar a entrega")


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


class S7Falso(Stage):
    id = "S7"
    nome = "gate-falso"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["gate_cinco_camadas"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {"gate_cinco_camadas": GATE_LIBERADO}


def t_integracao_s7_para_s8_no_runner():
    ctx = contexto()
    s8 = S8Entrega()
    s8.relogio = "2026-11-02T15:10:00+00:00"
    res = Runner([S0Falso(), S7Falso(), s8], ctx).rodar()
    assert res["parada"] == "fim", f"{res['parada']} em {res['estagio']}: {res['resultados']}"
    assert [r["estagio"] for r in res["resultados"]] == ["S0", "S7", "S8"]
    entrega = ctx.artefatos["S8"]["entrega"]
    assert entrega["assinado"] is False and entrega["protocolo"] is None
    assert Path(entrega["pacote_dir"], "manifesto.json").exists()


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

TESTES = [
    ("t_pacote_traz_os_cinco_arquivos", t_pacote_traz_os_cinco_arquivos),
    ("t_docx_tem_hierarquia_de_verdade", t_docx_tem_hierarquia_de_verdade),
    ("t_peca_bloqueada_ainda_entrega_com_bloqueio_escrito", t_peca_bloqueada_ainda_entrega_com_bloqueio_escrito),
    ("t_nunca_assina_nem_protocola", t_nunca_assina_nem_protocola),
    ("t_aviso_de_peca_parada_registra_entrega_sem_protocolo", t_aviso_de_peca_parada_registra_entrega_sem_protocolo),
    ("t_cadeia_de_auditoria_e_integra", t_cadeia_de_auditoria_e_integra),
    ("t_adulteracao_no_meio_quebra_a_cadeia", t_adulteracao_no_meio_quebra_a_cadeia),
    ("t_manifesto_declara_o_limite_da_cadeia", t_manifesto_declara_o_limite_da_cadeia),
    ("t_sem_s5_relatorio_diz_que_ninguem_conferiu", t_sem_s5_relatorio_diz_que_ninguem_conferiu),
    ("t_vacuidade_de_citacao_aparece_no_relatorio", t_vacuidade_de_citacao_aparece_no_relatorio),
    ("t_citacoes_com_estado_aparecem_uma_a_uma", t_citacoes_com_estado_aparecem_uma_a_uma),
    ("t_declaracao_ausente_registrada_como_ausencia", t_declaracao_ausente_registrada_como_ausencia),
    ("t_declaracao_presente_entra_no_pacote_com_autor", t_declaracao_presente_entra_no_pacote_com_autor),
    ("t_proveniencia_cobre_todos_os_artefatos", t_proveniencia_cobre_todos_os_artefatos),
    ("t_sem_s7_aborta", t_sem_s7_aborta),
    ("t_peca_vazia_aborta", t_peca_vazia_aborta),
    ("t_integracao_s7_para_s8_no_runner", t_integracao_s7_para_s8_no_runner),
]


if __name__ == "__main__":
    executar_e_sair("S8 ENTREGA", TESTES)
