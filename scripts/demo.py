#!/usr/bin/env python3
"""
Demo do kit: roda o pipeline no caso sintético com provedor determinístico.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O `S4Redacao.provedor` é injetado por atributo de classe: em produção é o
cliente do modelo que o escritório paga; nos testes é um falso determinístico.
Sem injeção, o S4 pausa em "nenhum provedor configurado" — o que é correto e
proposital.

A demo precisa de um provedor para provar o encanamento até S8. Este arquivo é
esse provedor, e ele NÃO redige: devolve texto estrutural que declara a si
mesmo. É o oposto de gerar peça jurídica falsa — o objetivo é testar o
transporte de dados, não o conteúdo.

O QUE ELE NÃO FAZ
-----------------
- Não chama rede, não custa nada, não depende de chave de API.
- Não inventa citação: o S5 vai reter a peça por vacuidade, e isso é o
  resultado esperado da demo, não uma falha.
- Não assina nem protocola: S8 entrega pré-assinatura.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def provedor_de_demonstracao(prompt: str, contexto: dict, *args) -> str:
    """
    Texto estrutural, declaradamente não jurídico.

    Lê `contexto["titulo"]` para que o bloco a que o texto pertence seja
    identificável na saída — assim quem lê o docx gerado sabe que está vendo
    demo, não peça.
    """
    # A assinatura real é (prompt, contexto); o contexto é o dicionário que o
    # S4 monta por bloco. Aceitar string também evita quebrar se a assinatura
    # do provedor mudar: o texto de demo não depende do conteúdo.
    if isinstance(contexto, dict):
        titulo = str(contexto.get("titulo") or "bloco")
    else:
        titulo = "bloco"
    return (
        f"[DEMONSTRAÇÃO — bloco {titulo}]\n\n"
        "Este parágrafo foi produzido por um provedor determinístico, sem "
        "modelo de linguagem e sem consulta a fonte externa. Ele existe para "
        "provar que o pipeline transporta texto do template até o pacote de "
        "entrega, preservando proveniência.\n\n"
        "Não há citação de jurisprudência, doutrina, súmula ou dispositivo "
        "nesta demo porque o provedor não tem como conferir nenhuma delas. "
        "Peça sem citação extraível é retida pelo estágio de verificação, e "
        "o pacote de entrega sai bloqueado e dizendo o motivo.\n\n"
        "A substituição por um modelo real é uma linha de configuração no "
        "dominio.yaml, sob responsabilidade e custo do escritório."
    )


def main(argv=None) -> int:
    import argparse

    from core.pipeline.runner import Runner, dag_canonico, formatar
    from core.pipeline.s4_redacao import S4Redacao
    from core.pipeline.stage import PipelineContext
    from core.pipeline.stages import ESTAGIOS

    p = argparse.ArgumentParser(description="Demo do SJC com provedor sintético.")
    p.add_argument("pasta_caso", help="pasta do caso")
    p.add_argument("--dominio", default="", help="id do domínio")
    p.add_argument("--ate", default=None, help="parar após este estágio")
    args = p.parse_args(argv)

    pasta = Path(args.pasta_caso)
    if not pasta.is_dir():
        print(f"[FALTA] pasta do caso não existe: {pasta}")
        return 2

    S4Redacao.provedor = provedor_de_demonstracao

    ctx = PipelineContext(pasta, args.dominio)
    entradas = ctx.carregar_entrada_do_caso()
    if args.dominio and "dominio_id" not in entradas:
        entradas["dominio_id"] = args.dominio
    if entradas:
        ctx.artefatos["S0"] = entradas

    res = Runner(dag_canonico(ESTAGIOS), ctx).rodar(ate=args.ate)
    print(formatar(res))
    ctx.gravar_manifesto()

    print()
    print("NOTA DA DEMO")
    print("  provedor determinístico, sem modelo de linguagem e sem rede.")
    print("  o texto dos blocos é estrutural e declaradamente não jurídico.")
    print("  peça sem citação extraível é retida por S5 — resultado esperado.")
    return {"fim": 0, "pausa": 2, "falha": 1}[str(res["parada"])]


if __name__ == "__main__":
    sys.exit(main())
