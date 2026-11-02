# AGENT.md — Contrato de Instanciação do SJC

> **Este arquivo não é uma introdução. É um contrato.**
> Você é um agente. Este é o primeiro arquivo que você lê. Ele termina com uma
> autoavaliação: se você não cumprir os pré-requisitos, **você não instala**.
>
> Projeto: `sjc-kit` · Sistema Jurídico Customizável · v0.1
> Leia também, na ordem: `LIMITES.md` → `METODO.md` → `ESPECIFICACAO-PRODUTO.md`.

---

## 0. Regras invioláveis

Estas não são recomendações. Violação desqualifica a instalação.

1. **Nunca infira o polo.** Se o operador não declarou em que polo atua, **pare**. Não
   deduza por vocativo, por ordem de qualificação, por padrão de petição, nem "porque é
   óbvio". A inferência falhou em **119 de 121** processos reais.
2. **Nunca complete lacuna com plausibilidade.** Quando você não sabe, escreva `"não sei"`
   e registre o que faltou. Lacuna preenchida é o defeito que este kit existe para impedir.
3. **Nunca altere as regras de reprovação do gate.** Código em `core/gates/` e as regras de
   `FAIL` são imutáveis por instrução de setup. Otimizar o gate que te reprova é sabotar a
   única coisa que dá confiabilidade ao sistema. Alteração exige revisão humana registrada.
4. **Nunca assine nem protocole.** Não existe comando, opção ou flag para isso. Se alguém
   pedir, recuse e explique.
5. **Nunca coloque dados reais de cliente no repositório.** Só fixtures sintéticas.
6. **Nunca cite sem verificar conteúdo.** Status HTTP 200 não é prova de nada. Só âncora de
   conteúdo (número da norma, trecho conferido, hash do dispositivo) conta.
7. **Nunca confie em um auditor que aprova tudo.** Se o revisor for o mesmo modelo do
   gerador, a configuração é inválida — recuse rodar.
8. **Não invente arquivo, comando ou campo.** Se um comando citado aqui não existir ao
   inspecionar o repositório, isso é incompatibilidade entre este documento e o código:
   **pare e reporte**. Não improvise equivalente.

---

## 1. O que você está instalando

Um pipeline de produção de peça jurídica que termina **antes da assinatura**, com:

- Núcleo genérico (`core/`) que não conhece área jurídica.
- Domínio de demonstração completo (`dominios/familia/`).
- Domínio-esqueleto vazio (`dominios/penal/`) como detector de acoplamento.
- Adaptadores de fonte opcionais (`adaptadores/`).
- Fixtures adversariais que **devem reprovar**.

Você instala, roda as fixtures, e **reporta o que não passou**. Instalação bem-sucedida é a
que termina em relatório, inclusive de falha.

---

## 2. Ordem de execução

Execute nesta ordem. Não pule etapas por parecerem redundantes — cada uma existe porque a
anterior já mentiu em algum caso.

### ETAPA 0 — Autoavaliação de pré-requisitos

Responda as perguntas da seção 9. **Se qualquer resposta reprovar, pare aqui** e reporte
qual pré-requisito faltou, com a pergunta exata.

### ETAPA 1 — Inspeção, antes de qualquer execução

```
ls -la
cat ESTADO-PROJETO.md
cat LIMITES.md
```

**Verifique:**
- A árvore de diretórios corresponde ao esperado? Se `core/`, `dominios/`, `tests/` não
  existirem, o repositório está em estágio pré-código: **não instale, reporte**.
- Existe `pyproject.toml`? Qual versão de Python é exigida?

**Nunca:** executar script de setup antes de ler `scripts/bootstrap.py`.

### ETAPA 2 — Bootstrap

```
python scripts/bootstrap.py
make verify
```

**Saída esperada:** linha final indicando testes aprovados e fixtures do domínio demo
executadas.

**Se falhar:** copie a mensagem integral, identifique o estágio, e consulte o bloco
`FALHA CONHECIDA` do estágio correspondente em `docs/`. **Não** conserte editando código do
núcleo. Reporte.

### ETAPA 3 — Execução das fixtures adversariais

```
make adversariais
```

**Critério de sucesso — atenção, é invertido:** cada fixture marcada como adversária
**deve** produzir `FAIL` ou `REPROVADO`. Uma fixture adversária que passa é uma **falha de
instalação**, não um sucesso. Reporte qual fixture aprovou indevidamente.

### ETAPA 4 — Criação de domínio (somente se o operador pedir)

```
python cli/main.py init-dominio --nome <area>
```

Isso copia `dominios/_template/` para `dominios/<area>/`. Depois, você preenche os YAMLs
**com o operador**, nunca sozinho:

- `dominio.yaml` — identificação e versão.
- `estrategia.yaml` — catálogo de gatilho → peça cabível. **Cada gatilho precisa de fonte
  normativa conferida.** Gatilho sem fonte não entra.
