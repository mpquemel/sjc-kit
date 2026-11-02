"""
Registro dos estágios implementados.

Este arquivo é o único lugar que sabe QUAIS estágios existem. O runner pergunta
aqui. Para adicionar um estágio: escreva a classe, registre neste mapa. Nada
mais muda.

Estado atual em 02/11/2026: S0 (entrada), S1 (conversão), S2 (vinculação), S3
(estratégia), S4 (redação), S5 (citações), S6 (gates) e S7 (gate de cinco
camadas) e S8 (entrega) implementados. O DAG está completo: S0 -> S8. — `estagios_faltando()`
os lista, para que a incompletude seja visível em vez de silenciosa.
"""

from __future__ import annotations

from typing import Dict, Type

from .s1_conversao import S1Conversao
from .s2_vinculacao import S2Vinculacao
from .s3_estrategia import S3Estrategia
from .s4_redacao import S4Redacao
from .s5_citacoes import S5Citacoes
from .s6_gates import S6Gates
from .s7_gate_cinco_camadas import S7GateCincoCamadas
from .s8_entrega import S8Entrega
from .stage import Stage

# Estágios concretos entram aqui conforme forem implementados.
ESTAGIOS: Dict[str, Type[Stage]] = {}

# ---------------------------------------------------------------------------
# S0 — Entrada. Implementado porque é o único estágio que não exige domínio:
#        recebe caminhos e valida invariantes de arquivo.
# ---------------------------------------------------------------------------


class S0Entrada(Stage):
    id = "S0"
    nome = "entrada"
    depende_de = []  # type: ignore[assignment]
    entrada_obriga = ["caso_id", "pdf_path", "dominio_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "pdf_path", "arvore_path", "dominio_id",
                    "perfil_atuacao", "criado_em", "criado_por"]  # type: ignore[assignment]

    def _invariantes_entrada(self, entrada: dict) -> list[str]:
        problemas: list[str] = []
        cid = entrada.get("caso_id")
        if isinstance(cid, str) and not _cnj_valido(cid):
            problemas.append(
                f"caso_id não é CNJ válido (20 dígitos, DV conferido): {cid!r}")

        pdf = entrada.get("pdf_path")
        if isinstance(pdf, str):
            from pathlib import Path
            p = Path(pdf)
            if not p.is_file():
                problemas.append(f"pdf_path não existe: {pdf}")
            else:
                try:
                    magic = p.read_bytes()[:5]
                    if magic != b"%PDF-":
                        problemas.append(
                            f"pdf_path não tem magic bytes de PDF: {magic!r}")
                except OSError as e:
                    problemas.append(f"pdf_path ilegível: {e}")
        return problemas

    def executar(self, ctx) -> dict:
        e = ctx.montar_entrada(self)
        return {
            "caso_id": e["caso_id"],
            "pdf_path": e["pdf_path"],
            "arvore_path": e.get("arvore_path"),
            "dominio_id": e["dominio_id"],
            # polo NUNCA inferido (§4.6): vai adiante como veio, inclusive None
            "perfil_atuacao": e.get("perfil_atuacao"),
            "criado_em": e.get("criado_em"),
            "criado_por": e.get("criado_por"),
        }


def _cnj_valido(cnj: str) -> bool:
    """
    Valida o número CNJ: 20 dígitos, com DV mód. 97 conferido.

    A regra do CNJ (Res. 65/2008) é ISO 7064 mod 97-10: o número inteiro,
    NNMMMMAAJJJJTTTTOOOODD (sem o DV), seguido do DV de 2 dígitos, deve dar
    resto 1 na divisão por 97.
    """
    digitos = "".join(ch for ch in cnj if ch.isdigit())
    if len(digitos) != 20:
        return False
    try:
        corpo, dv = int(digitos[:18]), int(digitos[18:])
    except ValueError:
        return False
    return (corpo * 100 + dv) % 97 == 1


ESTAGIOS["S0"] = S0Entrada
ESTAGIOS["S1"] = S1Conversao
ESTAGIOS["S2"] = S2Vinculacao
ESTAGIOS["S3"] = S3Estrategia
ESTAGIOS["S4"] = S4Redacao
ESTAGIOS["S5"] = S5Citacoes
ESTAGIOS["S6"] = S6Gates
ESTAGIOS["S7"] = S7GateCincoCamadas
ESTAGIOS["S8"] = S8Entrega
