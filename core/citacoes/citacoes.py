#!/usr/bin/env python3
"""
citacoes.py — extração e classificação de citações jurídicas em texto de peça.

Este módulo é a peça central do portão de citação. Ele NÃO consulta fonte
externa: extrai e classifica. A consulta é responsabilidade do adaptador.

Por que separar: um extrator que também consulta não pode ser testado sem rede,
e um extrator não testado é a origem do quarto tipo de falha — o falso positivo,
em que o texto não diz o que o extrator entendeu.

Regras que este módulo obedece (todas com origem medida):

1. Extrai TODAS as formas, inclusive não abreviadas ("artigo 1.694" sem "art.").
   Citação não extraída passa sem validar, e o relatório atesta um texto que
   não existe.
2. Distingue quatro tipos de defeito: numero_errado, numero_truncado,
   conteudo_diverso, falso_positivo. Um relatório que só diz "verificado" sem
   dizer o que foi verificado não verificou nada.
3. Numeral ambíguo nunca é resolvido por adivinhação. Se o texto diz "art. 121"
   e 121 também é número de página, a extração registra a ambiguidade.
4. Súmula, tema, julgado e dispositivo são classes diferentes. Misturar produz
   o erro de casar "Súmula 59" com "Súmula 593".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional

# ---------------------------------------------------------------- padrões

# Julgados: RE, REsp, HC, AREsp, AgRg, AgInt, RHC, RMS, MS, ADI, ADPF, ARE, AI, EDcl
_CLASSE = (
    r"(?:AgRg\s+no\s+|AgInt\s+no\s+|EDcl\s+no\s+|Rcl\s+)?"
    r"(?:REsp|RHC|AREsp|RE|HC|RMS|MS|ADI|ADPF|ARE|AI|CC|RHC|AgRg|AgInt|EDcl)\b"
)

# DEFEITO MEDIDO EM 02/11/2026 — numeral cortado em silêncio.
#
# A versão anterior era `(\d{1,3}(?:\.\d{3})*|\d+)`. A alternância avalia da
# esquerda para a direita, e `\d{1,3}` casa com os três primeiros dígitos: o
# ramo `\d+` NUNCA era tentado quando o numeral vinha sem separador de milhar.
# Medido: "RE 1234567" virava `RE 123`, "REsp 1947535/SP" virava `REsp 194`,
# "HC 123456789" virava `HC 123`. A chave canônica saía truncada e o portão
# classificava a citação VERDADEIRA como `numero_errado` — o pior defeito
# possível aqui: o erro é silencioso e acusa o operador pelo próprio bug.
#
# Correção: o numeral é uma sequência única de dígitos COM separador opcional
# de milhar, obrigatoriamente terminando em grupo de 3.
#   `\d{1,3}(?:\.\d{3})+`   -> 1.533.206
#   `|\d+`                    -> 1234567
# Com limite direito `(?![\d.])` para não cortar no meio de um número maior e
# `(?<=\d)` implícito pela própria construção.
RE_JULGADO = re.compile(
    r"\b" + _CLASSE + r"\s*(?:n[º°.]?\s*)?"
    r"(?P<numero>\d{1,3}(?:\.\d{3})*|\d+)(?!\d)"
    r"(?:\s*[/-]\s*(?P<uf>[A-Z]{2}))?",
    re.IGNORECASE,
)

# Súmula: aceita tribunal colado ("593/STJ") ou separado ("593 do STJ").
# Sem isso, a chave canônica sai sem tribunal e "Sumula 59" casa com
# "Sumula 593" — o falso positivo medido em uma das 10 peças furadas.
# O numeral é \d{1,3} sem alternância ambígua: a versão anterior deixava o
# grupo `numero` capturar a sigla do tribunal em "593 do STJ".
RE_SUMULA = re.compile(
    r"\bS[úu]mula(?:\s+Vinculante)?\s*(?:n[º°.]?\s*)?(?P<numero>\d{1,3})"
    r"(?:\s*[/-]\s*(?P<tribunal1>STF|STJ|TST|TSE|STM|TJRJ|[A-Z]{2})\b"
    r"|\s+do\s+(?P<tribunal2>STF|STJ|TST|TSE|STM|TJRJ))?",
    re.IGNORECASE,
)

RE_TEMA = re.compile(
    r"\bTema\s*(?:Repetitivo\s*)?(?:n[º°.]?\s*)?(?P<numero>\d{1,4})"
    r"(?:\s*[/-]\s*(?P<tribunal1>STF|STJ)"
    r"|\s+do\s+(?P<tribunal2>STF|STJ))?",
    re.IGNORECASE,
)

# Dispositivos: "art. 1.694", "artigo 1.694", "art. 217-A", "§ 5º", "inciso VII"
RE_ARTIGO = re.compile(
    r"\b(?:art\.?|artigo)\s*(?P<numero>\d{1,4}(?:\.\d{3})*(?:-[A-Z])?)",
    re.IGNORECASE,
)

# Números de página citados: "fl. 121", "p. 121", "pág. 121".
# Existem para permitir detectar ambiguidade com número de artigo.
RE_PAGINA = re.compile(r"\b(?:fls?\.?|p[áa]g?\.?)\s*(?P<numero>\d{1,4})", re.IGNORECASE)

# Nota de revogação dentro de dispositivo. Uma lei pode revogar um inciso
# interno sem revogar o caput — e ler "revogado" em qualquer parte do trecho
# como "artigo revogado" é o erro que anula homicídio simples.
RE_REVOGACAO = re.compile(r"\(\s*Revogad[oa][^)]*\)", re.IGNORECASE)


@dataclass
class Citacao:
    tipo: str                    # julgado | sumula | tema | dispositivo
    chave: str                   # forma normalizada para casamento
    numero: str
    tribunal: Optional[str] = None
    uf: Optional[str] = None
    posicao: int = 0
    trecho: str = ""
    ambiguidades: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _normalizar_numero(bruto: str) -> str:
    """Preserva o numeral como escrito, sem pontos de milhar. Não 'corrige'."""
    return re.sub(r"\.", "", bruto).strip()


def _chave_julgado(texto_do_match: str, numero: str, uf: Optional[str]) -> str:
    """
    Chave canônica de julgado, preservando o veículo processual.

    O mesmo recurso produz acórdãos diferentes: o de mérito e o que julga o
    agravo interno/regimental. Colapsar os dois na mesma chave perde informação
    real — o agravo pode ter tese diversa, ou simplesmente não ser acórdão de
    mérito. Por isso a chave preserva `AgRg`/`AgInt`/`EDcl` quando presentes.

    O processo-base vai em campo separado (`recurso_base`), que é o que casa com
    a consulta processual e com o número de registro.
    """
    t = texto_do_match.upper()
    veiculo = None
    for v, forma in (("AGRG", "AgRg"), ("AGINT", "AgInt"), ("EDCL", "EDcl")):
        if re.search(r"\b" + v + r"\b", t):
            veiculo = forma
            break

    base = None
    for classe, forma in (("ARESP", "AREsp"), ("RESP", "REsp"),
                          ("RHC", "RHC"), ("HC", "HC"), ("RE", "RE"),
                          ("RMS", "RMS"), ("MS", "MS"), ("ADI", "ADI"),
                          ("ADPF", "ADPF"), ("ARE", "ARE"), ("AI", "AI"),
                          ("CC", "CC")):
        if re.search(r"\b" + classe + r"\b", t):
            base = forma
            break
    if base is None:
        base = "?"

    prefixo = f"{veiculo} " if veiculo else ""
    chave = f"{prefixo}{base} {numero}"
    return chave + (f"/{uf}" if uf else "")


def recurso_base(chave: str) -> str:
    """Extrai o processo-base de uma chave de julgado: 'AgRg no REsp X' -> 'REsp X'."""
    return re.sub(r"^(?:AgRg|AgInt|EDcl)\s+", "", chave)


def extrair(texto: str) -> List[Citacao]:
    """
    Extrai todas as citações do texto, com posição e trecho de contexto.

    A posição permite que o relatório aponte a ocorrência exata, e o trecho de
    contexto (80 caracteres antes e depois) permite conferência humana sem
    reabrir a peça.
    """
    achados: List[Citacao] = []
    numeros_de_pagina = set()
    for m in RE_PAGINA.finditer(texto):
        numeros_de_pagina.add(_normalizar_numero(m.group("numero")))

    def contexto(inicio: int, fim: int) -> str:
        a = max(0, inicio - 80)
        b = min(len(texto), fim + 80)
        return re.sub(r"\s+", " ", texto[a:b]).strip()

    vistos = set()

    for m in RE_JULGADO.finditer(texto):
        numero = _normalizar_numero(m.group("numero"))
        uf = (m.group("uf") or "").upper() or None
        chave = _chave_julgado(m.group(0), numero, uf)
        k = ("julgado", chave, m.start())
        if k in vistos:
            continue
        vistos.add(k)
        c = Citacao(
            tipo="julgado",
            chave=chave,
            numero=numero,
            uf=uf,
            posicao=m.start(),
            trecho=contexto(m.start(), m.end()),
        )
        if not uf:
            c.ambiguidades.append("julgado sem UF: mesma classe e numeral existem em estados diferentes")
        achados.append(c)

    for m in RE_SUMULA.finditer(texto):
        numero = _normalizar_numero(m.group("numero"))
        tribunal = (m.group("tribunal1") or m.group("tribunal2") or "").upper() or None
        chave = f"Sumula {numero}" + (f"/{tribunal}" if tribunal else "")
        k = ("sumula", chave, m.start())
        if k in vistos:
            continue
        vistos.add(k)
        c = Citacao(
            tipo="sumula",
            chave=chave,
            numero=numero,
            tribunal=tribunal,
            posicao=m.start(),
            trecho=contexto(m.start(), m.end()),
        )
        if not tribunal:
            c.ambiguidades.append(
                "súmula sem tribunal: 59/STJ e 593/STJ são coisas distintas, e o "
                "extrator só vê o numeral se o tribunal não estiver no texto"
            )
        achados.append(c)

    for m in RE_TEMA.finditer(texto):
        numero = _normalizar_numero(m.group("numero"))
        tribunal = (m.group("tribunal1") or m.group("tribunal2") or "").upper() or None
        chave = f"Tema {numero}" + (f"/{tribunal}" if tribunal else "")
        k = ("tema", chave, m.start())
        if k in vistos:
            continue
        vistos.add(k)
        achados.append(Citacao(
            tipo="tema", chave=chave, numero=numero, tribunal=tribunal,
            posicao=m.start(), trecho=contexto(m.start(), m.end()),
        ))

    for m in RE_ARTIGO.finditer(texto):
        numero = _normalizar_numero(m.group("numero"))
        k = ("dispositivo", numero, m.start())
        if k in vistos:
            continue
        vistos.add(k)
        c = Citacao(
            tipo="dispositivo", chave=f"art. {numero}", numero=numero,
            posicao=m.start(), trecho=contexto(m.start(), m.end()),
        )
        # Ambiguidade real e medida: "art. 121" onde 121 também é número de página.
        if numero in numeros_de_pagina:
            c.ambiguidades.append(
                f"numeral {numero} também aparece como número de página no texto"
            )
        achados.append(c)

    achados.sort(key=lambda c: c.posicao)
    return achados


def analisar_revogacao(trecho_do_dispositivo: str) -> dict:
    """
    Distingue revogação do dispositivo inteiro de revogação interna.

    Origem: o art. 121 do CP carrega "Revogado pela Lei nº 14.994, de 2024" sobre
    um dispositivo interno. Ler isso como "artigo revogado" é ler homicídio
    simples como inexistente.

    Devolve classificação explícita; nunca infere sem sinal no texto.
    """
    tem_nota = bool(RE_REVOGACAO.search(trecho_do_dispositivo))
    return {
        "tem_nota_revogacao": tem_nota,
        "escopo": "interno_ou_indeterminado" if tem_nota else "sem_nota",
        "aviso": (
            "Nota de revogação encontrada. Verificar na fonte se atinge o caput "
            "ou dispositivo interno antes de declarar o artigo revogado."
            if tem_nota else None
        ),
    }


def classificar_falha(citacao: Citacao, resultado_fonte: dict) -> str:
    """
    Classifica o defeito em um dos quatro tipos medidos.

    ORDEM IMPORTA, e foi medida: consultar `existe` antes de `consulta_executada`
    fazia timeout virar "numero_truncado" — o portão declarava inexistente o que
    apenas não conseguiu verificar. Primeiro a pergunta "eu perguntei?", depois
    "o que voltou?".

    resultado_fonte precisa trazer:
      existe: bool          (aceita `encontrado` como sinônimo — contrato unificado)
      conteudo_confere: bool | None
      chave_casada: str | None
    Opcionais: consulta_executada (bool), erro_codigo (str)
    """
    # 1. A consulta chegou ao servidor? Se não, o veredito é "não sei".
    if resultado_fonte.get("consulta_executada") is False:
        return "nao_avaliado"

    # 2. O documento existe naquele formato de chave?
    #    Aceita os dois vocabulários: `existe` (interno) e `encontrado` (contrato).
    existe = resultado_fonte.get("existe", resultado_fonte.get("encontrado"))
    if existe is False:
        return "numero_truncado"
    if existe is None:
        # Não se sabe se existe. Retém, mas não classifica como inexistente.
        return "nao_avaliado"

    # 3. Existe, mas é outro processo? A chave casada diverge da citada.
    chave_casada = resultado_fonte.get("chave_casada")
    if chave_casada and chave_casada != citacao.chave:
        # Casamento por prefixo de numeral é falso positivo de extração;
        # numeral diferente é número errado. A distinção muda a correção:
        # um exige consertar o extrator, o outro consertar a peça.
        if _eh_prefixo(citacao.numero, chave_casada):
            return "falso_positivo"
        return "numero_errado"

    # 4. O conteúdo confere com o que a peça atribui?
    if resultado_fonte.get("conteudo_confere") is False:
        return "conteudo_diverso"
    if resultado_fonte.get("conteudo_confere") is None:
        return "falso_positivo"

    return "ok"


def _eh_prefixo(numero_citado: str, chave_casada: str) -> bool:
    """
    True quando o numeral citado é prefixo do que a fonte devolveu.

    Origem: "Súmula 593" lida como "Súmula 59". O numeral 59 é prefixo de 593,
    e o defeito está no extrator, não na peça.
    """
    if not numero_citado or not chave_casada:
        return False
    digitos_casada = re.sub(r"\D", "", chave_casada)
    alvo = re.sub(r"\D", "", numero_citado)
    if not alvo or not digitos_casada:
        return False
    if alvo == digitos_casada:
        return False
    return digitos_casada.startswith(alvo) or alvo.startswith(digitos_casada)


def relatorio(citacoes: List[Citacao], avaliacoes: dict) -> dict:
    """
    Monta o relatório com vereditos discretos. Nunca devolve nota 0-100.

    avaliacoes: chave_normalizada -> resultado_fonte
    """
    itens = []
    contagem = {"ok": 0, "numero_errado": 0, "numero_truncado": 0,
                "conteudo_diverso": 0, "falso_positivo": 0, "nao_avaliado": 0}
    for c in citacoes:
        r = avaliacoes.get(f"{c.tipo}:{c.chave}")
        if r is None:
            veredito = "nao_avaliado"
            contagem["nao_avaliado"] += 1
        else:
            veredito = classificar_falha(c, r)
            contagem[veredito] = contagem.get(veredito, 0) + 1
        itens.append({
            "tipo": c.tipo,
            "chave": c.chave,
            "recurso_base": recurso_base(c.chave) if c.tipo == "julgado" else None,
            "posicao": c.posicao,
            "trecho": c.trecho,
            "ambiguidades": c.ambiguidades,
            "veredito": veredito,
        })

    # Retenção: o que não se sabe NÃO libera. `nao_avaliado` (consulta não
    # concluída, incerteza) retém tanto quanto `conteudo_diverso`. A versão
    # anterior liberava a peça em caso de incerteza — o defeito mais grave
    # possível num portão que promete tornar o erro visível antes da assinatura.
    retem = any(
        i["veredito"] in ("numero_truncado", "conteudo_diverso",
                          "numero_errado", "falso_positivo", "nao_avaliado")
        for i in itens
    )
    return {
        "total": len(itens),
        "contagem": contagem,
        "itens": itens,
        "peça_retida": retem,
        "motivo_retencao": (
            "há citação não confirmada ou de conteúdo divergente; a tese que "
            "dependia dela deve ser marcada como descoberta"
            if retem else None
        ),
    }
