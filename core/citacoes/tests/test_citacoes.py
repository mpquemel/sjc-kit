#!/usr/bin/env python3
"""
test_citacoes.py — testes adversariais do extrator e classificador.

Regra de ouro desta bateria: cada teste deve FALHAR antes da correção que ele
protege. Um teste que só produz sucesso não validou nada.

Rodar:
    python3 -m pytest core/citacoes/tests/ -v
    python3 core/citacoes/tests/test_citacoes.py     # runner mínimo, sem pytest
"""
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_AQUI, "..", "..", "..")))

from core.citacoes import citacoes as C  # noqa: E402

TEXTOS = {
    # Forma abreviada, o caso fácil.
    "abreviado": "Conforme o REsp 1.782.418/RJ, o entendimento se firmou.",

    # Forma NÃO abreviada: "artigo 1.694" sem "art.". Origem: o extrator
    # antigo perdia 100% desta classe, e citação não extraída passa sem validar.
    "nao_abreviado": "Dispõe o artigo 1.694 do Código Civil sobre o dever de alimentos.",

    # Ambiguidade real: numeral que é artigo E página.
    "ambiguo_pagina": "Conforme o art. 121 do Código Penal (fl. 121), a pena é de reclusão.",

    # Súmula sem tribunal: 59/STJ e 593/STJ são distintas.
    "sumula_sem_tribunal": "Aplica-se a Súmula 593 ao caso.",

    # Súmula com numeral que é prefixo de outro (o falso positivo medido:
    # "Súmula 593" lida como "Súmula 59").
    "sumula_prefixo": "Nos termos da Súmula 593 do STJ, a tese não se aplica.",

    # Nota de revogação interna: não revoga o caput.
    "revogacao_interna": (
        "Art. 121. Matar alguém: Pena - reclusão, de seis a vinte anos. "
        "§ 3º Se o homicídio é culposo: Pena - detenção, de um a três anos. "
        "(Revogado pela Lei nº 14.994, de 2024)"
    ),

    # Tribunal por extenso: o extrator antigo devolvia tribunal "?" e gerava
    # alarme falso em 11 peças.
    "tribunal_extenso": "Segundo o Superior Tribunal de Justiça, no REsp 1.782.418.",

    # Tema repetitivo.
    "tema": "O Tema 918/STJ fixou tese sobre estupro de vulnerável.",
}


def t_extrai_abreviado():
    r = C.extrair(TEXTOS["abreviado"])
    assert len(r) == 1, r
    assert r[0].tipo == "julgado" and r[0].numero == "1782418" and r[0].uf == "RJ"


def t_extrai_nao_abreviado():
    """Regressão: 'artigo 1.694' precisa ser extraído como dispositivo."""
    r = C.extrair(TEXTOS["nao_abreviado"])
    arts = [c for c in r if c.tipo == "dispositivo"]
    assert arts, f"nenhum dispositivo extraído de: {r}"
    assert arts[0].numero == "1694", arts[0]


def t_ambiguidade_pagina():
    """Numeral 121 como artigo e como página precisa ser sinalizado."""
    r = C.extrair(TEXTOS["ambiguo_pagina"])
    arts = [c for c in r if c.tipo == "dispositivo" and c.numero == "121"]
    assert arts, r
    assert arts[0].ambiguidades, "ambiguidade não registrada"
    assert "página" in arts[0].ambiguidades[0]


def t_sumula_sem_tribunal_avisa():
    r = C.extrair(TEXTOS["sumula_sem_tribunal"])
    s = [c for c in r if c.tipo == "sumula"]
    assert s and s[0].ambiguidades, r


def t_sumula_prefixo_nao_confunde():
    """'Súmula 593' NÃO pode ser lida como 'Súmula 59'."""
    r = C.extrair(TEXTOS["sumula_prefixo"])
    nums = [c.numero for c in r if c.tipo == "sumula"]
    assert "59" not in nums, f"falso positivo: {nums}"
    assert "593" in nums, nums


