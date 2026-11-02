"""
S6 — Gates: aplica as regras do domínio contra a peça escrita.

O QUE ESTE ESTÁGIO FAZ
----------------------
Lê `gates/regras.yaml` do domínio, lê a peça em Markdown e devolve, para cada
regra, um veredito. Nada é corrigido aqui: o estágio APONTA. Quem conserta é o
operador (ou S4, numa volta).

O QUE ELE NÃO FAZ
-----------------
- Não reescreve a peça. Gate que conserta a si mesmo não é gate.
- Não dá nota (0-100). Veredito é discreto: PASSA / ADVERTE / REPROVA /
  NAO_AVALIADO. Escala contínua é convite a "tirou 82, tá bom" — e 82 numa peça
  que cita prazo não conferido é 82 mentiroso.
- Não inventa condição que a regra não declarou. Se a regra não é verificável
  por programa, o veredito é NAO_AVALIADO com o motivo — nunca PASSA.

POR QUE NAO_AVALIADO NÃO É PASSA
---------------------------------
Uma regra com `condicao` em prosa que o código não sabe ler produziria PASSA em
tudo. Isso é pior que não ter a regra: o operador lê uma bateria verde e não
sabe que metade dela nunca foi executada. Medido no catálogo de família em
02/11/2026: 6 regras, 2 verificáveis por programa sem heurística de texto.
As outras 4 declaram NAO_AVALIADO e dizem por quê.

POR QUE O VEREDITO FINAL É O PIOR, E NÃO A MÉDIA
------------------------------------------------
Peça com 5 gates aprovados e 1 reprovado é uma peça REPROVADA. Média é o
raciocínio que deixa protocolar recurso sem razões de reforma porque o resto
estava bonito.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - bootstrap exige PyYAML
    yaml = None  # type: ignore[assignment]

from .stage import Stage

RAIZ = Path(__file__).resolve().parents[2]

# Ordem de gravidade. O veredito da peça é o pior veredito entre as regras
# aplicáveis — nunca a média, nunca o consenso.
GRAVIDADE = {"PASSA": 0, "NAO_AVALIADO": 1, "ADVERTE": 2, "REPROVA": 3}

APELACAO = "apelacao"
AGRAVO = "agravo_instrumento"


def _sem_acento(texto: str) -> str:
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ",
        "aaaaaeeeeiiiiooooouuuucnAAAAAEEEEIIIIOOOOOUUUUCN")
    return texto.translate(tabela)


def _normalizar_id(texto: str) -> str:
    """Ids de peça chegam ora com hífen, ora com sublinhado."""
    return _sem_acento(str(texto or "")).lower().replace("-", "_").strip()


def _paragrafos(bloco: str) -> List[str]:
    """
    Parágrafos de um bloco. Parágrafo vazio, marcador de template e título
    (#) não contam: contar linha em branco transformaria bloco vazio em
    "bloco com 3 parágrafos".
    """
    uteis = []
    for bruto in re.split(r"\n\s*\n", bloco):
        t = bruto.strip()
        if not t:
            continue
        if t.startswith("#"):
            continue
        if t.upper() in ("[OBRIGATÓRIA]", "[OBRIGATORIA]", "[OPCIONAL]"):
            continue
        uteis.append(t)
    return uteis


class S6Gates(Stage):
    """
    Aplica as regras de gate do domínio contra uma peça em Markdown.

    Entrada: a peça (texto) e a estratégia decidida em S3. Sem a estratégia,
    os campos de contexto (prazo conferido, peça cabível) não existem e o
    gate estaria adivinhando.
    """

    id = "S6"
    nome = "gates"
    depende_de = ["S3", "S4"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id", "estrategia", "peca_texto"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "gates"]  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def executar(self, ctx) -> Dict[str, Any]:
        entrada = ctx.montar_entrada(self)
        dominio = entrada.get("dominio_id") or ctx.dominio_id
        estrategia = entrada.get("estrategia") or {}
        peca_texto = entrada.get("peca_texto") or ""

        if not str(peca_texto).strip():
            from .stage import EstagioAbortado
            raise EstagioAbortado(
                self.id,
                "peça vazia: não há o que conferir",
                "gere a peça (S4) ou informe peca_texto; gate sobre texto vazio "
                "daria PASSA em toda regra que não depende de conteúdo",
            )

        peca = _normalizar_id(estrategia.get("peca_cabivel"))
        regras = self._carregar_regras(dominio)

        avaliadas: List[Dict[str, Any]] = []
        for regra in regras:
            avaliadas.append(self._avaliar(regra, peca, peca_texto, estrategia))

        aplicaveis = [a for a in avaliadas if a["aplicavel"]]
        veredito_peca = self._veredito(regras, avaliadas)

        return {
            "caso_id": entrada["caso_id"],
            "gates": {
                "peca": peca,
                "dominio": dominio,
                "veredito": veredito_peca,
                "regras_avaliadas": avaliadas,
                "aplicaveis": len(aplicaveis),
                "nao_avaliadas": [a["id"] for a in aplicaveis
                                  if a["veredito"] == "NAO_AVALIADO"],
                "reprovas": [a["id"] for a in aplicaveis
                             if a["veredito"] == "REPROVA"],
                "advertencias": [a["id"] for a in aplicaveis
                                 if a["veredito"] == "ADVERTE"],
                "pode_protocolar": veredito_peca in ("PASSA",),
                "precisa_humano": True,  # gate nunca substitui o operador
            },
        }

    # ------------------------------------------------------------------
    # Leitura das regras
    # ------------------------------------------------------------------

    def _carregar_regras(self, dominio: str) -> List[Dict[str, Any]]:
        from .stage import ErroDeContrato

        if yaml is None:
            raise ErroDeContrato(
                self.id, "entrada",
                ["PyYAML ausente: não há como ler gates/regras.yaml"])

        caminho = RAIZ / "dominios" / dominio / "gates" / "regras.yaml"
        if not caminho.is_file():
            raise ErroDeContrato(
                self.id, "entrada",
                [f"gates/regras.yaml ausente em dominios/{dominio}/"])

        dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
        regras = dados.get("regras") or []
        if not regras:
            raise ErroDeContrato(
                self.id, "entrada",
                [f"dominios/{dominio}/gates/regras.yaml não declara regras: "
                 "bateria vazia daria veredito PASSA sem conferir nada"])
        return regras

    # ------------------------------------------------------------------
    # Avaliação de uma regra
    # ------------------------------------------------------------------

    def _aplicavel(self, aplica_a: Any, peca: str) -> bool:
        if aplica_a in ("*", ["*"], None):
            return True
        alvos = aplica_a if isinstance(aplica_a, list) else [aplica_a]
        alvos_norm = {_normalizar_id(a) for a in alvos}
        return peca in alvos_norm

    def _avaliar(self, regra: Dict[str, Any], peca: str, texto: str,
                 estrategia: Dict[str, Any]) -> Dict[str, Any]:
        avaliador = self._AVALIADORES.get(str(regra.get("id") or ""))
        base = {
            "id": regra.get("id"),
            "veredito_regra": regra.get("veredito"),
            "fundamento": regra.get("fundamento"),
            "aplicavel": self._aplicavel(regra.get("aplica_a"), peca),
        }

        if not base["aplicavel"]:
            base.update(veredito="NAO_APLICAVEL", motivo="peça fora do escopo da regra",
                        evidencia=[])
            return base

        if avaliador is None:
            # Não invento checagem: declaro que esta regra não é executável
            # por programa nesta versão. Veredito NAO_AVALIADO, nunca PASSA.
            base.update(
                veredito="NAO_AVALIADO",
                motivo="regra declarada em prosa e sem avaliador implementado "
                       "neste estágio",
                evidencia=[],
                acao_sugerida=regra.get("mensagem", "").strip(),
            )
            return base

        veredito, motivo, evidencia = avaliador(self, texto, estrategia, regra)
        base.update(veredito=veredito, motivo=motivo, evidencia=evidencia,
                    acao_sugerida=regra.get("mensagem", "").strip())
        return base

    # ------------------------------------------------------------------
    # Avaliadores. Um por regra executável.
    # ------------------------------------------------------------------

    def _bloco(self, texto: str, marcador: str) -> Optional[str]:
        """
        Recorta o conteúdo abaixo de um título (###/##) até o próximo título de
        mesmo nível ou superior. Devolve None se o título não existe.
        """
        linhas = texto.splitlines()
        alvo = _sem_acento(marcador).upper()
        for i, linha in enumerate(linhas):
            if not linha.lstrip().startswith("#"):
                continue
            if alvo not in _sem_acento(linha).upper():
                continue
            nivel = len(linha) - len(linha.lstrip("#"))
            corpo: List[str] = []
            for seg in linhas[i + 1:]:
                if seg.lstrip().startswith("#"):
                    n2 = len(seg) - len(seg.lstrip("#"))
                    if n2 <= nivel:
                        break
                corpo.append(seg)
            return "\n".join(corpo)
        return None

    def _apelacao_sem_razoes(self, texto, estrategia, regra) -> Tuple[str, str, List[str]]:
        """
        Apelação precisa de bloco 'RAZÕES PARA REFORMA' com ao menos 3
        parágrafos. Menos que isso é impugnação genérica com título.
        """
        bloco = self._bloco(texto, "RAZÕES PARA REFORMA")
        if bloco is None:
            return ("REPROVA",
                    "a peça não tem bloco 'RAZÕES PARA REFORMA'",
                    ["título ausente"])
        paras = _paragrafos(bloco)
        if len(paras) < 3:
            return ("REPROVA",
                    f"bloco presente com {len(paras)} parágrafo(s); o mínimo é 3",
                    [f"parágrafos: {len(paras)}"])
        return ("PASSA", f"{len(paras)} parágrafos de razão", [])

    def _impugnacao_especifica(self, texto, estrategia, regra) -> Tuple[str, str, List[str]]:
        """
        Recurso tem de referenciar ao menos um fundamento da decisão recorrida.

        Critério executável: a peça menciona dispositivo (artigo, inciso,
        parágrafo) OU transcreve trecho entre aspas de mais de 40 caracteres.
        Não é o ideal — o ideal é comparar com o texto da decisão —, mas é
        honesto: sem o texto da decisão no artefato, comparar seria inventar.
        """
        dispositivos = re.findall(r"art\.?\s*\d+|artigo\s+\d+", texto, re.IGNORECASE)
        citacoes = re.findall(r"[\"“]([^\"”]{40,})[\"”]", texto)
        if dispositivos or citacoes:
            return ("PASSA",
                    f"{len(dispositivos)} dispositivo(s) e {len(citacoes)} "
                    f"transcrição(ões) da decisão",
                    [f"dispositivos: {dispositivos[:3]}"])
        return ("ADVERTE",
                "a peça não referencia dispositivo nem transcreve trecho da "
                "decisão recorrida",
                ["sem citação do que foi decidido"])

    def _prazo_conferir(self, texto, estrategia, regra) -> Tuple[str, str, List[str]]:
        """
        Base de prazo com marca de conferência reprova a peça inteira.

        Lê a marca do artefato de S3, não do texto: o texto da peça é o lugar
        onde a marca foi LIMPA de propósito. Fonte é o catálogo.
        """
        prazo = estrategia.get("prazo_estimado") or {}
        # S3 publica a base em `base_legal`; a marca de conferência vive no
        # campo `conferido`. A primeira versão lia `base`, chave inexistente,
        # e a regra saía NAO_AVALIADO em 100% dos casos — o gate que devia
        # reprovar prazo não conferido nunca reprovava nada. Medido em
        # 02/11/2026 contra o catálogo real de família. Aceito as duas chaves
        # porque o contrato de S3 nomeia `base_legal`.
        base = str(prazo.get("base_legal") or prazo.get("base") or "")
        conferido = prazo.get("conferido")

        if not base:
            return ("NAO_AVALIADO",
                    "a estratégia não traz base de prazo (regra sem prazo próprio)",
                    ["base ausente"])
        if conferido is False or "conferir" in _sem_acento(base).lower():
            return ("REPROVA",
                    f"base de prazo não conferida na fonte: {base}",
                    [base])
        return ("PASSA", f"base conferida: {base}", [])

    # ------------------------------------------------------------------
    # Veredito agregado
    # ------------------------------------------------------------------

    def _veredito(self, regras: List[Dict[str, Any]],
                  avaliadas: List[Dict[str, Any]]) -> str:
        """
        Pior veredito entre as aplicáveis. Regra que exige conferência manual
        (NAO_AVALIADO) impede o 'PASSA' — bateria verde com metade não
        executada é mentira com aparência de método.
        """
        aplicaveis = [a for a in avaliadas if a["aplicavel"]]
        if not aplicaveis:
            return "NAO_AVALIADO"
        pior = max(GRAVIDADE[a["veredito"]] for a in aplicaveis)
        for nome, peso in GRAVIDADE.items():
            if peso == pior:
                return nome
        return "NAO_AVALIADO"  # pragma: no cover

    # Mapa regra -> avaliador. Regra fora do mapa sai NAO_AVALIADO com motivo.
    _AVALIADORES = {
        "apelacao-sem-razoes-de-reforma": _apelacao_sem_razoes,
        "apelacao-sem-impugnacao-especifica": _impugnacao_especifica,
        "prazo-conferir-marca": _prazo_conferir,
    }
