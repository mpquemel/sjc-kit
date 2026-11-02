#!/usr/bin/env python3
"""
test_adaptador.py — testes de contrato do adaptador de fontes.

Dois grupos:

  A. Contrato offline — roda sempre. Verifica que todo caminho de falha produz
     um objeto válido segundo verificacao-citacao.json, com retem=true onde a
     incerteza existe.

  B. Contrato ao vivo — marcado, exige CDP. Verifica que a via real cumpre o
     contrato para um caso que existe e um que não existe.

O teste que mais importa é A3: falha de infraestrutura NÃO pode virar
"encontrado: false". Um sistema que não conseguiu perguntar não pode afirmar
que não existe.
"""
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_AQUI, "..", "..", "..")))

from core.citacoes import adaptador as A  # noqa: E402

SCHEMA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "contratos", "schemas", "verificacao-citacao.json"
)

OBRIGATORIOS = ("consulta_executada", "encontrado", "chave_usada",
                 "prova_consulta", "fonte")


def _valida_contrato(obj: dict) -> list:
    """Validação mínima sem dependência externa. Devolve lista de violações."""
    faltas = [c for c in OBRIGATORIOS if c not in obj]
    if obj.get("encontrado") is None and obj.get("retem") is not True:
        faltas.append("encontrado=null exige retem=true")
    if obj.get("consulta_executada") is False and not obj.get("erro_codigo"):
        faltas.append("consulta_executada=false exige erro_codigo")
    chaves_ok = {
        "registro", "numeral", "numero_interno", "npu", "termo", "ementa",
    }
    if obj.get("chave_usada") not in chaves_ok:
        faltas.append(f"chave_usada inválida: {obj.get('chave_usada')}")
    return faltas


# ------------------------------------------------------------- offline
def t_offline_tribunal_desconhecido():
    r = A.verificar({"tipo": "julgado", "chave": "X 1", "tribunal": "XYZ"})
    faltas = _valida_contrato(r)
    assert not faltas, faltas
    assert r["erro_codigo"] == "formato_invalido"
    assert r["encontrado"] is None and r["retem"] is True


def t_offline_vazio_retem():
    """Falha de infraestrutura nunca vira encontrado=false."""
    v = A._vazio("timeout", "estourou", "x.jus.br")
    faltas = _valida_contrato(v)
    assert not faltas, faltas
    assert v["consulta_executada"] is False
    assert v["encontrado"] is None
    assert v["retem"] is True


def t_offline_json_embedded():
    """O extrator de JSON precisa achar o objeto mesmo com texto ao redor."""
    saida = 'lixo antes\n{"a": 1, "b": {"c": 2}}\ntexto depois'
    d = A._json_do_stdout(saida)
    assert d == {"a": 1, "b": {"c": 2}}, d


def t_offline_json_invalido_devolve_none():
    assert A._json_do_stdout("isto não é json") is None


def t_offline_schema_existe():
    with open(SCHEMA, encoding="utf-8") as f:
        s = json.load(f)
    assert "required" in s and "encontrado" in s["required"]
    assert "chave_usada" in s["properties"]


def t_offline_stj_sem_tribunal_nao_explode():
    """Citação sem tribunal declarado não pode derrubar o portão."""
    r = A.verificar({"tipo": "julgado", "chave": "REsp 1/RJ", "numero": "1"})
    faltas = _valida_contrato(r)
    assert not faltas, faltas
    assert r["erro_codigo"] == "formato_invalido"


# ------------------------------------------------------------- ao vivo
def t_live_stj_registro():
    r = A.verificar({
        "tipo": "julgado", "chave": "REsp 1533206/MG",
        "numero": "1533206", "tribunal": "STJ",
        "registro": "2014/0345653-7",
    })
    faltas = _valida_contrato(r)
    assert not faltas, faltas
    assert r["chave_usada"] == "registro"
    assert r["encontrado"] is True, r
    assert r["documentos"] and r["documentos"][0]["chave"].startswith("REsp")
    assert "/MG" in r["documentos"][0]["chave"], r["documentos"][0]["chave"]


def t_live_stf_inexistente_nao_mente():
    r = A.verificar({
        "tipo": "julgado", "chave": "RE 9999999", "numero": "9999999",
        "tribunal": "STF", "termo": "re 9999999",
    })
    faltas = _valida_contrato(r)
    assert not faltas, faltas
    assert r["encontrado"] is False
    assert r["retem"] is True


def main():
    ao_vivo = "--ao-vivo" in sys.argv
    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("t_offline") and callable(f)]
    if ao_vivo:
        testes += [(n, f) for n, f in sorted(globals().items())
                   if n.startswith("t_live") and callable(f)]
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
