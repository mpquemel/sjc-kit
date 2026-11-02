#!/usr/bin/env python3
"""
Bootstrap — prepara o ambiente sem adivinhar nada.

O QUE ESTE SCRIPT NÃO FAZ (e por quê)
-------------------------------------
- Não cria venv virtual. O kit não tem dependência além de PyYAML, e um venv
  criado por script é o tipo de conveniência que esconde qual Python está
  rodando. Se o operador quiser venv, ele faz. O AGENT.md pede explicitamente
  que o agente LEIA este arquivo antes de executá-lo — então ele precisa ser
  pequeno o bastante para ser lido.
- Não instala pacote da rede sem dizer qual e por quê. Um bootstrap que
  instala em silêncio é um bootstrap que pode instalar a coisa errada.
- Não falha sem dizer o que fazer. Toda checagem devolve ação concreta.

SAÍDA
-----
Código 0: ambiente pronto.
Código 1: falta algo, com a lista do que fazer.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 11)


def checar_python() -> tuple[bool, str]:
    if sys.version_info < MIN_PYTHON:
        return False, (f"Python {'.'.join(map(str, MIN_PYTHON))}+ exigido; "
                       f"encontrado {sys.version.split()[0]}. "
                       f"Instale uma versão compatível e rode de novo.")
    return True, f"Python {sys.version.split()[0]}"


def checar_yaml() -> tuple[bool, str]:
    try:
        import yaml  # noqa: F401
        return True, f"PyYAML {yaml.__version__}"
    except ImportError:
        return False, ("PyYAML ausente. Instale com: pip install pyyaml "
                       "(é a única dependência externa do kit)")


def checar_estrutura() -> tuple[bool, list[str]]:
    """
    Verifica a árvore mínima. Se `core/` ou `dominios/` não existem, o
    repositório está num estado que o AGENT.md chama de "pré-código" — e a
    orientação lá é NÃO instalar, reportar.
    """
    obrigatorios = ["core", "dominios", "dominios/_template",
                    "core/pipeline", "core/citacoes", "core/dominio"]
    faltando = [p for p in obrigatorios if not (RAIZ / p).is_dir()]
    return not faltando, faltando


def checar_suites() -> tuple[bool, list[str]]:
    """
    Lista as suites de teste conhecidas. Ausência de suite não é erro — e
    também não é sucesso: o relatório diz exatamente quantas existem, senão
    "0 testes rodaram, tudo passou" parece aprovação.
    """
    suites = sorted(
        str(p.relative_to(RAIZ))
        for p in RAIZ.rglob("test_*.py")
        if "__pycache__" not in p.parts)
    return bool(suites), suites


def checar_vocabulario() -> tuple[bool, str]:
    """A lista negra tem de existir e ser legível: o validador depende dela."""
    p = RAIZ / "core" / "contratos" / "vocabulario.json"
    if not p.is_file():
        return False, f"lista de vocabulário ausente: {p.relative_to(RAIZ)}"
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return False, f"lista de vocabulário ilegível: {e}"
    if not dados.get("termos_proibidos"):
        return False, "lista de vocabulário vazia — o detector não detectaria nada"
    return True, f"{len(dados['termos_proibidos'])} termos proibidos"


def _repo_que_contem(caminho):
    """Primeiro diretório ancestral (inclusive) que contém `.git`."""
    atual = caminho.resolve()
    for pai in [atual, *atual.parents]:
        if (pai / ".git").exists():
            return pai
    return None


def _gitignore_isola(repo, projeto):
    """
    Confere se alguma regra do .gitignore do repositório isola `casos/`.

    A checagem é TEXTUAL e declara isso: procura linha que mencione "casos".
    Não interpreta a semântica completa do .gitignore — negativas, precedência,
    globs compostos. Melhor aprovar com a limitação dita do que aprovar por
    omissão, que foi o defeito original.
    """
    ign = repo / ".gitignore"
    if not ign.is_file():
        return False, ("repositório git sem .gitignore — casos/ e dados de cliente "
                       "podem ser versionados no primeiro commit")
    for linha in ign.read_text(encoding="utf-8").splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#"):
            continue
        if "casos" in limpa:
            return True, f".gitignore de {repo.name} isola linhas com 'casos'"
    return False, ("nenhuma regra do .gitignore isola 'casos/' — dado de cliente "
                   "pode vazar mesmo com repositório configurado")


def checar_git() -> tuple[bool, str]:
    """
    Verifica se os dados de caso estão fora do controle de versão.

    Isto é barreira jurídica, não higiene técnica: dado de cliente em
    repositório público é vazamento, e o kit vai ser público.
    """
    # ACHADO 02/11/2026: a versão anterior procurava `.git` apenas em RAIZ. Rodada
    # de dentro do repositório do workspace — onde o projeto vive — ela respondia
    # "sem repositório git neste diretório (nada a vazar)" e saía com código 0,
    # enquanto 80 arquivos deste diretório estavam rastreados pelo git do
    # workspace. Um gate de vazamento que aprova quando não entende o ambiente é
    # pior que gate nenhum: ele tranquiliza.
    repo = _repo_que_contem(RAIZ)
    if repo is None:
        return True, "nenhum repositório git nos diretórios ascendentes (nada a vazar)"
    if repo != RAIZ:
        ok_ign, msg = _gitignore_isola(repo, RAIZ)
        return ok_ign, (f"repositório git em {repo} — {msg}" if ok_ign
                        else f"repositório git em {repo} — {msg}")
    ign = RAIZ / ".gitignore"
    if not ign.is_file():
        return False, (".gitignore ausente — casos/ e dados de cliente precisam "
                       "de barreira explícita antes do primeiro commit")
    texto = ign.read_text(encoding="utf-8")
    if "casos/" not in texto and "casos/*" not in texto:
        return False, ".gitignore não isola casos/ — dado de cliente pode vazar"
    return True, ".gitignore isola casos/"


def main() -> int:
    print("=" * 70)
    print(" SJC-KIT — BOOTSTRAP")
    print("=" * 70)
    print(f"raiz: {RAIZ}")
    print()

    problemas: list[str] = []

    ok, msg = checar_python()
    print(f"  [{'OK ' if ok else 'FALHA'}] {msg}")
    if not ok:
        problemas.append(msg)

    ok, msg = checar_yaml()
    print(f"  [{'OK ' if ok else 'FALHA'}] {msg}")
    if not ok:
        problemas.append(msg)

    ok, faltando = checar_estrutura()
    if ok:
        print("  [OK ] estrutura de diretórios completa")
    else:
        print(f"  [FALHA] faltam diretórios: {', '.join(faltando)}")
        problemas.append("estrutura incompleta — repositório em estágio pré-código; não instale")

    ok, suites = checar_suites()
    print(f"  [{'OK ' if ok else 'FALHA'}] {len(suites)} suíte(s) de teste "
          f"{'encontrada(s)' if ok else '— nenhuma: nada seria verificado'}")

    ok, msg = checar_vocabulario()
    print(f"  [{'OK ' if ok else 'FALHA'}] {msg}")
    if not ok:
        problemas.append(msg)

    ok, msg = checar_git()
    if ok:
        print(f"  [OK ] {msg}")
    else:
        # AVISO não é detalhe: repositório que não isola casos/ é risco de
        # vazamento de dado de cliente. Sai como problema, com código de erro,
        # porque gate que avisa e aprova é gate que só tranquiliza.
        print(f"  [FALHA] {msg}")
        problemas.append(msg)

    print()
    if problemas:
        print(f"AMBIENTE NÃO PRONTO — {len(problemas)} problema(s):")
        for p in problemas:
            print(f"  - {p}")
        return 1

    print("AMBIENTE PRONTO. Próximo passo: make verify")
    print(f"Suítes que rodarão: {len(suites)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
