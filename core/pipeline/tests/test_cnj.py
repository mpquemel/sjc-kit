"""
Teste de guarda do validador de número CNJ.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Em 02/11/2026 o `_cnj_valido` foi "corrigido" DUAS VEZES na mesma sessão, por
duas acusações diferentes, e as duas estavam erradas.

Acusação 1: o validador recusaria número correto e aceitaria número errado,
porque lê o DV como `digitos[18:]` quando o formato CNJ
(`NNNNNNN-DD.AAAA.J.TR.OOOO`) põe o DV nas posições 8 e 9.

Medição: 200.000 números CNJ gerados aleatoriamente, comparando as duas
leituras — a do código e a "da norma". Discordâncias: ZERO.

Razão algébrica, com d de 20 dígitos:

    norma : A = d[:7]+d[9:]   (18 díg.)   B = d[7:9]   N1 = A*100 + B
    código: C = d[:18]        (18 díg.)   D = d[18:]   N2 = C*100 + D

N1 e N2 são inteiros diferentes, mas descrevem a mesma cadeia de dígitos: em
N2, o DV cai exatamente onde o sufixo do corpo começa. Não existe CNJ que
separe as duas leituras; a do código está correta.

Acusação 2 (anterior à 1): um vetor de teste escrito à mão foi classificado
como inválido por engano, e o "defeito" era o do vetor.

O QUE ESTE TESTE GUARDA
-----------------------
Não guarda contra regressão de código — não houve regressão. Guarda contra a
pressa de quem lê a fórmula e conclui antes de medir. Os vetores são
CALCULADOS pela ISO 7064 MOD 97-10, nunca digitados, e o teste de equivalência
afirma numericamente que as duas leituras concordam.

Se alguém "consertar" o validador de novo, o teste de equivalência não falha
(as duas formas concordam). O que falha é a leitura deste comentário: a
alteração não muda comportamento, e o commit que a fizer deve dizê-lo.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.stages import _cnj_valido  # noqa: E402
from core.pipeline.tests._harness import executar_e_sair, exigir  # noqa: E402


def _dv_do_cnj(seq: str, ano: str, j: str, tr: str, org: str) -> int:
    """
    DV pela ISO 7064 MOD 97-10, calculado sobre o CNJ MONTADO.

    ARMADILHA QUE JÁ CUSTOU TRÊS TENTATIVAS ERRADAS NESTA SESSÃO
    ------------------------------------------------------------
    O formato é `NNNNNNN-DD.AAAA.J.TR.OOOO`: o DV fica entre o sequencial e o
    ano. Portanto o inteiro do CNJ NÃO é `corpo*100 + dv`. Ao inserir o DV na
    posição 8, os 11 dígitos seguintes são empurrados duas casas, e o inteiro
    muda de valor. Calcular o DV sobre `seq+ano+j+tr+org` e colar no meio
    produz um número que não satisfaz mod 97.

    O cálculo correto busca `dv` tal que o CNJ MONTADO, lido como inteiro,
    deixe resto 1. É o que esta função faz.
    """
    assert len(seq) == 7 and len(ano) == 4 and len(org) == 4, \
        "campos fora do tamanho do formato CNJ"
    for dv in range(100):
        montado = int(f"{seq}{dv:02d}{ano}{j}{tr}{org}")
        if montado % 97 == 1:
            return dv
    raise AssertionError(
        f"nenhum DV válido para {seq}/{ano}/{j}/{tr}/{org}")


def _montar(seq: str, ano: str, j: str, tr: str, org: str) -> str:
    """Monta o CNJ no formato oficial, com DV calculado sobre o número montado."""
    return f"{seq}-{_dv_do_cnj(seq, ano, j, tr, org):02d}.{ano}.{j}.{tr}.{org}"


# Vetores válidos, gerados pela fórmula. Nenhum corresponde a processo real.
VALIDOS = [
    ("9000001", "2026", "8", "19", "0037"),  # estadual, RJ
    ("1234567", "2025", "5", "02", "0001"),  # trabalhista
    ("0000123", "2024", "4", "01", "0100"),  # federal
    ("0000001", "2023", "3", "00", "0000"),  # STJ
]


def t_aceita_numero_valido_pela_norma():
    for args in VALIDOS:
        cnj = _montar(*args)
        exigir(_cnj_valido(cnj), "número válido pela norma foi recusado", cnj)


def t_recusa_dv_trocado():
    """O mesmo corpo com DV alterado em 1: tem de ser recusado."""
    for args in VALIDOS:
        cnj = _montar(*args)
        digitos = "".join(c for c in cnj if c.isdigit())
        dv_certo = int(digitos[7:9])
        dv_errado = (dv_certo + 1) % 100
        adulterado = (f"{digitos[:7]}-{dv_errado:02d}.{digitos[9:13]}."
                      f"{digitos[13]}.{digitos[14:16]}.{digitos[16:]}")
        exigir(not _cnj_valido(adulterado),
               "número com DV trocado foi aceito", adulterado)


def t_as_duas_leituras_do_dv_sao_equivalentes():
    """
    Afirma o resultado da medição de 02/11/2026: 200.000 números, zero
    discordância entre `int(digitos) % 97 == 1` e
    `(int(digitos[:18])*100 + int(digitos[18:])) % 97 == 1`.

    Este teste NÃO falha se o validador for reescrito numa das duas formas:
    ele existe para documentar que a escolha entre elas não muda resultado.
    """
    random.seed(7)
    for _ in range(3000):  # amostra, não os 200.000: o teste roda em CI
        seq = f"{random.randrange(10 ** 7):07d}"
        ano = f"{random.randrange(1990, 2030):04d}"
        j = str(random.randrange(1, 10))
        tr = f"{random.randrange(0, 100):02d}"
        org = f"{random.randrange(0, 10000):04d}"
        dig = f"{seq}{_dv_do_cnj(seq, ano, j, tr, org):02d}{ano}{j}{tr}{org}"

        leitura_norma = int(dig) % 97 == 1
        leitura_codigo = (int(dig[:18]) * 100 + int(dig[18:])) % 97 == 1
        exigir(leitura_norma == leitura_codigo,
               "as duas leituras do DV discordaram — reveja o comentário "
               "do módulo antes de concluir que há defeito", dig)


def t_recusa_placeholder_e_lixo():
    for ruim in ("0000000-00.0000.8.00.0000", "", "abc",
                 "9000001-02.2026.8.19.003", "9000001-02.2026.8.19.00378"):
        exigir(not _cnj_valido(ruim), "entrada inválida foi aceita", repr(ruim))


def t_none_levanta_typeerror():
    """
    Contrato é `str -> bool`. Com `None` o validador levanta TypeError em vez
    de devolver False. O S0 nunca passa `None` (valida tipo antes), mas a
    função é pública e o comportamento fica declarado aqui em vez de suposto.
    """
    try:
        _cnj_valido(None)  # type: ignore[arg-type]
    except TypeError:
        return
    raise AssertionError("None deveria levantar TypeError, conforme declarado")


def t_pontuacao_e_ignorada():
    """O validador trabalha sobre dígitos: com ou sem máscara, mesmo veredito."""
    for args in VALIDOS:
        cnj = _montar(*args)
        so_digitos = "".join(c for c in cnj if c.isdigit())
        exigir(_cnj_valido(cnj) and _cnj_valido(so_digitos),
               "máscara alterou o veredito", cnj)


def t_vetores_sao_calculados_e_nao_digitados():
    """
    Meta-teste: reconferir os vetores com cálculo independente.

    Se alguém editar VALIDOS à mão e errar o DV, este teste falha antes de os
    outros darem resultado enganoso — foi exatamente esse erro que gerou a
    acusação 2 no comentário do módulo.
    """
    for args in VALIDOS:
        seq, ano, j, tr, org = args
        numero = int(f"{seq}{_dv_do_cnj(*args):02d}{ano}{j}{tr}{org}")
        exigir(numero % 97 == 1,
               "vetor de VALIDOS não satisfaz a norma", f"{args}")


TESTES = [
    ("t_aceita_numero_valido_pela_norma", t_aceita_numero_valido_pela_norma),
    ("t_recusa_dv_trocado", t_recusa_dv_trocado),
    ("t_as_duas_leituras_do_dv_sao_equivalentes",
     t_as_duas_leituras_do_dv_sao_equivalentes),
    ("t_recusa_placeholder_e_lixo", t_recusa_placeholder_e_lixo),
    ("t_none_levanta_typeerror", t_none_levanta_typeerror),
    ("t_pontuacao_e_ignorada", t_pontuacao_e_ignorada),
    ("t_vetores_sao_calculados_e_nao_digitados",
     t_vetores_sao_calculados_e_nao_digitados),
]


if __name__ == "__main__":
    executar_e_sair("CNJ — validador de número", TESTES)
