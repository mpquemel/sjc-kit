"""
Testes do S1 — conversão de PDF com proveniência por página.

Regra herdada: teste que só produz sucesso não validou nada. O foco é onde o S1
DEVE RECUSAR ou CLASSIFICAR:

  - PDF só de imagem                    -> classe digitalizada, não erro
  - página com só o número do rodapé    -> classe própria, não "convertida"
  - página com imagem sem texto         -> classe de digitalizada, não "vazia"
  - PDF ilegível                        -> aborta com motivo
  - PDF sem páginas                     -> aborta
  - OCR desligado                       -> nenhuma página vira convertida
  - limiar baixo demais                 -> página real seria recusada

Nenhum teste exige PDF binário em disco: o abridor é injetado.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.pipeline.runner import Runner  # noqa: E402
from core.pipeline.s1_conversao import (  # noqa: E402
    S1Conversao, _classe_da_pagina, MIN_PALAVRAS, MIN_UNICAS, MIN_CHARS)
from core.pipeline.tests._harness import (  # noqa: E402
    executar_e_sair, resultados, teste)
from core.pipeline.stage import PipelineContext, Stage  # noqa: E402






# ---------------------------------------------------------------------------
# Páginas e documentos falsos
# ---------------------------------------------------------------------------

TEXTO_RICO = (
    "Julgo procedente o pedido para condenar o requerido ao pagamento de "
    "alimentos no valor de trinta por cento dos seus rendimentos líquidos, "
    "observado o binômio necessidade e possibilidade previsto no art. 1.694 "
    "do Código Civil. Condeno ainda o requerido ao pagamento das custas "
    "processuais e dos honorários advocatícios fixados em dez por cento."
)


class PaginaFalsa:
    def __init__(self, texto="", imagens=0):
        self._texto = texto
        self._imagens = imagens

    def get_text(self):
        return self._texto

    def get_images(self, full=True):
        return [("x",) for _ in range(self._imagens)]

    def get_pixmap(self, dpi=300):
        raise RuntimeError("OCR não deveria ser chamado neste teste")


class DocFalso:
    def __init__(self, paginas):
        self._paginas = paginas

    def __len__(self):
        return len(self._paginas)

    def __getitem__(self, i):
        return self._paginas[i]

    def close(self):
        pass


def _ctx(pdf_path="/tmp/falso.pdf"):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s1-")
    ctx = PipelineContext(Path(tmp), "familia")
    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "pdf_path": pdf_path,
        "arvore_path": None,
        "dominio_id": "familia",
        "perfil_atuacao": "ativo",
        "criado_em": None,
        "criado_por": None,
    }
    return ctx


def _rodar(paginas, ocr=False):
    s1 = S1Conversao()
    s1.abridor = lambda p: DocFalso(paginas)
    s1.ocr = ocr
    return s1.rodar(_ctx())


def _conv(r):
    assert r.ok and not r.pausado, f"S1 não rodou: {r.problemas or r.motivo_pausa}"
    return r.saida["conversao"]


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------

def t_pagina_rica_e_util():
    c = _conv(_rodar([PaginaFalsa(TEXTO_RICO)]))
    assert c["paginas_uteis"] == 1, c["paginas"]
    assert c["paginas"][0]["metodo"] == "texto_nativo"
    assert c["paginas_sem_texto"] == 0


def t_pagina_com_numero_de_rodape_nao_e_util():
    """
    Página cujo único texto é "88" devolve 2 caracteres. Um extrator que
    pergunta "saiu texto?" entregaria ao pipeline um documento cujo conteúdo é
    o número da página — pior que página vazia, porque parece conteúdo.
    """
    c = _conv(_rodar([PaginaFalsa("88")]))
    assert c["paginas_uteis"] == 0, c["paginas"]
    assert c["paginas_sem_texto"] == 1
    assert c["caso_sem_texto_util"] is True


def t_pagina_imagem_sem_texto_e_digitalizada():
    """
    Página com imagem e sem texto é documento escaneado. Chamá-la de "vazia"
    descreveria errado o que o operador vai encontrar ao abrir a página.
    """
    c = _conv(_rodar([PaginaFalsa("", imagens=1)]))
    classe = c["paginas"][0]["classe"]
    assert classe == "digitalizada_sem_ocr", classe


def t_pagina_sem_texto_e_sem_imagem_e_vazia():
    c = _conv(_rodar([PaginaFalsa("", imagens=0)]))
    assert c["paginas"][0]["classe"] == "vazia", c["paginas"][0]["classe"]


def t_pagina_curta_legitima_ainda_conta():
    """
    Despacho de uma linha e certidão curta são comuns em autos. O limiar baixo
    demais recusaria conteúdo legítimo; o alto demais recusaria página real.
    Medido em 02/11/2026: 90 palavras é a página mais pobre de 11 documentos
    jurídicos reais. O limiar fica com folga abaixo disso.
    """
    curta = ("Defiro a juntada dos documentos apresentados pelo requerido "
             "e intimem-se as partes para manifestação no prazo legal.")
    c = _conv(_rodar([PaginaFalsa(curta)]))
    uteis = c["paginas_uteis"]
    assert uteis == 1, f"página legível de {len(curta.split())} palavras recusada"


def t_limiares_abaixo_da_pagina_real_mais_pobre():
    """
    Guarda contra afrouxamento e contra aperto: os limiares têm de ficar
    abaixo da página real mais pobre medida (90 palavras / 78 únicas), senão
    documento jurídico completo é recusado.
    """
    assert MIN_PALAVRAS < 90, f"limiar {MIN_PALAVRAS} acima da página real mais pobre"
    assert MIN_UNICAS < 78, f"limiar {MIN_UNICAS} acima da página real mais pobre"
    assert MIN_PALAVRAS > 3, "limiar baixo demais: rodapé viraria conteúdo"


def t_ocr_desligado_nao_converte_imagem():
    """Com OCR desligado, página de imagem continua não convertida."""
    c = _conv(_rodar([PaginaFalsa("", imagens=2)], ocr=False))
    assert c["ocr_habilitado"] is False
    assert c["paginas_uteis"] == 0
    assert c["paginas"][0]["metodo"] == "nenhum"


def t_autos_txt_tem_marcador_de_pagina():
    """Cada bloco do texto carrega de qual página veio."""
    r = _rodar([PaginaFalsa(TEXTO_RICO), PaginaFalsa("88"),
                PaginaFalsa(TEXTO_RICO + " complemento")])
    assert r.ok, r.problemas
    txt = r.saida["texto_autos"]
    assert "=== [p.1] ===" in txt, txt[:200]
    assert "=== [p.2] ===" not in txt, "página sem texto não pode virar bloco"
    assert "=== [p.3] ===" in txt, txt[:400]


def t_documentos_carregam_proveniencia():
    r = _rodar([PaginaFalsa(TEXTO_RICO)])
    docs = r.saida["documentos"]
    assert len(docs) == 1, docs
    d = docs[0]
    assert d["pagina"] == 1 and d["metodo"] == "texto_nativo"
    assert d["fonte_pagina"].endswith("#p.1"), d["fonte_pagina"]


def t_pdf_ilegivel_aborta():
    s1 = S1Conversao()

    def explodir(p):
        raise RuntimeError("arquivo protegido")

    s1.abridor = explodir
    r = s1.rodar(_ctx())
    assert r.pausado, "PDF ilegível deveria abortar"
    assert "protegido" in r.motivo_pausa or "abrir" in r.motivo_pausa.lower(), r.motivo_pausa


def t_pdf_sem_paginas_aborta():
    """Zero página é arquivo errado, não caso vazio."""
    r = _rodar([])
    assert r.pausado, "PDF sem páginas deveria abortar"
    assert "página" in r.motivo_pausa.lower(), r.motivo_pausa


def t_caso_sem_texto_util_e_declarado():
    """
    PDF só de imagens é caso legítimo, não sucesso silencioso: sem texto não há
    o que decidir, e S3 diria "nenhuma regra casou" culpando o catálogo.
    """
    c = _conv(_rodar([PaginaFalsa("", imagens=1)] * 3))
    assert c["caso_sem_texto_util"] is True
    assert c["paginas_uteis"] == 0
    assert c["paginas_sem_texto"] == 3


def t_classe_nunca_e_erro_fatal():
    """
    Página sem texto é CLASSE, não exceção: o estágio conclui e reporta.
    """
    r = _rodar([PaginaFalsa("", imagens=1)])
    assert r.ok and not r.pausado
    assert r.saida["paginas_sem_texto"], "não reportou a página sem texto"


def t_integracao_s0_para_s1_no_runner():
    """S0 valida o PDF, S1 converte; o texto chega ao artefato."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="sjc-s01-")
    ctx = PipelineContext(Path(tmp), "familia")

    class S0Falso(Stage):
        id = "S0"
        nome = "entrada-de-teste"
        depende_de = []  # type: ignore[assignment]
        entrada_obriga = []  # type: ignore[assignment]
        saida_obriga = ["caso_id", "pdf_path", "arvore_path", "dominio_id",
                        "perfil_atuacao", "criado_em", "criado_por"]  # type: ignore[assignment]
        # `arvore_path`, `criado_em` e `criado_por` são legitimamente nulos: caso
        # sem árvore baixada e sem carimbo de criação. Sem declarar isso, o
        # validador de saída reprova o teste com "campo obrigatório nulo" e a
        # falha aparece em S0, não no estágio que se quer testar.
        campos_podem_ser_nulos = ["arvore_path", "criado_em",
                                  "criado_por", "perfil_atuacao"]  # type: ignore[assignment]

        def executar(self, ctx):
            return dict(ctx.artefatos.get("S0") or {})

    ctx.artefatos["S0"] = {
        "caso_id": "00000000000000000000",
        "pdf_path": "/tmp/falso.pdf",
        "arvore_path": None,
        "dominio_id": "familia",
        "perfil_atuacao": "ativo",
        "criado_em": None,
        "criado_por": None,
    }
    s1 = S1Conversao()
    s1.abridor = lambda p: DocFalso([PaginaFalsa(TEXTO_RICO)])
    res = Runner([S0Falso(), s1], ctx).rodar()
    assert res["parada"] == "fim", f"parada={res['parada']} em {res['estagio']}"
    assert ctx.artefatos["S1"]["texto_autos"].strip(), "S1 não produziu texto"


