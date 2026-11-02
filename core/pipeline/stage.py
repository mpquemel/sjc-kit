"""
Stage — a classe base de todo estágio do pipeline.

O QUE ESTA CLASSE GARANTE
-------------------------
1. Nenhum estágio roda com entrada inválida.
2. Nenhum estágio entrega saída inválida.
3. Nenhum estágio passa adiante um artefato que não tem hash.

As três são a mesma regra em três momentos: o contrato é verificado nas
fronteiras, não no meio. Um estágio que produz lixo tem de falhar na saída,
com o nome do estágio e o caminho exato do campo — não três estágios depois,
com um KeyError anônimo.

O QUE ELA NÃO FAZ
-----------------
Não conhece domínio. Não conhece fonte externa. Não chama LLM. Um estágio que
precise de qualquer dessas coisas recebe-as por injeção, e o runner não sabe
disso.

POR QUE `validate_input` E `validate_output` SÃO MÉTODOS E NÃO DECORADORES
--------------------------------------------------------------------------
Porque o erro precisa carregar contexto: qual estágio, qual campo, qual valor.
Um decorator genérico produz "validação falhou" — inútil às 3 da manhã.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ErroDeContrato(Exception):
    """
    Falha de contrato entre estágios.

    Carrega o estágio e os campos culpados. Não é `ValueError` genérico porque
    o runner precisa distinguir "o dado estava errado" (reparável: corrija a
    entrada e rode de novo) de "o código quebrou" (defeito: abra o editor).
    """

    def __init__(self, estagio: str, momento: str, problemas: List[str]):
        self.estagio = estagio
        self.momento = momento  # "entrada" | "saida"
        self.problemas = problemas
        super().__init__(
            f"{estagio}: contrato de {momento} violado em "
            f"{len(problemas)} ponto(s): " + "; ".join(problemas[:5])
            + (" ..." if len(problemas) > 5 else ""))


class EstagioAbortado(Exception):
    """
    O estágio recusou rodar por razão declarada e legítima.

    Diferente de `ErroDeContrato`: aqui o dado está correto, mas o estágio não
    pode decidir. Exemplo real: S3 sem polo declarado. Isso NÃO é bug — é o
    comportamento correto, e o pipeline precisa pausar e devolver ao operador.
    """

    def __init__(self, estagio: str, motivo: str, acao_sugerida: str = ""):
        self.estagio = estagio
        self.motivo = motivo
        self.acao_sugerida = acao_sugerida
        super().__init__(f"{estagio}: abortado — {motivo}")


@dataclass
class ResultadoEstagio:
    """
    O que o runner recebe de um estágio.

    `pausado` existe separado de `ok` porque pausa não é falha: é pedido de
    decisão humana. Misturar os dois faz o operador procurar bug onde há
    pergunta pendente, e ignorar pergunta pensando que é bug.
    """

    estagio: str
    ok: bool
    saida: Optional[Dict[str, Any]] = None
    pausado: bool = False
    motivo_pausa: str = ""
    acao_sugerida: str = ""
    problemas: List[str] = field(default_factory=list)
    duracao_ms: int = 0
    iniciado_em: str = ""

    def como_dict(self) -> Dict[str, Any]:
        return {
            "estagio": self.estagio,
            "ok": self.ok,
            "pausado": self.pausado,
            "motivo_pausa": self.motivo_pausa,
            "acao_sugerida": self.acao_sugerida,
            "problemas": self.problemas,
            "duracao_ms": self.duracao_ms,
            "iniciado_em": self.iniciado_em,
        }


class Stage:
    """
    Base de todo estágio. Subclasses declaram:

        id            = "S3"
        nome          = "estrategia"
        depende_de    = ["S2"]
        entrada_obriga= ["caso_id", "vinculacao"]
        saida_obriga  = ["caso_id", "estrategia"]

    e implementam `executar(ctx) -> dict`.

    `ctx` é um PipelineContext: leitura de artefatos anteriores, escrita de
    artefatos próprios, e o manifesto de proveniência.
    """

    id: str = ""
    nome: str = ""
    # ATENÇÃO: Stage NÃO é @dataclass. `dataclasses.field(...)` aqui avalia para
    # o objeto Field e o atributo vira lixo não-iterável — `for c in self.entrada_obriga`
    # levanta "'Field' object is not iterable". Medido em 02/11/2026: a classe já
    # tinha esse defeito latente; sobrevivia porque toda subclasse sobrescrevia os
    # atributos. O novo `campos_podem_ser_nulos` não era sobrescrito e expôs o bug,
    # derrubando 8 testes do runner. Lista literal é o correto aqui.
    depende_de: List[str] = []  # type: ignore[assignment]
    entrada_obriga: List[str] = []  # type: ignore[assignment]
    saida_obriga: List[str] = []  # type: ignore[assignment]
    # Campos em que `None` é informação legítima (ex.: polo não declarado),
    # não ausência de dado. Ver _checar_campos.
    campos_podem_ser_nulos: List[str] = []  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Validação — subclasses podem estender, não substituir
    # ------------------------------------------------------------------

    def validate_input(self, entrada: Dict[str, Any]) -> List[str]:
        """
        Devolve lista de problemas. Vazia = entrada aceitável.

        Devolve lista em vez de levantar exceção porque o operador quer ver
        TODOS os problemas de uma vez, não o primeiro. Corrigir um campo por
        execução é tortura.
        """
        problemas: List[str] = []
        if not isinstance(entrada, dict):
            return [f"entrada não é um mapa (é {type(entrada).__name__})"]
        problemas.extend(self._checar_campos(entrada, self.entrada_obriga))
        return problemas + self._invariantes_entrada(entrada)

    def _checar_campos(self, dados: Dict[str, Any], exigidos: List[str]) -> List[str]:
        """
        Ausente e NULO são estados diferentes, e confundi-los faz o relatório mentir.

        `campos_podem_ser_nulos` declara os campos em que null é informação, não
        falha. Exemplo medido em 02/11/2026: `polo_atuacao` nulo significa "o
        operador não declarou o polo" — estado legítimo que o contrato trata como
        `indefinido` e que FORÇA revisão humana. Reprovar por nulo fazia o S0 de
        qualquer caso sem polo declarado falhar com "campo obrigatório nulo",
        escondendo que o sistema estava se comportando exatamente como devia.
        """
        problemas: List[str] = []
        podem = set(getattr(self, "campos_podem_ser_nulos", []) or [])
        for campo in exigidos:
            if campo not in dados:
                problemas.append(f"campo obrigatório ausente: {campo}")
            elif dados[campo] is None and campo not in podem:
                problemas.append(f"campo obrigatório nulo: {campo}")
            elif dados[campo] is None and campo in podem:
                # Declarado, ausente e legítimo: registra como aviso de leitura,
                # não como problema. Quem consome decide o que fazer com null.
                pass
        return problemas

    def _invariantes_entrada(self, entrada: Dict[str, Any]) -> List[str]:
        """Extensível: invariantes além da presença de campo."""
        return []

    def validate_output(self, saida: Dict[str, Any]) -> List[str]:
        problemas: List[str] = []
        if not isinstance(saida, dict):
            return [f"saída não é um mapa (é {type(saida).__name__})"]
        problemas.extend(self._checar_campos(saida, self.saida_obriga))
        return problemas + self._invariantes_saida(saida)

    def _invariantes_saida(self, saida: Dict[str, Any]) -> List[str]:
        """Extensível: ex.: toda citação tem âncora de página."""
        return []

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    def executar(self, ctx: "PipelineContext") -> Dict[str, Any]:
        raise NotImplementedError(
            f"{type(self).__name__}.executar() não implementado")

    # ------------------------------------------------------------------
    # Orquestração de uma execução — o runner chama isto, não `executar`
    # ------------------------------------------------------------------

    def rodar(self, ctx: "PipelineContext") -> ResultadoEstagio:
        inicio = datetime.now(timezone.utc)
        r = ResultadoEstagio(estagio=self.id, ok=False,
                             iniciado_em=inicio.isoformat())

        def _fechar(ok: bool) -> ResultadoEstagio:
            r.ok = ok
            r.duracao_ms = int(
                (datetime.now(timezone.utc) - inicio).total_seconds() * 1000)
            return r

        # 1. Entrada
        entrada = ctx.montar_entrada(self)
        problemas = self.validate_input(entrada)
        if problemas:
            r.problemas = problemas
            ctx.registrar(self.id, "contrato_entrada", problemas=problemas)
            return _fechar(False)

        # 2. Execução
        try:
            saida = self.executar(ctx)
        except EstagioAbortado as e:
            # Pausa, não falha. O operador precisa decidir.
            r.pausado = True
            r.motivo_pausa = e.motivo
            r.acao_sugerida = e.acao_sugerida
            ctx.registrar(self.id, "pausado", motivo=e.motivo)
            return _fechar(True)
        except ErroDeContrato as e:
            r.problemas = e.problemas
            ctx.registrar(self.id, "contrato_execucao", problemas=e.problemas)
            return _fechar(False)
        except Exception as e:  # noqa: BLE001
            # Defeito de código, não de dado. A distinção importa: o operador
            # não pode corrigir isto na entrada.
            r.problemas = [
                f"exceção não tratada em {type(e).__name__}: {e}",
                traceback.format_exc(limit=3).strip(),
            ]
            ctx.registrar(self.id, "excecao", erro=f"{type(e).__name__}: {e}")
            return _fechar(False)

        # 3. Saída
        problemas = self.validate_output(saida)
        if problemas:
            r.problemas = problemas
            ctx.registrar(self.id, "contrato_saida", problemas=problemas)
            return _fechar(False)

        r.saida = saida
        ctx.registrar_saida(self, saida)
        return _fechar(True)


class PipelineContext:
    """
    Estado compartilhado entre estágios: artefatos, manifesto, trilha.

    REGRA DURA: estágio lê apenas o que está em `artefatos` e escreve apenas o
    seu próprio. Nenhum estágio importa outro estágio. A comunicação é por
    artefato versionado, não por chamada direta — senão o DAG é decorativo.
    """

    # Nome do arquivo de entrada do caso, procurado dentro de `pasta_caso`.
    ARQUIVO_ENTRADA = "caso.json"

    def __init__(self, pasta_caso: Path, dominio_id: str = ""):
        self.pasta = Path(pasta_caso)
        self.dominio_id = dominio_id
        self.artefatos: Dict[str, Dict[str, Any]] = {}
        self.manifesto: Dict[str, Any] = {
            "pasta": str(self.pasta),
            "dominio_id": dominio_id,
            "iniciado_em": datetime.now(timezone.utc).isoformat(),
            "estagios": [],
        }
        self.entrada_do_caso: Dict[str, Any] = {}

    def carregar_entrada_do_caso(self) -> Dict[str, Any]:
        """
        Lê `caso.json` da pasta do caso e devolve as entradas declaradas.

        Sem isto, `artefatos["S0"]` nunca é populado fora dos testes: cada
        estágio injetava o artefato à mão, e o pipeline jamais rodou a partir
        de uma pasta em disco. A ausência era invisível porque os 194 testes
        montavam o contexto manualmente.

        Contrato do arquivo (todos os campos, exceto os marcados opcionais):
            caso_id        — número CNJ com DV válido
            pdf_path       — relativo à pasta do caso, ou absoluto
            arvore_path    — opcional; caminho do arquivo de árvore
            perfil_atuacao — polo do operador; NUNCA inferido
            criado_em      — ISO-8601
            criado_por     — quem declarou o polo

        Caminho relativo é resolvido contra `pasta_caso`. Caminho absoluto é
        respeitado — o operador pode apontar para PDF fora do caso.

        Devolve o dicionário pronto para `artefatos["S0"]`. Arquivo ausente ou
        ilegível NÃO levanta exceção aqui: devolve `{}` para que o S0 reporte
        a falta campo a campo, em vez de estourar traceback antes do DAG.
        """
        arquivo = self.pasta / self.ARQUIVO_ENTRADA
        if not arquivo.is_file():
            self.entrada_do_caso = {}
            return {}

        try:
            bruto = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Ilegível é ausência declarada: o S0 dirá qual campo falta.
            self.entrada_do_caso = {}
            return {}

        if not isinstance(bruto, dict):
            self.entrada_do_caso = {}
            return {}

        def _resolver(chave: str) -> None:
            valor = bruto.get(chave)
            if isinstance(valor, str) and valor and not Path(valor).is_absolute():
                bruto[chave] = str((self.pasta / valor).resolve())

        for chave in ("pdf_path", "arvore_path"):
            _resolver(chave)

        self.entrada_do_caso = bruto
        return dict(bruto)

    def montar_entrada(self, stage: Stage) -> Dict[str, Any]:
        """
        Junta os artefatos dos quais este estágio depende, mais as entradas
        do caso. O estágio não sabe de onde veio cada campo.
        """
        entrada: Dict[str, Any] = {}
        for dep in (stage.depende_de or []):
            if dep not in self.artefatos:
                # Ausência de dependência é erro de entrada, não exceção:
                # o runner quer listar todos os problemas de uma vez.
                continue
            for k, v in self.artefatos[dep].items():
                if k in entrada:
                    # Colisão de chave entre estágios é defeito de contrato.
                    # Sobrescrever em silêncio esconde a inconsistência.
                    raise ErroDeContrato(
                        stage.id, "entrada",
                        [f"chave '{k}' definida por dois estágios e o "
                         f"estágio não declarou precedência"])
                entrada[k] = v
        # Entradas do caso (caso.json) e o artefato de S0 estão disponíveis a
        # todos, com precedência menor: um estágio pode sobrescrever `caso_id`,
        # não o contrário. A ordem importa — o caso.json é a fonte primária
        # para o PRÓPRIO S0, que ainda não tem artefato quando executa.
        for k, v in self.entrada_do_caso.items():
            entrada.setdefault(k, v)
        for k, v in self.artefatos.get("S0", {}).items():
            entrada.setdefault(k, v)
        return entrada

    def registrar(self, estagio: str, evento: str, **dados: Any) -> None:
        self.manifesto["estagios"].append({
            "estagio": estagio,
            "evento": evento,
            "quando": datetime.now(timezone.utc).isoformat(),
            **dados,
        })

    def registrar_saida(self, stage: Stage, saida: Dict[str, Any]) -> None:
        """
        Guarda o artefato e registra seu hash.

        O hash é da forma canônica (chaves ordenadas, sem espaço supérfluo) —
        senão dois artefatos idênticos em semântica pareceriam distintos só
        por ordem de chave, e a comparação de proveniência mentiria.
        """
        import hashlib

        self.artefatos[stage.id] = saida
        canonico = json.dumps(saida, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":"))
        h = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
        self.registrar(stage.id, "saida", hash_sha256=h, bytes=len(canonico))

    def gravar_manifesto(self) -> Path:
        self.manifesto["concluido_em"] = datetime.now(timezone.utc).isoformat()
        caminho = self.pasta / "manifesto.json"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(self.manifesto, ensure_ascii=False, indent=2),
            encoding="utf-8")
        return caminho
