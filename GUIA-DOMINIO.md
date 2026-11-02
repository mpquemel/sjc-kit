# Guia de domínio novo

> Como acrescentar uma área ao kit **sem tocar em `core/`**. Se tocar, o defeito
> é de arquitetura, não de configuração.

## 1. A regra que decide tudo

`core/` não conhece área nenhuma. Um domínio é um diretório com arquivos de
declaração — YAML e Markdown. O núcleo lê esses arquivos por contrato e nunca
pergunta "isto é família?".

A seta é sempre `dominios → core`. Duas consequências práticas:

1. Se você precisar de `if dominio == "trabalhista"` em `core/`, o desenho está
   errado. Corrija o desenho, não o `if`.
2. Se `core/` não oferecer o que o domínio precisa, isso é uma **lacuna do
   núcleo**, e deve ser resolvida de forma genérica — não com exceção por área.

## 2. O que é um domínio

```
dominios/<id>/
  dominio.yaml              identidade, acervo, modelos, contagem de prazo, polos
  estrategia.yaml           árvore de decisão: gatilho → peça → prazo
  tese-catalogo.yaml        teses com gatilho, fundamento e confiança
  gates/regras.yaml         o que reprova NESTA área, com fundamento
  prompts/estrategia.md     instrução de leitura dos autos
  prompts/elaboracao.md     instrução de redação
  prompts/revisao.md        instrução de auditoria
  templates/*.md            estrutura da peça, por tipo
  templates/_indice.yaml    mapa tipo → arquivo
  tests/casos-adversariais.yaml   entradas que DEVEM reprovar
```

Comece copiando `dominios/_template/`. Ele existe exatamente para isso, e não
traz nenhum conteúdo de área.

## 3. Procedimento, em sete passos

### Passo 1 — copiar o template

```
cp -r dominios/_template dominios/<id>
```

### Passo 2 — preencher `dominio.yaml`

Obrigatórios: `id`, `nome`, `versao`, `estado`, `polos_usuais`, `acervo`,
`contagem_prazo`. Campo que você ainda não sabe preencher fica com o texto
`a preencher` — nunca com um chute plausível. O validador lê `a preencher` como
pendência **declarada**, que é estado legítimo; um valor inventado é falha que
ninguém vê.

### Passo 3 — declarar as peças em `tese-catalogo.yaml`

Cada entrada precisa de quatro coisas: **gatilho** (que fato dos autos dispara),
**peça** (o tipo documental), **fundamento** (a norma que sustenta) e
**confiança** (`alta` / `media` / `baixa`).

Duas armadilhas que custaram defeito real neste kit:

- **`conteudo_contem` é alternativa, `conteudo_contem_todos` é conjunção.**
  "alimentos" sozinho casa a regra de cumprimento de sentença; "alimentos" **E**
  "cumprimento" casam a regra certa.
- **Tipo documental é `tipo_documento`, nunca substring.** `nao_contem: [sentenca]`
  mata a regra correta quando a peça apenas *menciona* a palavra sentença. Uma
  decisão interlocutória que cita "sentença" não é sentença.

### Passo 4 — escrever os três prompts

`estrategia.md` lê os autos **do ponto de vista do polo declarado** e não escolhe
lado. `elaboracao.md` preenche o template. `revisao.md` audita a peça pronta.

Os prompts são texto de instrução, não código. Mantenha-os curtos e verificáveis;
prompt que não pode ser violado de forma perceptível não está instruindo nada.

### Passo 5 — declarar os gates

`gates/regras.yaml` é onde a área diz o que a reprova. Cada regra precisa de:
`id`, `aplica_a`, `condicao`, `veredito`, `fundamento`, `mensagem`.

**Aviso medido:** no domínio família, **3 das 6 regras declaradas são executáveis
por programa**. Regra escrita em prosa, sem avaliador correspondente em
`core/pipeline/s6_gates.py`, sai `NAO_AVALIADO` com o motivo — nunca `PASSA`. Se
você declarar vinte regras e nenhuma tiver avaliador, o operador recebe vinte
`NAO_AVALIADO` e uma peça bloqueada. Isso é honesto, mas não é útil.

Escolha as regras que valem a pena automatizar primeiro: aquelas cuja verificação
é **contagem**, não julgamento. "A seção de razões tem menos de três parágrafos"
é contável. "A tese é a mais adequada" não é.

### Passo 6 — escrever os casos adversariais

`tests/casos-adversariais.yaml`. Cada caso pergunta: *qual é a entrada que faz
**este** domínio mentir?*

Categorias que já se provaram produtivas:

- **exceção dentro da regra** — nota de dispositivo interno contaminando o todo
- **forma ambígua** — dois documentos casando com o mesmo padrão
- **dado que contradiz o próprio texto** — status inferido contra o caput
- **codificação ou formato divergente** do declarado

Um caso adversarial que **passa** é um defeito: ou o caso está mal escrito, ou o
sistema está mentindo. Ambos exigem correção antes do commit.

### Passo 7 — validar

```
make validar-dominio DOMINIO=<id>
make adversariais
make verify
```

O validador devolve um veredito discreto: `APROVADO` (nenhum campo ausente,
nenhuma pendência), `ESQUELETO` (nenhum campo ausente **e** há pendências
`a preencher`) ou `REPROVADO` (campo obrigatório ausente). Código de saída:
0 para `APROVADO` e `ESQUELETO`, 1 para `REPROVADO`.

Esqueleto aprovado é sucesso — declarar o que não se sabe é o estado inicial
correto. Reprovado é campo faltando, não campo pendente.

## 4. O teste de acoplamento

`dominios/penal/` existe vazio por um motivo único: ser o **detector de
acoplamento**. Ele quebra premissas do núcleo que família esconde — prazo em dias
corridos, peça sem prazo, catálogo diferente, campo onde mais se mente em citação.

Se configurar penal exigir código novo em `core/`, a generalidade era marketing.
O mesmo teste se aplica ao seu domínio novo: **se ele exigiu tocar em `core/`,
pare e redesenhe.**

## 5. O que ainda não existe, e você não deve pressupor

- **Contrato automatizado de dependência.** Não há `import-linter` nem teste que
  falhe quando `core/` importa um domínio. A fronteira hoje é verificada por
  disciplina e pelo detector penal. Está na lista de trabalho.
- **Descoberta automática de domínio.** O domínio é identificado por `dominio_id`
  na entrada do caso. Um domínio que existe no disco e não é declarado não roda.
- **Validação semântica dos gates.** O validador confere estrutura e campos
  obrigatórios; não confere se a `condicao` faz sentido jurídico.

## 6. Checklist antes do primeiro commit do seu domínio

- [ ] `make validar-dominio DOMINIO=<id>` passa com veredito declarado
- [ ] todo campo desconhecido está escrito `a preencher`, não chutado
- [ ] nenhum dado de cliente, PDF ou transcrição real no diretório
- [ ] cada caso adversarial **reprova** em `make adversariais`
- [ ] nenhuma alteração em `core/` no mesmo commit
- [ ] os três prompts descrevem o polo declarado, nunca escolhem lado

Se algum item falhar, o domínio não está pronto — mesmo que o pipeline rode.
