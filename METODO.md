# O MÉTODO — como construir um sistema jurídico que não mente

> Sistema Jurídico Customizável (SJC) · `sjc-kit` · Camada 1 (pública, gratuita)
> Versão 0.1 · 02/11/2026
> Autoria: Melhym Pereira Quemel (concepção e método) + Basir (redação)
>
> Este documento é o degrau 1 do produto. Ele não vende o kit; ele publica o que foi
> aprendido errando. Ninguém publica os próprios fracassos — por isso este é o único ativo
> que a concorrência não copia por preço.

---

## 0. A regra que governa este documento

**Limite sem número é opinião. Opinião não entra.**

Cada afirmação abaixo tem origem identificada: medição com contagem, caso observado com
data, ou falha reproduzida com comando. Quando não há número, está escrito "não medido" —
e isso é declaração, não lacuna escondida. O mesmo padrão vale para o que o leitor
construir: se ele não consegue medir, ele não sabe, e o sistema precisa dizer isso em voz
alta em vez de improvisar.

---

## 1. O problema real não é gerar petição

Todo mundo já gera texto. O problema é que o texto gerado parece certo. Um modelo produz
parágrafo fluente, citação plausível, número de artigo com cara de número de artigo — e a
peça passa pelo olho de quem está com 40 processos abertos porque *nada ali parece errado*.
O erro não grita. Ele se veste de competência.

Ferramenta que promete acerto transfere risco em silêncio: quem assina responde, quem
produziu não. O método aqui inverte a assimetria. Ele não promete acerto. Ele garante uma
coisa só, e é uma coisa verificável: **o erro fica visível antes da assinatura**.

Isso muda o desenho de tudo. Não se otimiza para "peça bonita". Otimiza-se para
**reprovação honesta** — um sistema que sabe dizer "não passa" vale mais que um que sempre
aprova, porque o que sempre aprova não está verificando nada.

---

## 2. O que foi medido, e o que cada número mudou no projeto

### 2.1 Polo: sete tentativas de inferir, 119 de 121 fracassos

O sistema tentou deduzir em que polo o operador atuava — por vocativo, por padrão de
petição, por ordem de qualificação, por menção a "requerido", por seis abordagens
sucessivas e uma combinada. Resultado: **"não sei" em 119 de 121 processos.**

Um acerto aparente em 2 casos não é acerto; é coincidência com amostra insuficiente para
sustentar qualquer coisa. E aqui está o ponto que dói: um sistema que acerte 58 de 60
parece melhor que este e é **pior**, porque erra em silêncio nos 2. Polo invertido não é
detalhe de redação: é peça protocolada pelo lado errado, prazo perdido, ato processual em
favor de quem se estava combatendo.

**Decisão que saiu disso:** o polo é ato formal. O sistema **pergunta** e grava a
declaração com autor, hora e motivo. Sem declaração, não roda. Não há "modo automático",
nem quando parece óbvio. A regra não é sobre capacidade técnica — é sobre onde o erro cai.

**Regra transferível:** sempre que a inferência for confiável o suficiente para parecer
certa e não confiável o suficiente para ser certa, **tire a inferência do sistema e
coloque a declaração no humano, com registro**.

### 2.2 Auditor: um modelo aprovou 11 de 11 processos que o outro reprovou em 5 de 8

O pipeline sempre previu revisão. A questão era *qual* modelo revisa. Mediu-se: um modelo
avaliado como revisor **aprovou 11 de 11 processos** — inclusive os que o revisor
competente reprovou em **5 de 8**. Não viu polo invertido. Não viu litisconsórcio omitido.

Duas leituras possíveis, e só uma é correta. A errada: "o revisor bom é mais rigoroso".
A certa: **o revisor fraco não está revisando, está concordando.** Um auditor que aprova
tudo não tem opinião; tem inércia, e inércia com formato de parecer é o pior tipo de
falso positivo — dá conforto a quem ia errar.

