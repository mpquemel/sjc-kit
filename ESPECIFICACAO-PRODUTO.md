# SISTEMA JURÍDICO CUSTOMIZÁVEL (SJC) — Especificação de Produto

> **Repositório:** `sjc-kit`
> **Versão:** 0.2 (decisões de 02/11/2026 incorporadas)
> **Data:** 02/11/2026
> **Autoria:** Melhym Pereira Quemel (concepção, método e acessibilidade de origem)
> + Basir (engenharia, redação e consolidação a partir de três pareceres independentes)
> **Estado:** aprovada para desenho. Nenhuma linha de código escrita.
> **Público-alvo:** escritórios de advocacia e operadores do direito, de qualquer área e
> de qualquer polo e de qualquer área. O escritório configura a área e o polo; o kit não presume nenhum.

## Decisões fechadas (02/11/2026)

| # | Decisão | Valor |
|---|---|---|
| 1 | Nome | **Sistema Jurídico Customizável**, sigla **SJC**, repo `sjc-kit` |
| 2 | Área de demonstração | Família, validada com os fundamentos existentes |
| 3 | Extensibilidade | Esqueleto de **penal vazio desde o primeiro commit** (campos declarados, valores `a preencher`) |
| 4 | Acessibilidade | **Princípio declarado + checklist na v0.1**; auditoria formal com usuário real na v0.2 |
| 5 | Linguagem | Proibido vocabulário institucional ou de área no núcleo: `assistido`, `numero_verde` → `cliente`, `polo_operador`, `identificador_externo`, `orgao_julgador` |
| 6 | Integração | Adaptadores de **entrada** para PJe, eproc, Projudi e afins; todos opcionais; nenhum sistema de tribunal no núcleo |

> **Nome anterior nesta especificação:** "Protocolo Jurídico Aberto". Substituído. O termo
> "protocolo" permanece como nome interno do *corpo de regras* (o protocolo de verificação),
> não como nome do produto.

> **Versão:** 0.1 (especificação, sem código)
> **Data:** 02/11/2026
> **Autoria:** Melhym Pereira Quemel (concepção e método) + Basir (engenharia, redação e
> consolidação a partir de três pareceres independentes)
> **Estado:** aprovada para desenho. Nenhuma linha de código escrita.
> **Público-alvo:** escritórios de advocacia e operadores do direito. Não é atrelado a
> órgão público; órgãos públicos são clientes possíveis, não premissa.

---

## 0. A tese do produto em uma frase

O mercado vende petição pronta ou sistema de gestão. Este projeto vende **o método para
construir um sistema jurídico confiável**, entregue como um kit que um agente de IA lê e
instancia no escritório do cliente.

O ativo não é o texto gerado. É o **registro de onde a IA mente** — com número, página e
reprodução — e o procedimento que impede que isso chegue à assinatura do advogado.

---

## 1. Para quem é, e para quem não é

**É para:** sócio de escritório que assina peça e responde por ela; advogado autônomo com
volume de processo acima da capacidade de revisão; escritório pequeno sem equipe de
tecnologia; órgãos públicos que queiram o mesmo método sem depender deste autor.

**Não é para:** quem quer substituir o advogado; quem quer "IA que redige sozinha"; quem
não vai ler o relatório de verificação; quem processa dados de cliente em API de terceiro
sem base legal.

**Declaração de limites, que abre o README:** este kit não substitui juízo profissional,
não assina, não protocola, e não garante acerto. Ele garante que o erro seja **visível
antes da assinatura**.

**Declaração de origem, que vem logo depois:** este kit foi concebido por um advogado
cego que trabalha com leitor de tela. A acessibilidade não é recurso adicional — é a
condição em que o sistema nasceu. Ver seção 11.

---

## 2. As três camadas do produto

**Camada 1 — O MÉTODO.** Documento público, gratuito, com os números reais: por que inferir
o polo falhou em 119 de 121 processos; por que um revisor tem de ser modelo diferente do
gerador; por que um filtro pode parecer funcionar e ler o espelho errado. Constroi
autoridade e não compete com ninguém, porque ninguém publica os próprios fracassos.

**Camada 2 — O KIT.** O repositório `sjc-kit`. Núcleo pequeno e testável, mais um domínio
de demonstração (família) e um domínio-esqueleto de prova de extensão (penal, com campos
declarados e valores `a preencher`). Roda em cinco minutos com dados sintéticos e produz
uma peça com relatório de citações e vereditos de gate.

**Camada 3 — A INSTANCIAÇÃO.** O serviço. O agente lê o kit, pergunta a área, e constroi o
domínio do escritório. É onde o negócio vive.