- `tese-catalogo.yaml` — teses com fundamento e antítese.
- `templates/` — modelos com blocos `[OBRIGATÓRIA]`.
- `gates/regras.yaml` — regras de forma do domínio.

**BLOQUEIO:** se preencher o catálogo exigir alterar qualquer arquivo em `core/`, **pare**.
Isso é acoplamento, e é exatamente o que o domínio-esqueleto penal existe para detectar.
Reporte o campo que não coube.

### ETAPA 5 — Validação do domínio

```
make validar-dominio DOMINIO=<area>
```

**Saída esperada:** campos obrigatórios presentes; valores ausentes marcados como
`a preencher` (o validador aprova esqueleto declarado e reprova campo inventado).

---

## 3. Contrato de cada estágio

Todo estágio tem a mesma forma. Ao **executar** um estágio, você lê o contrato em
`core/contratos/schemas/` e respeita:

```
QUANDO:    pré-condição verificável (arquivo existe, campo presente, hash confere)
ENTRA:     artefato de entrada, com schema
SAI:       artefato de saída, com schema
NUNCA:     proibições explícitas
VERIFICA:  comando ou checagem + resultado esperado
FALHA CONHECIDA: o que já deu errado e por quê
CASO ADVERSARIAL: entrada que deve reprovar
```

Resumo dos estágios e das proibições que mais importam:

**S0 — Declaração.** Pergunta e grava polo, área, prazo, perfil. **Nunca** infere.
Saída com hash: é o documento de responsabilidade do operador.

**S1 — Conversão.** Triagem por página; OCR seletivo; proveniência por página.
**Nunca** trata descrição como prova. Página sem texto entra em lista com classe.
**Nunca** deixa página desaparecer em silêncio.

**S2 — Vinculação de IDs.** A árvore é **entrada**, não extração. **Nunca** chama LLM.
**Nunca** "corrige" um ID. ID citado que não existe na árvore é órfão → **exit 5**.
Se `arvore.txt` está ausente e o caso declara que há árvore, **falhe alto** — não produza
vinculação vazia fingindo sucesso.

**S3 — Estratégia.** Lê do ponto de vista declarado. **Nunca** escolhe peça sem gatilho
documentado. **Nunca** infere prazo. **Nunca** omite a alternativa mais grave.
Prazo com nível `CONFIRMADO` / `ESTIMADO` / `INCERTO`; peremptório **para o sistema**.
**Nunca** sugere peça para protelar.

**S4 — Tese.** Cada bloco tem afirmação, fundamento, doutrina literal, jurisprudência e
**antítese**. **Nunca** apresenta paráfrase como citação literal. Roteador de área é
preferência de ranking, **nunca** filtro excludente.

**S5 — Redação.** Template do domínio; cada parágrafo rastreável a uma tese.
**Nunca** escreve parágrafo sem tese de origem.

**S6 — Verificação de citações.** Extrai **todas**, inclusive formas não abreviadas
("artigo 1.694" sem "art."). Três estados: `Verified`, `Warning`, `Not Found`.
Conteúdo diverso do atribuído é tratado como **`Not Found`**, nunca `Warning`.
**`Not Found` retém a peça** e marca a tese como descoberta.

**S7 — Gate de cinco camadas.** G1 legal e G2 factual **não são automatizáveis**: exigem
declaração explícita do operador; sem ela, reprova. G3 forma reprova de verdade.
G4 transcrição. G5 auditoria por **modelo diferente** do gerador.
**Nunca** emite nota de 0 a 100. Veredito discreto com motivo por item.

**S8 — Entrega.** Pacote pré-assinatura, auditoria encadeada por SHA-256, aviso de peça
parada. **Nunca** assina. **Nunca** protocola. **Para aqui.**

---

## 4. Como você deve falhar

Falhar bem é parte do contrato. Um agente que falha em silêncio é pior que um que quebra.

**Formato de relatório de falha:**

```
ESTÁGIO:      <S0..S8 ou etapa de instalação>
COMANDO:      <o comando exato executado>
ESPERADO:     <o que o contrato diz que deveria acontecer>
OBSERVADO:    <a saída real, íntegra>
HIPÓTESE:     <a causa provável — marcada como HIPÓTESE, não como diagnóstico>
NÃO FIZ:      <o que você decidiu não fazer e por quê>
```

**Regra:** hipótese não é diagnóstico. Se você não mediu a causa, escreva "não sei" na
linha da hipótese. Empilhar hipóteses com cara de conclusão é o defeito mais comum.

---

## 5. O que você **não deve** fazer, listado por sedução

Estas são as coisas que um agente razoável faz e que aqui estão erradas:

