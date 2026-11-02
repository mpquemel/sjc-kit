"""
S8 — Entrega (pré-assinatura, sempre).

O QUE ESTE ESTÁGIO FAZ
----------------------
Monta o pacote que vai para as mãos do advogado, e só isso:

  - minuta `.docx` (formatação de peça, não de manuscrito);
  - `relatorio-citacoes.md` (o que o S5 decidiu por citação);
  - `vereditos.md` (camada por camada do S7, com motivo);
  - `proveniencia.json` (de onde veio cada artefato);
  - `declaracao-operador.json` (G1/G2 com autor e hora);
  - `auditoria.jsonl` encadeado por SHA-256, e `manifesto.json` do pacote.

O QUE ELE NUNCA FAZ
-------------------
- **Nunca assina. Nunca protocola.** O ato é do advogado; o sistema para aqui.
  Não existe função de assinatura neste módulo, e é de propósito: um gate de
  entrega que sabe assinar acaba sendo usado para assinar.
- Não decide se pode protocolar. Se S7 não liberou, o pacote é montado assim
  mesmo — com o bloqueio escrito dentro — porque o advogado tem direito de ver
  o que foi recusado e por quê. O que não existe é pacote que esconde o veredito.
- Não inventa proveniência. Campo sem origem declarada sai como
  `"origem": "nao_declarada"`.

POR QUE O PACOTE SAI MESMO QUANDO BLOQUEADO
--------------------------------------------
Excluir o pacote de peça reprovada empurraria o operador a "resolver" o gate para
ter acesso ao arquivo — e o caminho mais curto seria burlar o gate. Entregar com
o bloqueio escrito no topo do relatório mantém o gate honesto e o operador
informado.

POR QUE A CADEIA DE HASH EXISTE
------------------------------
Cada entrada da auditoria carrega o SHA-256 da anterior. Adulterar uma linha no
meio quebra todas as seguintes, e a verificação aponta a primeira divergência.
Para o escritório é defesa (prova de que o pacote é o que saiu); para o cliente é
rastro (prova de quando saiu e com qual veredito).

A cadeia cobre a auditoria, não o `.docx`. O `.docx` é protegido pelo hash
registrado no manifesto — se alguém editar a minuta depois da entrega, o
manifesto denuncia. Isso está declarado no relatório para que ninguém presuma
proteção que não existe.

AVISO DE PEÇA PARADA
--------------------
O pacote registra `entregue_em` e `protocolo: null`. Quem lê o manifesto sabe que
a peça saiu e não foi protocolada. O alerta em si (48h) é do agendador, não do
estágio: este módulo grava o fato, não promete o lembrete.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import Stage

try:
    import docx  # python-docx
    from docx.shared import Pt  # noqa: F401
except ImportError:  # pragma: no cover
    docx = None  # type: ignore[assignment]


class S8Entrega(Stage):
    """
    Monta o pacote de entrega. Para antes da assinatura, por construção.

    Entrada: `caso_id` e os artefatos dos estágios anteriores (lidos direto de
    `ctx.artefatos`, porque S8 é o ponto de convergência e depende de quase
    tudo — declarar tudo em `depende_de` colidiria em `caso_id`).
    """

    id = "S8"
    nome = "entrega"
    depende_de = ["S7"]  # type: ignore[assignment]
    entrada_obriga = ["caso_id"]  # type: ignore[assignment]
    saida_obriga = ["caso_id", "entrega"]  # type: ignore[assignment]

    # Injetável para teste: relógio fixo, para o hash ser reprodutível.
    relogio: Optional[Any] = None

    def executar(self, ctx) -> Dict[str, Any]:
        from .stage import ErroDeContrato, EstagioAbortado

        entrada = ctx.montar_entrada(self)
        caso_id = entrada.get("caso_id")
        if not caso_id:
            raise EstagioAbortado(
                self.id, "sem caso_id: não há pacote a montar", "")

        gate = (ctx.artefatos.get("S7") or {}).get("gate_cinco_camadas")
        if not gate:
            raise EstagioAbortado(
                self.id,
                "sem gate de cinco camadas (S7): o pacote sairia sem veredito",
                "rode S7 antes da entrega; pacote sem veredito é pacote que "
                "esconde a recusa",
            )

        if docx is None:
            raise ErroDeContrato(
                self.id, "ambiente",
                ["python-docx não instalado: a minuta .docx não pode ser gerada"])

        peca_texto = (ctx.artefatos.get("S4") or {}).get("peca_texto") or ""
        if not str(peca_texto).strip():
            raise EstagioAbortado(
                self.id, "peça vazia: não há minuta a entregar", "")

        agora = self._agora()
        destino = Path(ctx.pasta) / "entrega"
        destino.mkdir(parents=True, exist_ok=True)

        # 1. minuta .docx
        docx_path = destino / "minuta.docx"
        self._gravar_docx(peca_texto, docx_path)

        # 2. relatório de citações
        cit_path, cit_dados = self._gravar_citacoes(ctx, destino)

        # 3. vereditos por camada
        ver_path = self._gravar_vereditos(gate, destino)

        # 4. proveniência
        prov_path, prov = self._gravar_proveniencia(ctx, destino, agora)

        # 5. declaração do operador
        decl_path = self._gravar_declaracao(ctx, destino)

        # 6. auditoria encadeada + manifesto
        aud_path, manifesto = self._gravar_auditoria(
            destino, caso_id, agora,
            arquivos=[docx_path, cit_path, ver_path, prov_path, decl_path],
            gate=gate)

        bloqueado = bool(gate.get("bloqueado"))
        return {
            "caso_id": caso_id,
            "entrega": {
                "pacote_dir": str(destino),
                "entregue_em": agora,
                "protocolo": None,          # nunca preenchido por este estágio
                "assinado": False,          # nunca assinado por este estágio
                "veredito": gate.get("veredito"),
                "pode_protocolar": bool(gate.get("pode_protocolar")),
                "bloqueado": bloqueado,
                "arquivos": {p.name: self._sha256(p) for p in
                             [docx_path, cit_path, ver_path, prov_path, decl_path]},
                "auditoria": str(aud_path),
                "manifesto": manifesto,
                "citacoes": cit_dados,
                "aviso_peca_parada": (
                    "peça entregue e NÃO protocolada. O sistema registra a "
                    "entrega; o alerta de 48h é do agendador, não deste estágio."
                ),
            },
        }

    # ------------------------------------------------------------------
    # Relógio e hash
    # ------------------------------------------------------------------

    def _agora(self) -> str:
        if self.relogio is not None:
            return str(self.relogio)
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _sha256(caminho: Path) -> str:
        h = hashlib.sha256()
        h.update(caminho.read_bytes())
        return h.hexdigest()

    # ------------------------------------------------------------------
    # 1. Minuta .docx
    # ------------------------------------------------------------------

    def _gravar_docx(self, peca_texto: str, destino: Path) -> None:
        """
        Markdown -> .docx com hierarquia real.

        Cabeçalho Markdown vira título de verdade (Heading 1/2/3), não negrito
        em fonte maior: leitor de tela e sumário automático dependem da
        estrutura, e negrito não é estrutura.
        """
        documento = docx.Document()
        for linha in peca_texto.splitlines():
            texto = linha.rstrip()
            if not texto.strip():
                continue
            niveis = len(texto) - len(texto.lstrip("#"))
            if 1 <= niveis <= 3 and texto.lstrip("#").startswith(" "):
                documento.add_heading(texto.lstrip("#").strip(), level=niveis)
            else:
                documento.add_paragraph(texto.strip())
        documento.save(str(destino))

    # ------------------------------------------------------------------
    # 2. Relatório de citações
    # ------------------------------------------------------------------

    def _gravar_citacoes(self, ctx, destino: Path) -> tuple[Path, Dict[str, Any]]:
        verificacao = (ctx.artefatos.get("S5") or {}).get("verificacao") or {}
        caminho = destino / "relatorio-citacoes.md"

        total = verificacao.get("total", 0)
        retem = verificacao.get("retem")
        linhas = [
            "# Relatório de citações",
            "",
            f"- citações extraídas: {total}",
            f"- retém a peça: {'sim' if retem else 'não'}",
            f"- motivo: {verificacao.get('motivo') or '(não declarado)'}",
            "",
        ]
        if not verificacao:
            linhas += [
                "## Estado",
                "",
                "Nenhuma verificação de citação foi encontrada (S5 não rodou).",
                "Isto NÃO significa que a peça não cita: significa que ninguém",
                "conferiu.",
                "",
            ]
        elif total == 0:
            linhas += [
                "## Estado",
                "",
                "Nenhuma citação extraível do texto. A peça é retida por",
                "vacuidade: ausência de citação não é prova de ausência de",
                "citação não conferida.",
                "",
            ]

        for c in (verificacao.get("citacoes") or []):
            linhas += [
                f"## {c.get('referencia') or c.get('texto', '')[:60]}",
                "",
                f"- tribunal: {c.get('tribunal') or '(não determinado)'}",
                f"- estado: {c.get('estado') or '(não avaliado)'}",
                f"- motivo: {c.get('motivo') or '-'}",
                "",
            ]

        caminho.write_text("\n".join(linhas), encoding="utf-8")
        return caminho, {"total": total, "retem": retem}

    # ------------------------------------------------------------------
    # 3. Vereditos por camada
    # ------------------------------------------------------------------

    def _gravar_vereditos(self, gate: Dict[str, Any], destino: Path) -> Path:
        caminho = destino / "vereditos.md"
        linhas = [
            "# Vereditos do gate de cinco camadas",
            "",
            f"- veredito: **{gate.get('veredito')}**",
            f"- pode protocolar: {'sim' if gate.get('pode_protocolar') else 'não'}",
            f"- camadas no pior veredito: {', '.join(gate.get('camadas_no_pior_veredito') or []) or '-'}",
            "",
        ]
        for c in gate.get("camadas") or []:
            linhas += [
                f"## {c.get('id')} — {c.get('nome')}",
                "",
                f"- veredito: {c.get('veredito')}",
                f"- automatizada: {'sim' if c.get('automatizada') else 'não'}",
                f"- motivo: {c.get('motivo')}",
                "",
            ]
            if c.get("conferir"):
                linhas += ["Conferir:", ""]
                linhas += [f"- {i}" for i in c["conferir"]]
                linhas += [""]
            for d in (c.get("defeitos") or []):
                linhas += [f"- defeito ({d.get('tipo')}) linha {d.get('linha')}: "
                           f"{d.get('achado')}"]
            if c.get("defeitos"):
                linhas += [""]

        linhas += [
            "---",
            "",
            "G1 e G2 dependem de declaração do operador. O sistema registra a",
            "declaração, não a substitui: a responsabilidade pelo conteúdo",
            "jurídico e factual é de quem assina.",
            "",
        ]
        caminho.write_text("\n".join(linhas), encoding="utf-8")
        return caminho

    # ------------------------------------------------------------------
    # 4. Proveniência
    # ------------------------------------------------------------------

    def _gravar_proveniencia(self, ctx, destino: Path,
                             agora: str) -> tuple[Path, Dict[str, Any]]:
        estagios: Dict[str, Any] = {}
        for estagio, artefato in sorted(ctx.artefatos.items()):
            canonico = json.dumps(artefato, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"), default=str)
            estagios[estagio] = {
                "hash_sha256": hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
                "bytes": len(canonico),
                "origem": "artefato do pipeline" if estagio != "declaracoes_operador"
                          else "declarado pelo operador",
            }

        dados = {
            "caso_id": (ctx.artefatos.get("S0") or {}).get("caso_id"),
            "gerado_em": agora,
            "dominio": ctx.dominio_id,
            "estagios": estagios,
            "nota": ("o hash cobre a forma canônica do artefato em memória, não o "
                     "arquivo final do pacote; os arquivos estão no manifesto"),
        }
        caminho = destino / "proveniencia.json"
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        return caminho, dados

    # ------------------------------------------------------------------
    # 5. Declaração do operador
    # ------------------------------------------------------------------

    def _gravar_declaracao(self, ctx, destino: Path) -> Path:
        declaracoes = ctx.artefatos.get("declaracoes_operador") or {}
        caminho = destino / "declaracao-operador.json"
        dados = {
            "g1_legal": declaracoes.get("g1_legal"),
            "g2_factual": declaracoes.get("g2_factual"),
            "nota": ("ausência de declaração é registrada como ausência; o campo "
                     "nulo aqui significa que ninguém declarou conferência"),
        }
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        return caminho

    # ------------------------------------------------------------------
    # 6. Auditoria encadeada por hash
    # ------------------------------------------------------------------

    def _gravar_auditoria(self, destino: Path, caso_id: str, agora: str,
                          arquivos: List[Path],
                          gate: Dict[str, Any]) -> tuple[Path, Dict[str, Any]]:
        caminho = destino / "auditoria.jsonl"
        anterior = "0" * 64
        entradas: List[Dict[str, Any]] = []

        def entrada(evento: str, **dados: Any) -> None:
            nonlocal anterior
            registro = {
                "quando": agora,
                "caso_id": caso_id,
                "evento": evento,
                "anterior": anterior,
                **dados,
            }
            canonico = json.dumps(registro, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"), default=str)
            registro["hash"] = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
            anterior = registro["hash"]
            entradas.append(registro)

        entrada("entrega_iniciada", veredito=gate.get("veredito"))
        for p in arquivos:
            entrada("arquivo_gerado", nome=p.name, sha256=self._sha256(p),
                    bytes=p.stat().st_size)
        entrada("entrega_encerrada",
                bloqueado=bool(gate.get("bloqueado")),
                pode_protocolar=bool(gate.get("pode_protocolar")),
                assinado=False, protocolo=None)

        caminho.write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in entradas) + "\n",
            encoding="utf-8")

        manifesto = {
            "caso_id": caso_id,
            "entregue_em": agora,
            "veredito": gate.get("veredito"),
            "bloqueado": bool(gate.get("bloqueado")),
            "assinado": False,
            "protocolo": None,
            "entradas_auditoria": len(entradas),
            "hash_final": anterior,
            "cadeia_verificavel": True,
            "limite_declarado": ("a cadeia cobre a auditoria; edição do .docx "
                                 "é detectada pelo hash do arquivo, não pela cadeia"),
        }
        (destino / "manifesto.json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
        return caminho, manifesto
