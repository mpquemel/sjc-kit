# LIMITES — o que este projeto declara não saber

> Sistema Jurídico Customizável (SJC) · `sjc-kit`
> Versão 0.1 · 02/11/2026
>
> Este arquivo não é advertência de rodapé. É a primeira coisa que deve ser lida, por
> humanos e por agentes. Um sistema que não declara o próprio limite está pedindo para
> ser usado errado.

---

## 1. Por que este arquivo existe

Ferramenta jurídica que promete acerto é ferramenta que transfere risco em silêncio. Quem
assina a peça responde por ela; quem a produziu responde pelo método. A assimetria é
perigosa: quem vende a ferramenta raramente assina a consequência.

Este projeto adota a posição oposta. Ele declara, por escrito e antes do uso, o que não
faz, o que não garante e onde tem evidência de que erra. Não porque seja modesto, mas porque
a alternativa — prometer e falhar em silêncio — é exatamente o defeito que ele foi feito
para impedir.

**Regra dura:** se uma afirmação deste repositório não puder ser sustentada por medição, ela
não entra. Se for retirada de uma medição, ela diz qual, quando e com quantos casos.

---

## 2. O que o sistema não faz, e nunca fará

1. **Não assina, não protocola, não peticiona.** A assinatura é ato privativo do advogado,
   com responsabilidade pessoal. Todo o pipeline é pré-assinatura por desenho, não por
   limitação técnica.
2. **Não decide a tese em lugar do advogado.** Propõe teses com fundamento e com antítese.
   A escolha do que sustenta o interesse do cliente é do profissional.
3. **Não afirma fato que não conseguiu confirmar nos autos.** Sem página e linha, o fato não
   existe no relatório. "Não consta" exige busca documentada.
4. **Não cita autoridade sem fonte conferida.** O que não se confirma sai da peça, e a tese
   que dependia dele fica marcada como descoberta.
5. **Não infere em qual polo o operador atua.** Pergunta, registra a declaração com autor
   e hora, e para se não houver declaração.
6. **Não substitui o advogado perante o cliente.** Assessora o profissional. A relação com
   quem é atendido é dele.
7. **Não sugere peça para protelar.** Recurso sem vício real não entra como recomendação.

---

## 3. O que o sistema não garante

**Não garante que a peça esteja correta.** Garante que os erros verificáveis fiquem visíveis
antes da assinatura, e que cada verificação declare o que conferiu e o que não conferiu.
Correção jurídica depende de juízo humano e de informação que pode não estar nos autos.

**Não garante cobertura de área.** A versão 0.1 traz um domínio de demonstração completo
(família) e um esqueleto declarado (penal). Qualquer outra área é configuração a construir
pelo escritório, com o mesmo custo de validação que a primeira teve.

**Não garante prazo.** Contagem de prazo é o ponto de maior risco do sistema e é tratada
como tal: nível de confiança declarado, prazo peremptório interrompendo o fluxo. Ainda
assim, o prazo é responsabilidade do advogado. O sistema avisa; não assume.

**Não garante anonimização.** O acervo usado para fundamentar teses é material de origem
que precisa estar anonimizado antes de entrar no índice. O kit declara o padrão; a
verificação é do escritório.

**Não garante acessibilidade formal.** Ver seção 7.

---

## 4. Limites medidos — com números, não opinião

Estes números vêm do desenvolvimento do método, antes do kit. Eles são a evidência de que os
limites não são hipotéticos.

**Inferência de polo: falhou em 119 de 121 processos.** Sete abordagens sucessivas tentaram
deduzir em qual polo o operador atuava, a partir de texto e de padrões. O resultado foi
"não sei" em quase todos. A conclusão está no desenho: o polo é ato formal, extraído de sinal
documental explícito, e na ausência de sinal o sistema para. Este é o motivo pelo qual o kit
**pergunta** em vez de deduzir.

**Modelo fraco como auditor: inapto.** Um modelo avaliado como revisor aprovou 11 de 11
processos que um revisor competente reprovou em 5 de 8. Não viu polo invertido nem
litisconsórcio omitido. Consequência: a revisão final exige modelo **diferente** do gerador,
e isso está no desenho como regra, não como preferência.

**Citação jurídica: 10 peças com defeito confirmado em 136.** Em 45 citações únicas
extraídas, 29 foram conferidas e 16 permanecem em aberto. Dez peças tinham citação furada
de quatro tipos: número errado, número truncado (inexistente), conteúdo diverso do
atribuído, e falso positivo de extração. O quarto tipo é o mais perigoso: o texto não diz o
que o extrator entendeu.