- "O polo está óbvio pelo nome das partes." → **Errado.** Pergunte.
- "A citação existe, logo está conferida." → **Errado.** Confira o conteúdo.
- "A fixture passou, então o domínio está bom." → **Errado.** Passou a instalação.
- "O gate reprovou por regra muito rígida; vou afrouxar." → **Proibido.**
- "Não achei o campo, criei um equivalente." → **Proibido.** Reporte a lacuna.
- "Vou resumir o relatório para ficar mais legível." → **Cuidado.** O relatório item por
  item é requisito de acessibilidade e de auditoria, não enfeite.
- "O auditor aprovou tudo, ótimo." → **Alarme.** Meça o auditor antes de confiar no veredito.
- "Vou completar o que faltou com o que parece razoável." → **É disso que o kit trata.**

---

## 6. Acessibilidade — requisito do agente, não do produto

Ao produzir qualquer saída para o operador:

- Markdown com hierarquia de cabeçalhos correta, sem pular níveis.
- Sem posição, cor, ícone ou coordenada como instrução de interface.
- Nenhuma informação transmitida **só** por tabela; tabela pode existir em arquivo `.md`,
  mas o conteúdo precisa estar legível linearmente.
- Veredito declarado em frase completa ("reprovou porque X"), nunca apenas selo ou emoji.
- Nenhuma dependência de áudio.
- Instrução de navegação por nome de elemento ou tecla, não por localização visual.

---

## 7. Dados, sigilo e rastro

- Dados de cliente nunca em git. Antes de qualquer commit, rode a verificação de vazamento
  descrita em `docs/` e **não prossiga se ela falhar**.
- Escolha entre modelo local e API de terceiro é do escritório. Registre a escolha com
  rastro; não decida por ninguém.
- Toda entrega gera auditoria encadeada por hash. Não edite nem reordene entradas.

---

## 8. Critério de aceitação da v0.1

A instalação está correta quando, e somente quando:

1. `make verify` passa.
2. Família roda a fixture ponta a ponta até entrega, com relatório de citações.
3. Penal tem esqueleto declarado e o validador de domínio **aprova o esqueleto** (campos
   obrigatórios presentes, valores ausentes marcados `a preencher`).
4. **Nenhuma alteração foi necessária em `core/`** para declarar penal.
5. Todas as fixtures adversariais reprovam.
6. Existe relatório final, inclusive das falhas.

Se o item 4 falhar, **o produto falhou no teste que o define**. Reporte imediatamente.

---

## 9. AUTOAVALIAÇÃO DE PRÉ-REQUISITOS

Responda cada item com **SIM**, **NÃO** ou **PARCIAL**, e a evidência que sustenta a resposta.
`PARCIAL` reprova.

**A. Capacidade de execução**

1. Você consegue executar comandos de shell no ambiente do operador? Evidência: comando
   executado com saída.
2. Você consegue escrever arquivos no diretório do repositório? Evidência: arquivo criado.
3. Você tem acesso a `git`? Evidência: `git --version`.
4. Você tem Python 3.11 ou superior disponível? Evidência: `python --version`.

**B. Modelo e revisão**

5. Você consegue usar **um modelo diferente** do seu para o gate G5 de auditoria?
   Se não, **NÃO INSTALE** — a revisão por modelo identico é inapta e está medido.
6. Você sabe qual modelo gerou a peça e qual a revisou, e consegue registrar isso?
   Sem rastro da escolha de modelo, a instalação está incompleta.

**C. Rede e fontes**

7. Você consegue acessar as fontes oficiais de legislação e jurisprudência que o domínio
   exigir?
8. Você tem regra de validação **por conteúdo** (não por status HTTP)?

**D. Dados**

9. Você tem uma fixture sintética de processo (PDF + árvore) para rodar a validação?
10. Você confirmou que **nenhum** dado real de cliente está no índice ou no repositório?

**E. Disciplina**

11. Você aceita não alterar `core/gates/` mesmo que ele reprove sua própria saída?
12. Você aceita parar e reportar em vez de improvisar quando um campo não couber?
13. Você aceita tratar `Not Found` como retenção, não como aviso?

---

### Resultado da autoavaliação

Se todas as respostas forem **SIM**, escreva o relatório de instalação e prossiga.

Se **qualquer** resposta for **NÃO** ou **PARCIAL**:

```
INSTALAÇÃO RECUSADA
PRÉ-REQUISITO FALTANTE: <número e texto do item>
EVIDÊNCIA: <o que você observou>
CONSEQUÊNCIA: <o que acontece se instalar sem isso>
O QUE NÃO FIZ: <nada foi executado além da autoavaliação>
```

Recusar instalação é uma saída válida deste contrato. **Não é falha.** Instalar sem
pré-requisito é a falha — e ela se manifesta meses depois, numa peça assinada com polo
invertido.

---

*Este arquivo é o contrato de entrada. Se algo aqui não corresponde ao código, o documento
está errado ou o código está: descubra qual, reporte, e não siga improvisando.*
