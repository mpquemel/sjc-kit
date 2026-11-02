# Sistema Jurídico Customizável — `sjc-kit`

> Um método para construir um sistema jurídico que não mente — entregue como kit
> que um agente de IA lê e instancia no escritório.

**Antes de qualquer coisa, o limite:** este kit não substitui juízo profissional,
**não assina, não protocola e não garante acerto**. Ele garante uma coisa só, e é
verificável: **o erro fica visível antes da assinatura.**

**Depois do limite, a origem:** este kit foi concebido por um advogado cego que
trabalha com leitor de tela. A acessibilidade não é recurso adicional — é a
condição em que o sistema nasceu. Ver [Autoria](#autoria) e
[Acessibilidade](#9-acessibilidade).

---

## 1. O que é, em três camadas

| Camada | O que é | Custo |
|---|---|---|
| **Método** | `METODO.md` — como se faz e por que cada escolha, com os números que a forçaram | Gratuito, público |
| **Kit** | Este repositório — núcleo pequeno e testável, um domínio operacional, dois esqueletos declarados | Gratuito, aberto |
| **Instanciação** | O serviço: o agente lê o kit, pergunta a área, constrói o domínio do escritório | Pago por projeto |

O ativo não é o texto gerado. É o **registro de onde a IA mente** — com página,
reprodução e o procedimento que impede que isso chegue à assinatura.

---

## 2. O estado real, em números

Medido em 02/11/2026, no commit que acompanha este README:

```
estágios implementados   S0 S1 S2 S3 S4 S5 S6 S7 S8   (9, nenhum faltando)
testes                    205, em 15 suítes
suítes                    todas verdes
casos adversariais        11 (6 família, 5 penal) — todos recusados como exigido
domínios                 família (operacional parcial), penal (esqueleto), _template
regras de gate, família   6 declaradas, 3 executáveis por programa
páginas de PDF medidas    32 — 29 reconhecidas úteis, 3 recusadas (1 escaneada, 2 rodapés)
execução ponta a ponta    `make demo` — S0 a S8, entrega bloqueada por G1/G2/G3/S6
fronteira core→domínios   verificada por `core/tests/test_fronteira.py` (ast, stdlib)
```

Este bloco existe para que ninguém precise acreditar na palavra do README: ele
pode ser reconferido com `make verify`, `make adversariais` e `make demo`.

---

## 3. Para quem é, e para quem não é

**É para:** sócio de escritório que assina peça e responde por ela; advogado
autônomo com volume acima da capacidade de revisão; escritório pequeno sem equipe
de tecnologia; órgãos públicos que queiram o mesmo método sem
depender deste autor.

**Não é para:** quem quer substituir o advogado; quem quer "IA que redige
sozinha"; quem não vai ler o relatório de verificação; quem processa dados de
cliente em API de terceiro sem base legal.

Não é atrelado a órgão público nenhum. Órgãos públicos são usuários possíveis,
não premissa.

---

## 4. Como usar em cinco minutos

Pré-requisito: **Python 3.11+**. Para o caminho completo, também `pymupdf`
(leitura de PDF) e `PyYAML`. `python-docx` só é exigido no estágio de entrega.

```
git clone <url> sjc-kit
cd sjc-kit
make bootstrap        # confere Python, PyYAML, estrutura e barreira de dados
make verify           # bootstrap + 13 suítes + lista de domínios
make adversariais     # os 11 casos que DEVEM reprovar
```

`make verify` termina com uma linha de resultado e código de saída. Se ele passar,
**a instalação está correta** — o que significa que o kit roda e que as fixtures
produzem a saída esperada. Não significa que ele saiba jurídico. A diferença entre
instalação correta e peça correta é a diferença entre um carro que liga e um carro
que chega.

`make demo` roda o caso sintético versionado em `casos/_exemplo/` — PDF de duas
páginas, `arvore.txt` e `caso.json` com CNJ de DV calculado — **do S0 ao S8**:

```
[OK  ] S0  [OK  ] S1  [OK  ] S2  [OK  ] S3  [OK  ] S4
[OK  ] S5  [OK  ] S6  [OK  ] S7  [OK  ] S8        PARADA: fim em S8
```

E termina do jeito que tem de terminar: **peça bloqueada**.

```
vereditos.md      veredito: REPROVA | pode protocolar: não
camadas no pior veredito: G1, G2, G3, S6
motivo G1: sem declaração explícita de conferência legal
motivo G2: sem declaração explícita de conferência factual
minuta.docx       existe, com o bloqueio escrito dentro
```

O pipeline atravessa inteiro e para antes da assinatura, porque as camadas que
só o advogado pode declarar continuam não declaradas. Isso não é o demo
falhando: é o demo provando o que o kit promete — **o erro fica visível antes da
assinatura.**

O provedor da demo é determinístico, sem modelo de linguagem e sem rede: devolve
texto estrutural que se declara não jurídico em cada bloco. Ele prova o
transporte de dados, não o conteúdo. Trocar por modelo real é uma linha em
`dominio.yaml`, sob custo e responsabilidade do escritório.

**O tipo documental é declarado, não inferido.** `caso.json` traz
`tipo_documento`, e o S1 o aplica às páginas com texto. O kit não classifica
"isto é sentença" por regex de palavra: um classificador errado manda apelação
para o template de impugnação, com aparência de método. Ausente a declaração, o
S3 pausa e nomeia a lacuna.

---

## 5. O fluxo, em uma tela

```
S0 entrada      valida CNJ, PDF, árvore, domínio, polo declarado
S1 conversão    PDF → texto, com proveniência por página e classe por página sem texto
S2 vinculação   cruza IDs citados contra a árvore; órfão reprova
S3 estratégia   lê os autos do ponto de vista do polo DECLARADO (nunca escolhe lado)
S4 redação      preenche o template do domínio; pausa se o modelo não foi decidido
S5 citações     extrai e verifica; vacuidade e incerteza RETÊM
S6 gates        aplica as regras de forma do domínio; NAO_AVALIADO nunca é PASSA
S7 cinco camadas G1 legal, G2 factual, G3 forma, G4 transcrição, G5 auditoria
S8 entrega      monta o pacote e PARA antes da assinatura
```

Cada estágio é um arquivo que pode ser lido isoladamente. Nenhum importa outro:
a comunicação é por artefato versionado, não por chamada direta — senão o DAG
seria decorativo.

---

## 6. O que reprova, de verdade

| Situação | Consequência |
|---|---|
| Polo de atuação não declarado pelo operador | Pausa com motivo; o sistema nunca infere polo |
| ID citado que não existe na árvore (órfão) | `REPROVA` no artefato de vinculação; `pode_protocolar: false` |
| Citação não conferida, incerta ou de conteúdo diverso | Peça **retida**; tese marcada como descoberta |
| Peça sem nenhuma citação extraível | Retida por vacuidade — ausência de citação não é prova |
| Modelo gerador e revisor idênticos | `REPROVA` em G5: revisão sem independência |
| G1 ou G2 sem declaração explícita do operador | `REPROVA`; declaração sem autor ou hora não conta |
| Marcador de template residual, seção ausente ou fora de ordem | `REPROVA` em G3 |
| Transcrição citada sem fonte disponível | `NAO_AVALIADO` e bloqueio |

**Não há nota de 0 a 100.** O veredito por camada é discreto —
`PASSA`, `ADVERTE`, `REPROVA`, `NAO_AVALIADO`, `NAO_APLICAVEL` — e o veredito da
peça é **o pior entre as camadas aplicáveis**, nunca a média. A média esconde o
que não se compensa: forma impecável não compensa tese errada.

### O que NÃO é verificado automaticamente

Esta seção existe porque omiti-la seria a mesma mentira que o kit combate.

**G1 (legal) e G2 (factual) não são automatizáveis.** O sistema lista o que
conferir e exige declaração do operador com autor e hora. Não decide se a tese
cabe no ordenamento nem se o fato está nos autos.

**Das 6 regras de gate de família, 3 são executáveis por programa.** As outras 3
— `agravo-sem-pecas-obrigatorias`, `alimentos-sem-binomio`, `guarda-sem-fato-concreto`
— saem `NAO_AVALIADO` com o motivo, e nunca `PASSA`. Uma bateria verde que
escondesse isso seria pior que bateria nenhuma.

**O portão de citação confirma identidade, não conteúdo.** Ele encontra o
documento e compara o que o adaptador consegue comparar; não verifica vigência,
superação nem aderência à tese. Por isso, **peça que cita julgado não é liberada
automaticamente** — a decisão volta para o operador.

**O adaptador de fonte é opcional e frágil.** O kit não raspa tribunal. Se os
coletores não estiverem apontados em `SJC_FONTES`, a consulta devolve
`consulta_executada: false` e a peça é **retida** — nunca liberada por falta de
fonte.

---

## 7. Arquitetura em uma frase

Núcleo genérico (`core/`) que **não conhece área nenhuma**; domínios plugáveis
(`dominios/`) que trazem catálogo, templates e regras; coletores de fonte
opcionais, isolados em `core/citacoes/` e frágeis por natureza.

A seta é sempre `dominios → core`. Se `core/` precisar saber que existe
"família", a fronteira está errada.

**A fronteira é verificada por código.** `core/tests/test_fronteira.py` percorre
todo `core/` com `ast` e reprova: import estático de `dominios/`, import
dinâmico (`importlib`, `__import__`), e qualquer caminho literal para um domínio
específico. Caminho **parametrizado** (`RAIZ / "dominios" / dominio`) é o
contrato e passa — o núcleo sabe que existe uma pasta de domínios, não qual
delas usar. O teste tem meta-teste: injeta uma violação de propósito e exige que
o detector a encontre.

Sem `import-linter`. A biblioteca resolveria o mesmo problema ao custo de uma
dependência a instalar em cada máquina do escritório; `ast` é stdlib e o teste
inteiro cabe em uma tela.

O detector de acoplamento continua existindo por outro motivo: `dominios/penal/`
está vazio e declarado. Se configurá-lo exigir código novo em `core/`, a
generalidade era marketing. O teste de fronteira pega import; não pega schema que
rejeite um campo novo — e essa é a parte que só o domínio novo revela.

O núcleo funciona com **PDF + árvore em mão**. Nenhum sistema de tribunal é
pré-requisito, e nenhum é citado como dependência.

---

## 8. O teste que decide se o produto é real

**Família implementado não prova generalidade. Penal prova.**

O criminalista quebra mais premissas: prazo em dias corridos em parte dos
recursos, catálogo de peça diferente, `habeas corpus` sem prazo, e a dosimetria
como campo onde mais se mente em citação — três frases, três premissas do núcleo
sob tensão.

Por isso `dominios/penal/` nasce **vazio no primeiro commit**: campos
declarados, valores `a preencher`, 22 pendências nomeadas. Ele não roda; é o
**detector de acoplamento**. Rodar o pipeline em penal deve recusar por campo
não decidido — nunca por `KeyError`, `ImportError` ou schema que rejeite o campo.
Se recusar por erro de código, o defeito está em `core/`.

---

## 9. Acessibilidade

Construído por quem usa leitor de tela; auditável por quem não vê a tela.

Toda comunicação é textual e sequencial. Relatórios em Markdown com hierarquia
semântica de cabeçalhos. Verificação declarada em frase ("3 citações não
conferidas, aqui estão") em vez de selo gráfico — um selo não é lido, uma frase é.
Nenhuma dependência de áudio. Operação por teclado e por comando escrito.
Explicação de gate item por item, em linguagem direta.

**O que isso não significa:** não é conformidade com WCAG 2.2 nem com a Lei
Brasileira de Inclusão. Não houve auditoria formal. O teste com usuário real está
previsto para a v0.2 — é o único teste que vale.

---

## 10. Sigilo, dados e responsabilidade

- **Dados de clientes nunca entram no git.** O `.gitignore` isola `casos/`,
  `*.pdf`, saída de pipeline e bytecode, com o motivo de cada linha escrito.
- Repositório público só com código e **fixtures sintéticas**.
- **Falha conhecida e declarada:** o `bootstrap` verifica o repositório que contém
  o projeto e exige que alguma regra isole `casos/`. A checagem é **textual**; não
  interpreta a semântica completa do `.gitignore`.
- Escolha entre modelo local e API de terceiro é do escritório, com base legal,
  minimização e registro de tratamento (LGPD). O kit documenta o padrão; não
  decide.
- **Responsabilidade é de quem assina.** Nenhuma saída do sistema transfere isso.
- O agente que instala o kit **não pode alterar as regras de reprovação**. Se
  alterar, o sistema perde a única coisa que o torna confiável.

---

## 11. Documentos, e em que ordem ler

Para **entender**:

1. `LIMITES.md` — o que o projeto declara não saber. Leia primeiro; foi escrito
   para isso.
2. `METODO.md` — como se faz e por que, com os números que forçaram cada decisão.
3. `ESPECIFICACAO-PRODUTO.md` — o desenho completo, estágio por estágio.

Para **instalar**, comece por `AGENT.md` — é o arquivo escrito para a máquina, não
para o humano.

Para **estender**, leia `GUIA-DOMINIO.md`.

---

## 12. O que este projeto não promete

- Não garante acerto jurídico. Garante que o erro fica visível antes da assinatura.
- Não assina, não protocola, não envia.
- Não substitui o advogado em nenhuma etapa.
- Não valida vigência ou superação de precedente.
- Não é conforme WCAG nem auditado por usuário externo.
- Não tem nota. Tem veredito, com motivo.

A lista completa, com os números que a sustentam, está em `LIMITES.md`.

---

## Autoria

**Melhym Pereira Quemel**

Mestre em Direito; advogado; especialista em advocacia cível, ciências penais e
segurança pública, políticas públicas e tutela coletiva; graduando em Engenharia
de Software.

Contato: `mpquemel@gmail.com`

O método nasceu da prática de quem usa leitor de tela para trabalhar com
documento jurídico — e da constatação de que um sistema que promete acerto é
mais perigoso que um sistema que mostra onde errou.

Ver também `AUTORES.md`.

---

*Licença, status e estado do projeto: ver `ESTADO-PROJETO.md`.*
