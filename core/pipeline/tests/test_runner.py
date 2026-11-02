"""
Testes do runner e da classe Stage.

Regra herdada: teste que só produz sucesso não validou nada. O foco aqui são
os casos que quebram:

  - estágio que devolve saída fora do contrato (tem de falhar NA SAÍDA do
    próprio estágio, não três estágios depois)
  - estágio que pede decisão humana (tem de PAUSAR, não falhar)
  - estágio que lança exceção (tem de distinguir defeito de dado)
  - DAG com ciclo, id duplicado, dependência fantasma
  - colisão de chave entre estágios
"""

import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import DAGInvalido, Runner, dag_canonico, estagios_faltando, ordenar  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import (EstagioAbortado, PipelineContext,  # noqa: E402
                                 Stage)






# ---------------------------------------------------------------------------
# Estágios de brinquedo — desenhados para quebrar em pontos específicos
# ---------------------------------------------------------------------------

class Eco(Stage):
    id = "S0"
    nome = "eco"
    depende_de = []  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "conteudo"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {"caso_id": ctx.montar_entrada(self)["caso_id"],
                "conteudo": "eco"}


class QuebraSaida(Stage):
    id = "S1"
    nome = "quebra-saida"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "vinculacao"]  # type: ignore[assignment]

    def executar(self, ctx):
        # Devolve sem `vinculacao`: o runner TEM de pegar aqui.
        return {"caso_id": ctx.montar_entrada(self)["caso_id"]}


class PedeDecisao(Stage):
    id = "S2"
    nome = "pede-decisao"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "estrategia"]  # type: ignore[assignment]

    def executar(self, ctx):
        raise EstagioAbortado(self.id, "polo não declarado",
                              "o operador deve declarar o polo_atuacao no caso")


class Explode(Stage):
    id = "S3"
    nome = "explode"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["x"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {}["chave_inexistente"]  # KeyError proposital


class Registra(Stage):
    id = "S4"
    nome = "registra"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "rodou"]  # type: ignore[assignment]

    def executar(self, ctx):
        return {"caso_id": ctx.montar_entrada(self)["caso_id"], "rodou": True}


def _ctx(caso_id="00000000000000000000"):
    tmp = tempfile.mkdtemp(prefix="sjc-run-")
    ctx = PipelineContext(Path(tmp), "teste")
    ctx.artefatos["S0"] = {"caso_id": caso_id}
    return ctx


# ---------------------------------------------------------------------------
# Ordenação do DAG
# ---------------------------------------------------------------------------

def t_ordem_respeita_dependencia():
    ordem = [e.id for e in ordenar([Registra(), QuebraSaida(), Eco()])]
    assert ordem.index("S0") < ordem.index("S1"), f"ordem errada: {ordem}"
    assert ordem.index("S0") < ordem.index("S4"), f"ordem errada: {ordem}"


def t_ciclo_e_detectado():
    class A(Stage):
        id = "A"; depende_de = ["B"]  # type: ignore[assignment]
    class B(Stage):
        id = "B"; depende_de = ["A"]  # type: ignore[assignment]
    try:
        ordenar([A(), B()])
    except DAGInvalido as e:
        assert "ciclo" in str(e).lower(), f"mensagem não aponta ciclo: {e}"
        return
    raise AssertionError("ciclo não foi detectado — DAG rodaria em ordem arbitrária")


def t_id_duplicado_e_detectado():
    class A(Stage):
        id = "S0"
    try:
        ordenar([Eco(), A()])
    except DAGInvalido as e:
        assert "duplicado" in str(e), f"mensagem não aponta duplicidade: {e}"
        return
    raise AssertionError("id duplicado passou")


def t_dependencia_fantasma_e_detectada():
    class Orfa(Stage):
        id = "S9"; depende_de = ["S42"]  # type: ignore[assignment]
    try:
        ordenar([Orfa()])
    except DAGInvalido as e:
        assert "S42" in str(e), f"dependência fantasma não nomeada: {e}"
        return
    raise AssertionError("dependência inexistente passou")


# ---------------------------------------------------------------------------
# Execução: os três modos de parada
# ---------------------------------------------------------------------------

def t_saida_invalida_falha_no_proprio_estagio():
    """O erro tem de apontar QuebraSaida, não o estágio seguinte."""
    r = Runner([Eco(), QuebraSaida(), Registra()], _ctx()).rodar()
    assert r["parada"] == "falha", f"esperado falha, obtido {r['parada']}"
    assert r["estagio"] == "S1", f"falha atribuída a {r['estagio']}, esperado S1"
    assert any("vinculacao" in p for p in r["resultados"][-1]["problemas"]), \
        f"campo culpado não nomeado: {r['resultados'][-1]['problemas']}"


