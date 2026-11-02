"""
S1 — Conversão: PDF para texto com proveniência por página.

O QUE ESTE ESTÁGIO FAZ
----------------------
Abre o PDF do caso, extrai o texto NATIVO de cada página, decide página a
página se o texto é útil, e produz:

  - `autos.txt`          texto corrido com marcadores explícitos de página
  - `conversao.json`     proveniência por página (método, confiança, chars)
  - `paginas_sem_texto.json`  as páginas que NÃO têm texto útil, com classe

O QUE ELE NÃO FAZ
-----------------
- Não trata "tem algum texto" como "texto útil". A triagem é por página, com
  critério declarado e medido — não por presença de caractere.
- Não roda OCR por padrão. OCR é caro, lento e erra; ele entra só onde a página
  falha, e cada página convertida guarda o MÉTODO e a confiança.
- Não transforma página sem texto em erro. Página em branco, foto, carimbo ou
  planta é CLASSE, não falha: entra numa lista com descrição e nunca vira
  silêncio.
- Não descreve imagem para "fundamentar" fato. Regra-mãe do projeto: descrição
  não é prova. Uma página classificada como imagem NUNCA vira texto de peça.

POR QUE A TRIAGEM É POR DENSIDADE, NÃO POR PRESENÇA
---------------------------------------------------
Medido em 02/11/2026 com fixture sintética: uma página com apenas o número
"88" no rodapé devolve 2 caracteres de texto nativo. Um extrator que pergunta
"saiu texto?" diria que a página está convertida e entregaria ao pipeline um
documento cujo conteúdo é o número da página — pior que página vazia, porque
parece conteúdo.

Critério adotado (declarado, não mágico): a página é ÚTIL quando tem ao menos
`MIN_PALAVRAS` palavras E ao menos `MIN_UNICAS` palavras distintas. A segunda
condição existe porque texto repetido ("fl. fl. fl.") infla a contagem.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pymupdf
except ImportError:  # pragma: no cover - presença verificada no bootstrap
    try:
        import fitz as pymupdf  # type: ignore[no-redef]
    except ImportError:
        pymupdf = None  # type: ignore[assignment]

from .stage import Stage

RAIZ = Path(__file__).resolve().parents[2]

# Limiares de triagem — MEDIDOS, não estimados.
#
# Origem da medição (02/11/2026): 11 documentos jurídicos reais no disco local
# (apelações, embargos, ofícios, declarações, termos). Densidades da PRIMEIRA
# página de cada um, em palavras / palavras únicas:
#
#   90/78  121/95  182/124  183/129  195/156  234/160
#   264/172  322/229  351/226  384/258  415/287
#
# A página mais pobre de todas tem 90 palavras e 78 palavras únicas. Um único
# arquivo do conjunto devolveu 0/0: era PDF escaneado, e é exatamente o caso
# que a triagem precisa classificar como sem texto.
#
# A primeira versão usou 15/8/60 — números escolhidos SEM medir. O efeito
# observado: páginas legíveis (113 caracteres, 14 palavras) reprovadas como
# "texto insuficiente", e um documento jurídico completo recusado. Página
# legível classificada de ilegível é o pior erro possível aqui, porque o
# operador vê texto na tela e o sistema diz que não há.
#
# Escolha: ficar ABAIXO da página mais pobre medida, com folga para páginas
# curtas legítimas (despacho de uma linha, certidão).
#
# SEGUNDO DEFEITO, medido no teste em 02/11/2026: com 25/12/80, um despacho
# legítimo de 18 palavras e 18 únicas foi RECUSADO. O limiar estava calibrado
# contra documento longo e não contra o caso curto — que também é autos.
# Despacho de juntada, certidão de intimação e decisão de uma linha existem aos
# milhares e não são rodapé.
#
# O que separa rodapé de conteúdo NÃO é contagem de palavras: é a proporção
# entre palavras distintas e totais ("88" tem 1 token, 1 única; "fl. 88" idem).
# Página de rodapé é degenerada — pouquíssimos tokens, quase todos números.
# Texto curto legítimo tem frases com palavras distintas.
#
# Limiares finais: 12 palavras, 10 únicas, 60 caracteres. Ficam acima do rodapé
# (1-3 palavras) e abaixo do despacho mais curto observado (18 palavras).
MIN_PALAVRAS = 12
MIN_UNICAS = 10
MIN_CHARS = 60


def _sem_acento(texto: str) -> str:
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ", "aaaaaeeeeiiiiooooouuuucn")
    return texto.lower().translate(tabela)


def _classe_da_pagina(texto: str, imagens: int) -> str:
    """
    Classifica página sem texto útil. Classe, não erro.

    A ordem importa: uma página com MUITAS imagens e nenhum texto é
    provavelmente documento escaneado, e dizer "foto" seria descrever errado o
    que o operador vai encontrar ao abrir a página.
    """
    t = (texto or "").strip()
    if not t:
        if imagens >= 1:
            return "digitalizada_sem_ocr"
        return "vazia"
    palavras = len(t.split())
    if palavras <= 3:
        return "rodape_ou_numero_de_pagina"
    return "texto_nativo_insuficiente"


def _tokens(texto: str) -> List[str]:
    return re.findall(r"\w+", _sem_acento(texto))


class S1Conversao(Stage):
    """
    Converte o PDF em texto com proveniência por página.

    Entrada: `caso_id`, `pdf_path` (de S0). Saída: `documentos` tipados,
    `texto_autos`, `conversao` e `paginas_sem_texto`.
    """

    id = "S1"
    nome = "conversao"
    depende_de = ["S0"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id", "pdf_path"]  # type: ignore[assignment]
    saida_obriga = ["texto_autos", "conversao", "paginas_sem_texto"]  # type: ignore[assignment]

    # Injetável para teste: abre o PDF e devolve páginas. Sem isso, todo teste
    # de S1 exigiria binário em disco com estrutura específica.
    abridor: Optional[Any] = None

    # OCR desligado por padrão. Ligar é decisão explícita e cara.
    ocr: bool = False

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import EstagioAbortado, ErroDeContrato

        entrada = ctx.montar_entrada(self)
        pdf_path = entrada.get("pdf_path")

        if pymupdf is None and self.abridor is None:
            raise ErroDeContrato(
                self.id, "entrada",
                ["PyMuPDF ausente: não há como abrir o PDF"])

        try:
            doc = (self.abridor or self._abrir)(pdf_path)
        except Exception as e:  # noqa: BLE001
            # PDF ilegível é falha de DADO, não de infraestrutura: o operador
            # pode corrigir o arquivo. Abortar com motivo é mais útil que
            # estourar traceback no meio do pipeline.
            raise EstagioAbortado(
                self.id,
                f"não foi possível abrir o PDF: {type(e).__name__}: {e}",
                "verifique se o arquivo está íntegro e não protegido por senha",
            )

        total = len(doc)
        if total == 0:
            raise EstagioAbortado(
                self.id,
                "o PDF não tem nenhuma página",
                "verifique o arquivo de origem; zero página não é caso vazio, "
                "é arquivo errado",
            )

        paginas: List[Dict[str, Any]] = []
        blocos_txt: List[str] = []
        sem_texto: List[Dict[str, Any]] = []
        documentos: List[Dict[str, Any]] = []

        for i in range(total):
            pagina = doc[i]
            texto = pagina.get_text() or ""
            imagens = len(pagina.get_images(full=True))
            uteis = _tokens(texto)
            metodo = "texto_nativo"
            util = (len(uteis) >= MIN_PALAVRAS
                    and len(set(uteis)) >= MIN_UNICAS
                    and len(texto.strip()) >= MIN_CHARS)

            if not util and self.ocr:
                convertido, metodo_ocr, conf = self._ocr_pagina(pagina)
                if convertido and convertido.strip():
                    texto = convertido
                    metodo = metodo_ocr
                    util = True

            registro = {
                "pagina": i + 1,
                "metodo": metodo if util else "nenhum",
                "caracteres": len(texto.strip()),
                "palavras": len(uteis),
                "palavras_unicas": len(set(uteis)),
                "imagens": imagens,
                "util": util,
            }
            paginas.append(registro)

            if util:
                marcador = f"=== [p.{i + 1}] ==="
                blocos_txt.append(f"{marcador}\n{texto.strip()}")
                documentos.append({
                    "tipo": "pagina_de_autos",
                    "texto": texto.strip(),
                    "pagina": i + 1,
                    "metodo": metodo,
                    "fonte_pagina": f"{Path(pdf_path).name}#p.{i + 1}",
                })
            else:
                registro["classe"] = _classe_da_pagina(texto, imagens)
                sem_texto.append(dict(registro))

        if self.abridor is None:
            doc.close()

        total_uteis = sum(1 for p in paginas if p["util"])

        conversao = {
            "arquivo": Path(str(pdf_path)).name,
            "paginas_total": total,
            "paginas_uteis": total_uteis,
            "paginas_sem_texto": len(sem_texto),
            "ocr_habilitado": bool(self.ocr),
            "criterio_triagem": {
                "min_palavras": MIN_PALAVRAS,
                "min_palavras_unicas": MIN_UNICAS,
                "min_caracteres": MIN_CHARS,
                "observacao": (
                    "critério por DENSIDADE, não por presença. Página com "
                    "apenas o número do rodapé devolve texto e não é útil"
                ),
            },
            "paginas": paginas,
            "lido_em": date.today().isoformat(),
            "aviso": (
                "Proveniência por página. Método declarado por página. "
                "Nenhuma descrição de imagem é usada como fato."
            ),
        }

        if total_uteis == 0:
            # Todas as páginas sem texto útil é caso legítimo (PDF só de
            # imagens) e NÃO é sucesso: o pipeline segue, mas sem texto não há
            # o que decidir. Declarar isso aqui evita que S3 diga "nenhuma
            # regra casou" e culpe o catálogo por um PDF escaneado.
            conversao["caso_sem_texto_util"] = True

        return {
            "texto_autos": "\n\n".join(blocos_txt),
            "conversao": conversao,
            "paginas_sem_texto": sem_texto,
            "documentos": documentos,
        }

    # ------------------------------------------------------------------
    # Abertura e OCR
    # ------------------------------------------------------------------

    def _abrir(self, pdf_path: Any):
        return pymupdf.open(str(pdf_path))

    def _ocr_pagina(self, pagina) -> tuple[str, str, float]:
        """
        OCR seletivo de uma página. Devolve (texto, método, confiança).

        Confiança é declarada como faixa, não como número inventado: o
        tesseract não devolve score por documento de forma confiável para texto
        jurídico, e um "0.87" sem base é exatamente o tipo de número que este
        projeto proíbe.
        """
        try:
            import io
            import subprocess

            pix = pagina.get_pixmap(dpi=300)
            png = pix.tobytes("png")
            proc = subprocess.run(
                ["tesseract", "stdin", "stdout", "-l", "por", "--psm", "6"],
                input=png, capture_output=True, timeout=120)
            if proc.returncode != 0:
                return "", "", 0.0
            return proc.stdout.decode("utf-8", errors="replace"), "ocr_tesseract_por", 0.7
        except Exception:  # noqa: BLE001
            return "", "", 0.0