---

## 3. O repositório é lido por um AGENTE — o que isso muda

Esta é a decisão de projeto mais importante e a que diferencia o produto de tudo que existe.

Um humano lê README, seções, exemplos. Um agente precisa de: **ordem de execução,
pré-condições verificáveis, pontos de decisão explícitos, critérios de aceitação, e o que
fazer quando falha.** Se o repo não tiver isso, o agente improvisa — e improviso de agente
é exatamente o que gerou os 119/121.

**Consequências concretas:**

1. **O entrypoint é um contrato, não uma introdução.** `AGENT.md` na raiz é o arquivo que o
   agente lê primeiro. Ele termina com uma **autoavaliação**: o agente responde se tem os
   pré-requisitos. Sem pré-requisitos, não instala.

2. **Cada estágio é um arquivo que pode ser executado por leitura.** `estagios/s1-conversao.md`
   contém: entrada esperada, saída obrigatória, o que nunca fazer, como verificar sucesso,
   e um bloco de "caso adversarial" que o agente deve conseguir reprovar.

3. **O kit traz FIXTURES, não só descrição.** Cada domínio vem com um processo sintético e
   a saída esperada. O agente instala e **roda a fixture**; se o resultado não bate, ele
   para e reporta. Isso transforma instalação em teste.

4. **As decisões que o agente NÃO PODE TOMAR estão marcadas com `BLOQUEIO:`.** Exemplo:
   `BLOQUEIO: se o polo não foi declarado pelo operador, pare. Não infira.`

5. **Nada de prosa motivacional.** Cada arquivo responde: o que é, quando usar, o que entra,
   o que sai, como verificar, o que falhou antes e por quê.

**Formato de escrita que vou adotar em todo o kit:**

```
## ESTÁGIO S3 — ESTRATÉGIA
QUANDO: após S2 produzir linha do tempo tipada e polo declarado.
ENTRA: caso.json (com polo_fonte=declarado), linha_do_tempo[], documentos[]
SAI: estrategia.json {peca_escolhida, gatilho_disparado, alternativas[], prazo{}, confianca}
NUNCA: escolher peça sem gatilho documentado; inferir prazo; omitir alternativa mais grave.
VERIFICA: <comando ou checagem> deve devolver <resultado>
FALHA CONHECIDA: <o que já deu errado e por quê>
CASO ADVERSARIAL: <entrada que deve reprovar>
```

Isso é legível por humano e executável por agente. É o mesmo documento servindo aos dois.

---

## 4. O fluxo, estágio por estágio, do jeito que o agente vai ler

**S0 — DECLARAÇÃO DE OPERAÇÃO (obrigatório, antes de tudo)**

O sistema **pergunta**, não descobre. Coleta e grava:

- Área e domínio (ex.: `familia`), versão do domínio.
- **Polo em que atua: ativo ou passivo — declarado pelo operador.** Sem isso, não roda.
- Quem declara (nome), quando (timestamp), e o que motivou a declaração.
- Se há prazo fatal correndo e qual a data de referência.
- **Perfil de interação** (ver seção 11): canal de saída, densidade do relatório, canal de
  alerta, nível de detalhe da explicação do gate. Vem de `operador.yaml`, com padrão seguro.

Saída: `caso/declaracao.json` com hash. É o documento de responsabilidade do operador.
**Este é o item que mais protege o escritório e o produto.** O sistema não inventa polo;
registra que o humano afirmou.

**S1 — CONVERSÃO (PDF → texto com proveniência por página)**

O ponto onde mais se perde. O conhecimento acumulado, e que vai escrito:

- Texto nativo útil não é o mesmo que "tem algum texto". A triagem é por página, com
  critério medido.
- OCR seletivo só onde a página falha; cada página convertida guarda método e confiança.
- Página sem texto (foto, carimbo, planta, documento escaneado ilegível) **não é erro —
  é classe**. Ela entra numa lista com descrição de classe e nunca vira silêncio.
- **Regra-mãe: descrição não é prova.** Uma descrição de imagem nunca fundamenta fato.
- Saída: `autos.txt` com marcadores de página, `conversao.json` com proveniência por
  página e `paginas_sem_texto.json`.

**S2 — VINCULAÇÃO DE IDs (árvore × documentos × movimentos)**

- A árvore é **entrada**, não extração. O sistema não depende de portal específico; recebe
  `arvore.txt` e valida. É isso que o torna portável para qualquer escritório.
- Cada ID é casado com documento, tipo e movimento, com três chaves em ordem de
  confiabilidade.
