"""
S3 — Estratégia: decide QUAL peça cabe. Não escreve, não cita julgado.

O QUE ESTE ESTÁGIO FAZ
----------------------
Lê o catálogo `estrategia.yaml` do domínio e casa os gatilhos contra os
documentos do caso. A primeira regra que casar integralmente vence — a ordem
do catálogo é a decisão, e foi tomada por humano.

O QUE ELE NÃO FAZ
-----------------
- Não escreve a peça (S4).
- Não cita julgado com número (S5, com validação).
- Não decide polo por heurística de nome. Polo é declaração explícita do
  operador; sem ela, `indefinido` e `precisa_humano: true`.
- Não esconde incerteza: prazo sem base → `null` + `precisa_humano`.
- Não cai em LLM nesta versão. Quando nenhuma regra casar, PAUSA e diz que o
  fallback não está implementado. Fingir que decidiu por juízo seria pior.

POR QUE O FALLBACK É PAUSA E NÃO RESPOSTA
-------------------------------------------
A especificação prevê fallback para LLM com `confianca: baixa`. Implementá-lo
agora seria chamar modelo sem prompt conferido, sem custo declarado e sem
rastro L2 — três coisas que o próprio projeto exige antes de decidir. Melhor
pausar e dizer "não sei" do que produzir `peca_cabivel` inventada com selo de
baixa confiança: o operador lê "baixa" e protocola mesmo assim.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import Stage

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

RAIZ = Path(__file__).resolve().parents[2]


def _sem_acento(texto: str) -> str:
    """Normaliza para comparação de termos. Não altera dado em disco."""
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ",
        "aaaaaeeeeiiiiooooouuuucn")
    return texto.lower().translate(tabela)


def _tem_marca_conferir(base: str) -> bool:
    """Detecta a marca de prazo não conferido em qualquer das grafias usadas."""
    return "conferir" in _sem_acento(base)


def _limpar_marca_conferir(base: str) -> str:
    """
    Remove a marca da base que seguirá para a peça.

    A marca fica no catálogo (para o gate reprovar) e sai do texto da peça (para
    não virar citação truncada). O que sobra é o dispositivo puro.
    """
    import re
    limpo = re.sub(r"\s*(?:—|-|\[)\s*CONFERIR[^\]]*\]?", "", base,
                   flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", limpo).strip()


class S3Estrategia(Stage):
    id = "S3"
    nome = "estrategia"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id", "dominio_id", "documentos"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "estrategia"]  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Invariantes de ENTRADA
    # ------------------------------------------------------------------

    def _invariantes_entrada(self, entrada: Dict[str, Any]) -> List[str]:
        problemas: List[str] = []

        dominio = entrada.get("dominio_id")
        if isinstance(dominio, str):
            if not (RAIZ / "dominios" / dominio).is_dir():
                problemas.append(f"dominio_id não existe em dominios/: {dominio}")
            else:
                cat = RAIZ / "dominios" / dominio / "estrategia.yaml"
                if not cat.is_file():
                    problemas.append(
                        f"domínio {dominio} sem estrategia.yaml — o S3 não tem "
                        f"o que consultar")

        docs = entrada.get("documentos")
        if not isinstance(docs, list):
            problemas.append(
                "documentos ausente ou não é lista — S3 exige os documentos "
                "tipados (S2). Sem eles não há gatilho a casar")
        elif not docs:
            # Lista vazia é legítima (caso recém-aberto), mas então nenhuma
            # regra vai casar. Não é erro de entrada; é estado que produz pausa.
            pass

        polo = entrada.get("polo_atuacao", None)
        if polo not in (None, "ativo", "passivo", "interveniente", "indefinido"):
            problemas.append(
                f"polo_atuacao inválido: {polo!r} — aceito apenas ativo, "
                f"passivo, interveniente, indefinido ou ausência (None)")

        return problemas

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import EstagioAbortado

        entrada = ctx.montar_entrada(self)
        dominio = entrada["dominio_id"]
        docs: List[Dict[str, Any]] = entrada.get("documentos") or []
        polo = entrada.get("polo_atuacao") or "indefinido"

        catalogo = self._carregar_catalogo(dominio)

        casadas = self._casar_regras(catalogo.get("regras") or [], docs)

        if not casadas:
            raise EstagioAbortado(
                self.id,
                f"nenhuma regra do catálogo de '{dominio}' casou com os "
                f"{len(docs)} documento(s) do caso. O fallback para modelo "
                f"não está implementado",
                "declare o gatilho no estrategia.yaml do domínio, ou aguarde o "
                "fallback de S3 (previsto, não implementado)",
            )

        escolhida = casadas[0]

        # Regra do catálogo manda; o modelo não reescreve a decisão.
        peca = escolhida.get("peca_cabivel")
        if not peca or peca == "a preencher":
            raise EstagioAbortado(
                self.id,
                f"regra '{escolhida.get('id')}' casou mas não declara "
                f"peca_cabivel",
                "preencha `peca_cabivel` no estrategia.yaml do domínio",
            )

        if not (RAIZ / "dominios" / dominio / "templates" / f"{peca}.md").is_file():
            # Invariante do contrato: peca_cabivel existe em templates/.
            # Falhar aqui é honesto; entregar peça fantasma a S4 é pior.
            raise EstagioAbortado(
                self.id,
                f"peca_cabivel '{peca}' da regra '{escolhida.get('id')}' não "
                f"tem template em dominios/{dominio}/templates/",
                f"crie {peca}.md ou corrija o catálogo — S4 não tem o que ler",
            )

        prazo = self._montar_prazo(escolhida, entrada)
        alternativas = self._alternativas(casadas[1:], escolhida)
        teses = self._montar_teses(escolhida, dominio)
        modelo = self._modelo_sugerido(dominio)

        # Polo indefinido FORÇA revisão humana — invariante do contrato.
        precisa_humano = (polo == "indefinido") or bool(teses["nao_conferidas"])

        return {
            "caso_id": entrada["caso_id"],
            "estrategia": {
                "polo_atuacao": polo,
                "polo_sinal": entrada.get("polo_sinal"),
                "diagnostico": self._diagnostico(docs, escolhida),
                "gatilho": escolhida.get("id"),
                "peca_cabivel": peca,
                "pecas_alternativas": alternativas,
                "teses": teses["escolhidas"],
                "teses_nao_conferidas": teses["nao_conferidas"],
                "prazo_estimado": prazo,
                "modelo_sugerido": modelo,
                "confianca": self._confianca(polo, prazo, teses),
                "precisa_humano": precisa_humano,
                "justificativa": self._justificativa(
                    escolhida, casadas, entrada),
            },
        }

    # ------------------------------------------------------------------
    # Leitura do catálogo
    # ------------------------------------------------------------------

    def _carregar_catalogo(self, dominio: str) -> Dict[str, Any]:
        from .stage import ErroDeContrato

        caminho = RAIZ / "dominios" / dominio / "estrategia.yaml"
        if yaml is None:
            raise ErroDeContrato(
                self.id, "entrada", ["PyYAML ausente: não há como ler o catálogo"])
        try:
            dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            raise ErroDeContrato(
                self.id, "entrada",
                [f"catálogo ilegível em {caminho.relative_to(RAIZ)}: {e}"]) from e

        if not isinstance(dados, dict):
            raise ErroDeContrato(
                self.id, "entrada",
                [f"catálogo não é mapa YAML: {caminho.relative_to(RAIZ)}"])
        return dados

    # ------------------------------------------------------------------
    # Casamento de gatilho
    # ------------------------------------------------------------------

    def _casar_regras(self, regras: List[Dict[str, Any]],
                      docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Devolve TODAS as regras que casaram, na ordem do catálogo.

        Devolver todas, e não só a primeira, é o que permite relatar as
        alternativas — e a especificação proíbe decisão sem esse rastro (L1).
        """
        casadas: List[Dict[str, Any]] = []
        for regra in regras:
            if not isinstance(regra, dict):
                continue
            gatilho = regra.get("gatilho") or {}
            for doc in docs:
                if self._doc_casa(gatilho, doc):
                    casadas.append(regra)
                    break
        return casadas

    def _doc_casa(self, gatilho: Dict[str, Any], doc: Dict[str, Any]) -> bool:
        """
        Um documento casa quando TODAS as condições declaradas batem.

        Condição ausente não restringe. Condição declarada e não satisfeita
        impede o casamento — casamento parcial não é casamento, e forçá-lo
        escolheria peça errada com aparência de método.
        """
        tipo = gatilho.get("tipo_documento")
        if tipo and doc.get("tipo") != tipo:
            return False

        resultado = gatilho.get("resultado")
        if resultado:
            esperados = resultado if isinstance(resultado, list) else [resultado]
            if doc.get("resultado") not in esperados:
                return False

        texto = _sem_acento(str(doc.get("texto") or ""))

        # `conteudo_contem` aceita QUALQUER termo (alternativa).
        # `conteudo_contem_todos` exige TODOS os termos (conjunção).
        #
        # A separação existe porque o mesmo campo estava servindo a duas
        # semânticas e escolhia a errada. Medido em 02/11/2026: a regra de
        # cumprimento declarava [cumprimento, alimentos, execucao] como
        # alternativa, e "alimentos provisórios" sozinho a fazia casar —
        # sequestrando um caso de alimentos provisórios. Alternativa é para
        # sinônimo (tutela/liminar); conjunção é para contexto
        # (cumprimento E alimentos).
        contem = gatilho.get("conteudo_contem") or []
        if contem:
            termos = [_sem_acento(t) for t in contem]
            if not any(t in texto for t in termos):
                return False

        contem_todos = gatilho.get("conteudo_contem_todos") or []
        if contem_todos:
            termos = [_sem_acento(t) for t in contem_todos]
            if not all(t in texto for t in termos):
                return False

        # `conteudo_nao_contem` restringe por substring. Continua existindo,
        # mas o catálogo não deve usá-lo para distinguir TIPO documental: um
        # documento cita a palavra "sentença" sem ser sentença. Para isso,
        # use `tipo_documento`.
        nao_contem = gatilho.get("conteudo_nao_contem") or []
        if nao_contem:
            termos = [_sem_acento(t) for t in nao_contem]
            if any(t in texto for t in termos):
                return False

        return True

    # ------------------------------------------------------------------
    # Montagem dos campos de saída
    # ------------------------------------------------------------------

    def _montar_prazo(self, regra: Dict[str, Any],
                      entrada: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Devolve o prazo com a base declarada e a marca de conferência.

        NUNCA calcula data_limite sem data de intimação. Prazo que se conta de
        data que não existe é prazo inventado.
        """
        prazo = regra.get("prazo")
        if not isinstance(prazo, dict):
            return None

        base = str(prazo.get("base") or "")
        # A marca de conferência aparece no catálogo de duas formas: `[CONFERIR]`
        # e `— CONFERIR ...`. A primeira versão só procurava a forma com
        # colchetes e portanto declarava conferido todo prazo do catálogo real
        # de família, que usa travessão. Medido em 02/11/2026: 7 de 7 prazos
        # vinham com conferido=True sem nunca terem sido lidos na fonte.
        conferido = not _tem_marca_conferir(base)

        return {
            "tipo": prazo.get("tipo"),
            "dias": prazo.get("dias"),
            "contagem": prazo.get("contagem") or "dias_uteis",
            "base_legal": _limpar_marca_conferir(base),
            "conferido": conferido,
            # data_limite só existe quando a intimação é conhecida. Sem isso,
            # campo nulo com motivo — não cálculo silencioso.
            "data_limite": None,
            "data_limite_motivo": (
                None if entrada.get("data_intimacao")
                else "data de intimação ausente no caso"),
        }

    def _alternativas(self, demais: List[Dict[str, Any]],
                      escolhida: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rastro L1: por que cada outra regra que casou NÃO foi escolhida.

        Alternativa declarada só no catálogo ("pecas_alternativas") também
        entra — mas marcada, para não confundir com regra que efetivamente
        casou nos autos.
        """
        alternativas: List[Dict[str, Any]] = []
        for r in demais:
            alternativas.append({
                "peca": r.get("peca_cabivel"),
                "regra": r.get("id"),
                "porque_nao_escolhida": (
                    f"precedida por '{escolhida.get('id')}' na ordem do "
                    f"catálogo"),
                "casou_nos_autos": True,
            })

        for alt in (escolhida.get("pecas_alternativas") or []):
            if not isinstance(alt, dict):
                continue
            alternativas.append({
                "peca": alt.get("peca"),
                "regra": None,
                "porque_nao_escolhida": alt.get("quando"),
                "casou_nos_autos": False,
            })
        return alternativas

    def _montar_teses(self, regra: Dict[str, Any],
                      dominio: str) -> Dict[str, List[Any]]:
        """
        Separa teses CONFERIDAS das NÃO conferidas.

        Tese referenciada pelo catálogo mas ausente do tese-catalogo é
        `nao_conferidas` — não é silenciada. Tese com `verificado_em: null`
        também. A separação é o que faz `precisa_humano` significar algo.
        """
        escolhidas: List[Dict[str, Any]] = []
        nao_conferidas: List[str] = []

        ids = regra.get("teses_sugeridas") or []
        if not ids:
            return {"escolhidas": escolhidas, "nao_conferidas": nao_conferidas}

        caminho = RAIZ / "dominios" / dominio / "tese-catalogo.yaml"
        catalogo: Dict[str, Any] = {}
        if caminho.is_file() and yaml is not None:
            try:
                catalogo = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                catalogo = {}

        disponiveis = {t.get("id"): t for t in (catalogo.get("teses") or [])
                       if isinstance(t, dict)}

        for tid in ids:
            tese = disponiveis.get(tid)
            if tese is None:
                nao_conferidas.append(f"{tid}: ausente do tese-catalogo")
                continue
            if not tese.get("verificado_em"):
                nao_conferidas.append(f"{tid}: precedente não conferido")
            escolhidas.append({
                "tese": tid,
                "fundamento_normativo": [
                    f.get("chave") for f in (tese.get("fundamentos") or [])
                    if isinstance(f, dict)],
                "tipo": "merito",   # classificação fina é decisão humana
                "conferida": bool(tese.get("verificado_em")),
            })

        return {"escolhidas": escolhidas, "nao_conferidas": nao_conferidas}

    def _modelo_sugerido(self, dominio: str) -> Dict[str, Any]:
        """
        Rastro L2. Se o domínio não decidiu, o campo diz isso — não invento
        provider.
        """
        caminho = RAIZ / "dominios" / dominio / "dominio.yaml"
        dados: Dict[str, Any] = {}
        if caminho.is_file() and yaml is not None:
            try:
                dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                dados = {}
        m = (dados.get("modelos") or {}).get("default") or {}
        return {
            "provider": m.get("provider"),
            "modelo": m.get("modelo"),
            "motivo": m.get("motivo"),
            "decidido": bool(m.get("provider") and m.get("modelo")
                             and "a preencher" not in str(m.get("provider"))),
        }

    def _confianca(self, polo: str, prazo: Optional[Dict[str, Any]],
                   teses: Dict[str, List[Any]]) -> str:
        """
        Confiança NÃO é probabilidade de sucesso: é qualidade da decisão.
        Polo indefinido, prazo não conferido ou tese não conferida rebaixam.
        """
        if polo == "indefinido":
            return "baixa"
        if prazo is not None and not prazo.get("conferido"):
            return "baixa"
        if teses["nao_conferidas"]:
            return "media"
        return "alta"

    def _diagnostico(self, docs: List[Dict[str, Any]],
                     regra: Dict[str, Any]) -> str:
        """
        Descrição do que está acontecendo, referindo os autos — não o direito
        em abstrato. Sem documento, não há diagnóstico: diz isso.
        """
        if not docs:
            return ("Nenhum documento tipado no caso. Não há como descrever o "
                    "que está acontecendo.")
        tipos = ", ".join(sorted({str(d.get("tipo")) for d in docs}))
        return (f"{len(docs)} documento(s) tipado(s) no caso ({tipos}). "
                f"Gatilho casado: '{regra.get('id')}' — "
                f"{regra.get('descricao') or 'sem descrição no catálogo'}.")

    def _justificativa(self, escolhida: Dict[str, Any],
                       casadas: List[Dict[str, Any]],
                       entrada: Dict[str, Any]) -> str:
        n_outras = max(0, len(casadas) - 1)
        base = (f"Regra '{escolhida.get('id')}' casou integralmente e precede "
                f"as demais na ordem do catálogo")
        if n_outras:
            base += f" ({n_outras} outra(s) regra(s) também casaram e estão "
            base += "listadas como alternativas)"
        return base + "."


# ---------------------------------------------------------------------------
# Helpers de construção de caso — sem eles, testar S3 exigiria montar o mundo
# ---------------------------------------------------------------------------

def documento(tipo: str, texto: str = "", resultado: Optional[str] = None,
              **extra: Any) -> Dict[str, Any]:
    """Constrói um documento tipado como S2 entregaria."""
    d: Dict[str, Any] = {"tipo": tipo, "texto": texto}
    if resultado:
        d["resultado"] = resultado
    d.update(extra)
    return d