def t_revogacao_interna_nao_anula_artigo():
    """
    Origem medida: o art. 121 do CP carrega nota de revogação sobre dispositivo
    interno. Declarar o artigo inteiro revogado seria dizer que homicídio
    simples não existe.
    """
    a = C.analisar_revogacao(TEXTOS["revogacao_interna"])
    assert a["tem_nota_revogacao"] is True
    assert a["escopo"] == "interno_ou_indeterminado"
    assert a["aviso"], "nota de revogação sem aviso"


def t_tribunal_extenso_nao_quebra():
    r = C.extrair(TEXTOS["tribunal_extenso"])
    assert r, "nada extraído"
    j = [c for c in r if c.tipo == "julgado"][0]
    assert j.numero == "1782418"


def t_tema_extraido():
    r = C.extrair(TEXTOS["tema"])
    t = [c for c in r if c.tipo == "tema"]
    assert t and t[0].numero == "918" and t[0].tribunal == "STJ", r


def t_classifica_numero_truncado():
    c = C.Citacao(tipo="julgado", chave="HC 12842", numero="12842")
    v = C.classificar_falha(c, {"existe": False})
    assert v == "numero_truncado", v


def t_classifica_conteudo_diverso():
    """O tipo mais perigoso: número certo, diz outra coisa."""
    c = C.Citacao(tipo="julgado", chave="AgRg REsp 1947535/SP", numero="1947535")
    v = C.classificar_falha(
        c, {"existe": True, "conteudo_confere": False, "chave_casada": c.chave}
    )
    assert v == "conteudo_diverso", v


def t_classifica_numero_errado():
    """Existe, mas é outro processo — o caso AREsp/RJ no lugar do REsp/MG."""
    c = C.Citacao(tipo="julgado", chave="REsp 1533206/MG", numero="1533206", uf="MG")
    v = C.classificar_falha(
        c, {"existe": True, "conteudo_confere": True, "chave_casada": "AREsp 1533206/RJ"}
    )
    assert v == "numero_errado", v


def t_classifica_falso_positivo():
    c = C.Citacao(tipo="sumula", chave="Sumula 59", numero="59")
    v = C.classificar_falha(c, {"existe": True, "conteudo_confere": None})
    assert v == "falso_positivo", v


def t_relatorio_retem_peca():
    cits = [
        C.Citacao(tipo="julgado", chave="REsp 1782418/RJ", numero="1782418", uf="RJ"),
        C.Citacao(tipo="julgado", chave="HC 12842", numero="12842"),
    ]
    aval = {
        "julgado:REsp 1782418/RJ": {
            "existe": True, "conteudo_confere": True, "chave_casada": "REsp 1782418/RJ"
        },
        "julgado:HC 12842": {"existe": False},
    }
    r = C.relatorio(cits, aval)
    assert r["peça_retida"] is True, r
    assert r["contagem"]["numero_truncado"] == 1


def t_relatorio_sem_nota():
    """Nenhuma saída pode conter nota 0-100."""
    cits = [C.Citacao(tipo="julgado", chave="REsp 1/RJ", numero="1", uf="RJ")]
    r = C.relatorio(cits, {})
    texto = str(r)
    for proibido in ("score", "nota", "pontuacao", "0-100"):
        assert proibido not in texto.lower(), proibido


def main():
    testes = [(n, f) for n, f in sorted(globals().items()) if n.startswith("t_") and callable(f)]
    falhas = []
    for nome, fn in testes:
        try:
            fn()
            print(f"[PASS] {nome}")
        except AssertionError as e:
            print(f"[FAIL] {nome}: {e}")
            falhas.append(nome)
        except Exception as e:  # noqa: BLE001
            print(f"[ERRO] {nome}: {type(e).__name__}: {e}")
            falhas.append(nome)
    print(f"\n{len(testes) - len(falhas)}/{len(testes)} aprovados")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