- **Gate de IDs:** ID citado que não existe na árvore é órfão. Órfão é **reprovação**, não
  aviso. Saída com código de erro.
- **Falha conhecida:** layout de árvore muda; árvore truncada produz órfãos falsos ou,
  pior, órfãos invisíveis. Por isso, fixture de árvore versionada e teste adversarial com
  árvore malformada a cada versão.

**S3 — LEITURA ESPECIALISTA E ESTRATÉGIA**

- Lê os autos **do ponto de vista do polo declarado** em S0. Não escolhe lado.
- Produz a linha do tempo, o estado processual e a **decisão de peça** a partir do catálogo
  de gatilhos do domínio (`estrategia.yaml`).
- Cada decisão declara: gatilho disparado, peça cabível, alternativas, prazo com nível de
  confiança.
- **Prazo é o risco irreversível.** Contagem só com termo inicial extraído e fonte oficial
  de dias úteis. Nível: CONFIRMADO, ESTIMADO ou INCERTO. Prazo peremptório **para o
  sistema** e exige humano.
- Se mais de uma peça é cabível, apresenta as duas com consequência de cada uma. Não
  esconde a mais grave.
- **Trava deontológica:** embargos sem vício real não entram como sugestão. Nenhuma peça
  recomendada para protelar.

**S4 — CONSTRUÇÃO DA TESE**

- Tese por bloco, cada uma com: afirmação, fundamento legal, fundamento doutrinário,
  jurisprudência de reforço, e a **antítese** — como o adversário ataca.
- Consulta doutrina (RAG) buscando o trecho **literal**, com identificação da obra e
  localização. Sem literal, vira paráfrase declarada como tal.
- Consulta jurisprudência (STF, STJ, TJRJ para começar; adaptador por tribunal).
- **Roteador como preferência, não filtro:** restringir por ramo derruba o julgado que
  decide a questão por outro fundamento. Filtro só se o operador aplicar.
- Sai: `tese.json` com cada afirmação e a lista de autoridades que a sustentam.

**S5 — REDAÇÃO**

- Escolhe o template do domínio, com marcadores `[OBRIGATÓRIA]` que o gate vai conferir.
- Escreve por seção, cada parágrafo rastreável a uma tese de S4.
- Modelo por tipo de peça declarado no domínio, com motivo registrado (isto fecha a lacuna
  de rastro de escolha de modelo).
- Saída: rascunho `.md` com rastreio parágrafo → tese → autoridade.

**S6 — ENRIQUECIMENTO E VERIFICAÇÃO DE AUTORIDADE**

- Extrai **todas** as citações do texto por padrão, incluindo formas não abreviadas
  ("artigo 1.694" sem "art."). Extrator de citação tem teste adversarial próprio, porque
  citação não extraída passa sem validar.
- Valida cada uma em lote, na fonte oficial, com data e âncora de conteúdo.
- Três estados: **Verified** (existe e o conteúdo confere), **Warning** (existe, campo
  diverge), **Not Found** (não existe).
- **Os quatro tipos de falha que precisam ser detectados separadamente:** número errado;
  número truncado; conteúdo diverso do atribuído; falso positivo de extração.
- **Not Found e conteúdo diverso retêm a peça.** A tese que dependia daquela citação fica
  marcada como descoberta. O sistema entrega com a lacuna visível, não com a lacuna
  preenchida por plausibilidade.
- Saída: `relatorio-citacoes.md` e `.json`, com estado por citação.

**S7 — GATE DE CINCO CAMADAS**

- G1 legal e G2 factual: **não automatizáveis** por natureza. O sistema lista o que
  conferir e exige **declaração explícita** do operador. Sem declaração, reprova.
- G3 forma: automatizado, reprova de verdade. Formato do modelo, marcadores residuais,
  ortografia armadilha, seções obrigatórias presentes na ordem.
- G4 transcrição: só quando a peça cita transcrição, com conferência na linha exata.
- G5 auditoria: leitura crítica do ponto de vista do juiz e do adversário. Veredito
  discreto: PASS, PASS COM RESSALVAS, FAIL, com motivo por item.
- Revisão por **modelo diferente** do que gerou. Modelo fraco como auditor é inapto e isso
  está medido: um aprovou 11 de 11 processos que o outro reprovou em 5 de 8.

**S8 — ENTREGA (pré-assinatura, sempre)**

- Pacote: minuta `.docx`, relatório de citações, vereditos por gate, proveniência, e o
  registro de declaração do operador.
