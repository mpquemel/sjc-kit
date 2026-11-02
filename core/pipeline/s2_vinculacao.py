"""
S2 — Vinculação de IDs: árvore × documentos × movimentos.

O QUE ESTE ESTÁGIO FAZ
----------------------
Recebe `arvore.txt` (entrada, não extração), valida o formato, indexa cada ID
com tipo e movimento, e cruza os IDs CITADOS na peça contra o índice. ID citado
que não existe na árvore é ÓRFÃO — e órfão aqui é REPROVAÇÃO, não aviso.

O QUE ELE NÃO FAZ
-----------------
- Não raspa portal. A árvore é entrada: o kit não depende de sistema
  processual específico, e é isso que o torna portável para qualquer
  escritório. Quem quiser outro portal escreve um extrator que produza
  `arvore.txt` neste formato.
- Não adivinha ID ausente. Árvore truncada produz órfãos falsos (ID existe mas
  não está na árvore lida) e, pior, órfãos INVISÍVEIS (ID não citado porque o
  texto não foi lido). Ambos são declarados como risco estrutural, não
  mascarados.
- Não trata "não achei órfão" como "está correto". Se a árvore veio vazia ou o
  texto não cita ID nenhum, o resultado é NAO_AVALIADO com motivo — nunca
  PASSA.

POR QUE ÓRFÃO É REPROVAÇÃO E NÃO AVISO
--------------------------------------
ID órfão significa que a peça se refere a um documento que não está nos autos
como o operador acredita — fls. 88 que não existem, decisão de fls. 32 que veio
em outra página. Protocolada assim, a peça cita prova inexistente. Aviso é
para o que incomoda; reprovação é para o que invalida.

POR QUE O FORMATO É DECLARADO E VERSIONADO
------------------------------------------
Layout de árvore muda. O parser aceita variações conhecidas (com ou sem
parênteses de fls., tipos reconhecidos e declarados) e REGISTRA o que não
entendeu em vez de descartar em silêncio. Árvore malformada não vira árvore
vazia por acidente: vira erro de contrato com a linha culpada.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import Stage

RAIZ = Path(__file__).resolve().parents[2]

# Formato canônico da árvore, versão 1.
#   ID 10 - Certidão de Publicação (fls. 46)
# O ID é numérico; o tipo é o texto antes do parêntese; as fls. podem faltar.
RE_LINHA_ARVORE = re.compile(
    r"^\s*ID\s+(?P<id>\d+)\s*[-–—]\s*(?P<descricao>.+?)\s*$",
    re.IGNORECASE)

RE_FLS = re.compile(
    r"\(\s*fls?\.?\s*(?P<inicio>\d+)\s*(?:/\s*(?P<fim>\d+))?\s*\)",
    re.IGNORECASE)

# IDs citados em texto de peça: "fls. 32", "fl. 88", "ID 7", "doc. 4".
# Só o que o texto REALMENTE escreve: não invento forma de citação.
RE_ID_CITADO = re.compile(
    r"\b(?:ID|doc\.?|documento)\s*(?:n[º°.]?\s*)?(?P<id>\d+)\b"
    r"|\bfls?\.?\s*(?P<fls>\d+)\b",
    re.IGNORECASE)


class S2Vinculacao(Stage):
    """
    Vincula IDs da árvore e reprova peça com ID órfão.

    Entrada: `arvore_path` (de S0) e, opcionalmente, `peca_texto` (de S4) para
    o cruzamento. Saída: índice da árvore, IDs citados, órfãos e veredito.
    """

    id = "S2"
    nome = "vinculacao"
    # Só S0: o runner trata chave definida por dois estágios como defeito de
    # contrato, e S4 republica campos de S0. A peça é buscada diretamente em
    # `ctx.artefatos` — declarar S4 aqui quebraria o DAG por colisão.
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["arvore_path"]  # type: ignore[assignment]
    saida_obriga = ["vinculacao"]  # type: ignore[assignment]

    # Injetável para teste: devolve o texto da árvore sem tocar disco.
    leitor: Optional[Any] = None

    # Árvore sem peça ainda é válida: indexa e fica pronta para o cruzamento.
    # Reprovar por falta de peça seria punir o operador por rodar S2 sozinho.

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import EstagioAbortado, ErroDeContrato

        entrada = ctx.montar_entrada(self)
        arvore_path = entrada.get("arvore_path")
        # Leitura direta, porque S4 não pode estar em `depende_de` (ver acima).
        # Preferência: o que veio pela entrada; senão, o artefato de S4.
        peca_texto = (entrada.get("peca_texto")
                      or (ctx.artefatos.get("S4") or {}).get("peca_texto")
                      or "")

        if not arvore_path:
            raise EstagioAbortado(
                self.id,
                "nenhuma árvore informada: sem `arvore.txt` não há como saber "
                "quais IDs existem",
                "baixe a árvore do sistema processual e informe arvore_path; "
                "sem ela, nenhum cruzamento de ID é possível",
            )

        try:
            bruto = (self.leitor or self._ler)(arvore_path)
        except Exception as e:  # noqa: BLE001
            raise ErroDeContrato(
                self.id, "entrada",
                [f"arvore_path ilegível: {type(e).__name__}: {e}"])

        indice, nao_reconhecidas = self._indexar(bruto)

        if not indice:
            detalhe = (f"{len(nao_reconhecidas)} linha(s) não entendida(s): "
                       + "; ".join(nao_reconhecidas[:3])
                       if nao_reconhecidas
                       else "o arquivo não contém nenhuma linha com 'ID <número>' "
                            "no formato v1")
            raise ErroDeContrato(
                self.id, "entrada",
                [f"árvore sem nenhum ID reconhecível — {detalhe}. Árvore "
                 f"malformada não vira árvore vazia por acidente"])

        # Faixas sobrepostas são defeito da FONTE, não ambiguidade da citação:
        # dois documentos não podem ocupar as mesmas folhas. Declarado para que
        # o operador saiba que um órfão dali pode ser artefato da árvore.
        sobrepostas = self._faixas_sobrepostas(indice)

        citados = self._extrair_citados(peca_texto) if peca_texto.strip() else []
        orfaos, encontrados = self._cruzar(citados, indice)

        veredito, motivo = self._veredito(peca_texto, citados, orfaos, indice)

        return {
            "vinculacao": {
                "arvore": {
                    "arquivo": Path(str(arvore_path)).name,
                    "total_ids": len(indice),
                    "linhas_nao_reconhecidas": nao_reconhecidas,
                    "faixas_sobrepostas": sobrepostas,
                    "ids": indice,
                },
                "peca": {
                    "analisada": bool(peca_texto.strip()),
                    "ids_citados": citados,
                    "ids_encontrados": encontrados,
                    "ids_orfaos": orfaos,
                },
                "veredito": veredito,
                "motivo": motivo,
                "reprova": veredito == "REPROVA",
                "pode_protocolar": veredito == "PASSA",
                "aviso_estrutural": (
                    "Árvore truncada produz órfão falso (ID existe, não está na "
                    "árvore lida) e órfão invisível (ID não citado porque o "
                    "texto não foi lido). O relatório declara o risco; não o "
                    "resolve por conta própria."
                ),
            }
        }

    # ------------------------------------------------------------------
    # Leitura e índice
    # ------------------------------------------------------------------

    def _ler(self, caminho: Any) -> str:
        return Path(str(caminho)).read_text(encoding="utf-8")

    def _indexar(self, bruto: str) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        """
        Indexa a árvore por ID. Devolve (índice, linhas não reconhecidas).

        Linha com "ID" e número e ilegível quanto ao resto é registrada como não
        reconhecida, NÃO descartada: cabeçalho e rodapé do portal são comuns, e
        sumir com eles sem dizer esconde que o parser ficou cego.
        """
        indice: Dict[str, Dict[str, Any]] = {}
        nao_reconhecidas: List[str] = []

        for numero_linha, linha in enumerate(bruto.splitlines(), 1):
            if not linha.strip():
                continue
            m = RE_LINHA_ARVORE.match(linha)
            if not m:
                # Só reporta linha que PARECE um ID. Cabeçalhos ("Processo: 000…")
                # não são erro de parser e poluiriam o relatório.
                if re.search(r"\bID\b", linha, re.IGNORECASE):
                    nao_reconhecidas.append(f"linha {numero_linha}: {linha.strip()[:90]}")
                continue

            id_arvore = m.group("id")
            descricao = m.group("descricao").strip()

            fls_m = RE_FLS.search(descricao)
            fls_inicio = fls_m.group("inicio") if fls_m else None
            fls_fim = fls_m.group("fim") if fls_m else None
            tipo = RE_FLS.sub("", descricao).strip(" -–—")

            if id_arvore in indice:
                # ID duplicado é defeito da árvore, não do parser: dois
                # documentos com o mesmo ID deixam o cruzamento ambíguo.
                nao_reconhecidas.append(
                    f"linha {numero_linha}: ID {id_arvore} duplicado")
                continue

            # FAIXA INVERTIDA, medido em 02/11/2026: "ID 4 - Documento
            # (fls. 20/10)" era indexado como 20/10 sem uma palavra de aviso.
            # Faixa invertida NUNCA contém número algum, então toda citação a
            # esse documento vira órfão falso — ou, pior, o documento fica
            # invisível para o cruzamento. Defeito da árvore, não da peça: tem de
            # ser reportado, não acomodado.
            if fls_inicio and fls_fim and int(fls_fim) < int(fls_inicio):
                nao_reconhecidas.append(
                    f"linha {numero_linha}: ID {id_arvore} tem faixa de fls. "
                    f"invertida ({fls_inicio}/{fls_fim})")
                continue

            indice[id_arvore] = {
                "id": id_arvore,
                "tipo": tipo,
                "fls_inicio": fls_inicio,
                "fls_fim": fls_fim or fls_inicio,
                "descricao": descricao,
            }

        return indice, nao_reconhecidas

    def _faixas_sobrepostas(self, indice: Dict[str, Dict[str, Any]]
                            ) -> List[Dict[str, Any]]:
        """
        Pares de documentos que ocupam as mesmas folhas.

        Dois documentos não podem começar na mesma página. Quando acontece, a
        árvore está inconsistente ou alguém juntou documento depois da
        numeração — e o cruzamento por fls. fica ambíguo por culpa da fonte.
        """
        com_faixa = [v for v in indice.values()
                     if v["fls_inicio"] and v["fls_fim"]]
        achados: List[Dict[str, Any]] = []
        for i, a in enumerate(com_faixa):
            for b in com_faixa[i + 1:]:
                if (int(a["fls_inicio"]) <= int(b["fls_fim"])
                        and int(b["fls_inicio"]) <= int(a["fls_fim"])):
                    achados.append({
                        "ids": [a["id"], b["id"]],
                        "faixas": [f"{a['fls_inicio']}/{a['fls_fim']}",
                                   f"{b['fls_inicio']}/{b['fls_fim']}"],
                    })
        return achados

    # ------------------------------------------------------------------
    # Cruzamento
    # ------------------------------------------------------------------

    def _extrair_citados(self, texto: str) -> List[Dict[str, Any]]:
        """IDs citados no texto da peça, na ordem em que aparecem."""
        citados: List[Dict[str, Any]] = []
        vistos: set[str] = set()
        for m in RE_ID_CITADO.finditer(texto):
            bruto = m.group("id") or m.group("fls")
            chave = f"ID {bruto}" if m.group("id") else f"fls. {bruto}"
            if chave in vistos:
                continue
            vistos.add(chave)
            citados.append({
                "forma": chave,
                "numero": bruto,
                "criterio": "id" if m.group("id") else "fls",
                "posicao": m.start(),
            })
        return citados

    def _cruzar(self, citados: List[Dict[str, Any]],
                indice: Dict[str, Dict[str, Any]]
                ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Casa cada citação com a árvore, em ordem de confiabilidade:

          1. ID explícito   — a peça diz "ID 7"; casa direto.
          2. fls. — casa quando o número cai DENTRO de uma faixa da árvore.
          3. ambíguo        — fls. cai em mais de uma faixa: declara ambiguidade
                              em vez de escolher a primeira.

        Nenhum casamento é inferido por semelhança de texto. Adivinhar que
        "decisão de alimentos" é o ID 7 pelo nome seria o defeito que o projeto
        combate, e ele produziria órfão invisível.
        """
        encontrados: List[Dict[str, Any]] = []
        orfaos: List[Dict[str, Any]] = []

        for c in citados:
            if c["criterio"] == "id":
                alvo = indice.get(c["numero"])
                if alvo:
                    encontrados.append({**c, "casou_com": alvo["id"],
                                        "tipo": alvo["tipo"]})
                else:
                    orfaos.append({**c, "motivo": "ID não existe na árvore"})
                continue

            # critério fls.: procura faixas que contenham o número
            atingidos = [
                v for v in indice.values()
                if v["fls_inicio"] and v["fls_fim"]
                and int(v["fls_inicio"]) <= int(c["numero"]) <= int(v["fls_fim"])
            ]
            if not atingidos:
                orfaos.append({**c, "motivo": "fls. não cai em nenhuma faixa da árvore"})
            elif len(atingidos) > 1:
                orfaos.append({
                    **c,
                    "motivo": "fls. cai em mais de uma faixa da árvore",
                    "candidatos": [a["id"] for a in atingidos],
                })
            else:
                a = atingidos[0]
                encontrados.append({**c, "casou_com": a["id"], "tipo": a["tipo"]})

        return orfaos, encontrados

    # ------------------------------------------------------------------
    # Veredito
    # ------------------------------------------------------------------

    def _veredito(self, peca_texto: str, citados: List[Dict[str, Any]],
                  orfaos: List[Dict[str, Any]],
                  indice: Dict[str, Dict[str, Any]]) -> tuple[str, str]:
        """
        Órfão reprova. Nenhuma citação de ID é NAO_AVALIADO, não PASSA — o
        mesmo critério de vacuidade do S5: "não achei" não é "não há".
        """
        if orfaos:
            formas = ", ".join(o["forma"] for o in orfaos[:5])
            return ("REPROVA",
                    f"{len(orfaos)} ID(s) citado(s) sem correspondência na "
                    f"árvore: {formas}")

        if not peca_texto.strip():
            return ("NAO_AVALIADO",
                    "árvore indexada, mas nenhuma peça foi analisada: o "
                    "cruzamento de IDs não ocorreu")

        if not citados:
            return ("NAO_AVALIADO",
                    "a peça não cita ID nem fls.; nada foi cruzado. Ausência "
                    "de citação não é prova de vinculação correta")

        return ("PASSA",
                f"{len(citados)} ID(s) citado(s), todos vinculados à árvore "
                f"de {len(indice)} documento(s)")
