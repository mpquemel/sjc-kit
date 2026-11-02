"""
Testes do S2 — vinculação de IDs (árvore × documentos × movimentos).

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S2
DEVE REPROVAR, RECUSAR ou DECLARAR NÃO AVALIADO:

  - ID citado ausente da árvore     -> REPROVA (requisito §11 da especificação)
  - fls. fora de toda faixa         -> REPROVA
  - fls. em duas faixas             -> órfão por ambiguidade, não escolha da 1ª
  - peça sem citação de ID          -> NAO_AVALIADO (vacuidade não é sucesso)
  - árvore sem peça                 -> NAO_AVALIADO
  - árvore malformada               -> erro de contrato com linha culpada
  - ID duplicado na árvore          -> reportado, não silenciado
  - faixa invertida                 -> linha recusada, não indexada
  - árvore truncada                 -> risco estrutural declarado

Nenhum teste exige árvore real em disco: o leitor é injetado.
"""

import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s2_vinculacao import S2Vinculacao  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import (  # noqa: E402
    ErroDeContrato, EstagioAbortado, PipelineContext, Stage)






# ---------------------------------------------------------------------------
# Fixtures de árvore — formato v1, versionado
# ---------------------------------------------------------------------------

ARVORE_V1 = """=== ÁRVORE DO PROCESSO ===
Processo: 0000000-00.0000.8.00.0000

ID 1 - Petição Inicial (fls. 1/12)
ID 2 - Certidão de Distribuição (fls. 13)
ID 3 - Despacho inicial (fls. 14)
ID 4 - Mandado de Citação (fls. 15/16)
ID 5 - Contestação (fls. 17/28)
ID 6 - Réplica (fls. 29/31)
ID 7 - Decisão interlocutória - alimentos provisórios (fls. 32)
ID 8 - Agravo de Instrumento (fls. 33/40)
ID 9 - Sentença (fls. 41/45)
ID 10 - Certidão de Publicação (fls. 46)
ID 11 - Apelação (fls. 47/55)
"""


def contexto(arvore_path="/tmp/arvore.txt", peca_texto=None):
    ctx = PipelineContext(Path(tempfile.mkdtemp()), "familia")
    ctx.artefatos["S0"] = {
        "caso_id": "0" * 20,
        "pdf_path": "/tmp/falso.pdf",
        "arvore_path": arvore_path,
        "dominio_id": "familia",
        "perfil_atuacao": "ativo",
        "criado_em": "2026-11-02T00:00:00",
        "criado_por": "teste",
    }
    if peca_texto is not None:
        ctx.artefatos["S4"] = {"peca_texto": peca_texto}
    return ctx


def rodar(arvore, peca_texto=None):
    """Roda S2 com leitor injetado. Devolve (saida_vinculacao, ctx)."""
    ctx = contexto(peca_texto=peca_texto)
    s2 = S2Vinculacao()
    s2.leitor = lambda _caminho: arvore
    saida = s2.executar(ctx)
    return saida["vinculacao"], ctx


# ---------------------------------------------------------------------------
# Índice da árvore
# ---------------------------------------------------------------------------

def t_arvore_v1_indexa_todos_os_ids():
    idx, nao_rec = S2Vinculacao()._indexar(ARVORE_V1)
    assert len(idx) == 11, f"esperava 11 IDs, veio {len(idx)}"
    assert nao_rec == [], f"árvore v1 limpa não pode ter linha não reconhecida: {nao_rec}"
    assert idx["7"]["tipo"] == "Decisão interlocutória - alimentos provisórios", idx["7"]
    assert idx["7"]["fls_inicio"] == "32" and idx["7"]["fls_fim"] == "32", idx["7"]


def t_documento_sem_fls_e_indexado():
    """Documento sem parênteses de fls. existe: a árvore nem sempre tem a faixa."""
    idx, _ = S2Vinculacao()._indexar("ID 3 - Despacho inicial")
    assert "3" in idx, "documento sem fls. continua sendo documento"
    assert idx["3"]["fls_inicio"] is None, idx["3"]