- **Nunca assina, nunca protocola.** O ato é do advogado. O sistema para aqui.
- Relatório de auditoria encadeado por hash: cada entrada ligada à anterior por SHA-256.
  Adulteração detectável. Para o escritório, é defesa; para o cliente, é rastro.
- **Aviso de peça parada:** o sistema registra que entregou e quando. Peça entregue e não
  protocolada é alertada. Isto resolve o problema dos 77 que não foram protocoladas.

---

## 5. O que o kit entrega pronto, além da instrução

1. **Catálogo de decisão em YAML** por domínio — gatilho, peça, prazo, confiança.
2. **Portão de citação funcional** — extrai do texto e valida em lote, três estados.
3. **Fixtures adversariais** — processos sintéticos que devem reprovar. Um kit que sabe
   reprovar a si mesmo é a prova de que se importa com acerto.
4. **Relatório de proveniência** com hash encadeado.
5. **Um domínio completo de demonstração**, com tudo acima funcionando ponta a ponta.
6. **Um domínio vazio com checklist** — a prova de que estender é possível sem código.

---

## 6. O teste que decide se o produto é real

**Família implementado não prova generalidade. Penal prova.**

O criminalista quebra mais premissas: prazo em dias corridos, catálogo de peça diferente,
`habeas corpus` sem prazo, dosimetria como campo onde mais se mente em citação. Se o núcleo
absorve penal **só com YAML e templates, sem código novo**, a generalidade é real. Se exige
código, era marketing — e é melhor descobrir antes de vender.

**Estratégia aprovada:** o esqueleto de penal (`dominios/penal/`) nasce **no primeiro
commit**, com todos os arquivos de configuração declarados e valores `a preencher`. Ele não
roda — mas é o detector de acoplamento. Toda vez que um campo do núcleo não couber no
esqueleto de penal, o acoplamento aparece na hora, não em seis meses. É o teste de
extensibilidade rodando de forma contínua, a custo quase zero.

**Regra de nomenclatura (decisão 5):** nenhum nome de campo, arquivo, variável ou estágio
pode conter termo de área jurídica ou de instituição. Proibido no núcleo: `assistido`,
`assistido`, `numero_verde`, `pje`, `eproc`. Usar: `cliente`,
`polo_operador`, `identificador_externo`, `orgao_julgador`. Isso parece detalhe de estilo;
é o que decide se o produto generaliza ou apodrece no segundo cliente.

**Critério de aceitação da v0.1:** família completo e rodando a fixture; penal com esqueleto
declarado e validador de domínio aprovando o esqueleto (campos obrigatórios presentes,
valores ausentes marcados); nenhuma alteração necessária em `core/` para declarar penal.

---

## 7. Modelo de negócio, em três degraus

**Degrau 1 — Método e kit, gratuitos e abertos.** Reputação e demanda. Sem isto, ninguém
confia.

**Degrau 2 — Instanciação, paga por projeto.** Construção do domínio do escritório, com os
templates, as fontes e a validação em processos reais do próprio cliente. Margem alta,
escala baixa por desenho. Cria dependência legítima.

**Degrau 3 — Curadoria contínua, assinatura.** O gargalo apontado pelo crítico não é
obstáculo: é o produto recorrente. Acervo de jurisprudência verificado e mantido por área,
com proveniência e atualização, é assinatura mensal. Ninguém quer montar curadoria; todos
querem acervo confiável. E curadoria é exatamente o que a IA sozinha não faz bem, porque
exige juízo humano que confere.

**Sinergia:** cada ficha conferida no trabalho real é um item de acervo reutilizável.
O acervo que já foi necessário construir é o primeiro produto recorrente.

---

## 8. Riscos nomeados, com mitigação

**Sigilo e segredo de justiça.** Processar autos reais em máquina de cliente, com opção de
modelo local, não é preferência técnica: é condição de operação. Uso de API de terceiro
exige base legal, minimização e registro de tratamento (LGPD). O kit declara o padrão e o
escritório assume a escolha com rastro.

**Responsabilidade profissional.** É do advogado que assina, sempre. O produto diz isso na
interface, no relatório e no rodapé da minuta. Marketing que prometa substituição de
advogado é risco de passivo, não argumento de venda.

**Agente que se auto-configura.** Um agente que lê o repo e instala pode "otimizar" o gate
que o está reprovando. Trava: código de gate e regras de reprovação são **imutáveis por
instrução de setup**; alteração exige revisão humana registrada.

**Fantasia da cobertura universal.** O README declara o que não sabe. Cada domínio traz a
lista do que não foi validado. Generalidade é contrato de extensão, não promessa de
cobertura.

---

