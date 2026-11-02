"""
S4 — Redação: preenche o template do domínio, bloco por bloco.

O QUE ESTE ESTÁGIO FAZ
----------------------
Lê o template da peça decidida em S3, descobre os blocos `[OBRIGATÓRIA]` e
`[OPCIONAL]`, pede ao provedor de redação o texto de cada bloco e monta a peça
em Markdown — com rastro de qual tese e qual autoridade sustentam cada bloco.

O QUE ELE NÃO FAZ
-----------------
- Não escolhe modelo. O modelo é decisão do escritório, declarada no
  `dominio.yaml` com motivo. Sem declaração, este estágio PAUSA.
- Não inventa citação. Se o provedor devolver uma citação que não está na
  lista de autoridades do bloco, o estágio REGISTRA como não sustentada e
  marca a peça como precisa_humano. Ele não apaga — apagar esconderia o
  problema; ele não deixa passar — passar seria o defeito de origem do projeto.
- Não aprova a peça. Aprovação é S6 mais o operador.

POR QUE O MODELO É PAUSA E NÃO DEFAULT
---------------------------------------
Linha 204 da especificação: "Modelo por tipo de peça declarado no domínio, com
motivo registrado". O requisito é o RASTRO, não o valor. Um default inventado
seria uma decisão tomada em nome de quem paga a conta, e o rastro apontaria
para uma escolha que ninguém fez. Em processo produzido com apoio de IA, o
rastro de escolha é defesa: "usamos o que estava à mão" não sustenta.

POR QUE O PROVEDOR É INJETÁVEL
------------------------------
Teste que depende de rede não roda em CI; teste que não roda não protege. O
provedor entra por atributo de classe, como o `verificador` de S5. Os testes
usam um provedor falso determinístico: zero custo, zero alucinação, zero rede.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from .stage import Stage

RAIZ = Path(__file__).resolve().parents[2]

TIPOS_DE_BLOCO = re.compile(
    r"^\[(OBRIGAT[ÓO]RIA|OPCIONAL)\]\s*$", re.IGNORECASE)
MARCADOR_VAZIO = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

# DEFEITO MEDIDO em 02/11/2026: comentário de template usado `# motivo: ...`
# era lido como TÍTULO de nível 1 dentro de um bloco de nível 3. Como 1 <= 3, o
# consumo do bloco parava na primeira linha de justificativa e o marcador
# `{{preliminares}}` ficava órfão na peça — 3 de 4 blocos eram montados.
#
# A causa de fundo: formato de comentário ambíguo com o conteúdo. A regra aqui
# é que um comentário nunca pode ser confundido com sintaxe do documento.
# Aceita a forma `# motivo:` (já em uso nos templates) e a forma `<!-- -->`, mas
# só quando a linha é RECONHECÍVEL como justificativa: `#` seguido de palavra
# conhecida de comentário, não de texto jurídico qualquer.
COMENTARIO_TEMPLATE = re.compile(
    r"^#\s*(motivo|nota|coment[aá]rio|obs|justificativa)\b", re.IGNORECASE)


def _eh_titulo(linha: str) -> bool:
    """
    Título de verdade é `#` de Markdown, NÃO comentário `# motivo: ...`.

    Separar isso é o que impede o comentário de justificativa de ser lido como
    cabeçalho — e de quebrar o recorte de bloco que depende de níveis.
    """
    t = linha.lstrip()
    if not t.startswith("#"):
        return False
    if COMENTARIO_TEMPLATE.match(t):
        return False
    return True


class S4Redacao(Stage):
    """
    Redige a peça a partir do template, bloco por bloco.

    Entrada: `estrategia` (de S3) e, opcionalmente, `autoridades` por bloco.
    Saída: `peca_texto` (Markdown) e o rastro por bloco.
    """

    id = "S4"
    nome = "redacao"
    depende_de = ["S3"]
    entrada_obriga = ["caso_id", "estrategia"]  # type: ignore[assignment]
    # S4 NÃO republica `caso_id`: ele já chega de S0 a todos os estágios, e
    # repetir produz colisão de chave em qualquer consumidor que dependa de S3
    # e S4 ao mesmo tempo. O runner trata colisão como defeito de contrato —
    # corretamente — e a origem aqui era a republicação desnecessária.
    saida_obriga = ["peca_texto"]  # type: ignore[assignment]

    # Injetável para teste: (prompt, contexto) -> texto.
    provedor: Optional[Callable[[str, Dict[str, Any]], str]] = None

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import EstagioAbortado

        entrada = ctx.montar_entrada(self)
        dominio = entrada.get("dominio_id") or ctx.dominio_id
        estrategia = entrada.get("estrategia") or {}
        peca = str(estrategia.get("peca_cabivel") or "")

        if not peca:
            raise EstagioAbortado(
                self.id,
                "a estratégia não declara peca_cabivel: não há o que redigir",
                "rode S3; sem peça decidida, S4 escreveria no vazio",
            )

        config = self._carregar_dominio(dominio)
        modelo = self._modelo_decidido(config, peca)
        if modelo is None:
            raise EstagioAbortado(
                self.id,
                f"modelo de redação não decidido para '{peca}' em '{dominio}'",
                "declare modelos.por_peca com provider, modelo, motivo e "
                "verificado_em no dominio.yaml; o rastro de escolha é "
                "requisito (especificação, linha 204), não formalidade",
            )

        if self.provedor is None:
            raise EstagioAbortado(
                self.id,
                "nenhum provedor de redação configurado",
                "injete um provedor (S4Redacao.provedor) ou configure o "
                "provedor real; sem ele não há como redigir",
            )

        template = self._carregar_template(dominio, peca)
        blocos = self._dividir_blocos(template)
        if not blocos:
            raise EstagioAbortado(
                self.id,
                f"template '{peca}.md' não tem bloco [OBRIGATÓRIA]",
                "template sem bloco obrigatório não permite conferência em S6",
            )

        autoridades = entrada.get("autoridades") or {}
        preenchidos: List[Dict[str, Any]] = []
        for bloco in blocos:
            prompt = self._montar_prompt(dominio, peca, bloco, estrategia)
            contexto = {
                "dominio": dominio,
                "peca": peca,
                "titulo": bloco["titulo"],
                "exigencia": bloco["exigencia"],
                "estrategia": estrategia,
                "autoridades": autoridades.get(bloco["chave"]) or [],
            }
            texto = self.provedor(prompt, contexto)
            preenchidos.append({**bloco, "texto": texto})

        peca_texto = self._montar_peca(template, preenchidos)
        rastro = self._rastro(preenchidos, autoridades, modelo)

        return {
            "peca_texto": peca_texto,
            "redacao": {
                "peca": peca,
                "dominio": dominio,
                "modelo": modelo,
                "blocos": rastro["blocos"],
                "citacoes_nao_sustentadas": rastro["nao_sustentadas"],
                "precisa_humano": bool(rastro["nao_sustentadas"]),
            },
        }

    # ------------------------------------------------------------------
    # Configuração do domínio
    # ------------------------------------------------------------------

    def _carregar_dominio(self, dominio: str) -> Dict[str, Any]:
        from .stage import ErroDeContrato

        if yaml is None:
            raise ErroDeContrato(
                self.id, "entrada", ["PyYAML ausente: não há como ler dominio.yaml"])
        caminho = RAIZ / "dominios" / dominio / "dominio.yaml"
        if not caminho.is_file():
            raise ErroDeContrato(
                self.id, "entrada", [f"dominio.yaml ausente em dominios/{dominio}/"])
        return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}

    def _modelo_decidido(self, config: Dict[str, Any],
                         peca: str) -> Optional[Dict[str, Any]]:
        """
        Devolve a decisão de modelo para a peça, ou None.

        Aceita `modelos.por_peca[peca]` (preferido) e cai para
        `modelos.default` se este estiver COMPLETO. Campo com "a preencher" não
        é decisão — é a ausência dela escrita de forma educada.
        """
        modelos = config.get("modelos") or {}
        candidatos = []
        por_peca = (modelos.get("por_peca") or {})
        if isinstance(por_peca, dict) and peca in por_peca:
            candidatos.append(por_peca[peca])
        if modelos.get("default"):
            candidatos.append(modelos["default"])

        for c in candidatos:
            if not isinstance(c, dict):
                continue
            campos = {k: str(c.get(k) or "").strip()
                      for k in ("provider", "modelo", "motivo")}
            if all(v and "a preencher" not in v.lower() for v in campos.values()):
                return {**campos, "verificado_em": c.get("verificado_em")}
        return None

    # ------------------------------------------------------------------
    # Template
    # ------------------------------------------------------------------

    def _carregar_template(self, dominio: str, peca: str) -> str:
        from .stage import ErroDeContrato

        caminho = RAIZ / "dominios" / dominio / "templates" / f"{peca}.md"
        if not caminho.is_file():
            raise ErroDeContrato(
                self.id, "entrada",
                [f"template '{peca}.md' ausente em dominios/{dominio}/templates/"])
        return caminho.read_text(encoding="utf-8")

    def _dividir_blocos(self, template: str) -> List[Dict[str, Any]]:
        """
        Divide o template em seções (# / ## / ###) e associa a cada uma o
        marcador de exigência que aparece logo abaixo.

        Só devolve seções COM marcador. Texto fora de bloco (cabeçalho,
        endereçamento) vai para a peça como está: ele é forma, não conteúdo.
        """
        linhas = template.splitlines()
        blocos: List[Dict[str, Any]] = []
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            if not _eh_titulo(linha):
                i += 1
                continue
            titulo = linha.lstrip("#").strip()
            j = i + 1
            exigencia = None
            while j < len(linhas) and not _eh_titulo(linhas[j]):
                m = TIPOS_DE_BLOCO.match(linhas[j].strip())
                if m:
                    exigencia = m.group(1).upper()
                    if exigencia.startswith("OBRIGAT"):
                        exigencia = "OBRIGATORIA"
                    break
                j += 1
            if exigencia:
                chave = re.sub(r"[^a-z0-9]+", "_", titulo.lower()).strip("_")
                blocos.append({
                    "titulo": titulo,
                    "chave": chave,
                    "exigencia": exigencia,
                    "linha_inicio": i,
                })
            # DEFEITO MEDIDO em 02/11/2026: `i = j + 1 if exigencia else i + 1`.
            # Em seção SEM marcador, `j` avançou até o PRÓXIMO título; voltar a
            # `i + 1` reprocessava a mesma linha como título e recomeçava a busca
            # a partir dali — o bloco `[OPCIONAL]` de apelacao.md era pulado em
            # silêncio (3 de 4 blocos eram encontrados). Pior: o template saía
            # com `{{preliminares}}` no lugar do texto, e `_montar_peca` não
            # substitui bloco que não está na lista. O avanço correto é sempre
            # posterior ao título corrente, com ou sem marcador.
            i = max(j, i + 1)
        return blocos

    def _montar_prompt(self, dominio: str, peca: str, bloco: Dict[str, Any],
                       estrategia: Dict[str, Any]) -> str:
        """
        Prompt de bloco. Declara o que NÃO fazer — a maior parte dos defeitos
        de texto jurídico gerado vem de instrução que só pede, não proíbe.
        """
        return (
            f"Domínio: {dominio}. Peça: {peca}.\n"
            f"Bloco: {bloco['titulo']} (exigência: {bloco['exigencia']}).\n"
            f"Gatilho decidido pelo catálogo: {estrategia.get('gatilho')}.\n"
            f"Polo do operador: {estrategia.get('polo_atuacao')}.\n\n"
            "Escreva APENAS o corpo deste bloco, em português jurídico.\n"
            "NÃO invente número de acórdão, súmula, tema, artigo ou data.\n"
            "NÃO cite autoridade que não esteja na lista fornecida.\n"
            "NÃO assine, NÃO datе, NÃO repita o título do bloco.\n"
        )

    def _montar_peca(self, template: str, blocos: List[Dict[str, Any]]) -> str:
        """
        Substitui o corpo de cada bloco pelo texto redigido, preservando tudo
        o mais: cabeçalho, títulos, marcadores de posição e assinatura.
        """
        linhas = template.splitlines()
        por_titulo = {b["titulo"]: b["texto"] for b in blocos}
        saida: List[str] = []
        i = 0
        while i < len(linhas):
            linha = linhas[i]
            saida.append(linha)
            if not _eh_titulo(linha):
                i += 1
                continue
            titulo = linha.lstrip("#").strip()
            if titulo not in por_titulo:
                i += 1
                continue
            nivel = len(linha) - len(linha.lstrip("#"))
            # consome o corpo original até o próximo título de nível <=
            i += 1
            while i < len(linhas):
                seg = linhas[i]
                if _eh_titulo(seg):
                    n2 = len(seg) - len(seg.lstrip("#"))
                    if n2 <= nivel:
                        break
                i += 1
            saida.append("")
            saida.append(por_titulo[titulo].strip())
            saida.append("")
        return "\n".join(saida).strip() + "\n"

    # ------------------------------------------------------------------
    # Rastro
    # ------------------------------------------------------------------

    def _rastro(self, blocos: List[Dict[str, Any]],
                autoridades: Dict[str, Any],
                modelo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra, por bloco, o que foi escrito e quais autoridades o sustentam.
        Citação presente no texto e ausente na lista é NÃO SUSTENTADA — o
        defeito de origem do projeto, agora visível no rastro.
        """
        nao_sustentadas: List[Dict[str, Any]] = []
        rastro_blocos = []
        for b in blocos:
            lista = autoridades.get(b["chave"]) or []
            permitidas = {
                str(a.get("chave") if isinstance(a, dict) else a)
                for a in lista
            }
            citadas = {m.group(1) for m in MARCADOR_VAZIO.finditer(b["texto"])}
            # Marcadores {{...}} não são citações: são campos não preenchidos.
            cit_doc = re.findall(
                r"\b(?:REsp|RE|HC|AREsp|AgRg|S[úu]mula|Tema)\s*(?:n[º°.]?\s*)?\d[\d.]*",
                b["texto"])
            orfas = [c for c in cit_doc if c not in permitidas]
            if orfas:
                nao_sustentadas.append({"bloco": b["chave"], "citacoes": orfas})
            rastro_blocos.append({
                "bloco": b["chave"],
                "titulo": b["titulo"],
                "exigencia": b["exigencia"],
                "caracteres": len(b["texto"]),
                "autoridades_declaradas": sorted(permitidas),
                "citacoes_no_texto": cit_doc,
                "campos_nao_preenchidos": sorted(citadas),
            })
        return {"blocos": rastro_blocos, "nao_sustentadas": nao_sustentadas}