def t_id_duplicado_e_reportado_nao_sobrescrito():
    idx, nao_rec = S2Vinculacao()._indexar(
        "ID 1 - Petição (fls. 1/5)\nID 1 - Contestação (fls. 6/9)")
    assert len(idx) == 1, f"ID duplicado não pode gerar duas entradas: {idx}"
    assert idx["1"]["tipo"] == "Petição", "o primeiro documento preservado"
    assert any("duplicado" in x for x in nao_rec), nao_rec


def t_faixa_invertida_e_recusada():
    """
    Medido em 02/11/2026: "fls. 20/10" era indexado sem aviso. Faixa invertida
    nunca contém número: toda citação vira órfão falso por culpa da árvore.
    """
    idx, nao_rec = S2Vinculacao()._indexar("ID 4 - Documento (fls. 20/10)")
    assert "4" not in idx, "faixa invertida não pode entrar no índice"
    assert any("invertida" in x for x in nao_rec), nao_rec


def t_faixas_sobrepostas_sao_declaradas():
    idx, _ = S2Vinculacao()._indexar(
        "ID 1 - Inicial (fls. 1/10)\nID 2 - Petição (fls. 5/8)")
    sobre = S2Vinculacao()._faixas_sobrepostas(idx)
    assert len(sobre) == 1, f"sobreposição 1/10 x 5/8 devia ser achada: {sobre}"
    assert sobre[0]["ids"] == ["1", "2"], sobre


def t_linha_id_malformada_e_reportada():
    idx, nao_rec = S2Vinculacao()._indexar("ID abc - Coisa estranha")
    assert idx == {}, "linha malformada não pode virar documento"
    assert any("linha 1" in x for x in nao_rec), nao_rec


def t_cabecalho_nao_e_ruido_de_parser():
    """Cabeçalho do portal não é erro: só reporta linha que parece ID."""
    _, nao_rec = S2Vinculacao()._indexar(ARVORE_V1)
    assert nao_rec == [], nao_rec


# ---------------------------------------------------------------------------
# Cruzamento
# ---------------------------------------------------------------------------

def t_id_explicito_casa_direto():
    s, _ = rodar(ARVORE_V1, "Conforme ID 7, os alimentos foram fixados.")
    v = s["veredito"]
    assert v == "PASSA", f"{v}: {s['motivo']}"
    assert s["peca"]["ids_encontrados"][0]["casou_com"] == "7", s["peca"]


def t_fls_casa_dentro_da_faixa():
    s, _ = rodar(ARVORE_V1, "Vide fls. 30, onde consta a réplica.")
    assert s["veredito"] == "PASSA", s["motivo"]
    assert s["peca"]["ids_encontrados"][0]["casou_com"] == "6", s["peca"]


def t_id_e_fls_apontam_para_o_mesmo_documento():
    s, _ = rodar(ARVORE_V1, "ID 7 (fls. 32) fixou os alimentos.")
    casados = {e["casou_com"] for e in s["peca"]["ids_encontrados"]}
    assert casados == {"7"}, f"ID 7 e fls. 32 são o mesmo documento: {casados}"


def t_id_orfao_reprova_nao_avisa():
    """
    Requisito central da especificação (§11): nenhuma peça entregue com ID
    órfão. Órfão é REPROVAÇÃO, não aviso.
    """
    s, _ = rodar(ARVORE_V1, "Conforme ID 99, o pedido foi deferido.")
    assert s["veredito"] == "REPROVA", f"{s['veredito']} — órfão deve reprovar"
    assert s["reprova"] is True and s["pode_protocolar"] is False
    assert s["peca"]["ids_orfaos"][0]["forma"] == "ID 99", s["peca"]


def t_fls_fora_de_toda_faixa_reprova():
    s, _ = rodar(ARVORE_V1, "Vide fls. 99, documento essencial.")
    assert s["veredito"] == "REPROVA", s["veredito"]
    assert "faixa" in s["peca"]["ids_orfaos"][0]["motivo"]


