"""
Contrato de fronteira: `core/` não pode importar `dominios/`.

POR QUE ESTE TESTE EXISTE
-------------------------
A promessa central do kit é que o núcleo é genérico: um domínio novo se
acrescenta escrevendo YAML, sem tocar em `core/`. Até 02/11/2026 essa promessa
era verificada por disciplina e por um domínio-esqueleto (penal), não por
código. Disciplina não sobrevive a pressa.

POR QUE NÃO `import-linter`
---------------------------
O kit se publica para ser lido e rodado com o mínimo: Python 3.11+ e PyYAML.
Acrescentar uma dependência para checar 30 arquivos seria trocar uma regra de
uma linha por um pacote a instalar em cada máquina do escritório. `ast` é stdlib
e o teste inteiro cabe em uma tela.

O QUE ELE NÃO VERIFICA
----------------------
- Não verifica import dinâmico (`importlib.import_module("dominios.x")`), que
  `ast` não resolve estaticamente. Um `grep` textual cobre esse caso e roda
  junto, mais abaixo.
- Não verifica dependência de DADOS (um `core/` que abrisse
  `dominios/familia/x.yaml` por caminho literal). O teste de vocabulário em
  `core/dominio/tests/` cobre parte disso.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from core.pipeline.tests._harness import executar_e_sair, exigir  # noqa: E402

CORE = RAIZ / "core"

# Nomes de domínio instalados. Usado para detectar escolha por literal.
NOMES_DE_DOMINIO = [
    d.name for d in (RAIZ / "dominios").iterdir()
    if d.is_dir() and not d.name.startswith("_")
]


def _imports_estaticos(arquivo: Path):
    """Devolve todos os módulos citados em import/from de um arquivo."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                yield alias.name
        elif isinstance(no, ast.ImportFrom):
            # módulo None acontece em `from . import x`; o nível relativo é
            # tratado fora, aqui interessa o nome absoluto.
            if no.module:
                yield no.module
            # `from .dominios import x` não existe dentro de core/, mas
            # `from ..dominios import` existiria: o nome fica em no.level.
            for alias in no.names:
                yield alias.name


def t_core_nao_importa_dominios_estaticamente():
    violacoes = []
    for arquivo in CORE.rglob("*.py"):
        for modulo in _imports_estaticos(arquivo):
            raiz = modulo.split(".")[0]
            if raiz in ("dominios", "dominio_dados", "casos"):
                violacoes.append(f"{arquivo.relative_to(RAIZ)}: import {modulo}")
    exigir(not violacoes,
           "core/ importa de fora de core/ — a fronteira foi violada",
           "; ".join(violacoes[:6]))


def t_core_nao_importa_dominios_por_string():
    """
    Cobre import dinâmico, que `ast` não vê: `importlib`, `__import__`,
    `exec` com nome de domínio. O grep é grosseiro de propósito — falso
    positivo aqui é uma linha a explicar, falso negativo é a fronteira
    quebrada em silêncio.
    """
    suspeitos = []
    for arquivo in CORE.rglob("*.py"):
        if arquivo == Path(__file__).resolve():
            continue  # este arquivo nomeia os gatilhos de propósito
        texto = arquivo.read_text(encoding="utf-8")
        # Import dinamico de um dominio e violacao.
        for gatilho in ("importlib", "__import__"):
            if gatilho in texto:
                suspeitos.append(f"{arquivo.relative_to(RAIZ)}: {gatilho}")
        # Escolher um dominio por nome literal tambem e violacao. Caminho
        # parametrizado (`RAIZ / "dominios" / dominio`) e o contrato: o nucleo
        # sabe que existe uma pasta de dominios, nao qual delas usar.
        for nome in NOMES_DE_DOMINIO:
            if f'"dominios/{nome}' in texto or f"'dominios/{nome}" in texto:
                suspeitos.append(
                    f"{arquivo.relative_to(RAIZ)}: caminho literal para "
                    f"dominios/{nome}")
    exigir(not suspeitos,
           "core/ tem import dinâmico ou caminho literal para domínios/",
           "; ".join(suspeitos[:6]))


def t_core_nao_le_arquivo_de_dominio():
    """
    Dependência de dado também é acoplamento: um `core/` que abre
    `dominios/<id>/algo.yaml` com caminho literal já sabe que domínios existem.
    O caminho relativo a RAIZ é aceitável quando o domínio é PARÂMETRO
    (`RAIZ / "dominios" / dominio`), porque aí o núcleo não escolhe qual.
    Este teste procura nome de domínio específico no código.
    """
    nomes = NOMES_DE_DOMINIO
    violacoes = []
    for arquivo in CORE.rglob("*.py"):
        # Testes de core/ citam um domínio real como FIXTURE: o teste precisa
        # de um domínio concreto para exercitar o estágio. O contrato vale para
        # o código de produção.
        if "tests" in arquivo.parts:
            continue
        texto = arquivo.read_text(encoding="utf-8")
        for nome in nomes:
            if f'"{nome}"' in texto or f"'{nome}'" in texto:
                violacoes.append(f"{arquivo.relative_to(RAIZ)}: cita '{nome}'")
    exigir(not violacoes,
           "core/ cita um domínio específico pelo nome",
           "; ".join(sorted(set(violacoes))[:6]))


def t_o_teste_pega_uma_violacao_de_verdade():
    """
    Meta-teste: injetar uma violação num arquivo temporário DENTRO de core/ e
    exigir que o detector a encontre. Sem isto, o teste acima pode estar
    passando porque nunca olhou para lugar nenhum.
    """
    falso = CORE / "_violacao_de_proposito.py"
    falso.write_text("from dominios.familia import estrategia\n",
                     encoding="utf-8")
    try:
        modulos = list(_imports_estaticos(falso))
        exigir(any(m.split(".")[0] == "dominios" for m in modulos),
               "o detector não reconheceu uma violação evidente", str(modulos))
    finally:
        falso.unlink(missing_ok=True)


TESTES = [
    ("t_core_nao_importa_dominios_estaticamente",
     t_core_nao_importa_dominios_estaticamente),
    ("t_core_nao_importa_dominios_por_string",
     t_core_nao_importa_dominios_por_string),
    ("t_core_nao_le_arquivo_de_dominio", t_core_nao_le_arquivo_de_dominio),
    ("t_o_teste_pega_uma_violacao_de_verdade",
     t_o_teste_pega_uma_violacao_de_verdade),
]


if __name__ == "__main__":
    executar_e_sair("Fronteira core/ -> dominios/", TESTES)
