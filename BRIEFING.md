# BRIEFING — Projeto "Sistema Jurídico Portátil" (nome provisório)

## O que existe hoje (medido, não suposto)
- Skills: direito-familia-infancia-idoso (templates 14, checklists, references 10), legislacao-brasil (Planalto/CCivil, validação por conteúdo), stf-jurisprudencia, stj-jurisprudencia (multi-camada, SCON via CDP), tjrj-jurisprudencia, ~50 skills setoriais.
- Acervo de consulta: duas coleções de doutrina e peças, mais uma de jurisprudência magra (45 trechos). Nenhuma vem versionada: acervo é do escritório.
- Pipeline de análise: camada de fatos determinística (extrair_fatos.py, página citada), geração por modelo forte, revisão por modelo DIFERENTE, arbitragem por grep com página/linha. Validado em 8 processos, 141 apontamentos. §4.6: não inferir o polo do operador — extrair sinal documental explícito (7 tentativas de inferir falharam em 119/121).
- Gate de 5 camadas (gate_peca.py, 328 linhas): G3 forma 100% automatizado e REPROVA de verdade; G1 legal e G2 factual NÃO automatizáveis — exigem declaração explícita (--gate1-ok/--gate2-ok), sem a qual reprova. G4 ASR condicional. Gate de IDs: ID órfão da árvore = exit 5, REPROVADO.
- Fluxo PDF→peça em 7 passos com comando exato (fluxo-pdf-a-peca.md).

## Evidência de falhas reais (usar como requisitos)
- 136 peças → 45 citações únicas → 29 conferidas, 16 em aberto, 10 peças com citação furada confirmada. 4 tipos: número errado, número truncado, conteúdo diverso do atribuído, falso positivo de extração.
- Filtros que mentem em silêncio: filtro de UF vivia na query string, não no DOM; 5 cenários ao vivo revelaram UF=SC devolvendo RS.
- Modelo fraco como auditor: nemotron aprovou 11/11 — inapto. Modelo DIFERENTE do gerador é regra.
- Peça pronta não protocolada: 77 peças concluídas no sistema de origem (02/11).

## Lacunas identificadas
L1 sem passo formal de "qual peça é a melhor"; L2 sem rastro de escolha de modelo; L3 templates sem marcadores [OBRIGATÓRIA] executáveis; L4 sem verificação de lastro de citação; L5 RAG jurisprudência magro; L6 ingestão manual ficha-a-ficha; L7 filtros silenciosos.

## Técnicas externas a avaliar
- china-law-mcp (MIT): verify_citation + check_citations_in_text (regex em texto inteiro, valida em lote).
- Legal-RAG (sem licença): lastro por chunk_id; roteador como PREFERÊNCIA não filtro (caso Puttaswamy); artefato portátil chunks.sqlite+bm25.npz com RRF; nada falha fechado.
- local-legal-ai: grounding guard; modo extrativo sem GPU; audit log encadeado por SHA-256; detecção de tipo de documento.
- ctresb/leis: cabeçalho YAML de proveniência + snapshot SHA-256; _falhas.jsonl versionado. (NÃO usar como fonte de citação: RJ=0 normas, 8.253 falhas sem_texto.)
- ai-legal-claude: 5 agentes com pesos — mas score numérico é falsa precisão; recusar.

## O pedido do usuário
Criar UM projeto no git, totalmente reescrito, sem o acúmulo de camadas. Generalista (não só uma área) — a área e o tema se configuram. Recebe PDF + árvore com IDs. Fluxo: converter → relacionar IDs a documentos/movimentos → "advogado experiente" lê, identifica o polo em que atua (ativo/passivo) → define a melhor estratégia → seleciona modelo de peça → elabora teses com doutrina/jurisprudência/legislação validada → gate de 5 camadas → entega. Deve dizer o que funciona, o que não funciona e POR QUÊ. Alvo: escritórios e operadores do direito. Ao apontar o agente para o repo, ele deve saber construir seu próprio sistema jurídico.

## Restrições
- Melhym é cego (NVDA): toda saída deve ser Markdown semântico, listas lineares, sem tabela aninhada em chat (tabela em arquivo .md é ok).
- Nunca confiar em status HTTP; validar por conteúdo.
- Nenhuma citação sem fonte conferida; o que não se confirmou SAI.
- TDD e validação adversarial obrigatórios: procurar o caso que quebra.