**Decisão que saiu disso:** a revisão final é feita por modelo **diferente** do gerador.
Não por ser mais forte — por não compartilhar os mesmos pontos cegos. Modelo igual ao
gerador concorda consigo mesmo com eloquência.

**Regra transferível:** validar o validador antes de confiar no veredito. Se o auditor
aprova tudo que vê, o problema é o auditor, e ele precisa ser medido como qualquer outra
peça do sistema.

### 2.3 Citação: 10 peças com defeito confirmado em 136

Este é o número central do método, e ele precisa ser lido inteiro: **136 peças → 45
citações únicas extraídas → 29 conferidas → 16 em aberto → 10 peças com citação furada
confirmada.**

Não é "10 de 136 erradas" no sentido de sorte. É: em cada dez peças verificadas, uma
carregava citação que não sustentava o que se dizia. E os defeitos não foram de um tipo
só — foram **quatro**, e o quarto é o que decide o desenho:

1. **Número errado.** O artigo existe, o número está trocado. Fácil de pegar, se alguém
   olhar.
2. **Número truncado.** Cita-se um inciso que não existe, ou um artigo que o dispositivo
   não tem. Parece preciso, é inventado.
3. **Conteúdo diverso do atribuído.** O dispositivo existe, o número está certo, e diz
   outra coisa. É o tipo mais perigoso: passa por qualquer conferência que só cheque
   existência.
4. **Falso positivo de extração.** O texto não diz o que o extrator entendeu. Aqui a falha
   está no leitor, não no autor — e por isso é o tipo que **mais** engana: o relatório diz
   "verificado" porque o que se verificou foi uma leitura errada do próprio material.

O tipo 4 explica por que o extrator de citação precisa de teste adversarial próprio. Uma
citação que não foi extraída nunca é validada — e o relatório, tecnicamente correto, atesta
um texto que não existe. O sistema não mente porque quis; mente porque a pergunta estava
mal feita.

**Decisão que saiu disso:** extrai-se **toda** citação, incluindo as não abreviadas
("artigo 1.694" sem "art."). Validação em lote na fonte oficial. Três estados — Verified,
Warning, Not Found — e conteúdo diverso é tratado como Not Found, não como Warning.
Not Found retém a peça e **marca a tese que dependia dela como descoberta**: entrega com
lacuna visível, nunca preenchida por plausibilidade.

**Regra transferível:** verificar existência não é verificar conteúdo. E a ferramenta que
extrai precisa ser testada com o mesmo rigor que a ferramenta que valida.

### 2.4 Filtro que funcionava e lia o espelho errado

Cinco cenários ao vivo, mesmo filtro, mesmo código, aparentemente correto: filtrar por
estado e receber resultados de outro estado.

Três hipóteses caíram no teste — identificador de campo obsoleto, painel recolhido,
formulário não submetido. A causa era outra: **a seleção vivia na URL, fora do lugar onde
o sistema a lia.** Os controles visíveis apareciam desmarcados porque a página não os
repovoava a partir da consulta. Toda a superfície visível dizia "sem filtro aplicado"; o
resultado vinha filtrado; ninguém conseguia explicar a divergência olhando a tela.

Um filtro assim não quebra — ele **restringe em silêncio**. E restrição silenciosa, em
jurisprudência, é o caso decidido que a busca nunca devolve: você não recebe a resposta
errada, recebe a ausência de resposta certa, que é pior porque ninguém nota.

**Decisão que saiu disso:** todo filtro tem (a) teste ao vivo com cenário que deve mudar
o resultado, (b) leitura do estado **onde ele realmente mora** (URL, cookie, sessão,
cache), (c) log de filtros aplicados, e (d) bateria de consultas-padrão com diff por
versão. Roteador de área é **preferência de ranking**, nunca filtro excludente — porque
restringir por ramo derruba o julgado que decide a questão por outro fundamento.

