"""
Validador de domínio — o detector de acoplamento em forma executável.

O QUE ELE PROVA
---------------
Que declarar um domínio novo não exige código em `core/`. Ele lê apenas
arquivos de configuração (YAML/MD) do diretório do domínio e devolve um
relatório. Não importa `dominios.*` e não precisa de nenhum campo novo em
`core/`.

O QUE ELE RECUSA A FAZER
------------------------
Não preenche valor. Não inventa regra. `a preencher` é um estado VÁLIDO:
significa "declarado, não decidido". O validador o distingue de campo ausente
porque as duas coisas exigem ação diferente do operador.

Vereditos (discretos, sem nota):
  APROVADO      — nenhum campo ausente; pode haver pendências declaradas
  ESQUELETO     — nenhum campo ausente E há pendências `a preencher`
  REPROVADO     — campo obrigatório ausente ou arquivo ilegível

Uso:
    python3 core/dominio/validador.py dominios/penal
    python3 core/dominio/validador.py dominios/penal --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

MARCADOR_PENDENTE = "a preencher"

# Arquivos que qualquer domínio precisa ter. Nome de arquivo é contrato:
# o núcleo procura por eles e não pergunta ao domínio onde estão.
ARQUIVOS_OBRIGATORIOS = {
    "dominio.yaml": "metadados do domínio",
    "estrategia.yaml": "catálogo de decisão (gatilho → peça)",
    "tese-catalogo.yaml": "tese → fundamento → precedente",
    "gates/regras.yaml": "regras de gate específicas do domínio",
    "tests/casos-adversariais.yaml": "casos que quebram",
}

# Pastas que o pipeline procura. Vazias são válidas em esqueleto.
PASTAS_OBRIGATORIAS = ["templates", "prompts"]

# Campos que o contrato de domínio exige. Ausente = REPROVADO.
CAMPOS_DOMINIO = ["id", "nome", "descricao", "versao", "fontes", "acervo",
                  "modelos", "template_base", "contagem_prazo"]

# Vocabulário institucional proibido no núcleo (decisão 5 da especificação).
# O validador acusa em QUALQUER arquivo do domínio e em core/, porque o
# vazamento de vocabulário é o primeiro sintoma de vazamento de arquitetura.
VOCABULARIO_PROIBIDO = [
    "assistido", "defensoria", "polo_defensoria", "numero_verde",
    "vara_familia", "pje", "eproc",
]


def _ler_yaml(caminho: Path) -> tuple[Optional[Any], Optional[str]]:
    """Devolve (dados, erro). Erro é string legível, nunca exceção vazada."""
    if yaml is None:
        return None, "PyYAML não instalado — não é possível validar YAML"
    try:
        with open(caminho, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except FileNotFoundError:
        return None, f"arquivo ausente: {caminho.name}"
    except yaml.YAMLError as e:
        return None, f"YAML inválido em {caminho.name}: {e}"
    except OSError as e:
        return None, f"não foi possível ler {caminho.name}: {e}"


def _contar_pendentes(objeto: Any, caminho: str = "") -> List[str]:
    """
    Lista os caminhos (ex.: 'fontes[0]', 'modelos.default.provider') cujo valor é
    `a preencher`. Percorre estruturas aninhadas.

    Não conta string vazia nem None como pendente: ausência e pendência são
    estados diferentes, e confundi-los faz o relatório mentir.
    """
    achados: List[str] = []
    if isinstance(objeto, str):
        if MARCADOR_PENDENTE in objeto.lower():
            achados.append(caminho or "(raiz)")
    elif isinstance(objeto, dict):
        for k, v in objeto.items():
            achados.extend(_contar_pendentes(v, f"{caminho}.{k}" if caminho else str(k)))
    elif isinstance(objeto, list):
        for i, v in enumerate(objeto):
            achados.extend(_contar_pendentes(v, f"{caminho}[{i}]"))
    return achados


def _campos_ausentes(dados: dict, exigidos: List[str]) -> List[str]:
    return [c for c in exigidos if c not in dados or dados[c] in (None, "")]


def _sem_acento(texto: str) -> str:
    """
    Remove acentos para comparação. NÃO altera o texto original em disco.

    Necessário porque `"família".lower()` continua sendo `"família"`: lower não
    dobra acento. Sem isso, um prompt adaptado que fala "família" era acusado de
    genérico porque o id do domínio é `familia` sem acento — falso positivo
    medido em 02/11/2026 nos três prompts de família.
    """
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ",
        "aaaaaeeeeiiiiooooouuuucn")
    return texto.lower().translate(tabela)


def _prompt_generico(caminho: Path, dominio_id: str) -> bool:
    """
    Um prompt copiado do template não menciona o id nem os termos do domínio.
    Se não menciona, é aviso — não reprovação. Trocar de área sem trocar o
    prompt é usar advogado de família em causa penal: o sistema permite, mas
    precisa dizer.

    Comparação sem acento: o id é `familia`, o texto diz `família`. Distinguir
    os dois faria o detector acusar exatamente os prompts bem adaptados.
    """
    try:
        texto = _sem_acento(caminho.read_text(encoding="utf-8"))
    except OSError:
        return False
    if "adaptacoes pendentes" in texto:
        return True
    return (_sem_acento(dominio_id) not in texto
            and "(a preencher" not in texto)


def _procurar_vocabulario(raiz: Path) -> List[dict]:
    """Varre o diretório procurando termos institucionais proibidos."""
    achados: List[dict] = []
    padrao = re.compile(r"\b(" + "|".join(VOCABULARIO_PROIBIDO) + r")\b",
                        re.IGNORECASE)
    for caminho in raiz.rglob("*"):
        if not caminho.is_file() or caminho.suffix not in (".py", ".yaml", ".yml", ".md", ".json"):
            continue
        if "__pycache__" in caminho.parts:
            continue
        try:
            for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
                for m in padrao.finditer(linha):
                    achados.append({"arquivo": str(caminho.relative_to(raiz)),
                                    "linha": n, "termo": m.group(1).lower()})
        except (OSError, UnicodeDecodeError):
            continue
    return achados


def validar(caminho_dominio: str) -> dict:
    """
    Valida um diretório de domínio. Devolve relatório com veredito discreto.

    Não levanta exceção em nenhum caminho: um validador que quebra não valida
    nada, e o operador precisa ver o que faltou, não um traceback.
    """
    raiz = Path(caminho_dominio)
    relatorio: Dict[str, Any] = {
        "dominio": raiz.name,
        "caminho": str(raiz),
        "veredito": "APROVADO",
        "arquivos": {"presentes": [], "ausentes": []},
        "pastas": {"presentes": [], "ausentes": []},
        "campos_ausentes": [],
        "pendencias": [],
        "avisos": [],
        "vocabulario_proibido": [],
        "estado": None,
    }

    if not raiz.is_dir():
        relatorio["veredito"] = "REPROVADO"
        relatorio["campos_ausentes"].append(f"diretório inexistente: {raiz}")
        return relatorio

    # 1. Arquivos e pastas obrigatórios
    for nome in ARQUIVOS_OBRIGATORIOS:
        if (raiz / nome).is_file():
            relatorio["arquivos"]["presentes"].append(nome)
        else:
            relatorio["arquivos"]["ausentes"].append(nome)
    for pasta in PASTAS_OBRIGATORIAS:
        if (raiz / pasta).is_dir():
            relatorio["pastas"]["presentes"].append(pasta)
        else:
            relatorio["pastas"]["ausentes"].append(pasta)

    # 2. Metadados do domínio
    dados, erro = _ler_yaml(raiz / "dominio.yaml")
    if erro:
        relatorio["avisos"].append(erro)
    elif isinstance(dados, dict):
        relatorio["campos_ausentes"].extend(_campos_ausentes(dados, CAMPOS_DOMINIO))
        relatorio["estado"] = dados.get("estado")
        relatorio["pendencias"].extend(
            f"dominio.yaml:{c}" for c in _contar_pendentes(dados))
    elif dados is not None:
        relatorio["avisos"].append("dominio.yaml não é um mapa YAML")

    # 3. Catálogos: pendências declaradas
    for nome in ("estrategia.yaml", "tese-catalogo.yaml", "gates/regras.yaml",
                 "tests/casos-adversariais.yaml"):
        d, e = _ler_yaml(raiz / nome)
        if e:
            relatorio["avisos"].append(e)
            continue
        if d is None:
            continue
        for c in _contar_pendentes(d):
            relatorio["pendencias"].append(f"{nome}:{c}")

    # 4. Templates: precisa haver ao menos um .md com bloco [OBRIGATÓRIA]
    templates = list((raiz / "templates").glob("*.md")) if (raiz / "templates").is_dir() else []
    if not templates:
        relatorio["avisos"].append("nenhum template .md em templates/")
    else:
        for t in templates:
            try:
                if "[OBRIGATÓRIA]" not in t.read_text(encoding="utf-8").upper():
                    relatorio["avisos"].append(
                        f"template sem bloco [OBRIGATÓRIA]: {t.name}")
            except OSError:
                relatorio["avisos"].append(f"template ilegível: {t.name}")

    # 5. Prompts: genérico é aviso, não reprovação
    if (raiz / "prompts").is_dir():
        for p in (raiz / "prompts").glob("*.md"):
            if _prompt_generico(p, raiz.name):
                relatorio["avisos"].append(
                    f"prompt_do_dominio: generico ({p.name}) — copiado do template")

    # 6. Vocabulário institucional
    relatorio["vocabulario_proibido"] = _procurar_vocabulario(raiz)

    # 7. Veredito
    if relatorio["arquivos"]["ausentes"] or relatorio["campos_ausentes"]:
        relatorio["veredito"] = "REPROVADO"
    elif relatorio["pendencias"]:
        relatorio["veredito"] = "ESQUELETO"
    else:
        relatorio["veredito"] = "APROVADO"

    relatorio["totais"] = {
        "arquivos_ausentes": len(relatorio["arquivos"]["ausentes"]),
        "campos_ausentes": len(relatorio["campos_ausentes"]),
        "pendencias": len(relatorio["pendencias"]),
        "avisos": len(relatorio["avisos"]),
        "vocabulario_proibido": len(relatorio["vocabulario_proibido"]),
    }
    return relatorio


def formatar(r: dict) -> str:
    linhas = [
        f"DOMÍNIO: {r['dominio']}",
        f"VEREDITO: {r['veredito']}",
        "",
        f"arquivos presentes : {len(r['arquivos']['presentes'])}",
        f"arquivos ausentes  : {len(r['arquivos']['ausentes'])}",
    ]
    for a in r["arquivos"]["ausentes"]:
        linhas.append(f"  FALTA  {a}")
    for c in r["campos_ausentes"]:
        linhas.append(f"  CAMPO  {c}")
    linhas.append(f"pendências declaradas: {len(r['pendencias'])}")
    for p in r["pendencias"][:20]:
        linhas.append(f"  pendente  {p}")
    if len(r["pendencias"]) > 20:
        linhas.append(f"  ... e {len(r['pendencias']) - 20} outras")
    if r["avisos"]:
        linhas.append(f"avisos: {len(r['avisos'])}")
        for a in r["avisos"]:
            linhas.append(f"  AVISO  {a}")
    if r["vocabulario_proibido"]:
        linhas.append(f"VOCABULÁRIO PROIBIDO: {len(r['vocabulario_proibido'])}")
        for v in r["vocabulario_proibido"]:
            linhas.append(f"  {v['arquivo']}:{v['linha']}  {v['termo']}")
    return "\n".join(linhas)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Valida um domínio do SJC.")
    p.add_argument("dominio", help="caminho do diretório do domínio")
    p.add_argument("--json", action="store_true", help="saída JSON")
    args = p.parse_args(argv)

    r = validar(args.dominio)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else formatar(r))

    # Exit codes distintas por veredito: o CI precisa distinguir "esqueleto
    # declarado" (esperado em penal) de "reprovado" (defeito).
    return {"APROVADO": 0, "ESQUELETO": 0, "REPROVADO": 1}[r["veredito"]]


if __name__ == "__main__":
    sys.exit(main())
