# ESTADO DO PROJETO SJC — sjc-kit

> Ponto de retomada. Se a conversa for reiniciada, leia este arquivo primeiro, depois
> `ESPECIFICACAO-PRODUTO.md` e `LIMITES.md`.
> Última atualização: 02/11/2026, 15:50 (BRT)

## Identidade

- **Produto:** Sistema Jurídico Customizável (SJC)
- **Repositório:** `sjc-kit`
- **Público:** escritórios de advocacia e operadores do direito, qualquer área, qualquer polo.
  **Não é de órgão público nenhum.** Servidor público e estagiário são usuários
  possíveis, não premissa.
- **Autoria:** Melhym Pereira Quemel (concepção, método, acessibilidade de origem).
  Ver `AUTORES.md`.

## Decisões fechadas

1. Nome SJC, repo `sjc-kit`.
2. Domínio de demonstração: **família** (fundamentos já existentes).
3. Esqueleto de **penal vazio desde o primeiro commit** — detector de acoplamento.
4. Acessibilidade: princípio declarado + checklist na v0.1; auditoria formal com usuário real
   na v0.2; perfis adicionais na v0.3.
5. Nomenclatura proibida no núcleo: `assistido`, `numero_verde`, `pje`, `eproc`.
   Usar: `cliente`, `polo_operador`, `identificador_externo`, `orgao_julgador`.
6. Integração por **adaptadores de entrada opcionais**: `pje/`, `eproc/`, `projudi/` e afins.
   Nenhum sistema de tribunal no núcleo. O núcleo funciona com PDF + árvore em mão.

## Documentos no repositório público

| Arquivo | Estado |
|---|---|
| `ESPECIFICACAO-PRODUTO.md` | v0.2, aprovada; decisões, fluxo S0–S8, árvore proposta |
| `LIMITES.md` | escrito e **aprovado por Melhym em 02/11** |
| `METODO.md` | escrito |
| `README.md` | reescrito em 02/11 contra o código; números reconferidos |
| `AUTORES.md` | autoria, titulação e contato |
| `GUIA-DOMINIO.md` | procedimento de domínio novo, com as armadilhas medidas |

Fora do repositório público, por decisão: pareceres internos de agentes
(`PARECER-1..3`), backups e anotações de trabalho. Permanecem no diretório
privado de origem.

## Implementação — estado em 02/11/2026

| Item | Estado |
|---|---|
| Pipeline S0–S8 | **completo**, registrado em `core/pipeline/stages.py` |
| Testes | 194 em 13 suítes, todas verdes |
| Casos adversariais | 11 (6 família, 5 penal), todos recusados como exigido |
| Domínio família | `operacional_parcial`; 22 pendências declaradas |
| Domínio penal | esqueleto declarado, 22 pendências; detector de acoplamento |
| Regras de gate, família | 6 declaradas, **3 executáveis** por programa |
| `make demo` | alvo existe, **não processa**: falta `casos/_exemplo/` |
| Contrato de dependência (`import-linter`) | **não existe** — pendente |
| Portão de citação | funcional fora de rede; adaptador de fonte é opcional |

## Próximos passos, em ordem

1. **Fixtures de caso sintético** (`casos/_exemplo/`) para destravar `make demo`.
2. **Contrato automatizado de dependência** — hoje a fronteira é verificada por
   disciplina e pelo detector penal.
3. **Avaliadores para as 3 regras de gate restantes** de família, ou rebaixá-las
   a prosa declarada no catálogo.
4. Fechar as pendências declaradas de família e penal (22 + 22).
5. Etapa 0 sem código: acompanhamento de peças entregues e não protocoladas.

## Pendências abertas

- 16 citações em aberto a fechar.
- Lastro por trecho (`chunk_id`) na doutrina de família + cabeçalho de proveniência SHA-256.
- Coletores de fonte (`SJC_FONTES`) — opcionais, frágeis, fora do kit.

## Regras de operação que não mudam

- O sistema pergunta o polo e grava a declaração; nunca infere.
- Nunca assina, nunca protocola: entrega é sempre pré-assinatura.
- Nada de nota 0–100: vereditos discretos com evidência + três frações auditáveis.
- Roteador de área é preferência de ranking, nunca filtro excludente.
- Citação não confirmada retém a peça e marca a tese como descoberta.
- Código de gate e regras de reprovação são imutáveis por instrução de setup.
- Backup antes de qualquer edição em arquivo de código ou configuração.
