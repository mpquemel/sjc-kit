"""
S7 — Gate de cinco camadas.

O QUE ESTE ESTÁGIO FAZ
----------------------
Antes de a peça sair, cinco camadas de conferência, com naturezas diferentes e
tratamento diferente para cada uma:

  G1  legal      — a tese cabe no ordenamento?      NÃO AUTOMATIZÁVEL
  G2  factual    — o que a peça afirma está nos autos?  NÃO AUTOMATIZÁVEL
  G3  forma      — formato, marcadores, seções       AUTOMATIZADO, reprova
  G4  transcrição— citação literal confere na linha?  AUTOMATIZADO quando há
  G5  auditoria  — leitura crítica do juiz e do adversário  DISCRETO, com motivo

O QUE ELE NÃO FAZ
-----------------
- Não decide G1 nem G2. O sistema LISTA o que conferir e exige declaração
  explícita do operador. Sem declaração, reprova — não "passa em branco".
- Não dá nota. Veredito é discreto e nunca é média: o pior veredito manda.
- Não reescreve a peça. Gate que conserta a si mesmo não é gate.
- Não assina, não protocola, não empacota. Isso é S8. O ato é do advogado.

POR QUE G1 E G2 NÃO SÃO AUTOMATIZÁVEIS — E O QUE SE FAZ COM ISSO
----------------------------------------------------------------
Um programa pode achar "art. 1.694" no texto; não pode decidir se o pedido de
alimentos cabe no caso concreto nem se o valor afirmado corresponde à prova dos
autos. Fingir que pode é o defeito mais caro do produto: um gate verde em tese
errada é pior que gate nenhum, porque transfere ao sistema uma responsabilidade
que ele não tem.

Então a saída é: listar os pontos, exigir declaração nominal, e registrar QUEM
declarou e QUANDO. Declaração não é formalidade — é a prova de que houve leitura.
Ausência de declaração reprova, porque "ninguém declarou" e "tudo certo" são
fatos diferentes que um relatório mal-feito confunde.

POR QUE G3 REPROVA DE VERDADE
-----------------------------
G3 é onde a máquina é melhor que o humano cansado: marcador residual de
template, seção obrigatória fora de ordem, bloco vazio, campo não preenchido.
Nada disso é julgamento — é contagem. Reprovar aqui custa nada e evita o
constrangimento de protocolar peça com "{{preliminares}}" no corpo.

POR QUE G4 SÓ AGE QUANDO HÁ TRANSCRIÇÃO
---------------------------------------
Peça que cita transcrição de audiência e não confere a linha é risco de
falsidade ideológica. Peça que não cita transcrição não tem o que conferir — e
`NAO_APLICAVEL` é diferente de `PASSA`. O relatório distingue.

POR QUE A REVISÃO EXIGE MODELO DIFERENTE
-----------------------------------------
Medido (ESPECIFICACAO-PRODUTO.md §9): um modelo aprovou 11 de 11 processos que
outro reprovou em 5 de 8. Modelo que revisa o próprio texto tende a concordar
consigo. O estágio RECUSA rodar G5 quando o revisor declarado é o gerador — e
recusar é o comportamento correto, não um detalhe a contornar.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import Stage

# ---------------------------------------------------------------------------
# G3 — camada de forma: reprova de verdade, sem heurística de julgamento
# ---------------------------------------------------------------------------

# Marcadores residuais de template. Cada um é defeito objetivo: o operador
# veria isso ao abrir o .docx.
RE_MARCADOR = re.compile(r"\{\{[^}]*\}\}|\{\{[^}]*$|\[OPCIONAL\]|\[EXIGENCIA\]",
                         re.MULTILINE)

# Campo que o operador deixa em branco com educação — "a preencher" é ausência
# escrita de forma polida e não pode passar como conteúdo.
RE_A_PREENCHER = re.compile(
    r"\b(a\s+preencher|preencher|xxxx+|\.\.\.\s*$|\?\?\?)",
    re.IGNORECASE)

RE_SECAO = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# Seções que a estrutura de peça recursal exige, na ordem em que aparecem.
SECOES_OBRIGATORIAS = [
    ("tempestividade", re.compile(r"tempestividade", re.IGNORECASE)),
    ("razoes", re.compile(r"(raz[oõ]es|fundamenta|mérito)", re.IGNORECASE)),
    ("pedidos", re.compile(r"pedidos?", re.IGNORECASE)),
]


class S7GateCincoCamadas(Stage):
    """
    Gate de cinco camadas antes da entrega.

    Entrada: peça (S4), gates de forma (S6), estratégia (S3) e as declarações
    do operador (G1/G2). Saída: `gate_cinco_camadas` com veredito por camada e
    veredito final, que é o PIOR entre as camadas aplicáveis.
    """

    id = "S7"
    nome = "gate-cinco-camadas"
    depende_de = ["S3", "S6"]  # type: ignore[assignment]
    # peca_texto vem de S4, que não pode estar em depende_de (republica campos
    # de S0 e o runner trata colisão como defeito de contrato). Lido direto.
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "gate_cinco_camadas"]  # type: ignore[assignment]

    # Injetável para teste: revisor de G5.
    revisor: Optional[Any] = None

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import EstagioAbortado

        entrada = ctx.montar_entrada(self)
        peca_texto = ((ctx.artefatos.get("S4") or {}).get("peca_texto")
                      or entrada.get("peca_texto") or "")
        if not str(peca_texto).strip():
            raise EstagioAbortado(
                self.id,
                "peça vazia: não há o que auditar",
                "gere a peça (S4) antes do gate de cinco camadas",
            )

        gates = entrada.get("gates") or {}
        estrategia = entrada.get("estrategia") or {}
        # Declarações de G1/G2. `montar_entrada` só entrega chaves dos estágios
        # em `depende_de`; nenhum deles produz `declaracoes`. Fonte única
        # declarada: artefato próprio `declaracoes_operador`, escrito pelo
        # operador (CLI/UI) antes do S7. Ler de S3 seria inventar precedência.
        declaracoes = (ctx.artefatos.get("declaracoes_operador")
                       or entrada.get("declaracoes") or {})

        camadas: List[Dict[str, Any]] = [
            self._g1(declaracoes, estrategia),
            self._g2(declaracoes),
            self._g3(peca_texto, estrategia),
            self._g4(peca_texto),
            self._g5(peca_texto, estrategia, gates),
        ]

        # S6 é pré-requisito do S7, não uma sexta camada: se a bateria de regras
        # de forma do domínio reprovou, a peça não sai por aqui tampouco.
        veredito_s6 = gates.get("veredito")
        if veredito_s6 in ("REPROVA",):
            camadas.append({
                "id": "S6",
                "nome": "regras-de-forma-do-dominio",
                "automatizada": True,
                "veredito": "REPROVA",
                "motivo": f"bateria de S6 reprovou: {gates.get('reprovas')}",
            })

        final = self._pior(camadas)
        # Empate de gravidade é comum (G2 factual e G5 auditoria valem o mesmo).
        # Declarar TODAS as camadas que chegaram no pior veredito evita a
        # ilusão de que só uma bloqueou a peça.
        piores = [c["id"] for c in camadas if c["veredito"] == final]

        return {
            "caso_id": entrada["caso_id"],
            "gate_cinco_camadas": {
                "camadas": camadas,
                "veredito": final,
                "pode_protocolar": final == "PASSA",
                "bloqueado": final in ("REPROVA", "NAO_AVALIADO"),
                "pior_camada": piores[0] if piores else None,
                "camadas_no_pior_veredito": piores,
                "declaracoes_registradas": {
                    k: v for k, v in declaracoes.items() if v
                },
                "nao_avaliaveis": [c["id"] for c in camadas
                                   if not c.get("automatizada")],
                "aviso": (
                    "G1 e G2 dependem de declaração do operador. O sistema "
                    "registra a declaração, não a substitui: a responsabilidade "
                    "pelo conteúdo jurídico e factual é de quem assina."
                ),
            },
        }

    # ------------------------------------------------------------------
    # G1 / G2 — não automatizáveis: exigem declaração explícita
    # ------------------------------------------------------------------

    def _g1(self, declaracoes: Dict[str, Any], estrategia: Dict[str, Any]
            ) -> Dict[str, Any]:
        d = declaracoes.get("g1_legal") or {}
        if d.get("declarado_por") and d.get("em"):
            return {
                "id": "G1", "nome": "legal", "automatizada": False,
                "veredito": "PASSA",
                "motivo": f"declarado por {d['declarado_por']} em {d['em']}",
                "declaracao": d.get("texto"),
            }
        return {
            "id": "G1", "nome": "legal", "automatizada": False,
            "veredito": "REPROVA",
            "motivo": ("sem declaração explícita de conferência legal. "
                       "Ausência de declaração não é ausência de problema"),
            "conferir": [
                f"tese: {estrategia.get('tese') or '(não decidida)'}",
                f"peça cabível: {estrategia.get('peca_cabivel') or '(não decidida)'}",
                "prazo e cabimento conferidos na lei vigente",
                "fundamento normativo citado existe e sustenta o pedido",
            ],
        }

    def _g2(self, declaracoes: Dict[str, Any]) -> Dict[str, Any]:
        d = declaracoes.get("g2_factual") or {}
        if d.get("declarado_por") and d.get("em"):
            return {
                "id": "G2", "nome": "factual", "automatizada": False,
                "veredito": "PASSA",
                "motivo": f"declarado por {d['declarado_por']} em {d['em']}",
                "declaracao": d.get("texto"),
            }
        return {
            "id": "G2", "nome": "factual", "automatizada": False,
            "veredito": "REPROVA",
            "motivo": ("sem declaração explícita de conferência factual. "
                       "Fato afirmado sem prova nos autos é invenção"),
            "conferir": [
                "cada fato afirmado tem página nos autos",
                "valores, datas e nomes conferem com o documento citado",
                "nenhuma afirmação veio de descrição de imagem (§ regra-mãe)",
            ],
        }

    # ------------------------------------------------------------------
    # G3 — forma: automatizado, reprova de verdade
    # ------------------------------------------------------------------

    def _g3(self, peca_texto: str, estrategia: Dict[str, Any]) -> Dict[str, Any]:
        defeitos: List[Dict[str, str]] = []

        for m in RE_MARCADOR.finditer(peca_texto):
            linha = peca_texto.count("\n", 0, m.start()) + 1
            defeitos.append({
                "tipo": "marcador_residual",
                "linha": str(linha),
                "achado": m.group(0)[:40],
            })

        for i, linha_txt in enumerate(peca_texto.splitlines(), 1):
            if RE_A_PREENCHER.search(linha_txt) and not RE_SECAO.match(linha_txt):
                defeitos.append({
                    "tipo": "campo_a_preencher",
                    "linha": str(i),
                    "achado": linha_txt.strip()[:60],
                })

        # Seções obrigatórias presentes E na ordem — ordem é requisito
        # estrutural, não preferência estética: leitor de tela navega por
        # cabeçalho e um pedido antes das razões confunde a leitura.
        secoes = [m.group(2) for m in RE_SECAO.finditer(peca_texto)]
        posicoes: List[tuple[str, int]] = []
        faltando: List[str] = []
        for nome, padrao in SECOES_OBRIGATORIAS:
            pos = next((i for i, s in enumerate(secoes) if padrao.search(s)), None)
            if pos is None:
                faltando.append(nome)
            else:
                posicoes.append((nome, pos))
        if faltando:
            defeitos.append({
                "tipo": "secao_ausente",
                "linha": "-",
                "achado": ", ".join(faltando),
            })
        if len(posicoes) > 1 and [p for _, p in posicoes] != sorted(p for _, p in posicoes):
            defeitos.append({
                "tipo": "secao_fora_de_ordem",
                "linha": "-",
                "achado": " > ".join(n for n, _ in posicoes),
            })

        # NOTA (02/11/2026): tentei verificar aqui se a peça traz "Processo nº
        # <número>" e RECUSEI a checagem. Motivo: o cabeçalho da peça é campo
        # de S4 (`identificador_externo`), não de forma. G3 tem de ser
        # reproduzível fora do pipeline — um revisor humano olhando a peça não
        # sabe se o número faltou porque o operador apagou ou porque o domínio
        # não declara esse campo. Misturar os dois faria G3 reprovar peça
        # correta de domínio que não usa identificador. A checagem de campo
        # obrigatório do template é de S4/S6, onde a fonte do dado é conhecida.

        # Peça curta demais para ser peça: 20 palavras não sustentam pedido.
        palavras = len(peca_texto.split())
        if palavras < 20 and not defeitos:
            defeitos.append({
                "tipo": "peca_curta",
                "linha": "-",
                "achado": f"{palavras} palavra(s)",
            })

        if defeitos:
            return {
                "id": "G3", "nome": "forma", "automatizada": True,
                "veredito": "REPROVA",
                "motivo": f"{len(defeitos)} defeito(s) de forma",
                "defeitos": defeitos,
            }
        return {
            "id": "G3", "nome": "forma", "automatizada": True,
            "veredito": "PASSA",
            "motivo": ("sem marcador residual, sem campo a preencher, seções "
                       "obrigatórias presentes e na ordem"),
            "defeitos": [],
        }

    # ------------------------------------------------------------------
    # G4 — transcrição: só quando há
    # ------------------------------------------------------------------

    def _g4(self, peca_texto: str) -> Dict[str, Any]:
        # NOTA (02/11/2026): tentei tratar TODA citação entre aspas como
        # transcrição e RECUSEI. Qualquer frase entre aspas virava G4
        # NAO_AVALIADO e bloqueava a peça — citação doutrinária e transcrição de
        # audiência têm o mesmo formato de aspas. G4 só deve agir quando a peça
        # DECLARA transcrição (termo de audiência, depoimento, fala gravada):
        # sem essa marca, o veredito é NAO_APLICAVEL, não NAO_AVALIADO.
        marca = re.search(r"(transcri[çc][ãa]o|termo\s+de\s+(audi[êe]ncia|depoimento)"
                          r"|depoimento\s+de|audi[êe]ncia\s+de\s+instru[çc][ãa]o)",
                          peca_texto, re.IGNORECASE)
        citacoes = re.findall(r"[\"“]([^\"”]{15,})[\"”]", peca_texto) if marca else []
        if not citacoes:
            return {
                "id": "G4", "nome": "transcricao", "automatizada": True,
                "veredito": "NAO_APLICAVEL",
                "motivo": "a peça não cita transcrição literal",
            }
        # Conferir linha exata exige a transcrição de origem, que não está no
        # pipeline. Declarar isso é obrigatório: fingir conferência seria pior
        # que não conferir.
        return {
            "id": "G4", "nome": "transcricao", "automatizada": True,
            "veredito": "NAO_AVALIADO",
            "motivo": (f"{len(citacoes)} citação(ões) literal(is) na peça, mas a "
                       f"transcrição de origem não está disponível no pipeline: "
                       f"conferência na linha exata não foi executada"),
            "citacoes": [c[:60] for c in citacoes[:5]],
        }

    # ------------------------------------------------------------------
    # G5 — auditoria: veredito discreto com motivo por item
    # ------------------------------------------------------------------

    def _g5(self, peca_texto: str, estrategia: Dict[str, Any],
            gates: Dict[str, Any]) -> Dict[str, Any]:
        if self.revisor is None:
            return {
                "id": "G5", "nome": "auditoria", "automatizada": True,
                "veredito": "NAO_AVALIADO",
                "motivo": ("nenhum revisor configurado. G5 exige modelo "
                           "DIFERENTE do que gerou a peça; sem revisor "
                           "declarado, a auditoria não foi executada"),
            }

        modelo = estrategia.get("modelo")
        gerador = modelo.get("modelo") if isinstance(modelo, dict) else None
        revisor_decl = getattr(self.revisor, "modelo", None)

        # Recusa rodar revisor igual ao gerador: medido que modelo que revisa o
        # próprio texto tende a concordar consigo (1 aprovou 11/11 que outro
        # reprovou em 5/8). Recusar é o comportamento correto.
        if gerador and revisor_decl and gerador == revisor_decl:
            return {
                "id": "G5", "nome": "auditoria", "automatizada": True,
                "veredito": "REPROVA",
                "motivo": (f"revisor e gerador são o mesmo modelo "
                           f"({gerador}): revisão sem independência"),
            }

        try:
            laudo = self.revisor.auditar(peca_texto=peca_texto,
                                         estrategia=estrategia,
                                         gates=gates)
        except Exception as e:  # noqa: BLE001
            return {
                "id": "G5", "nome": "auditoria", "automatizada": True,
                "veredito": "NAO_AVALIADO",
                "motivo": f"revisor falhou: {type(e).__name__}: {e}",
            }

        veredito = str(laudo.get("veredito", "")).upper()
        if veredito not in ("PASSA", "ADVERTE", "REPROVA"):
            return {
                "id": "G5", "nome": "auditoria", "automatizada": True,
                "veredito": "NAO_AVALIADO",
                "motivo": (f"revisor devolveu veredito não reconhecido: "
                           f"{laudo.get('veredito')!r}"),
            }

        return {
            "id": "G5", "nome": "auditoria", "automatizada": True,
            "veredito": veredito,
            "motivo": laudo.get("motivo") or "sem motivo declarado pelo revisor",
            "itens": laudo.get("itens") or [],
            "revisor": revisor_decl,
        }

    # ------------------------------------------------------------------
    # Veredito final
    # ------------------------------------------------------------------

    @staticmethod
    def _pior(camadas: List[Dict[str, Any]]) -> str:
        """
        Pior veredito entre as camadas aplicáveis. Nunca média.

        NAO_AVALIADO pesa como gravidade alta: camada que não rodou não é
        camada aprovada. Só NAO_APLICAVEL fica de fora — ali não havia o que
        conferir, e isso está declarado.
        """
        gravidade = {"PASSA": 0, "NAO_APLICAVEL": -1,
                     "NAO_AVALIADO": 2, "ADVERTE": 2, "REPROVA": 3}
        aplicaveis = [c for c in camadas if c["veredito"] != "NAO_APLICAVEL"]
        if not aplicaveis:
            return "NAO_AVALIADO"
        return max((c["veredito"] for c in aplicaveis),
                   key=lambda v: gravidade.get(v, 3))