def t_fls_ambiguo_nao_escolhe_a_primeira():
    """
    Duas faixas contendo o mesmo número: o S2 declara ambiguidade. Escolher a
    primeira seria inventar vinculação num momento em que a própria árvore
    está inconsistente.
    """
    arvore = "ID 1 - Inicial (fls. 1/10)\nID 2 - Petição (fls. 5/8)"
    s, _ = rodar(arvore, "Vide fls. 6.")
    assert s["veredito"] == "REPROVA", s["veredito"]
    orf = s["peca"]["ids_orfaos"][0]
    assert "mais de uma faixa" in orf["motivo"], orf
    assert set(orf["candidatos"]) == {"1", "2"}, orf


def t_nenhum_casamento_por_semelhanca_de_texto():
    """
    "decisão de alimentos" existe na árvore como ID 7, mas a peça não cita ID
    nem fls. Nada é vinculado por nome: inferir seria produzir órfão invisível.
    """
    s, _ = rodar(ARVORE_V1, "A decisão de alimentos provisórios merece reforma.")
    assert s["peca"]["ids_citados"] == [], s["peca"]
    assert s["veredito"] == "NAO_AVALIADO", s["veredito"]


# ---------------------------------------------------------------------------
# Vacuidade — ausência de prova não é prova de ausência
# ---------------------------------------------------------------------------

def t_peca_sem_citacao_e_nao_avaliado():
    s, _ = rodar(ARVORE_V1, "Peça sem nenhuma referência a documento.")
    assert s["veredito"] == "NAO_AVALIADO", f"{s['veredito']}: {s['motivo']}"
    assert s["pode_protocolar"] is False, "vacuidade não autoriza protocolo"
    assert "não é prova" in s["motivo"] or "nada foi cruzado" in s["motivo"], s["motivo"]


def t_arvore_sem_peca_e_nao_avaliado_mas_indexa():
    s, _ = rodar(ARVORE_V1, None)
    assert s["veredito"] == "NAO_AVALIADO", s["veredito"]
    assert s["arvore"]["total_ids"] == 11, "sem peça, a árvore ainda é indexada"
    assert s["peca"]["analisada"] is False, s["peca"]


def t_peca_vazia_e_nao_avaliado():
    s, _ = rodar(ARVORE_V1, "   \n\n  ")
    assert s["veredito"] == "NAO_AVALIADO", s["veredito"]


# ---------------------------------------------------------------------------
# Falhas de entrada
# ---------------------------------------------------------------------------

def t_sem_arvore_aborta_com_orientacao():
    ctx = contexto(arvore_path=None)
    s2 = S2Vinculacao()
    s2.leitor = lambda _c: ARVORE_V1
    try:
        s2.executar(ctx)
    except EstagioAbortado as e:
        assert "árvore" in str(e).lower(), e
        return
    raise AssertionError("sem árvore o S2 não pode prosseguir")


def t_arvore_ilegivel_e_erro_de_contrato():
    ctx = contexto()
    s2 = S2Vinculacao()

    def estoura(_c):
        raise PermissionError("permissão negada")

    s2.leitor = estoura
    try:
        s2.executar(ctx)
    except ErroDeContrato as e:
        assert "ilegível" in str(e), e
        return
    raise AssertionError("árvore ilegível deve ser erro de contrato, não traceback")


def t_arvore_vazia_e_erro_de_contrato_com_motivo():
    ctx = contexto()
    s2 = S2Vinculacao()
    s2.leitor = lambda _c: "=== ÁRVORE ===\nNada aqui\n"
    try:
        s2.executar(ctx)
    except ErroDeContrato as e:
        msg = str(e)
        assert "nenhum ID reconhecível" in msg, msg
        assert "formato v1" in msg, f"mensagem deve apontar o formato: {msg}"
        return
    raise AssertionError("árvore sem ID deve ser erro de contrato")


def t_risco_de_arvore_truncada_e_declarado():
    s, _ = rodar(ARVORE_V1, "Vide fls. 30.")
    aviso = s.get("aviso_estrutural", "")
    assert "truncada" in aviso, f"risco estrutural deve ser declarado: {aviso!r}"


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