TESTES = [
    ("t_pagina_rica_e_util", t_pagina_rica_e_util),
    ("t_pagina_com_numero_de_rodape_nao_e_util", t_pagina_com_numero_de_rodape_nao_e_util),
    ("t_pagina_imagem_sem_texto_e_digitalizada", t_pagina_imagem_sem_texto_e_digitalizada),
    ("t_pagina_sem_texto_e_sem_imagem_e_vazia", t_pagina_sem_texto_e_sem_imagem_e_vazia),
    ("t_pagina_curta_legitima_ainda_conta", t_pagina_curta_legitima_ainda_conta),
    ("t_limiares_abaixo_da_pagina_real_mais_pobre",
     t_limiares_abaixo_da_pagina_real_mais_pobre),
    ("t_ocr_desligado_nao_converte_imagem", t_ocr_desligado_nao_converte_imagem),
    ("t_autos_txt_tem_marcador_de_pagina", t_autos_txt_tem_marcador_de_pagina),
    ("t_documentos_carregam_proveniencia", t_documentos_carregam_proveniencia),
    ("t_pdf_ilegivel_aborta", t_pdf_ilegivel_aborta),
    ("t_pdf_sem_paginas_aborta", t_pdf_sem_paginas_aborta),
    ("t_caso_sem_texto_util_e_declarado", t_caso_sem_texto_util_e_declarado),
    ("t_classe_nunca_e_erro_fatal", t_classe_nunca_e_erro_fatal),
    ("t_integracao_s0_para_s1_no_runner", t_integracao_s0_para_s1_no_runner),
]


if __name__ == "__main__":
    executar_e_sair("S1 CONVERSÃO", TESTES)
