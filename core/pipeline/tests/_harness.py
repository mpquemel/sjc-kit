"""
Encanamento comum dos testes do kit.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Nove suítes repetiam, cada uma por cópia, o mesmo trio: a lista `resultados`, a
função `teste(nome, fn)` que captura AssertionError, e um rodapé que conta
aprovados e devolve código de saída. As cópias divergiram: cinco tinham `main()`
com `falhas = 0`, três tinham laço inline, uma contava com `sum()`.

A divergência não era cosmética. Três commits seguidos tiveram teste que falhou
por argumento no lugar errado — e cada vez o conserto foi local, sem que nada
impedisse a próxima cópia de repetir o erro. Com um só encanamento, um defeito no
contador aparece em nove lugares ao mesmo tempo, o que é caro de esconder.

POR QUE NÃO PYTEST
------------------
O kit é publicado para ser lido, e um `pytest` esconderia o que o teste faz
atrás de fixtures e plugins. Aqui o teste é uma função com asserção; rodar é
chamar a função. O que se ganha com o encanamento comum é consistência, não
abstração.

O QUE ESTE MÓDULO NÃO FAZ
------------------------
- Não descobre teste automaticamente. A lista `TESTES` é explícita: teste que
  ninguém listou não roda, e isso é intencional — lista explícita é o que faz
  o revisor perceber quando um teste some.
- Não isola estado entre testes. Cada suíte usa fixture própria; um teste que
  dependa da ordem é defeito do teste, e o encanamento não o esconde.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, List, Tuple

# (aprovado, nome, mensagem_de_erro)
Resultado = Tuple[bool, str, str]

resultados: List[Resultado] = []


def zerar() -> None:
    """Limpa o registro. Chamado por `main` para reexecução em processo único."""
    resultados.clear()


def teste(nome: str, fn: Callable[[], Any]) -> None:
    """
    Executa um teste e registra o resultado.

    AssertionError é falha do teste (o sistema respondeu diferente do esperado).
    Qualquer outra exceção é falha do harness ou quebra inesperada — também
    conta como falha, com o tipo nomeado para que não se confunda com asserção.
    """
    try:
        fn()
        resultados.append((True, nome, ""))
    except AssertionError as e:
        resultados.append((False, nome, str(e)))
    except Exception as e:  # noqa: BLE001
        resultados.append((False, nome, f"{type(e).__name__}: {e}"))


def executar(titulo: str, testes: List[Tuple[str, Callable[[], Any]]],
             verbose: bool = False) -> int:
    """
    Roda a lista de testes e devolve o código de saída.

    Imprime os aprovados só em modo `verbose`: silêncio no caso verde é o que
    torna o vermelho visível no meio de nove suítes.
    """
    print(f"{titulo} — TESTES")
    print("=" * 70)
    for nome, fn in testes:
        teste(nome, fn)

    falhas = [r for r in resultados if not r[0]]
    for ok, nome, msg in resultados:
        if ok and not verbose:
            continue
        marca = "[PASS]" if ok else "[FAIL]"
        print(f"{marca} {nome}")
        if not ok and msg:
            print(f"       {msg}")

    print("-" * 70)
    print(f"{len(resultados) - len(falhas)}/{len(resultados)} aprovados")
    return 1 if falhas else 0


def executar_e_sair(titulo: str, testes: List[Tuple[str, Callable[[], Any]]]
                    ) -> None:
    """Atalho para o bloco `__main__`. Sai com código de erro se algo falhou."""
    sys.exit(executar(titulo, testes))


def exigir(condicao: bool, mensagem: str, detalhe: Any = None) -> None:
    """
    Asserção com detalhe obrigatório na mensagem quando falha.

    Existe porque a mensagem de falha é o produto do teste: um `assert x` nu
    obriga o próximo leitor a reconstruir o estado mental de quem escreveu. Se
    o teste falhar em produção alheia, ninguém tem esse estado mental.
    """
    if condicao:
        return
    texto = mensagem if detalhe is None else f"{mensagem}: {detalhe!r}"
    raise AssertionError(texto)


def resumo_falhas() -> str:
    """Lista as falhas em forma compacta, para relatório de suíte agregada."""
    falhas = [r for r in resultados if not r[0]]
    if not falhas:
        return "0 falhas"
    return "; ".join(f"{nome}: {msg[:80]}" for _, nome, msg in falhas)