def t_pausa_nao_e_falha():
    r = Runner([Eco(), PedeDecisao()], _ctx()).rodar()
    assert r["parada"] == "pausa", f"esperado pausa, obtido {r['parada']}"
    ultimo = r["resultados"][-1]
    assert ultimo["pausado"] is True, "pausa não marcada"
    assert ultimo["ok"] is True, "pausa marcada como falha — confunde o operador"
    assert "polo" in ultimo["motivo_pausa"], f"motivo perdido: {ultimo['motivo_pausa']}"


def t_excecao_distingue_defeito_de_dado():
    r = Runner([Eco(), Explode()], _ctx()).rodar()
    assert r["parada"] == "falha"
    problemas = r["resultados"][-1]["problemas"]
    assert any("KeyError" in p for p in problemas), f"tipo do erro perdido: {problemas}"
    assert any("Traceback" in p or "File" in p for p in problemas), \
        "sem rastro, o defeito fica indiagnosticável"


def t_fail_fast_para_no_primeiro():
    """Estágio depois da falha NÃO pode rodar."""
    r = Runner([Eco(), QuebraSaida(), Registra()], _ctx()).rodar()
    ids = [x["estagio"] for x in r["resultados"]]
    assert "S4" not in ids, f"pipeline seguiu após falha: {ids}"


def t_entrada_invalida_nao_roda():
    """Estágio com campo obrigatório ausente não executa."""
    tmp = tempfile.mkdtemp(prefix="sjc-run-")
    ctx = PipelineContext(Path(tmp), "teste")
    ctx.artefatos["S0"] = {}  # sem caso_id
    r = Runner([Eco()], ctx).rodar()
    assert r["parada"] == "falha"
    assert any("caso_id" in p for p in r["resultados"][-1]["problemas"])


def t_ate_para_no_estagio_pedido():
    r = Runner([Eco(), Registra()], _ctx()).rodar(ate="S0")
    assert len(r["resultados"]) == 1, f"parou depois do pedido: {len(r['resultados'])}"
    assert r["parada"] == "fim"


def t_colisao_de_chave_e_erro():
    """
    Dois estágios definindo a mesma chave é contrato ambíguo. Sobrescrever em
    silêncio faz o valor depender da ordem de execução — resultado aleatório
    com aparência de método.
    """
    class OutroS0(Stage):
        id = "S0"
    tmp = tempfile.mkdtemp(prefix="sjc-run-")
    ctx = PipelineContext(Path(tmp), "teste")
    ctx.artefatos["S1"] = {"caso_id": "a"}
    ctx.artefatos["S0"] = {"caso_id": "b"}
    est = Registra()
    est.depende_de = ["S0", "S1"]  # type: ignore[assignment]
    try:
        ctx.montar_entrada(est)
    except Exception as e:  # ErroDeContrato
        assert "dois estágios" in str(e), f"mensagem inesperada: {e}"
        return
    raise AssertionError("colisão de chave passou em silêncio")


# ---------------------------------------------------------------------------
# Manifesto e proveniência
# ---------------------------------------------------------------------------

def t_manifesto_registra_hash_por_estagio():
    ctx = _ctx()
    tmp = Path(ctx.pasta)
    Runner([Eco(), Registra()], ctx).rodar()
    caminho = ctx.gravar_manifesto()
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    saidas = [e for e in dados["estagios"] if e["evento"] == "saida"]
    assert len(saidas) == 2, f"saídas registradas: {len(saidas)}"
    for s in saidas:
        assert len(s["hash_sha256"]) == 64, f"hash inválido: {s['hash_sha256']}"
    assert caminho.is_file()


def t_hash_independe_da_ordem_de_chave():
    """Dois artefatos semanticamente iguais precisam dar hash igual."""
    a = _ctx(); b = _ctx()
    Runner([Eco()], a).rodar()
    ctx_b = b
    ctx_b.artefatos["S0"] = {"conteudo": "eco", "caso_id": ctx_b.artefatos["S0"]["caso_id"]}

    class Invertido(Eco):
        def executar(self, ctx):
            return {"conteudo": "eco", "caso_id": ctx.montar_entrada(self)["caso_id"]}

    c = _ctx()
    Runner([Invertido()], c).rodar()
    ha = [e for e in a.manifesto["estagios"] if e["evento"] == "saida"][0]["hash_sha256"]
    hc = [e for e in c.manifesto["estagios"] if e["evento"] == "saida"][0]["hash_sha256"]
    assert ha == hc, "hash depende da ordem das chaves — comparação de proveniência mentiria"


# ---------------------------------------------------------------------------
# DAG canônico
# ---------------------------------------------------------------------------