**Filtro que parecia funcionar e mentia.** Um filtro de unidade federativa devolvia
resultados de outro estado. O código parecia correto; a seleção vivia fora do local onde o
sistema a lia. Consequência: toda automação de filtro tem teste ao vivo, e o estado do
sistema é lido onde ele realmente mora, não onde parece morar.

**Acervo de jurisprudência: pequeno por escolha e por custo.** O índice de jurisprudência
próprio cresce por curadoria humana, ficha por ficha, com conferência em fonte primária. A
taxa é baixa e deliberada. O kit declara: **a base própria serve para validar e para
recuperar o que já foi conferido. Para fundamentar tese nova, use as consultas às fontes
oficiais.** Isto é limite, não defeito a esconder.

---

## 5. Limites estruturais — o que a arquitetura não resolve

**O sistema não está no repositório.** Está no acervo curado, na calibragem de modelos
medida em processos reais, e nas decisões que só foram tomadas depois de errar. Um agente
que lê este repositório reconstrói a **estrutura**; não herda o **conhecimento**. Por isso o
kit entrega fixtures de aceitação, não promessas de competência.

**Fixture que passa não prova competência.** Prova que a instalação está correta. A
diferença entre instalação correta e peça correta é a diferença entre um carro que liga e um
carro que chega.

**Generalidade não se demonstra por declaração.** O kit traz o esqueleto de uma segunda área
vazio. Se configurar essa área exigir tocar no núcleo, o desenho está errado — e o teste
existe para descobrir isso cedo, não para afirmar o contrário.

**O adaptador é sempre frágil.** Todo sistema de tribunal muda de layout, de autenticação e
de forma de exportar. Adaptador é a parte do kit com maior taxa de quebra. Por isso ele é
opcional, isolado, e o núcleo funciona com apenas PDF e árvore em mão.

---

## 6. Limites de operação e de responsabilidade

**Sigilo e dados pessoais.** O escritório processa dados de clientes, frequentemente
sensíveis e sob segredo de justiça. A escolha entre modelo local e API de terceiro é do
escritório e deve ter base legal, minimização e registro de tratamento. O kit documenta o
padrão e exige que a escolha seja registrada com rastro. Ele não decide por ninguém.

**Responsabilidade é de quem assina.** O sistema produz, verifica, retém e relata. O ato que
converte minuta em petição é a assinatura do advogado, que responde civil, ética e
processualmente. Nenhuma saída do sistema transfere essa responsabilidade.

**Automação de configuração não é autonomia de controle.** Um agente que instala o kit não
pode alterar as regras de reprovação do gate. Se alterar, o sistema perde a única coisa que
o torna confiável. Alteração de gate exige revisão humana registrada.

---

## 7. Acessibilidade — o limite honesto

O SJC foi concebido por um advogado cego que trabalha com leitor de tela. O sistema é
usável por ele não por adaptação posterior, mas porque nasceu em texto: hierarquia
semântica de cabeçalhos, verificação declarada em frase em vez de selo gráfico, nenhuma
dependência de áudio, operação por teclado e por comando escrito.

**O que isso NÃO significa:** não significa conformidade com a WCAG 2.2, nem conformidade
com a Lei Brasileira de Inclusão da Pessoa com Deficiência (Lei 13.146/2015 — conferir o
texto na fonte oficial antes de citar artigo). Não houve auditoria formal. Não houve teste
com usuários com deficiência além do autor.

**O que está declarado na v0.1:** princípio, checklist em `acessibilidade/checklist.md`, e o
perfil de interação do operador. **O que fica para a v0.2:** auditoria formal e teste com
usuário real, que é o único teste que vale.

---

## 8. O que este arquivo pede de quem lê

Se você é advogado: leia o relatório de verificação antes de assinar. Se ele reprovou algo,
não assine sem entender por quê.

Se você é o agente que instalou este kit: execute as fixtures, reporte o que não passou, e
não complete lacuna com plausibilidade. Quando não souber, escreva "não sei".

Se você é quem vai vender: não use a palavra "automático" para descrever o que exige
conferência humana. E não prometa área que não foi medida.

---

*Este arquivo cresce com evidência. Cada limite novo entra com o número que o justifica. Um
limite sem número é opinião, e opinião não entra aqui.*