**Regra transferível:** antes de consertar um filtro, descobrir onde o sistema guarda a
verdade. O DOM é frequentemente um espelho, e espelho não é fonte.

### 2.5 Peça entregue não é peça protocolada: 77 paradas

O número mais banal e o mais revelador: **77 peças prontas e não protocoladas** na mesma
data.

Nenhuma delas falhou por qualidade técnica. Falharam porque "pronta" e "entregue ao juízo"
são estados diferentes, e o método, como estava desenhado, enxergava só o primeiro. Um
sistema que mede produção e não mede protocolo é um sistema que fabrica estoque parado com
a consciência tranquila.

**Decisão que saiu disso:** o estágio de entrega registra **o que foi entregue, quando, e
se foi protocolado**. Peça entregue e não protocolada é sinalizada em 48 horas. É o passo
"Etapa 0" do roteiro: ganho imediato, sem uma linha de código.

**Regra transferível:** medir o que aconteceu de fato, não o que o sistema conseguiu
produzir. A métrica que só enxerga o próprio pipeline sempre parece boa.

### 2.6 Acervo pequeno por escolha: a taxa de curadoria é o limite

O índice de jurisprudência próprio cresce por curadoria humana, ficha por ficha, com
conferência em fonte primária. A taxa é baixa — e é **deliberada**, não falha a corrigir
com automação. A base própria serve para validar e para recuperar o que já foi conferido.
Para fundamentar tese nova, vai-se à fonte oficial.

Isso não é modéstia; é arquitetura. Uma base que cresce rápido e sem conferência é uma
base que produz citação bonita e errada em escala. O gargalo é o produto: acervo verificado
e mantido é a parte recorrente que ninguém quer construir e todos querem ter.

---

## 3. As sete regras do método

Cada regra nasceu de um fracasso nomeado. Nenhuma é princípio abstrato.

### Regra 1 — Pergunte, não descubra

Toda premissa que muda o sentido da peça é **declarada** pelo operador e registrada com
autor, hora e motivo: polo, área, prazo fatal, perfil de interação. O sistema não infere
o que não pode errar. (Base: 119/121.)

### Regra 2 — Descrição não é prova

Texto extraído por OCR, descrição de imagem, resumo de modelo — nada disso fundamenta
fato. Fato exige página, linha e trecho reproduzido. Página sem texto não é erro: é
**classe**, listada com descrição e nunca convertida em silêncio. Silêncio em página é
como citação truncada: parece que está tudo lá.

### Regra 3 — Verifique o conteúdo, não o status

HTTP 200 com página de manutenção existe. Portal que redireciona para login também. Fonte
que devolve a norma de outro ano não é hipótese remota. Toda verificação exige **âncora de
conteúdo**: o número da norma dentro do texto retornado, o trecho conferido, o hash do
dispositivo. Falha de âncora é Not Found. Nunca "conferido".

### Regra 4 — Separe os tipos de falha, porque eles se escondem um atrás do outro

Número errado, número truncado, conteúdo diverso, falso positivo de extração. Quatro
perguntas distintas, quatro verificações distintas. Um relatório que diz "citação
verificada" sem dizer **o que** foi verificado não verificou nada — é o tipo 4 disfarçado
de sucesso.

### Regra 5 — Auditor diferente do autor

Modelo gerador e modelo revisor distintos, sempre. E o revisor tem de ser medido: um
auditor que aprova tudo não é criterioso, é cego — e cego com parecer é pior que nenhum.
(Base: 11/11 aprovados onde o competente reprovou 5 de 8.)

### Regra 6 — Sem nota; veredito com evidência

Nenhuma nota de 0 a 100, nenhuma média ponderada. Forma impecável não compensa tese errada,
e o número esconde exatamente a dimensão que não se compensa. O relatório é lista de
vereditos discretos — PASS, PASS COM RESSALVAS, FAIL — cada um com o motivo por item, mais
três frações auditáveis: afirmações com lastro, citações verificadas, peças com ajuste
humano. (Base: recusa explícita do modelo de score por pesos.)