## 9. Roteiro de construção

**Etapa 0 (sem código, ganho imediato):** passo de acompanhamento das peças entregues e não
protocoladas. Cobrança e registro.

**Etapa 1:** fechar as citações em aberto e construir o portão de citação, usando as peças
com citação furada confirmada como fixtures de aceitação.

**Etapa 2:** catálogo de decisão de peça em família, a partir dos gatilhos já levantados.

**Etapa 3:** lastro por trecho na doutrina de família, e cabeçalho de proveniência com hash.

**Etapa 4:** núcleo extraído, domínio família migrado, fixture ponta a ponta.

**Etapa 5:** domínio penal só por YAML. Se exigir código, parar e redesenhar.

**Etapa 6:** instanciação em um escritório real, com três métricas: citações reprovadas por
peça, taxa de ajuste humano, peças entregues e protocoladas.

---

## 10. Acessibilidade — princípio de origem, não recurso adicional

**Fato de origem:** este kit foi concebido por um advogado cego que opera com leitor de
tela. O sistema é usável por ele — não por adaptação posterior, mas porque nasceu em texto.

**Por que isso é estrutural e não retórica.** O desenho inteiro do pipeline é compatível com
interação não visual por consequência das escolhas já feitas:

- Toda comunicação é textual e sequencial. Não há posição, cor, ícone ou arrastar.
- Todo relatório é Markdown semântico com hierarquia de cabeçalhos — leitor de tela navega
  por cabeçalho. Não há tabela aninhada como única forma de ler um resultado.
- Verificação é declarada em texto ("3 citações não conferidas, aqui estão") em vez de selo
  gráfico. Um selo não é lido; uma frase é.
- Nenhum estágio depende de áudio, portanto nenhum estágio exclui pessoa surda.
- O fluxo inteiro é operável por teclado e por comando escrito — sem cadeia de cliques,
  portanto sem barreira para limitação motora.
- A explicação do gate é item por item, em linguagem direta ("reprovou porque X"), o que
  serve quem precisa de explicação explícita em vez de mensagem de erro.

**Perfil do operador (`operador.yaml`), distinto do perfil do escritório:**

```yaml
# operador.yaml — cada advogado do escritório tem o seu
id: adv-exemplo
interacao:
  canal_principal: texto_telegram      # texto_telegram | arquivo | voz_sintetizada
  densidade_relatorio: detalhado        # resumido | detalhado | item_por_item
  explicacao_gate: sempre               # sempre | somente_falhas
  alerta_prazo:
    canal: mensagem                     # mensagem | som | vibracao | piscar_tela
  navegacao: cabecalho_markdown         # cabecalho_markdown | texto_linear | comandos
  imagens: descrever_em_texto           # toda imagem gerada tem descrição textual
```

**Limite honesto, declarado na v0.1:** o sistema é acessível *por construção*, não por
auditoria formal. Ainda não medimos conformidade com WCAG 2.2 nem com a Lei Brasileira de
Inclusão (Lei 13.146/2015, art. 63 — conferir texto na fonte oficial). Prometer acessibilidade
sem medição é o mesmo erro que este projeto acusa nos outros.

**Roteiro de acessibilidade:**

- v0.1 — princípio declarado, `operador.yaml`, checklist em `acessibilidade/checklist.md`,
  toda saída textual e sem dependência de áudio. Nenhuma afirmação de conformidade.
- v0.2 — auditoria formal: contraste, ordem de foco, navegação por teclado, texto alternativo
  em documento gerado, e **teste com usuário real com deficiência**, que é o único teste que
  vale.
- v0.3 — perfis adicionais medidos: deficiência motora, surdez, deficiência intelectual.

**Formulação para o README:** *construído por quem usa leitor de tela; auditável por quem
não vê a tela.*

---

## 11. Critério de sucesso, em números, não em adjetivos

- 100% das citações de peça entregue em estado Verified ou explicitamente retidas.
- Nenhuma peça entregue com ID órfão.
- Nenhuma peça entregue sem polo declarado com autoria e hora.
- Peça entregue e não protocolada sinalizada em 48 horas.
- Domínio novo configurável sem tocar em `core/`.
- Toda afirmação de fato rastreável a página e linha.

**Não há nota de 0 a 100.** A média esconde o que não se compensa: forma impecável não
compensa tese errada. O relatório é uma lista de vereditos com evidência, e três frações:
percentual de afirmações com lastro, percentual de citações verificadas, percentual de
peças com ajuste humano.

---

*Próximo passo: apresentar a árvore de diretórios do repositório para aprovação, antes de
qualquer código.*
