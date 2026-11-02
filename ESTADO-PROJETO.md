# ESTADO DO PROJETO SJC — sjc-kit

> Ponto de retomada. Se a conversa for reiniciada, leia este arquivo primeiro, depois
> `ESPECIFICACAO-PRODUTO.md` e `LIMITES.md`.
> Última atualização: 02/11/2026, 12:15 (BRT)

## Identidade

- **Produto:** Sistema Jurídico Customizável (SJC)
- **Repositório:** `sjc-kit`
- **Público:** escritórios de advocacia e operadores do direito, qualquer área, qualquer polo.
  **Não é da Defensoria Pública nem do Ministério Público.** Defensor, estagiário e residente
  são usuários possíveis, não premissa.
- **Autoria:** Melhym Pereira Quemel (concepção, método, acessibilidade de origem) + Basir.

## Decisões fechadas

1. Nome SJC, repo `sjc-kit`.
2. Domínio de demonstração: **família** (fundamentos já existentes).
3. Esqueleto de **penal vazio desde o primeiro commit** — detector de acoplamento.
4. Acessibilidade: princípio declarado + checklist na v0.1; auditoria formal com usuário real
   na v0.2; perfis adicionais na v0.3.
5. Nomenclatura proibida no núcleo: `assistido`, `defensoria`, `mp`, `polo_defensoria`,
   `numero_verde`, `vara_familia`, `pje`, `eproc`.
   Usar: `cliente`, `polo_operador`, `identificador_externo`, `orgao_julgador`.
6. Integração por **adaptadores de entrada opcionais**: `pje/`, `eproc/`, `projudi/` e afins.
   Nenhum sistema de tribunal no núcleo. O núcleo funciona com PDF + árvore em mão.
   **O Sistema Verde não é mencionado no produto** (instrução expressa do Melhym, 02/11).

## Documentos escritos e aprovados

| Arquivo | Estado |
|---|---|
| `ESPECIFICACAO-PRODUTO.md` | v0.2, aprovada; 416+ linhas; decisões, fluxo S0–S8, árvore proposta |
| `LIMITES.md` | escrito e **aprovado por Melhym em 02/11** |
| `PARECER-1-ARQUITETO.md` | 1.027 linhas |
| `PARECER-2-JURISTA.md` | 504 linhas |
| `PARECER-3-CRITICO.md` | 150 linhas |

Backups: `ESPECIFICACAO-PRODUTO.md.bak-20261102-1145`, `.bak-20261102-1155`.

## Próximo passo — bloqueado apenas por decisão de onde escrever

**Escrever `METODO.md`** — camada 1, produto de entrada gratuito. Explica *como se faz* e
*por que cada escolha foi tomada*, com os números reais (119/121 do polo; modelo auditor que
aprovou 11/11; 10 peças com citação furada em 136; filtro de UF que lia o espelho errado).
Regra: limite sem número não entra.

Depois dele, nesta ordem:
1. `README.md` (humano) e `AGENT.md` (agente, com autoavaliação de pré-requisitos).
2. Portão de citação (`core/`) com as 10 peças furadas como fixtures de aceitação.
3. Fechar as 16 citações em aberto.
4. Etapa 0 sem código: passo de acompanhamento das 77 peças entregues e não protocoladas.

## Pendências abertas

- 16 citações em aberto a fechar.
- Catálogo de decisão de peça em YAML para família (a partir dos gatilhos do PARECER-2).
- Lastro por trecho (`chunk_id`) na doutrina de família + cabeçalho de proveniência SHA-256.
- Árvore de diretórios apresentada ao Melhym — **aguardando aprovação formal** antes de código.

## Regras de operação que não mudam

- O sistema pergunta o polo e grava a declaração; nunca infere.
- Nunca assina, nunca protocola: entrega é sempre pré-assinatura.
- Nada de nota 0–100: vereditos discretos com evidência + três frações auditáveis.
- Roteador de área é preferência de ranking, nunca filtro excludente.
- Citação não confirmada retém a peça e marca a tese como descoberta.
- Código de gate e regras de reprovação são imutáveis por instrução de setup.
- Backup antes de qualquer edição em arquivo de código ou configuração.
