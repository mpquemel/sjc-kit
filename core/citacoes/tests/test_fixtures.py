#!/usr/bin/env python3
"""
test_fixtures.py — roda as fixtures de aceitação contra o portão real.

Cada fixture declara um veredito esperado. O teste falha se o portão devolver
outra coisa. Isso inclui o controle negativo FX-05: um portão que reprova tudo
é tão inútil quanto um que aprova tudo.

Rodar:
    python3 core/citacoes/tests/test_fixtures.py
"""
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_AQUI, "..", "..", "..")))

from core.citacoes import citacoes as C  # noqa: E402

FIXTURES = os.path.join(_AQUI, "fixtures", "fixtures-falhas.json")


def carregar():
    with open(FIXTURES, encoding="utf-8") as f:
        return json.load(f)["fixtures"]


def _avaliar(fx) -> dict:
    """
    Extrai do texto e devolve o relatório como o portão devolveria.

    Quando `resultado_fonte` é null, a fixture testa só a extração/ambiguidade,
    não a classificação.
    """
    extraidas = C.extrair(fx["texto"])
    if fx.get("resultado_fonte") is None:
        return {"extraidas": extraidas, "relatorio": None}

    aval = {}
    for c in extraidas:
        rf = dict(fx["resultado_fonte"])
        chave_casada = fx.get("chave_casada_na_fonte")
        if chave_casada:
            rf["chave_casada"] = chave_casada
        aval[f"{c.tipo}:{c.chave}"] = rf
    return {"extraidas": extraidas, "relatorio": C.relatorio(extraidas, aval)}


def t_fixtures_vereditos():
    falhas = []
    for fx in carregar():
        r = _avaliar(fx)
        esperado = fx["veredito_esperado"]

        if r["relatorio"] is None:
            # Só verifica que a citação foi extraída e, se exigido, a ambiguidade.
            alvo = fx["citação_extraida"]
            achou = [c for c in r["extraidas"]
                     if c.tipo == alvo["tipo"] and c.numero == alvo["numero"]]
            if not achou:
                falhas.append(f"{fx['id']}: citação não extraída")
                continue
            exig = fx.get("exige_ambiguidade")
            if exig and not any(exig in a for a in achou[0].ambiguidades):
                falhas.append(f"{fx['id']}: ambiguidade '{exig}' não registrada")
            continue

        vereditos = [i["veredito"] for i in r["relatorio"]["itens"]]
        if esperado not in vereditos:
            falhas.append(f"{fx['id']}: esperado {esperado}, obtido {vereditos}")
            continue
        if fx["peca_retida"] != r["relatorio"]["peça_retida"]:
            falhas.append(
                f"{fx['id']}: retenção esperada {fx['peca_retida']}, "
                f"obtida {r['relatorio']['peça_retida']}"
            )
    assert not falhas, "; ".join(falhas)


def t_fixture_controle_negativo_passa():
    """FX-05 precisa NÃO reter. Se retiver, o portão reprova citação correta."""
    fx = [f for f in carregar() if f["id"] == "FX-05-citacao-correcta"][0]
    r = _avaliar(fx)
    assert r["relatorio"]["peça_retida"] is False, r["relatorio"]
    assert r["relatorio"]["itens"][0]["veredito"] == "ok"


def t_fixture_timeout_nao_vira_ausencia():
    """FX-06: falha de infraestrutura não pode virar 'não existe'."""
    fx = [f for f in carregar() if f["id"] == "FX-06-fonte-indisponivel"][0]
    r = _avaliar(fx)
    veredito = r["relatorio"]["itens"][0]["veredito"]
    assert veredito != "numero_truncado", "timeout classificado como inexistência"
    assert r["relatorio"]["peça_retida"] is True


def t_fixtures_sem_dado_de_caso_real():
    """Repo público: nenhuma fixture pode conter idade, nome ou CPF."""
    import re
    with open(FIXTURES, encoding="utf-8") as f:
        bruto = f.read()
    assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", bruto), "CPF na fixture"
    proibidos = ["12 ANOS", "16 ANOS", "MENOR)", "RECORRENTE", "AGRAVANTE"]
    achados = [p for p in proibidos if p in bruto]
    assert not achados, f"identificação de caso real: {achados}"


def main():
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("t_") and callable(f)]
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
