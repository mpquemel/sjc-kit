# =============================================================================
# SJC-KIT — Makefile
#
# Regra deste arquivo: nenhum alvo pode mentir. Se um alvo depende de algo que
# não existe, ele DIZ o que falta e sai com código de erro — em vez de falhar
# de forma confusa ou, pior, passar em silêncio.
#
# Saída legível por leitor de tela: uma linha por resultado, sem barra
# animada, sem cor, sem cursor de controle.
# =============================================================================

PYTHON   ?= python3
DOMINIO  ?=

# Suites de teste, na ordem em que rodam. Ordem importa: o portão de citação é
# mais fundamental que o pipeline, porque o pipeline o consome.
SUITES = \
	core/citacoes/tests/test_citacoes.py \
	core/citacoes/tests/test_adaptador.py \
	core/citacoes/tests/test_fixtures.py \
	core/dominio/tests/test_validador.py \
	core/pipeline/tests/test_runner.py \
	core/pipeline/tests/test_s1_conversao.py \
	core/pipeline/tests/test_s2_vinculacao.py \
	core/pipeline/tests/test_s3_estrategia.py \
	core/pipeline/tests/test_s4_redacao.py \
	core/pipeline/tests/test_s5_citacoes.py \
	core/pipeline/tests/test_s6_gates.py \
	core/pipeline/tests/test_s7_gate_cinco_camadas.py \
	core/pipeline/tests/test_s8_entrega.py \
	core/pipeline/tests/test_cnj.py \
	core/tests/test_fronteira.py

DOMINIOS_DECLARADOS = dominios/familia dominios/penal dominios/_template

.PHONY: help verify testes dominio-validar dominio-listar demo adversariais \
        limites limpar

# ---------------------------------------------------------------------------
help:
	@echo "SJC-KIT - alvos disponíveis"
	@echo
	@echo "  make bootstrap           prepara e confere o ambiente"
	@echo "  make verify              roda tudo (bootstrap + testes + domínios)"
	@echo "  make testes              roda só as suítes de teste"
	@echo "  make dominio-listar      lista domínios e seus vereditos"
	@echo "  make validar-dominio DOMINIO=<id>   valida um domínio"
	@echo "  make adversariais       confere que as fixtures adversárias reprovam"
	@echo "  make demo                processa casos/_exemplo/ ponta a ponta"
	@echo "  make limites             mostra o que o kit NÃO faz"
	@echo "  make limpar              remove caches de bytecode"

# ---------------------------------------------------------------------------
bootstrap:
	@echo "=== BOOTSTRAP ==="
	@$(PYTHON) scripts/bootstrap.py

# ---------------------------------------------------------------------------
testes:
	@echo "=== TESTES ==="
	@falhas=0; total=0; \
	for suite in $(SUITES); do \
		if [ ! -f "$$suite" ]; then \
			echo "  [FALHA] suíte ausente: $$suite"; \
			falhas=$$((falhas+1)); \
			continue; \
		fi; \
		saida=$$($(PYTHON) "$$suite" 2>&1); \
		codigo=$$?; \
		if [ $$codigo -eq 0 ]; then \
			echo "  [OK   ] $$suite"; \
		else \
			echo "  [FALHA] $$suite";        \
			echo "$$saida" | tail -6 | sed 's/^/           /'; \
			falhas=$$((falhas+1)); \
		fi; \
		total=$$((total+1)); \
	done; \
	echo; \
	if [ $$falhas -eq 0 ]; then \
		echo "RESULTADO: $$total suítes aprovadas, 0 falhas"; \
	else \
		echo "RESULTADO: $$falhas de $$total suítes FALHARAM"; \
		exit 1; \
	fi

# ---------------------------------------------------------------------------
dominio-listar:
	@echo "=== DOMÍNIOS ==="
	@for d in $(DOMINIOS_DECLARADOS); do \
		if [ ! -d "$$d" ]; then \
			echo "  [FALTA] $$d"; \
			continue; \
		fi; \
		$(PYTHON) core/dominio/validador.py "$$d" 2>&1 \
			| grep -E "^VEREDITO" | sed "s|^|  $$d  |"; \
	done

validar-dominio:
	@if [ -z "$(DOMINIO)" ]; then \
		echo "ERRO: informe o domínio. Exemplo:"; \
		echo "  make validar-dominio DOMINIO=penal"; \
		echo; \
		echo "Domínios existentes:"; \
		for d in $(DOMINIOS_DECLARADOS); do echo "  $$(basename $$d)"; done; \
		exit 1; \
	fi
	@if [ ! -d "dominios/$(DOMINIO)" ]; then \
		echo "ERRO: dominios/$(DOMINIO) não existe."; \
		echo "Crie a partir do template: cp -r dominios/_template dominios/$(DOMINIO)"; \
		exit 1; \
	fi
	@$(PYTHON) core/dominio/validador.py "dominios/$(DOMINIO)"

# ---------------------------------------------------------------------------
# Adversariais: critério INVERTIDO — sucesso é o caso REPROVAR.
adversariais:
	@echo "=== CASOS ADVERSARIAIS ==="
	@echo "Critério invertido: cada caso adversário DEVE reprovar."
	@echo
	@$(PYTHON) scripts/conferir_adversariais.py

# ---------------------------------------------------------------------------
demo:
	@echo "=== DEMO ==="
	@if [ ! -d "casos/_exemplo" ]; then \
		echo "  [FALTA] casos/_exemplo/ não existe."; \
		echo; \
		echo "  O demo exige um caso sintético versionado, sem dado de cliente."; \
		echo "  Enquanto ele não existir, este alvo NÃO processa nada — e diz isso"; \
		echo "  em vez de fingir que rodou."; \
		exit 2; \
	fi
	@$(PYTHON) -m scripts.demo casos/_exemplo --dominio $${DOMINIO:-familia}

# ---------------------------------------------------------------------------
limites:
	@if [ -f LIMITES.md ]; then \
		sed -n '1,60p' LIMITES.md; \
		echo; \
		echo "(texto completo em LIMITES.md)"; \
	else \
		echo "LIMITES.md ausente — isso é, ele mesmo, um limite não declarado."; \
		exit 1; \
	fi

# ---------------------------------------------------------------------------
verify: bootstrap testes dominio-listar
	@echo
	@echo "=== VERIFY CONCLUÍDO ==="
	@echo "Ambiente, testes e domínios declarados conferidos."
	@echo "Isto NÃO significa que o sistema sabe jurídico: significa que ele roda."
	@echo "Ver LIMITES.md para o que segue fora."

limpar:
	@find . -name "__pycache__" -type d -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true
	@echo "caches de bytecode removidos"