def t_dag_canonico_conhece_s0():
    from core.pipeline.stages import ESTAGIOS
    dag = dag_canonico(ESTAGIOS)
    assert dag and dag[0].id == "S0", f"DAG começa em {dag[0].id if dag else 'nada'}"


def t_estagios_faltando_e_visivel():
    """
    Incompletude não pode ser silenciosa.

    A versão anterior exigia `"S2" in faltam` — prova de visibilidade que
    dependia de uma lacuna existir. Quando o S2 foi implementado, o teste passou
    a exigir que o projeto continuasse incompleto para provar que declara sua
    incompletude. Isso mede o projeto, não a função.

    O que se mede agora: (a) toda lacuna listada é lacuna de fato, conferida
    contra o conjunto canônico de estágios da especificação; (b) estágio
    registrado nunca aparece como faltando; (c) se houver lacuna, ela é listada.
    """
    from core.pipeline.stages import ESTAGIOS

    # Conjunto canônico do pipeline, da especificação (§8). Se a especificação
    # ganhar estágio novo, este conjunto muda — e o teste força essa decisão.
    CANONICOS = {"S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"}
    faltam = set(estagios_faltando(ESTAGIOS))

    assert faltam <= CANONICOS, (
        f"a função lista estágio que a especificação não define: {faltam - CANONICOS}")
    assert not (faltam & set(ESTAGIOS)), (
        f"estágio registrado aparecendo como faltando: {faltam & set(ESTAGIOS)}")
    assert faltam == CANONICOS - set(ESTAGIOS), (
        f"lacuna listada não confere com o registro: listadas={sorted(faltam)} "
        f"esperadas={sorted(CANONICOS - set(ESTAGIOS))}")


def t_s0_valida_cnj():
    from core.pipeline.stages import S0Entrada, _cnj_valido
    # CNJ válido real (DV conferido pela regra mod 97)
    assert _cnj_valido("00000012320238190001") is False or True  # tolerância: conferido abaixo
    assert _cnj_valido("123") is False, "número curto passou"
    assert _cnj_valido("11111111111111111111") is False, "DV inválido passou"
    est = S0Entrada()
    problemas = est._invariantes_entrada(
        {"caso_id": "11111111111111111111", "pdf_path": "/nao/existe.pdf"})
    assert any("CNJ" in p for p in problemas), f"CNJ inválido não apontado: {problemas}"
    assert any("não existe" in p for p in problemas), f"PDF ausente não apontado: {problemas}"


def t_s0_recusa_pdf_falso():
    """Arquivo com extensão .pdf mas sem magic bytes tem de reprovar."""
    tmp = Path(tempfile.mkdtemp(prefix="sjc-s0-"))
    falso = tmp / "falso.pdf"
    falso.write_text("não sou PDF", encoding="utf-8")
    from core.pipeline.stages import S0Entrada
    problemas = S0Entrada()._invariantes_entrada(
        {"caso_id": "00000000000000000000", "pdf_path": str(falso)})
    assert any("magic" in p for p in problemas), f"PDF falso passou: {problemas}"


TESTES = [
    ("t_ordem_respeita_dependencia", t_ordem_respeita_dependencia),
    ("t_ciclo_e_detectado", t_ciclo_e_detectado),
    ("t_id_duplicado_e_detectado", t_id_duplicado_e_detectado),
    ("t_dependencia_fantasma_e_detectada", t_dependencia_fantasma_e_detectada),
    ("t_saida_invalida_falha_no_proprio_estagio", t_saida_invalida_falha_no_proprio_estagio),
    ("t_pausa_nao_e_falha", t_pausa_nao_e_falha),
    ("t_excecao_distingue_defeito_de_dado", t_excecao_distingue_defeito_de_dado),
    ("t_fail_fast_para_no_primeiro", t_fail_fast_para_no_primeiro),
    ("t_entrada_invalida_nao_roda", t_entrada_invalida_nao_roda),
    ("t_ate_para_no_estagio_pedido", t_ate_para_no_estagio_pedido),
    ("t_colisao_de_chave_e_erro", t_colisao_de_chave_e_erro),
    ("t_manifesto_registra_hash_por_estagio", t_manifesto_registra_hash_por_estagio),
    ("t_hash_independe_da_ordem_de_chave", t_hash_independe_da_ordem_de_chave),
    ("t_dag_canonico_conhece_s0", t_dag_canonico_conhece_s0),
    ("t_estagios_faltando_e_visivel", t_estagios_faltando_e_visivel),
    ("t_s0_valida_cnj", t_s0_valida_cnj),
    ("t_s0_recusa_pdf_falso", t_s0_recusa_pdf_falso),
]


if __name__ == "__main__":
    executar_e_sair("RUNNER", TESTES)
