"""
Runner — executa o DAG de estágios com fail-fast e pausa explícita.

TRÊS MODOS DE PARADA, TRÊS SIGNIFICADOS
----------------------------------------
  fail-fast   — contrato violado ou exceção. Defeito: corrija o dado ou o código.
  pausa       — estágio pediu decisão humana (EstagioAbortado). NÃO é defeito.
  fim         — último estágio executou com contrato válido.

Confundir os três é o erro clássico: tratar pausa como falha faz o operador
procurar bug onde há pergunta; tratar falha como pausa faz o operador esperar
uma resposta que nunca virá.

O QUE O RUNNER NÃO FAZ
----------------------
Não conhece domínio, não chama LLM, não lê PDF. Ele ordena, verifica e
registra. Toda a inteligência está nos estágios.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Type

from .stage import (ErroDeContrato, EstagioAbortado, PipelineContext,
                    ResultadoEstagio, Stage)


class DAGInvalido(Exception):
    """O grafo de estágios está mal formado. Defeito de configuração."""


def ordenar(estagios: Sequence[Stage]) -> List[Stage]:
    """
    Ordena por dependência (topológico), preservando a ordem declarada entre
    estágios independentes.

    Falha alto em: id duplicado, dependência inexistente, ciclo. Nenhum dos
    três é recuperável — seguir adiante produz ordem arbitrária, e ordem
    arbitrária num pipeline jurídico é resultado aleatório com aparência de
    método.
    """
    por_id: Dict[str, Stage] = {}
    for e in estagios:
        if not e.id:
            raise DAGInvalido(f"estágio sem id: {type(e).__name__}")
        if e.id in por_id:
            raise DAGInvalido(f"id duplicado: {e.id}")
        por_id[e.id] = e

    for e in estagios:
        for d in (e.depende_de or []):
            if d not in por_id:
                raise DAGInvalido(
                    f"{e.id} depende de '{d}', que não existe no DAG")

    # Kahn, com ordenação estável pela ordem de declaração
    ordem_declarada = {e.id: i for i, e in enumerate(estagios)}
    prontos = [e for e in estagios if not (e.depende_de or [])]
    ordenados: List[Stage] = []
    vistos: set[str] = set()

    while prontos:
        prontos.sort(key=lambda e: ordem_declarada[e.id])
        atual = prontos.pop(0)
        if atual.id in vistos:
            continue
        ordenados.append(atual)
        vistos.add(atual.id)
        for e in estagios:
            if e.id in vistos or e in prontos:
                continue
            if all(d in vistos for d in (e.depende_de or [])):
                prontos.append(e)

    if len(ordenados) != len(estagios):
        faltando = sorted(set(por_id) - vistos)
        raise DAGInvalido(f"ciclo detectado envolvendo: {faltando}")

    return ordenados


class Runner:
    """
    Executa a sequência. Devolve resultado agregado, nunca lança por falha de
    estágio — o chamador (CLI) decide o exit code.
    """

    def __init__(self, estagios: Sequence[Stage], contexto: PipelineContext):
        self.estagios = ordenar(estagios)
        self.ctx = contexto
        self.resultados: List[ResultadoEstagio] = []

    def rodar(self, ate: Optional[str] = None) -> Dict[str, object]:
        """
        Executa até o estágio `ate` (inclusive), ou até o fim.

        Devolve:
            {"parada": "fim"|"falha"|"pausa",
             "estagio": <onde parou>,
             "resultados": [...],
             "artefatos": {...}}
        """
        for estagio in self.estagios:
            r = estagio.rodar(self.ctx)
            self.resultados.append(r)

            if r.pausado:
                return self._fechar("pausa", estagio.id)
            if not r.ok:
                return self._fechar("falha", estagio.id)
            if ate and estagio.id == ate:
                return self._fechar("fim", estagio.id)

        return self._fechar("fim", self.estagios[-1].id if self.estagios else "")

    def _fechar(self, parada: str, estagio: str) -> Dict[str, object]:
        return {
            "parada": parada,
            "estagio": estagio,
            "resultados": [r.como_dict() for r in self.resultados],
            "artefatos": self.ctx.artefatos,
        }


# ---------------------------------------------------------------------------
# DAG canônico — registro dos estágios que existirem
# ---------------------------------------------------------------------------

# Fonte ÚNICA da ordem do pipeline. Antes havia duas listas literais (aqui e em
# `estagios_faltando`), e elas divergiram em 02/11/2026: ao registrar o S8, o
# DAG deixou de incluí-lo e `estagios_faltando` dizia "faltando: nenhum". Um
# relatório que afirma pipeline completo ao mesmo tempo em que não o executa é
# pior que relatório incompleto. Duas cópias de uma decisão é uma cópia e meia.
ORDEM_CANONICA = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

def dag_canonico(estagios_disponiveis: Dict[str, Type[Stage]]) -> List[Stage]:
    """
    Monta o DAG com os estágios implementados.

    Estágio ausente não quebra: o DAG simplesmente termina onde o último
    implementado termina, e o relatório diz onde parou. Isso é diferente de
    fingir que o pipeline está completo — `estagios_faltando` torna a
    incompletude visível em vez de silenciosa.
    """
    ordem = list(ORDEM_CANONICA)
    instancias: List[Stage] = []
    for sid in ordem:
        if sid in estagios_disponiveis:
            instancias.append(estagios_disponiveis[sid]())
    return instancias


def estagios_faltando(estagios_disponiveis: Dict[str, Type[Stage]]) -> List[str]:
    return [s for s in ORDEM_CANONICA if s not in estagios_disponiveis]


def formatar(res: Dict[str, object]) -> str:
    linhas = ["PIPELINE", ""]
    for r in res["resultados"]:  # type: ignore[index]
        marca = {"ok": "OK  ", "pausa": "PAUSA", "falha": "FALHA"}
        estado = "pausa" if r["pausado"] else ("ok" if r["ok"] else "falha")
        linhas.append(f"  [{marca[estado]}] {r['estagio']}  ({r['duracao_ms']} ms)")
        if r["pausado"]:
            linhas.append(f"         motivo: {r['motivo_pausa']}")
            if r["acao_sugerida"]:
                linhas.append(f"         ação  : {r['acao_sugerida']}")
        for p in r["problemas"]:
            linhas.append(f"         {p}")
    linhas.append("")
    linhas.append(f"PARADA: {res['parada']} em {res['estagio']}")
    return "\n".join(linhas)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Execução vazia — sem estágios implementados ainda.

    Existe para que `make verify` tenha o que chamar e para que a ausência de
    estágio seja EXPLÍCITA no CI, em vez de "comando não encontrado".
    """
    import argparse

    p = argparse.ArgumentParser(description="Executa o pipeline do SJC.")
    p.add_argument("pasta_caso", nargs="?", help="pasta do caso")
    p.add_argument("--dominio", default="", help="id do domínio")
    p.add_argument("--ate", default=None, help="parar após este estágio")
    args = p.parse_args(argv)

    from core.pipeline.stages import ESTAGIOS

    if not args.pasta_caso:
        print("Estágios implementados:", sorted(ESTAGIOS) or "(nenhum)")
        print("Faltando:", estagios_faltando(ESTAGIOS) or "(nenhum)")
        return 0

    ctx = PipelineContext(Path(args.pasta_caso), args.dominio)
    runner = Runner(dag_canonico(ESTAGIOS), ctx)
    res = runner.rodar(ate=args.ate)
    print(formatar(res))
    ctx.gravar_manifesto()

    return {"fim": 0, "pausa": 2, "falha": 1}[str(res["parada"])]


if __name__ == "__main__":
    sys.exit(main())
