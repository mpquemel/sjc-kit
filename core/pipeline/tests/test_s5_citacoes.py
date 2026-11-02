"""
Testes do S5 — conferência de citação ligada ao pipeline.

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S5
DEVE RECUSAR:

  - citação sem tribunal identificável     -> nao_avaliado, NUNCA ok
  - falha de infraestrutura                 -> nao_avaliado, retém
  - fonte diz que não existe                -> numero_truncado, retém
  - fonte devolve outro processo            -> numero_errado, retém
  - fonte devolve prefixo                  -> falso_positivo
  - peça vazia                             -> aborta
  - modo offline                           -> extração conferida, fonte não

Nenhum teste aqui toca a rede: o verificador é injetado.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s3_estrategia import S3Estrategia, documento  # noqa: E402
from core.pipeline.s5_citacoes import S5Citacoes, _tribunal_de, _com_milhar  # noqa: E402
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import PipelineContext, Stage  # noqa: E402
from core.citacoes.citacoes import extrair  # noqa: E402






PECA = """\
# APELAÇÃO

Conforme o REsp 1.533.206/MG (STJ), o recurso merece provimento.

Também o RE 9999999 do STF foi invocado pela parte contrária.

A Súmula 593 do STJ sustenta o que se alega.
"""


def _ctx(peca_texto, dominio="familia", **extra):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s5-")
    ctx = PipelineContext(Path(tmp), dominio)
    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": dominio,
        "polo_atuacao": "ativo",
    }
    ctx.artefatos["S3"] = {
        "caso_id": "00000000000000000000",
        "estrategia": {
            "polo_atuacao": "ativo",
            "gatilho": "sentenca-procedente-ou-improcedente",
            "peca_cabivel": "apelacao",
            "prazo_estimado": {"base_legal": "art. 1.003, §5º, do CPC",
                               "conferido": True},
            "precisa_humano": False,
        },
    }
    if peca_texto is not None:
        ctx.artefatos["S0"]["peca_texto"] = peca_texto
    for k, v in extra.items():
        ctx.artefatos["S0"][k] = v
    return ctx


def _rodar(peca_texto, verificador=None, **kw):
    s5 = S5Citacoes()
    if verificador is not None:
        s5.verificador = verificador
    return s5.rodar(_ctx(peca_texto, **kw))


def _cit(r):
    assert r.ok and not r.pausado, f"S5 não rodou: {r.problemas or r.motivo_pausa}"
    return r.saida["citacoes"]


# ---------------------------------------------------------------------------
# Verificadores falsos — nenhum toca a rede
# ---------------------------------------------------------------------------

def _fonte_encontrada(citacao):
    """
    Fonte que devolve o documento, com conteúdo conferido.

    `conteudo_confere: True` é obrigatório aqui: o adaptador real NUNCA preenche
    esse campo (ele verifica identidade, não conteúdo). Sem ele,
    `classificar_falha` cai no ramo `is None` e devolve `falso_positivo`, que
    retém. Medido em 02/11/2026: o teste que esperava `ok` recebia 3
    `falso_positivo`. O comportamento do portão está certo — consulta de
    identidade não pode liberar citação cujo conteúdo ninguém comparou.
    """
    return {
        "consulta_executada": True,
        "encontrado": True,
        "conteudo_confere": True,
        "chave_usada": "registro",
        "total": 1,
        "ambiguo": False,
        "prova_consulta": {"consulta_texto": "stub"},
        "fonte": "stub.local",
        "lido_em": "2026-11-02",
        "erro_codigo": None,
        "erro": None,
        "retem": False,
        "documentos": [{"chave": citacao.get("chave")}],
        "aviso_citacao": "identidade apenas",
    }


def _fonte_inexistente(citacao):
    d = _fonte_encontrada(citacao)
    d.update(encontrado=False, total=0, retem=True, erro_codigo="acervo_vazio")
    return d


def _fonte_offline(citacao):
    return {
        "consulta_executada": False,
        "encontrado": None,
        "chave_usada": "termo",
        "total": 0,
        "ambiguo": False,
        "prova_consulta": {},
        "fonte": "stub.local",
        "lido_em": "2026-11-02",
        "erro_codigo": "timeout",
        "erro": "estourou 200s",
        "retem": True,
        "documentos": [],
        "aviso_citacao": "identidade apenas",
    }


def _fonte_outro_processo(citacao):
    d = _fonte_encontrada(citacao)
    d.update(chave_casada="REsp 9999999/RS", documentos=[])
    return d


def _fonte_identidade_apenas(citacao):
    """Adaptador real: confirma que existe, NUNCA diz que o conteúdo confere."""
    d = _fonte_encontrada(citacao)
    d.pop("conteudo_confere", None)
    return d


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def t_com_milhar():
    assert _com_milhar("1533206") == "1.533.206"
    assert _com_milhar("123") == "123"
    assert _com_milhar("1947535") == "1.947.535"


def t_tribunal_depois_da_citacao():
    """
    A sigla vem DEPOIS do numeral. A primeira versão abria a janela 20
    caracteres ANTES da posição e não achava nada: todas as citações ficariam
    "sem tribunal" e nada seria consultado.
    """
    t = "Conforme o REsp 1.533.206/MG (STJ) e o RE 9.999.999 do STF."
    cits = extrair(t)
    assert len(cits) == 2, [c.chave for c in cits]
    assert _tribunal_de(cits[0], t) == "STJ", cits[0].chave
    assert _tribunal_de(cits[1], t) == "STF", cits[1].chave


def t_tribunal_nao_vaza_para_vizinho():
    """
    O `STJ` da súmula anterior NÃO pode atribuir tribunal a `art. 1.694`.
    Inferência por proximidade é palpite com aparência de determinação.
    """
    t = "Conforme Súmula 593 do STJ. Art. 1.694 do Código Civil."
    cits = extrair(t)
    art = [c for c in cits if c.tipo == "dispositivo"]
    assert art, "dispositivo não extraído"
    assert _tribunal_de(art[0], t) is None, \
        f"dispositivo herdou tribunal: {_tribunal_de(art[0], t)}"


def t_tribunal_nao_usa_numeral_anterior_como_ancora():
    """
    O primeiro numeral do trecho pode ser de OUTRA citação. Ancorar nele
    atribuía STJ a uma citação do STF.
    """
    t = "Vide fl. 88. O RE 9.999.999 do STF e o AgRg no REsp 1.947.535/SP (STJ)."
    cits = extrair(t)
    por_chave = {c.chave: _tribunal_de(c, t) for c in cits}
    assert por_chave.get("RE 9999999") == "STF", por_chave
    assert por_chave.get("AgRg REsp 1947535/SP") == "STJ", por_chave


def t_sem_tribunal_nao_consulta():
    """Sem tribunal: nao_avaliado, retém, e o relatório diz por quê."""
    chamadas = []

    def ver(c):
        chamadas.append(c)
        return _fonte_encontrada(c)

    c = _cit(_rodar("O RE 1234567, sem tribunal em lugar nenhum.", verificador=ver))
    assert chamadas == [], f"consultou sem tribunal: {chamadas}"
    assert c["contagem"]["nao_avaliado"] == 1, c["contagem"]
    assert c["retem"] is True
    assert c["sem_tribunal"], "não declarou qual citação ficou sem tribunal"


def t_falha_de_infraestrutura_nao_vira_inexistente():
    c = _cit(_rodar(PECA, verificador=_fonte_offline))
    assert c["contagem"]["nao_avaliado"] >= 1, c["contagem"]
    assert c["contagem"]["numero_truncado"] == 0, \
        f"timeout virou inexistente: {c['contagem']}"
    assert c["retem"] is True


def t_fonte_inexistente_reprova_citacao():
    c = _cit(_rodar(PECA, verificador=_fonte_inexistente))
    assert c["contagem"]["numero_truncado"] >= 1, c["contagem"]
    assert c["retem"] is True


def t_fonte_com_outro_processo_marca_numero_errado():
    c = _cit(_rodar(PECA, verificador=_fonte_outro_processo))
    assert c["contagem"]["numero_errado"] >= 1, c["contagem"]
    assert c["retem"] is True


def t_peca_vazia_aborta():
    r = _rodar("   ")
    assert r.pausado, "peça vazia deveria abortar"
    assert "vazia" in r.motivo_pausa.lower(), r.motivo_pausa


def t_modo_offline_confere_extracao_e_rete_m_fonte():
    c = _cit(_rodar(PECA, consulta_fonte=False))
    assert c["consulta_fonte"] is False
    assert c["total"] >= 3, f"extração não rodou: {c['total']}"
    assert c["contagem"]["nao_avaliado"] == c["total"], \
        f"offline marcou como avaliado: {c['contagem']}"
    assert c["retem"] is True


def t_todas_encontradas_libera():
    c = _cit(_rodar(PECA, verificador=_fonte_encontrada))
    assert c["contagem"]["ok"] >= 1, c["contagem"]
    assert c["contagem"]["nao_avaliado"] == 0, c["contagem"]


def t_identidade_confirmada_sem_conferencia_de_conteudo_rete_m():
    """
    Achado medido: o adaptador NUNCA preenche `conteudo_confere`. O portão
    classifica como `falso_positivo` e RETÉM. Isso é correto — identidade não é
    conteúdo — e precisa estar testado, porque é o comportamento real do
    sistema hoje, não um caso hipotético.
    """
    c = _cit(_rodar(PECA, verificador=_fonte_identidade_apenas))
    assert c["contagem"]["falso_positivo"] >= 1, c["contagem"]
    assert c["contagem"]["ok"] == 0, \
        f"liberou sem conferir conteúdo: {c['contagem']}"
    assert c["retem"] is True


def t_aviso_de_escopo_presente():
    """O relatório tem de dizer o que NÃO verificou."""
    c = _cit(_rodar(PECA, verificador=_fonte_encontrada))
    assert "NÃO verifica" in c["aviso"], c["aviso"]


def t_integracao_s3_para_s5_no_runner():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s35-")
    ctx = PipelineContext(Path(tmp), "familia")

    class S0Falso(Stage):
        id = "S0"
        nome = "entrada-de-teste"
        depende_de = []  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["caso_id", "dominio_id", "documentos", "polo_atuacao",
                        "peca_texto"]  # type: ignore[assignment]

        def executar(self, ctx):
            return dict(ctx.artefatos.get("S0") or {})

    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "dominio_id": "familia",
        "polo_atuacao": "ativo",
        "peca_texto": PECA,
        "consulta_fonte": False,
        "documentos": [documento("sentenca", resultado="procedente",
                                 texto="Julgo procedente.")],
    }
    # S5 declara dependência de S4 (de onde vem a peça). Dependência declarada
    # tem de existir no DAG, então o teste inclui S4 — e S4 pausa por modelo
    # indefinido, por isso a config é injetada. Sem isso o DAG nem monta:
    # DAGInvalido: S5 depende de 'S4', que não existe no DAG.
    from core.pipeline.s4_redacao import S4Redacao

    s4 = S4Redacao()
    s4.provedor = lambda prompt, contexto: "Texto do bloco, sem citação."
    s4._carregar_dominio = lambda d: {"modelos": {"default": {
        "provider": "local", "modelo": "m", "motivo": "teste"}}}

    res = Runner([S0Falso(), S3Estrategia(), s4, S5Citacoes()], ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}"
    assert "citacoes" in ctx.artefatos["S5"], "S5 não registrou citação"
    assert ctx.artefatos["S5"]["citacoes"]["retem"] is True


TESTES = [
    ("t_com_milhar", t_com_milhar),
    ("t_tribunal_depois_da_citacao", t_tribunal_depois_da_citacao),
    ("t_tribunal_nao_vaza_para_vizinho", t_tribunal_nao_vaza_para_vizinho),
    ("t_tribunal_nao_usa_numeral_anterior_como_ancora",
     t_tribunal_nao_usa_numeral_anterior_como_ancora),
    ("t_sem_tribunal_nao_consulta", t_sem_tribunal_nao_consulta),
    ("t_falha_de_infraestrutura_nao_vira_inexistente",
     t_falha_de_infraestrutura_nao_vira_inexistente),
    ("t_fonte_inexistente_reprova_citacao", t_fonte_inexistente_reprova_citacao),
    ("t_fonte_com_outro_processo_marca_numero_errado",
     t_fonte_com_outro_processo_marca_numero_errado),
    ("t_peca_vazia_aborta", t_peca_vazia_aborta),
    ("t_modo_offline_confere_extracao_e_rete_m_fonte",
     t_modo_offline_confere_extracao_e_rete_m_fonte),
    ("t_todas_encontradas_libera", t_todas_encontradas_libera),
    ("t_identidade_confirmada_sem_conferencia_de_conteudo_rete_m",
     t_identidade_confirmada_sem_conferencia_de_conteudo_rete_m),
    ("t_aviso_de_escopo_presente", t_aviso_de_escopo_presente),
    ("t_integracao_s3_para_s5_no_runner", t_integracao_s3_para_s5_no_runner),
]


if __name__ == "__main__":
    executar_e_sair("S5 CITAÇÕES", TESTES)