### Regra 7 — Medir o validador, e procurar o caso que quebra

Passar no caso fácil não é validar. Para cada extrator, filtro ou regra, a pergunta é
"qual entrada faz isso mentir?", e essa entrada vira fixture de reprovação. Um kit que
sabe reprovar a si mesmo é a prova de que se importa com acerto. (Base: as quatro falhas
de citação e o filtro de UF.)

---

## 4. O fluxo, e o motivo de cada estágio existir

O pipeline é sequencial porque cada estágio responde a uma pergunta que o anterior não
pode responder. Quando um estágio tenta responder a pergunta do seguinte, é ali que
nascem os erros — é o improviso de agente.

**S0 · Declaração.** Pergunta e grava. Polo, área, prazo, perfil. Saída com hash:
é o documento de responsabilidade do operador, e é o item que mais protege o escritório.
*Por que primeiro:* toda inferência posterior depende dele, e a única inferência proibida
é a que ninguém percebe que foi feita.

**S1 · Conversão.** Triagem por página com critério medido, OCR seletivo só onde falha,
proveniência por página. Página sem texto entra em lista com classe. *Por que separado:*
o ponto onde mais se perde informação é a conversão, e perda silenciosa aqui envenena
todos os estágios seguintes sem deixar rastro.

**S2 · Vinculação de IDs.** A árvore é entrada, não extração. Cada ID casa com documento,
tipo e movimento, por três chaves em ordem de confiabilidade. ID citado que não existe na
árvore é órfão — e órfão **reprova**, com código de erro. *Por que gate:* arquivo citado
que não existe é assinatura de peça com fato inventado. Falha conhecida: árvore truncada
produz órfãos falsos e, pior, órfãos invisíveis — daí fixture versionada e teste
adversarial com árvore malformada em cada release.

**S3 · Estratégia.** Leitura dos autos **do ponto de vista declarado**, decisão de peça por
catálogo de gatilhos, prazo com nível de confiança (Confirmado, Estimado, Incerto). Duas
peças cabíveis: as duas vão ao relatório, com a consequência de cada uma. A mais grave não
se esconde. Prazo peremptório **para o sistema** e exige humano. *Por que catálogo:*
"qual é a melhor peça" era a lacuna L1 — e decisão sem gatilho documentado é palpite com
formato de estratégia.

**S4 · Tese.** Cada bloco tem afirmação, fundamento legal, doutrina literal, jurisprudência
e a **antítese** — como o adversário ataca. Sem trecho literal, a doutrina vira paráfrase
declarada. *Por que antítese:* peça que não antecipa o ataque é peça escrita para o próprio
autor, não para o juiz.

**S5 · Redação.** Template do domínio, marcadores obrigatórios que o gate vai conferir,
cada parágrafo rastreável a uma tese. *Por que rastrear:* parágrafo sem tese de origem é
onde modelo enfeita com afirmação que ninguém pediu e ninguém vai checar.

**S6 · Verificação de autoridade.** Todas as citações extraídas e validadas em lote, três
estados, quatro tipos de falha distintos. Not Found retém a peça. *Por que retém:* é a
única hora em que o sistema tem a chance de impedir que o erro chegue à assinatura.
Depois disso, o ato é do advogado.

**S7 · Gate de cinco camadas.** G1 legal e G2 factual **não são automatizáveis** — exigem
declaração explícita do operador, e sem ela reprovam. G3 forma reprova de verdade. G4
transcrição, quando a peça cita transcrição. G5 auditoria por modelo distinto. *Por que
dois declarativos:* fingir automação onde não há é o começo de todo falso selo verde.

