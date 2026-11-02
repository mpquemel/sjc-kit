"""
S5 — Citações: confere, na fonte, cada citação da peça.

O QUE ESTE ESTÁGIO FAZ
----------------------
Extrai as citações do texto da peça (extrator do portão de citação), pergunta
ao adaptador de cada tribunal se o documento existe, e devolve veredito
discreto por citação. Nada é corrigido: o estágio APONTA e RETÉM.

O QUE ELE NÃO FAZ
-----------------
- Não reescreve citação. Corrigir o número na peça é decisão do operador, com
  a fonte aberta.
- Não dá nota. O veredito é `ok`, `numero_errado`, `numero_truncado`,
  `conteudo_diverso`, `falso_positivo` ou `nao_avaliado`.
- Não afirma inexistência quando não conseguiu perguntar. Falha de
  infraestrutura vira `nao_avaliado` com `retem: true`. Um sistema que não
  pôde consultar não pode dizer "não existe".

POR QUE SEM TRIBUNAL NÃO HÁ CONSULTA
------------------------------------
O adaptador exige tribunal para escolher a fonte. Uma peça que cita "REsp
1.533.206" sem dizer "STJ" não é uma citação incompleta — é uma citação cujo
tribunal o extrator não determinou. Adivinhar STJ porque "REsp" costuma ser STJ
seria trocar um `nao_avaliado` honesto por um `ok` que ninguém conferiu.
Veredito: `nao_avaliado`, com motivo.

POR QUE O MODO `consulta_fonte=False`
-------------------------------------
Teste que depende de rede não roda em CI, e teste que não roda não protege.
No modo offline o estágio extrai e classifica a EXTRAÇÃO (ambiguidade
registrada, chave canônica estável, nada inventado) e marca toda citação como
`nao_avaliado` — que retém. Ele nunca finge `ok` sem ter perguntado.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from .stage import Stage

TRIBUNAIS_CONHECIDOS = {"STJ", "STF", "TJRJ"}


def _sem_acento(texto: str) -> str:
    tabela = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçñ", "aaaaaeeeeiiiiooooouuuucn")
    return texto.lower().translate(tabela)


def _com_milhar(numero: str) -> str:
    """1533206 -> 1.533.206. Só para localizar o numeral escrito no trecho."""
    d = re.sub(r"\D", "", numero or "")
    if len(d) <= 3:
        return d
    partes = []
    while d:
        partes.insert(0, d[-3:])
        d = d[:-3]
    return ".".join(partes)


def _tribunal_de(citacao: Any, texto: str) -> Optional[str]:
    """
    Determina o tribunal de uma citação sem adivinhar.

    1. Campo `tribunal` do próprio extrator.
    2. Tribunal imediatamente APÓS a citação no texto, dentro do trecho
       capturado (o extrator guarda 80 caracteres de contexto adiante).

    Dois defeitos medidos em 02/11/2026, antes do primeiro teste:
    - A janela original começava 20 caracteres ANTES da posição e era curta
      demais adiante: `REsp 1.533.206/MG (STJ)` devolvia None, porque a sigla
      vem DEPOIS do numeral. Todas as citações ficariam "sem tribunal" e
      nada seria consultado.
    - A mesma janela pegava o `STJ` da `Súmula 593/STJ` nove caracteres antes
      e atribuía STJ a `art. 1.694`. Inferência por proximidade é palpite com
      aparência de determinação — o erro que esta função existe para evitar.

    A janela agora só olha adiante, e é curta: o tribunal de uma citação vem
    imediatamente depois dela, não depois da citação seguinte.
    """
    direto = (getattr(citacao, "tribunal", None) or "").upper()
    if direto in TRIBUNAIS_CONHECIDOS:
        return direto

    # Dispositivo de lei não tem tribunal: atribuir um seria inventar fonte.
    if getattr(citacao, "tipo", "") == "dispositivo":
        return None

    pos = getattr(citacao, "posicao", 0) or 0
    trecho = str(getattr(citacao, "trecho", "") or "")
    numero = str(getattr(citacao, "numero", "") or "")
    if trecho:
        # `trecho` começa até 80 caracteres antes do match e termina 80
        # depois. O deslocamento do match dentro do trecho é o que interessa.
        #
        # DUAS ARMADILHAS MEDIDAS em 02/11/2026:
        # 1. `citacao.numero` é o numeral SEM separador (1533206), mas o trecho
        #    preserva o texto como escrito (1.533.206). Procurar `numero` no
        #    trecho NUNCA encontrava nada.
        # 2. A primeira correção usou `re.search(r"\d[\d.]*", trecho)`. Isso
        #    ancorava no PRIMEIRO numeral do trecho — que pode ser a posição
        #    ("fl. 88") ou o numeral de uma citação ANTERIOR. Medido: `RE
        #    9.999.999 do STF` saía com tribunal=STJ porque o primeiro numeral
        #    encontrado era o da citação precedente, e a janela caía depois
        #    dela. Tribunal errado é pior que tribunal indeterminado: produz
        #    consulta na fonte errada com veredito de aparência válida.
        #
        # Correção: ancorar no numeral DO MEIO da citação (c.numero), usando o
        # deslocamento do início do trecho em relação à posição do match.
        antes = min(80, pos)
        inicio_no_trecho = antes
        # A citação do meio usa pontuação de milhar: procurar a forma escrita
        # do próprio numero (1.533.206) a partir do fim do prefixo.
        escrito = _com_milhar(numero)
        achado = trecho.find(escrito, max(0, inicio_no_trecho - 5))
        if achado < 0:
            achado = trecho.find(numero, max(0, inicio_no_trecho - 5))
        corte = achado + (len(escrito) if trecho[achado:achado + len(escrito)] == escrito
                          else len(numero)) if achado >= 0 else 0
        janela = trecho[corte:corte + 30].upper()
    else:
        janela = texto[pos + len(numero):pos + len(numero) + 30].upper()

    achados = [t for t in TRIBUNAIS_CONHECIDOS
               if re.search(rf"\b{t}\b", janela)]
    if len(achados) == 1:
        return achados[0]
    return None


class S5Citacoes(Stage):
    """
    Confere as citações da peça contra a fonte.

    Entrada: `peca_texto` e, opcionalmente, `consulta_fonte` (default True).
    Saída: relatório do portão de citação, com `retem` e contagem por veredito.
    """

    id = "S5"
    nome = "citacoes"
    # A peça vem de S4. Se S4 não estiver no DAG, `montar_entrada` cai para o
    # artefato de S0 — por isso S5 NÃO declara S0 aqui: declarar S0, S3 e S4
    # juntos produz colisão de `caso_id`/`dominio_id`/`documentos` entre
    # estágios, e o runner levanta ErroDeContrato. O fallback de S0 é
    # automático no PipelineContext; declarar dependência é para o dado que
    # só aquele estágio produz.
    depende_de = ["S3", "S4"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id", "peca_texto"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "citacoes"]  # type: ignore[assignment]

    # Injetáveis para teste: sem isso, testar S5 exige rede.
    verificador: Optional[Callable[[dict], dict]] = None

    def executar(self, ctx) -> Dict[str, Any]:
        from core.citacoes import adaptador as adaptador_padrao
        from core.citacoes.citacoes import extrair, relatorio

        entrada = ctx.montar_entrada(self)
        peca_texto = entrada.get("peca_texto") or ""
        consulta_fonte = entrada.get("consulta_fonte", True)
        verificar = self.verificador or adaptador_padrao.verificar

        if not str(peca_texto).strip():
            from .stage import EstagioAbortado
            raise EstagioAbortado(
                self.id,
                "peça vazia: não há citação a conferir",
                "gere a peça (S4) ou informe peca_texto; relatório sobre texto "
                "vazio atestaria que zero citações estão corretas",
            )

        citacoes = extrair(peca_texto)
        avaliacoes: Dict[str, Dict[str, Any]] = {}
        consultas: List[Dict[str, Any]] = []
        sem_tribunal: List[str] = []

        for c in citacoes:
            chave = f"{c.tipo}:{c.chave}"

            # Dispositivo de lei não tem fonte remota neste adaptador. Declarar
            # isso é diferente de dizer que está errado.
            if c.tipo == "dispositivo":
                avaliacoes[chave] = {
                    "consulta_executada": False,
                    "encontrado": None,
                    "erro_codigo": "sem_adaptador_para_tipo",
                    "erro": "dispositivo de lei não é conferido por este "
                            "adaptador (só julgado, súmula e tema)",
                }
                consultas.append({"chave": c.chave, "tipo": c.tipo,
                                  "tribunal": None,
                                  "consulta_executada": False})
                continue

            if not consulta_fonte:
                avaliacoes[chave] = {
                    "consulta_executada": False,
                    "encontrado": None,
                    "erro_codigo": "consulta_desligada",
                    "erro": "modo offline: extração conferida, fonte não",
                }
                continue

            tribunal = _tribunal_de(c, peca_texto)
            if tribunal is None:
                sem_tribunal.append(c.chave)
                avaliacoes[chave] = {
                    "consulta_executada": False,
                    "encontrado": None,
                    "erro_codigo": "tribunal_indeterminado",
                    "erro": "a peça não identifica o tribunal desta citação",
                }
                consultas.append({"chave": c.chave, "tipo": c.tipo,
                                  "tribunal": None,
                                  "consulta_executada": False})
                continue

            resultado = verificar({
                "tipo": c.tipo,
                "chave": c.chave,
                "numero": c.numero,
                "tribunal": tribunal,
                "uf": c.uf,
                "termo": c.termo if hasattr(c, "termo") else c.chave,
            })
            avaliacoes[chave] = resultado
            consultas.append({
                "chave": c.chave,
                "tipo": c.tipo,
                "tribunal": tribunal,
                "consulta_executada": bool(resultado.get("consulta_executada")),
                "encontrado": resultado.get("encontrado"),
                "erro_codigo": resultado.get("erro_codigo"),
                "fonte": resultado.get("fonte"),
            })

        rel = relatorio(citacoes, avaliacoes)

        # Retenção é a do relatório, MAIS o que ele não vê: citação sem
        # tribunal ficou com resultado None e já retém, mas declarar o motivo
        # é o que permite ao operador consertar.
        # VACUIDADE MEDIDA em 02/11/2026: peça SEM nenhuma citação extraída
        # saía `total: 0`, `retem: False` — passava sem ter sido examinada.
        # O relatório do portão dizia "zero citações erradas" quando o certo era
        # "não havia citação". Peça de família sem citação de dispositivo ou
        # precedente é peça sem fundamentação; tratar isso como sucesso é a
        # mesma mentira que tratar falha de infraestrutura como inexistência.
        sem_citacao = rel["total"] == 0
        retem = bool(rel["peça_retida"] or sem_citacao)
        motivo = rel["motivo_retencao"]
        if sem_citacao:
            motivo = (
                "a peça não contém citação extraível (dispositivo, súmula, tema "
                "ou julgado). Nada foi conferido; ausência de citação não é "
                "prova de correção")

        rel["citacoes"] = {
            "total": rel["total"],
            "contagem": rel["contagem"],
            "itens": rel["itens"],
            "retem": retem,
            "motivo_retencao": motivo,
            "sem_citacao": sem_citacao,
            "consultas": consultas,
            "sem_tribunal": sem_tribunal,
            "consulta_fonte": consulta_fonte,
            "fonte_consultada": sorted({c["fonte"] for c in consultas
                                        if c.get("fonte")}),
            "aviso": (
                "Consulta verifica identidade do documento. NÃO verifica "
                "vigência, superação nem aderência a tese."
            ),
        }

        return {"caso_id": entrada["caso_id"], "citacoes": rel["citacoes"]}