def t_integracao_s0_para_s2_no_runner():
    ctx = contexto(peca_texto="Conforme ID 7, os alimentos foram fixados.")
    s2 = S2Vinculacao()
    s2.leitor = lambda _c: ARVORE_V1
    res = Runner([S0Falso(), s2], ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}: {res['resultados']}"
    nomes = [r["estagio"] for r in res["resultados"]]
    assert nomes == ["S0", "S2"], nomes
    assert ctx.artefatos["S2"]["vinculacao"]["veredito"] == "PASSA"


def t_integracao_orfaos_interrompe_o_runner():
    """
    Órfão não é aviso: o estágio devolve REPROVA e o runner deve conseguir
    expor isso ao chamador sem transformar em exceção silenciosa.
    """
    ctx = contexto(peca_texto="Conforme ID 404, o pedido foi deferido.")
    s2 = S2Vinculacao()
    s2.leitor = lambda _c: ARVORE_V1
    res = Runner([S0Falso(), s2], ctx).rodar()
    vinc = ctx.artefatos["S2"]["vinculacao"]
    assert vinc["veredito"] == "REPROVA", vinc["veredito"]
    assert vinc["reprova"] is True
    assert res["parada"] == "fim", f"o runner não estourou: {res['parada']}"


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

TESTES = [
    ("t_arvore_v1_indexa_todos_os_ids", t_arvore_v1_indexa_todos_os_ids),
    ("t_documento_sem_fls_e_indexado", t_documento_sem_fls_e_indexado),
    ("t_id_duplicado_e_reportado_nao_sobrescrito", t_id_duplicado_e_reportado_nao_sobrescrito),
    ("t_faixa_invertida_e_recusada", t_faixa_invertida_e_recusada),
    ("t_faixas_sobrepostas_sao_declaradas", t_faixas_sobrepostas_sao_declaradas),
    ("t_linha_id_malformada_e_reportada", t_linha_id_malformada_e_reportada),
    ("t_cabecalho_nao_e_ruido_de_parser", t_cabecalho_nao_e_ruido_de_parser),
    ("t_id_explicito_casa_direto", t_id_explicito_casa_direto),
    ("t_fls_casa_dentro_da_faixa", t_fls_casa_dentro_da_faixa),
    ("t_id_e_fls_apontam_para_o_mesmo_documento", t_id_e_fls_apontam_para_o_mesmo_documento),
    ("t_id_orfao_reprova_nao_avisa", t_id_orfao_reprova_nao_avisa),
    ("t_fls_fora_de_toda_faixa_reprova", t_fls_fora_de_toda_faixa_reprova),
    ("t_fls_ambiguo_nao_escolhe_a_primeira", t_fls_ambiguo_nao_escolhe_a_primeira),
    ("t_nenhum_casamento_por_semelhanca_de_texto", t_nenhum_casamento_por_semelhanca_de_texto),
    ("t_peca_sem_citacao_e_nao_avaliado", t_peca_sem_citacao_e_nao_avaliado),
    ("t_arvore_sem_peca_e_nao_avaliado_mas_indexa", t_arvore_sem_peca_e_nao_avaliado_mas_indexa),
    ("t_peca_vazia_e_nao_avaliado", t_peca_vazia_e_nao_avaliado),
    ("t_sem_arvore_aborta_com_orientacao", t_sem_arvore_aborta_com_orientacao),
    ("t_arvore_ilegivel_e_erro_de_contrato", t_arvore_ilegivel_e_erro_de_contrato),
    ("t_arvore_vazia_e_erro_de_contrato_com_motivo", t_arvore_vazia_e_erro_de_contrato_com_motivo),
    ("t_risco_de_arvore_truncada_e_declarado", t_risco_de_arvore_truncada_e_declarado),
    ("t_integracao_s0_para_s2_no_runner", t_integracao_s0_para_s2_no_runner),
    ("t_integracao_orfaos_interrompe_o_runner", t_integracao_orfaos_interrompe_o_runner),
]


if __name__ == "__main__":
    executar_e_sair("S2 VINCULAÇÃO", TESTES)