**S8 · Entrega.** Pacote pré-assinatura, relatório de auditoria encadeado por SHA-256,
aviso de peça parada. Nunca assina, nunca protocola. *Por que parar:* a assinatura é ato
privativo e pessoal; qualquer coisa que a contorne é passivo, não recurso.

**Estágio transversal — Acessibilidade.** Não é camada final. Todo relatório nasce em
Markdown com hierarquia de cabeçalhos, verificação declarada em frase em vez de selo
gráfico, nenhuma dependência de áudio, operável por teclado e comando escrito. Não por
conformidade, mas porque foi concebido por quem usa leitor de tela: acessibilidade de
origem é arquitetura, não retrabalho.

---

## 5. O teste que decide se o método é geral

Família implementado não prova generalidade — prova que o autor sabe família. **Penal
prova**: prazo em dias corridos, catálogo de peça diferente, habeas corpus sem prazo,
dosimetria como campo onde mais se mente em citação. Cada uma dessas características
quebra uma premissa diferente do núcleo.

Por isso o esqueleto de penal nasce **vazio no primeiro commit**, com todos os campos
declarados e valores "a preencher". Ele não roda — ele é o **detector de acoplamento**.
Toda vez que um campo do núcleo não couber no esqueleto de penal, o acoplamento aparece
naquele dia, não seis meses depois. Custo quase zero, sinal contínuo.

Se configurar penal exigir código novo em `core/`, a generalidade era marketing. Melhor
descobrir antes de vender.

**Corolário de nomenclatura:** nenhum campo, arquivo ou variável do núcleo carrega termo
de área ou de instituição. Isso não é estilo — é o que decide se o produto generaliza ou
apodrece no segundo cliente.

---

## 6. O que isso custa — e por que o custo é o modo de falha mais provável

O risco maior não é alucinação. É **abandono por atrito**. Se cada peça custa quarenta
chamadas e trinta minutos, na terceira o profissional volta ao template e ao copiar-e-colar,
e o sistema morre por desuso — sem nunca ter errado.

Portanto: orçamento de chamadas por tipo de peça, medido e publicado; caminho barato para
peça simples (cota de sobrestamento é uma chamada); e a regra de que nenhum caso com prazo
fatal migra para o fluxo novo antes de o fluxo novo provar-se em peças que não travam.
Método que não caiba na rotina real não é rigor, é ornamento.

---

## 7. O que este método não faz

Está escrito em detalhe em `LIMITES.md`. Em resumo, porque repetir é método:

- Não assina, não protocola, não peticiona.
- Não decide tese em lugar do advogado; propõe com fundamento e com antítese.
- Não afirma fato sem página e linha.
- Não cita autoridade sem conferência de conteúdo.
- Não infere polo, área nem prazo fatal.
- Não garante que a peça esteja correta — garante que o erro verificável fique visível.
- Não garante cobertura de área, nem acessibilidade formal além do construído.
- Não sugere peça para protelar. Recurso sem vício real não entra como recomendação.

---

## 8. Quem deve usar, e em que ordem

**O advogado** lê o relatório antes de assinar. Se algo reprovou, não assina sem entender
por quê. O veredito não é sugestão.

**O agente que instala** executa as fixtures, reporta o que não passou, e não completa
lacuna com plausibilidade. Quando não souber, escreve "não sei".

**Quem vende** não chama de "automático" o que exige conferência humana, e não promete
área que não foi medida.

Ordem de leitura, para construir: `ESTADO-PROJETO.md` → `ESPECIFICACAO-PRODUTO.md` →
`LIMITES.md` → este método → `AGENT.md`.

---

## 9. A frase que resume

O valor deste método não está no que ele produz. Está no registro de onde a IA mente —
com número, página e reprodução — e no procedimento que impede que isso chegue à
assinatura de um advogado.

Tudo o mais é consequência disso.

---

*Este documento cresce com evidência. Cada limite novo entra com o número que o justifica.
Um método que não mede o próprio fracasso está vendendo confiança, não confiabilidade.*
