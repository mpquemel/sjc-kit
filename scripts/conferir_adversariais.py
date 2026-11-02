#!/usr/bin/env python3
"""
Conferência dos casos adversariais — o critério aqui é INVERTIDO.

FIXTURE ADVERSÁRIA QUE PASSA É FALHA DE INSTALAÇÃO.

Esta é a parte que quase todo projeto erra: escrever testes que provam que o
sistema funciona. Um caso adversarial existe para provar que o sistema FALHA
quando deve. Se ele passa, o sistema perdeu a capacidade de recusar — e um
sistema jurídico que não recusa é pior que um que erra.

O QUE ELE FAZ, EM CONCRETO
--------------------------
Para cada fixture marcada `adversaria: true`, avalia com o portão de citação
real (`extrair` + `relatorio`) e exige que o resultado NÃO seja `ok`. Ou seja:
exige que a peça seja RETIDA, ou que ao menos um veredito não seja positivo.

Fixture adversária cujo resultado sai `ok` e sem retenção = aprovada
indevidamente = falha de instalação.

Uso: make adversariais
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core.citacoes import citacoes as C  # noqa: E402


def coletar() -> list[dict]:
    """
    Junta as fixtures de TODOS os lugares legítimos, não só de um.

    A primeira versão procurava apenas em `dominios/*/tests/fixtures/` e
    portanto não achava nada — as fixtures do portão de citação vivem em
    `core/citacoes/tests/fixtures/`. Alvo que procura no lugar errado falha
    por ausência e finge ser "critério invertido não conferível".

    Procura em todo o repositório, exceto cache, e exige que o arquivo pareça
    uma coleção de fixtures (ter `fixtures` ou ser lista).
    """
    achados: list[dict] = []
    for caminho in sorted(RAIZ.rglob("*.json")):
        if "__pycache__" in caminho.parts or ".git" in caminho.parts:
            continue
        if "fixture" not in caminho.name.lower() and "fixtures" not in caminho.parts:
            continue
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"  [AVISO] {caminho.relative_to(RAIZ)} ilegível: {e}")
            continue
        itens = dados.get("fixtures", dados if isinstance(dados, list) else [])
        if isinstance(itens, dict):
            itens = list(itens.values())
        for it in itens:
            if isinstance(it, dict):
                it["_arquivo"] = str(caminho.relative_to(RAIZ))
                achados.append(it)
    return achados


def avaliar(fx: dict) -> dict | None:
    """
    Roda o portão sobre a fixture, exatamente como `test_fixtures.py` faz.

    Devolve None quando a fixture testa só extração (sem resultado_fonte):
    nesse caso não há veredito a conferir, e tratá-la como 'aprovada' seria
    inventar sucesso.
    """
    texto = fx.get("texto")
    if not isinstance(texto, str):
        return None
    extraidas = C.extrair(texto)
    rf_base = fx.get("resultado_fonte")
    if rf_base is None:
        return {"extraidas": extraidas, "relatorio": None}

    aval = {}
    for c in extraidas:
        rf = dict(rf_base)
        casada = fx.get("chave_casada_na_fonte")
        if casada:
            rf["chave_casada"] = casada
        aval[f"{c.tipo}:{c.chave}"] = rf
    return {"extraidas": extraidas, "relatorio": C.relatorio(extraidas, aval)}


def avaliar_extracao(fx: dict) -> tuple[bool, str]:
    """
    Critério para fixture adversarial que testa SÓ extração (sem fonte).

    FX-07 é o caso: 'art. 121' com 'fl. 121' no mesmo texto. Não há veredito de
    classificação a exigir, mas há um comportamento a exigir: a ambiguidade tem
    de ser REGISTRADA, não resolvida em silêncio.

    Sem este caminho, a fixture ficava 'não conferível' para sempre — decoração
    com nome de teste. Um adversarial que nunca roda não prova nada.
    """
    extraidas = C.extrair(fx["texto"])
    alvo = fx.get("citação_extraida") or {}
    exig = fx.get("exige_ambiguidade")

    achou = [c for c in extraidas
             if c.tipo == alvo.get("tipo") and c.numero == alvo.get("numero")]
    if not achou:
        return False, (f"citação {alvo.get('tipo')} {alvo.get('numero')} "
                       f"não extraída (extraídas: "
                       f"{[(c.tipo, c.numero) for c in extraidas]})")

    if exig:
        if not any(exig in a for a in achou[0].ambiguidades):
            return False, (f"ambiguidade '{exig}' NÃO registrada — o extrator "
                           f"resolveria em silêncio")
        return True, f"ambiguidade '{exig}' registrada, não adivinhada"

    # Sem exigência de ambiguidade, o comportamento esperado é extrair bem.
    return True, "citação extraída conforme esperado"


def main() -> int:
    fixtures = coletar()

    if not fixtures:
        print("  Nenhuma fixture encontrada no repositório (*fixtures*.json).")
        print()
        print("  Isso NÃO é aprovação: significa que o critério invertido não pode")
        print("  ser conferido. Um kit sem caso adversário não demonstrou que recusa.")
        return 2

    adversarias = [f for f in fixtures if f.get("adversaria")]
    print(f"  fixtures encontradas      : {len(fixtures)}")
    print(f"  marcadas como adversárias : {len(adversarias)}")
    print()

    if not adversarias:
        print("  [FALHA] Nenhuma fixture está marcada `adversaria: true`.")
        print("          O critério invertido não pode ser conferido.")
        return 2

    falhas = 0
    nao_conferiveis = 0

    for fx in adversarias:
        fid = fx.get("id", "(sem id)")

        # Adversarial de extração: exige comportamento de registro, não veredito.
        if fx.get("resultado_fonte") is None:
            ok, motivo = avaliar_extracao(fx)
            print(f"  [{'OK   ' if ok else 'FALHA'}] {fid}: {motivo}")
            if not ok:
                falhas += 1
            continue

        r = avaliar(fx)
        if r is None or r["relatorio"] is None:
            print(f"  [NAO-CONF] {fid}: fixture malformada — sem texto avaliável")
            nao_conferiveis += 1
            continue

        rel = r["relatorio"]
        vereditos = [i["veredito"] for i in rel["itens"]]
        retida = rel["peça_retida"]

        # Critério invertido: adversária precisa ser recusada.
        if retida or any(v != "ok" for v in vereditos):
            print(f"  [OK   ] {fid}: recusada como exigido "
                  f"(vereditos={vereditos}, retida={retida})")
        else:
            print(f"  [FALHA] {fid}: PASSOU — deveria ser recusada "
                  f"(vereditos={vereditos}, retida={retida})")
            falhas += 1

    print()
    if falhas:
        print(f"RESULTADO: {falhas} fixture(s) adversária(s) aprovada(s) indevidamente.")
        print("           Um caso que deveria quebrar não quebrou: o sistema")
        print("           perdeu a capacidade de recusar.")
        return 1

    conferidas = len(adversarias) - nao_conferiveis
    if conferidas == 0:
        print("RESULTADO: nenhuma adversária foi realmente conferida.")
        print("           Não é aprovação — é ausência de prova.")
        return 2

    print(f"RESULTADO: {conferidas} caso(s) adversário(s) recusado(s) como exigido"
          + (f"; {nao_conferiveis} não conferível(is)" if nao_conferiveis else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
