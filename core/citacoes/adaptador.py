#!/usr/bin/env python3
"""
adaptador.py — liga o portão de citação às skills de jurisprudência.

Responsabilidade única: traduzir o que a skill devolve para o contrato
`verificacao-citacao.json`. O portão não conhece tribunal; o adaptador sim.

Regra que este módulo obedece: falha de infraestrutura NUNCA vira
`encontrado: false`. Vira `encontrado: null` com `retem: true`. Um sistema que
não conseguiu perguntar não pode afirmar que não existe.

Uso:
    from core.citacoes.adaptador import verificar
    r = verificar({"tipo": "julgado", "chave": "REsp 1533206/MG", "numero": "1533206", "uf": "MG"})
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from typing import Optional

# Diretório dos coletores de fonte. O kit NÃO os traz: cada fonte externa é
# frágil por natureza e muda sem aviso (ver LIMITES.md). Quem quiser ligar a
# consulta aponta SJC_FONTES para o diretório onde os coletores vivem.
#
# Ausência do diretório NÃO é falha silenciosa: `verificar` devolve
# `consulta_executada: false` e `retem: true`, e a peça é retida. Melhor retido
# por fonte ausente do que liberado por fonte que ninguém conferiu.
FONTES = os.environ.get(
    "SJC_FONTES",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fontes"),
)
STJ_SCRIPTS = os.path.join(FONTES, "stj")
STF_SCRIPTS = os.path.join(FONTES, "stf")
TJRJ_SCRIPTS = os.path.join(FONTES, "tjrj")

AVISO_PADRAO = (
    "Consulta verifica identidade do documento. NAO verifica vigencia, "
    "superacao nem aderencia a tese."
)


def _vazio(erro_codigo: str, erro: str, fonte: str, chave_usada: str = "termo") -> dict:
    return {
        "consulta_executada": False,
        "encontrado": None,
        "chave_usada": chave_usada,
        "total": 0,
        "ambiguo": False,
        "prova_consulta": {},
        "fonte": fonte,
        "lido_em": date.today().isoformat(),
        "erro_codigo": erro_codigo,
        "erro": erro,
        "retem": True,
        "documentos": [],
        "aviso_citacao": AVISO_PADRAO,
    }


def _rodar(cmd, cwd, timeout=200):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _json_do_stdout(saida: str) -> Optional[dict]:
    """Extrai o primeiro objeto JSON completo do stdout."""
    inicio = saida.find("{")
    if inicio < 0:
        return None
    profundidade = 0
    for i in range(inicio, len(saida)):
        if saida[i] == "{":
            profundidade += 1
        elif saida[i] == "}":
            profundidade -= 1
            if profundidade == 0:
                try:
                    return json.loads(saida[inicio:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---------------------------------------------------------------- STJ
def _stj(citacao: dict) -> dict:
    """
    STJ exige o REGISTRO como chave. Sem registro, deriva por numeral e marca
    a limitação. Origem medida: numeral 1533206 devolve AREsp/RJ quando o alvo
    é o REsp/MG.
    """
    registro = citacao.get("registro")
    if registro:
        try:
            r = _rodar(
                [sys.executable, "stj_scraper.py", "--registro", registro],
                STJ_SCRIPTS, timeout=220,
            )
        except subprocess.TimeoutExpired:
            return _vazio("timeout", "consulta por registro excedeu 220s",
                          "processo.stj.jus.br", "registro")
        d = _json_do_stdout(r.stdout)
        if not d:
            return _vazio("pagina_vazia", "saída sem JSON parseável",
                          "processo.stj.jus.br", "registro")
        if not d.get("consulta_executada", True):
            return _vazio(d.get("erro_codigo") or "timeout",
                          d.get("erro") or "consulta não concluída",
                          "processo.stj.jus.br", "registro")
        dados = d.get("dados") or {}
        encontrado = bool(d.get("encontrado"))
        chave_casada = None
        if encontrado:
            chave_casada = f"{dados.get('tipo', '?')} {dados.get('numero_interno', '?')}"
            if dados.get("uf"):
                chave_casada += f"/{dados['uf']}"
        return {
            "consulta_executada": True,
            "encontrado": encontrado,
            "chave_usada": "registro",
            "total": 1 if encontrado else 0,
            "ambiguo": False,
            "prova_consulta": {
                "campo_enviado": "idNumeroRegistro",
                "valor_enviado": registro,
                "base": "processo.stj.jus.br",
            },
            "fonte": "processo.stj.jus.br",
            "lido_em": date.today().isoformat(),
            "erro_codigo": None if encontrado else "acervo_vazio",
            "erro": None if encontrado else d.get("erro"),
            "retem": not encontrado,
            "documentos": ([{
                "chave": chave_casada,
                "registro": dados.get("registro"),
                "tribunal": "STJ",
                "orgao": None,
                "relator": None,
                "data_julgamento": dados.get("autuacao"),
                "texto": "",
                "texto_de": "desconhecido",
            }] if encontrado else []),
            "aviso_citacao": AVISO_PADRAO,
        }

    # Sem registro: deriva por numeral, e diz que fez isso.
    numero = citacao.get("numero") or ""
    try:
        r = _rodar([sys.executable, "stj_scraper.py", "--numero", numero],
                   STJ_SCRIPTS, timeout=220)
    except subprocess.TimeoutExpired:
        return _vazio("timeout", "consulta por numeral excedeu 220s",
                      "processo.stj.jus.br", "numeral")
    d = _json_do_stdout(r.stdout) or {}
    dados = d.get("dados") or {}
    encontrado = bool(d.get("encontrado"))
    chave_casada = None
    if encontrado:
        chave_casada = f"{dados.get('tipo', '?')} {dados.get('numero_interno', '?')}"
        if dados.get("uf"):
            chave_casada += f"/{dados['uf']}"
    return {
        "consulta_executada": True,
        "encontrado": encontrado,
        "chave_usada": "numeral",
        "total": 1 if encontrado else 0,
        "ambiguo": False,
        "prova_consulta": {"campo_enviado": "idNumeroProcesso", "valor_enviado": numero,
                           "base": "processo.stj.jus.br"},
        "fonte": "processo.stj.jus.br",
        "lido_em": date.today().isoformat(),
        "erro_codigo": None if encontrado else "acervo_vazio",
        "erro": None if encontrado else d.get("erro"),
        "retem": not encontrado,
        "documentos": ([{
            "chave": chave_casada,
            "registro": dados.get("registro"),
            "tribunal": "STJ",
            "orgao": None,
            "relator": None,
            "data_julgamento": dados.get("autuacao"),
            "texto": "",
            "texto_de": "desconhecido",
        }] if encontrado else []),
        "aviso_citacao": AVISO_PADRAO + (
            " AVISO: consulta por numeral identifica o PROCESSO, nao o ACORDAO; "
            "confira o registro antes de citar."
        ),
    }


# ---------------------------------------------------------------- STF
def _stf(citacao: dict) -> dict:
    termo = citacao.get("termo") or f"{citacao.get('chave', '')}".replace(" ", " ").lower()
    try:
        r = _rodar([sys.executable, "stf_validador.py", termo], STF_SCRIPTS, timeout=180)
    except subprocess.TimeoutExpired:
        return _vazio("timeout", "validação STF excedeu 180s",
                      "portal.stf.jus.br", "numeral")
    saida = r.stdout
    encontrado = "ENCONTRADO" in saida.upper() and "NÃO ENCONTRADO" not in saida.upper()
    return {
        "consulta_executada": True,
        "encontrado": encontrado,
        "chave_usada": "numeral",
        "total": 1 if encontrado else 0,
        "ambiguo": "AVISO:" in saida and "mesmo número" in saida,
        "prova_consulta": {"consulta_texto": saida.splitlines()[0] if saida else "",
                           "base": "portal.stf.jus.br"},
        "fonte": "portal.stf.jus.br",
        "lido_em": date.today().isoformat(),
        "erro_codigo": None if encontrado else "acervo_vazio",
        "erro": None if encontrado else "julgado não encontrado na base",
        "retem": not encontrado,
        "documentos": [],
        "aviso_citacao": AVISO_PADRAO,
    }


# ---------------------------------------------------------------- TJRJ
def _tjrj(citacao: dict) -> dict:
    numero = citacao.get("numero") or ""
    try:
        r = _rodar([sys.executable, "tjrj_busca.py", "--numero", numero],
                   TJRJ_SCRIPTS, timeout=180)
    except subprocess.TimeoutExpired:
        return _vazio("timeout", "consulta TJRJ excedeu 180s",
                      "tjrj.jus.br", "numeral")
    d = _json_do_stdout(r.stdout)
    if not d:
        return _vazio("pagina_vazia", "saída sem JSON parseável",
                      "tjrj.jus.br", "numeral")
    encontrado = bool(d.get("encontrado"))
    return {
        "consulta_executada": bool(d.get("consulta_executada")),
        "encontrado": encontrado,
        "chave_usada": "numeral",
        "total": int(d.get("total") or 0),
        "ambiguo": bool(d.get("ambiguo")),
        "prova_consulta": {"consulta_texto": json.dumps(d.get("parametros") or {},
                                                        ensure_ascii=False)[:400],
                           "base": "tjrj.jus.br"},
        "fonte": "tjrj.jus.br",
        "lido_em": date.today().isoformat(),
        "erro_codigo": None if encontrado else "acervo_vazio",
        "erro": d.get("erro"),
        "retem": not encontrado,
        "documentos": [],
        "aviso_citacao": AVISO_PADRAO,
    }


_REDIRECT = {"STJ": _stj, "STF": _stf, "TJRJ": _tjrj}


def verificar(citacao: dict) -> dict:
    """
    Verifica uma citação. citacao precisa de: tipo, chave, tribunal.
    """
    tribunal = (citacao.get("tribunal") or "").upper()
    fn = _REDIRECT.get(tribunal)
    if fn is None:
        return _vazio(
            "formato_invalido",
            f"tribunal '{tribunal}' sem adaptador. Adaptadores disponíveis: {sorted(_REDIRECT)}",
            "desconhecido",
        )
    return fn(citacao)
