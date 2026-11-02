"""
Testes do validador de domínio — o detector de acoplamento.

Regra herdada do método (§5): teste que só produz sucesso não validou nada.
Por isso cada teste aqui primeiro monta o caso que DEVIA reprovar e confirma
que reprova. Um validador que aprova tudo é pior que nenhum: dá selo.

O teste central é `t_penal_esqueleto_aprovado_sem_tocar_nucleo`: ele prova a
tese do produto — declarar um domínio novo não exige código em core/.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from core.dominio import validador as V  # noqa: E402

DOMINIOS = RAIZ / "dominios"

resultados = []


def teste(nome, fn):
    try:
        fn()
        resultados.append((True, nome, ""))
    except AssertionError as e:
        resultados.append((False, nome, str(e)))
    except Exception as e:  # noqa: BLE001
        resultados.append((False, nome, f"{type(e).__name__}: {e}"))


# ---------------------------------------------------------------------------
# Testes de aceitação: os domínios reais do repositório
# ---------------------------------------------------------------------------

def t_penal_esqueleto_aprovado_sem_tocar_nucleo():
    """
    A tese do produto, em um teste.

    penal/ foi escrito só com YAML e Markdown. Se o validador precisasse de
    campo novo em core/ ou de import de dominios.*, este teste falharia.
    """
    r = V.validar(str(DOMINIOS / "penal"))
    assert r["veredito"] == "ESQUELETO", f"esperado ESQUELETO, obtido {r['veredito']}"
    assert r["arquivos"]["ausentes"] == [], f"faltam arquivos: {r['arquivos']['ausentes']}"
    assert r["campos_ausentes"] == [], f"campos ausentes: {r['campos_ausentes']}"
    assert r["pendencias"], "esqueleto sem pendência declarada é suspeito: nada foi decidido?"


def t_prompts_genericos_sao_avisados():
    """Prompt copiado do template sem adaptação precisa aparecer como aviso."""
    r = V.validar(str(DOMINIOS / "penal"))
    avisos = " ".join(r["avisos"])
    assert "prompt_do_dominio: generico" in avisos, \
        "prompt não adaptado passou em silêncio — o aviso prometido não existe"


def t_sem_vocabulario_institucional():
    """Decisão 5: nem dominios/ nem core/ podem citar vocabulário institucional."""
    for d in ("penal", "_template"):
        r = V.validar(str(DOMINIOS / d))
        assert not r["vocabulario_proibido"], \
            f"{d} tem vocabulário proibido: {r['vocabulario_proibido'][:3]}"


def t_template_valido():
    """O próprio template precisa ser válido, senão ensina errado."""
    r = V.validar(str(DOMINIOS / "_template"))
    assert r["arquivos"]["ausentes"] == [], f"template incompleto: {r['arquivos']['ausentes']}"


# ---------------------------------------------------------------------------
# Testes adversariais: o validador precisa REPROVAR
# ---------------------------------------------------------------------------

def _copia_temporaria(nome):
    tmp = Path(tempfile.mkdtemp(prefix="sjc-val-"))
    destino = tmp / nome
    shutil.copytree(DOMINIOS / "penal", destino)
    return tmp, destino


def t_campo_ausente_reprova():
    """Apagar um campo obrigatório de dominio.yaml tem de reprovar."""
    tmp, d = _copia_temporaria("penal")
    try:
        p = d / "dominio.yaml"
        texto = p.read_textl() if False else p.read_text(encoding="utf-8")
        # Remove a linha de `acervo:` e o bloco que a segue (2 espaços)
        linhas = texto.splitlines()
        saida, pulando = [], False
        for ln in linhas:
            if ln.startswith("acervo:"):
                pulando = True
                continue
            if pulando and (ln.startswith(" ") or ln.strip() == ""):
                continue
            pulando = False
            saida.append(ln)
        p.write_text("\n".join(saida) + "\n", encoding="utf-8")

        r = V.validar(str(d))
        assert r["veredito"] == "REPROVADO", f"esperado REPROVADO, obtido {r['veredito']}"
        assert "acervo" in " ".join(r["campos_ausentes"]), \
            f"campo acervo não foi apontado: {r['campos_ausentes']}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_arquivo_ausente_reprova():
    """Sem estrategia.yaml o domínio não pode rodar — e o validador tem de dizer."""
    tmp, d = _copia_temporaria("penal")
    try:
        (d / "estrategia.yaml").unlink()
        r = V.validar(str(d))
        assert r["veredito"] == "REPROVADO", f"esperado REPROVADO, obtido {r['veredito']}"
        assert "estrategia.yaml" in r["arquivos"]["ausentes"], \
            f"arquivo ausente não apontado: {r['arquivos']['ausentes']}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_yaml_invalido_nao_quebra():
    """
    YAML malformado tem de virar AVISO legível, não traceback.
    Validador que explode no caso ruim não serve para o operador corrigir.
    """
    tmp, d = _copia_temporaria("penal")
    try:
        (d / "estrategia.yaml").write_text("regras: [\n  - id: quebrado\n    x: :\n",
                                           encoding="utf-8")
        r = V.validar(str(d))
        assert any("YAML inválido" in a for a in r["avisos"]), \
            f"YAML malformado não gerou aviso: {r['avisos']}"
        assert r["veredito"] in ("REPROVADO", "ESQUELETO"), "veredito inesperado"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_vocabulario_proibido_e_detectado():
    """
    O detector de vocabulário tem de detectar. Escrevo o termo proibido de
    propósito e exijo que apareça — se não aparecer, a checagem é teatro.
    """
    tmp, d = _copia_temporaria("penal")
    try:
        (d / "nota.md").write_text("Este texto diz assistido por engano.\n",
                                   encoding="utf-8")
        r = V.validar(str(d))
        assert r["vocabulario_proibido"], "termo proibido não foi detectado"
        assert r["vocabulario_proibido"][0]["termo"] == "assistido", \
            f"termo errado detectado: {r['vocabulario_proibido']}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_pendente_distingue_de_ausente():
    """
    `a preencher` é estado declarado; ausente é buraco. Os dois exigem ação
    diferente do operador e não podem ser confundidos no relatório.
    """
    tmp, d = _copia_temporaria("penal")
    try:
        r = V.validar(str(d))
        assert r["pendencias"], "pendências `a preencher` não foram listadas"
        assert r["campos_ausentes"] == [], "pendência foi confundida com ausência"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_exit_code_distingue_esqueleto_de_reprovado():
    """
    O CI precisa distinguir 'esqueleto declarado' (esperado em penal) de
    'reprovado' (defeito). Mesmo exit code para os dois esconde regressão.
    """
    assert V.main([str(DOMINIOS / "penal")]) == 0, "penal deveria sair 0 (esqueleto)"
    tmp, d = _copia_temporaria("penal")
    try:
        (d / "estrategia.yaml").unlink()
        assert V.main([str(d)]) == 1, "reprovado deveria sair 1"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_relatorio_serializavel():
    """O relatório vai para arquivo e para CI: precisa ser JSON puro."""
    r = V.validar(str(DOMINIOS / "penal"))
    texto = json.dumps(r, ensure_ascii=False)
    assert json.loads(texto) == r, "relatório não sobreviveu ao round-trip JSON"


TESTES = [
    ("t_penal_esqueleto_aprovado_sem_tocar_nucleo", t_penal_esqueleto_aprovado_sem_tocar_nucleo),
    ("t_prompts_genericos_sao_avisados", t_prompts_genericos_sao_avisados),
    ("t_sem_vocabulario_institucional", t_sem_vocabulario_institucional),
    ("t_template_valido", t_template_valido),
    ("t_campo_ausente_reprova", t_campo_ausente_reprova),
    ("t_arquivo_ausente_reprova", t_arquivo_ausente_reprova),
    ("t_yaml_invalido_nao_quebra", t_yaml_invalido_nao_quebra),
    ("t_vocabulario_proibido_e_detectado", t_vocabulario_proibido_e_detectado),
    ("t_pendente_distingue_de_ausente", t_pendente_distingue_de_ausente),
    ("t_exit_code_distingue_esqueleto_de_reprovado", t_exit_code_distingue_esqueleto_de_reprovado),
    ("t_relatorio_serializavel", t_relatorio_serializavel),
]


def main():
    print("=" * 70)
    print(" VALIDADOR DE DOMÍNIO — TESTES")
    print("=" * 70)
    for nome, fn in TESTES:
        teste(nome, fn)
    for ok, nome, msg in resultados:
        print(f"[{'PASS' if ok else 'FAIL'}] {nome}" + (f"\n       {msg}" if msg else ""))
    aprovados = sum(1 for ok, _, _ in resultados if ok)
    print("-" * 70)
    print(f"{aprovados}/{len(resultados)} aprovados")
    return 0 if aprovados == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
