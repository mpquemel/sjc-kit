# Sistema Jurídico Customizável (SJC) — `sjc-kit`

> Um método para construir um sistema jurídico que não mente — entregue como kit que um
> agente de IA lê e instancia no escritório.

**Antes de qualquer coisa, o limite:** este kit não substitui juízo profissional, **não
assina, não protocola e não garante acerto**. Ele garante uma coisa só, e é verificável:
**o erro fica visível antes da assinatura.**

**Depois do limite, a origem:** este kit foi concebido por um advogado cego que trabalha com
leitor de tela. A acessibilidade não é recurso adicional — é a condição em que o sistema
nasceu. Ver [Acessibilidade](#10-acessibilidade).

---

## 1. O que é, em três camadas

| Camada | O que é | Custo |
|---|---|---|
| **Método** | `METODO.md` — como se faz e por que cada escolha foi tomada, com os números reais | Gratuito, público |
| **Kit** | Este repositório — núcleo pequeno e testável, domínio de demonstração, esqueleto de um segundo domínio | Gratuito, aberto |
| **Instanciação** | O serviço: o agente lê o kit, pergunta a área, constrói o domínio do escritório | Pago por projeto |

O ativo não é o texto gerado. É o **registro de onde a IA mente** — com número, página e
reprodução — e o procedimento que impede que isso chegue à assinatura.

---

## 2. Para quem é, e para quem não é

**É para:** sócio de escritório que assina peça e responde por ela; advogado autônomo com
volume acima da capacidade de revisão; escritório pequeno sem equipe de tecnologia;
defensorias e procuradorias que queiram o mesmo método sem depender deste autor.

**Não é para:** quem quer substituir o advogado; quem quer "IA que redige sozinha"; quem não
vai ler o relatório de verificação; quem processa dados de cliente em API de terceiro sem
base legal.

Não é atrelado a Defensoria Pública nem a Ministério Público. Esses são usuários possíveis,
não premissa.

---

## 3. O que o kit entrega

1. **Catálogo de decisão de peça em YAML** por domínio — gatilho, peça, prazo, confiança.
2. **Portão de citação funcional** — extrai todas as citações do texto e valida em lote, na
   fonte oficial, com três estados: `Verified`, `Warning`, `Not Found`.
3. **Fixtures adversariais** — processos sintéticos que **devem reprovar**. Um kit que sabe
   reprovar a si mesmo é a prova de que se importa com acerto.
4. **Relatório de proveniência** com hash encadeado SHA-256: adulteração detectável.
5. **Um domínio completo de demonstração** (família), funcionando ponta a ponta com dados
   sintéticos.
6. **Um domínio vazio com checklist** (penal) — a prova de que estender é possível sem
   código.

---

## 4. Como usar em cinco minutos

Pré-requisito: Python 3.11+ e `git`. Nada mais.

```
git clone <url> sjc-kit
cd sjc-kit
python scripts/bootstrap.py          # cria venv, instala deps, verifica chaves
make verify                          # roda os testes e as fixtures do domínio demo
make demo                            # processa casos/_exemplo/ ponta a ponta
```

`make verify` termina com uma linha de resultado. Se ele passar, **a instalação está
correta**. Isso não significa que o sistema saiba jurídico — significa que ele roda e que as
fixtures produzem a saída esperada. A diferença entre instalação correta e peça correta é a
diferença entre um carro que liga e um carro que chega.

Se algum passo falhar, **não continue**: o kit não foi instalado. Consulte `LIMITES.md` e o
bloco `FALHA CONHECIDA` do estágio que quebrou.

---

## 5. O fluxo, em uma tela

```
S0 Declaração  → pergunta polo, área, prazo. Grava com autor e hora. Sem isso, não roda.
S1 Conversão   → PDF → texto com proveniência por página; OCR seletivo; página sem texto
                 entra em lista com classe, nunca vira silêncio.
S2 IDs         → árvore × documentos × movimentos. ID citado que não existe = órfão =
                 REPROVAÇÃO, com código de erro.
S3 Estratégia  → lê do ponto de vista declarado; decide peça por gatilho documentado;
                 prazo com nível CONFIRMADO / ESTIMADO / INCERTO.
S4 Tese        → afirmação + fundamento + doutrina literal + jurisprudência + ANTÍTESE
                 (como o adversário ataca).
S5 Redação     → template do domínio; cada parágrafo rastreável a uma tese.
S6 Verificação → todas as citações extraídas e validadas. Not Found RETÉM a peça.
S7 Gate        → 5 camadas. G1 legal e G2 factual exigem declaração humana explícita.
S8 Entrega     → pacote pré-assinatura, auditoria encadeada, aviso de peça parada.
```

**Nunca assina. Nunca protocola.** O ato é do advogado, com responsabilidade pessoal.

---

## 6. O que reprova, de verdade

| Situação | Consequência |
|---|---|
| Polo não declarado pelo operador | O sistema não roda |
| ID citado que não existe na árvore (órfão) | Reprovação, exit code 5 |
| Citação `Not Found` ou de conteúdo diverso | Peça retida; tese marcada como descoberta |
| Modelo gerador e revisor idênticos | Configuração inválida |
| Gate G1 ou G2 sem declaração explícita | Reprovação |
| Campo, arquivo ou variável do núcleo com termo de área ou instituição | Falha de build |
| Domínio novo que exige alterar `core/` | Desenho errado — pare e redesenhe |

Não há nota de 0 a 100. A média esconde o que não se compensa: forma impecável não
compensa tese errada. O relatório é lista de vereditos — `PASS`, `PASS COM RESSALVAS`,
`FAIL` — com motivo por item, e três frações auditáveis: afirmações com lastro, citações
verificadas, peças com ajuste humano.

---

## 7. Arquitetura em uma frase

Núcleo genérico (`core/`) que **não conhece área nenhuma**; domínios plugáveis
(`dominios/`) que trazem catálogo, templates e regras; adaptadores de fonte
(`adaptadores/`) opcionais, isolados e frágeis por natureza.

A seta é sempre `dominios → core` e `adaptadores → core`. Se `core/` precisar saber que
existe "família", a fronteira está errada — e existe teste automatizado que falha quando
isso acontece (`import-linter`).

O núcleo funciona com **PDF + árvore em mão**. Nenhum sistema de tribunal é pré-requisito,
e nenhum é citado como dependência.

---

## 8. O teste que decide se o produto é real

**Família implementado não prova generalidade. Penal prova.**

O criminalista quebra mais premissas: prazo em dias corridos, catálogo de peça diferente,
`habeas corpus` sem prazo, dosimetria como campo onde mais se mente em citação.

Por isso o esqueleto de `dominios/penal/` nasce **vazio no primeiro commit** — campos
declarados, valores `a preencher`. Ele não roda; é o **detector de acoplamento**. Se
configurar penal exigir código novo em `core/`, a generalidade era marketing.

---

## 9. Sigilo, dados e responsabilidade

- **Dados de clientes nunca entram no git.** `.gitignore` agressivo, com teste que falha se
  um caminho proibido for versionado.
- Repo público só com código e **fixtures sintéticas**.
- Escolha entre modelo local e API de terceiro é do escritório, com base legal,
  minimização e registro de tratamento (LGPD). O kit documenta o padrão; não decide.
- **Responsabilidade é de quem assina.** Nenhuma saída do sistema transfere isso.
- O agente que instala o kit **não pode alterar as regras de reprovação**. Se alterar, o
  sistema perde a única coisa que o torna confiável.

---

## 10. Acessibilidade

Construído por quem usa leitor de tela; auditável por quem não vê a tela.

Toda comunicação é textual e sequencial. Relatórios em Markdown com hierarquia semântica de
cabeçalhos. Verificação declarada em frase ("3 citações não conferidas, aqui estão") em vez
de selo gráfico — um selo não é lido, uma frase é. Nenhuma dependência de áudio. Operação
por teclado e por comando escrito. Explicação de gate item por item, em linguagem direta.

**O que isso não significa:** não é conformidade com WCAG 2.2 nem com a Lei Brasileira de
Inclusão. Não houve auditoria formal. O teste com usuário real está previsto para a v0.2 —
é o único teste que vale.

---

## 11. Documentos, e em que ordem ler

Para **entender**:

1. `LIMITES.md` — o que o projeto declara não saber. Leia primeiro; foi escrito para isso.
2. `METODO.md` — como se faz e por que, com os números que forçaram cada decisão.
3. `ESPECIFICACAO-PRODUTO.md` — o desenho completo, estágio por estágio.

Para **instalar**, comece por `AGENT.md` — é o arquivo escrito para a máquina, não para o
humano.

---

## 12. O que este projeto não promete

Não promete que a peça esteja correta. Não promete prazo. Não promete cobertura de área que
não foi medida. Não promete anonimização. Não promete acessibilidade formal.

Promete que cada verificação declare **o que conferiu e o que não conferiu** — e que nada
saia sem o registro de onde se mentiu.

A lista completa, com os números que a sustentam, está em `LIMITES.md`.

---

*Licença, status e estado do projeto: ver `ESTADO-PROJETO.md`.*
