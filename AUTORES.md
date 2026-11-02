# Autoria

## Autor

**Melhym Pereira Quemel**

- Mestre em Direito
- Advogado
- Especialista em advocacia cível
- Especialista em ciências penais e segurança pública
- Especialista em políticas públicas e tutela coletiva
- Graduando em Engenharia de Software

Contato: `mpquemel@gmail.com`

---

## O que a autoria explica, e o que não explica

Este não é um projeto de tecnologia que resolveu aprender Direito, nem um
projeto jurídico que contratou um programador. É um sistema desenhado por quem
usa, no mesmo dia, os dois lados: a peça que precisa estar correta e o código que
precisa não mentir sobre ela.

**O que a autoria justifica:** a escolha de tornar visível o que o sistema não
verifica. Quem assina peça sabe que a assinatura é pessoal e intransferível;
quem programa sabe que um `except` silencioso esconde a falha que depois aparece
em produção. Este kit existe na interseção — e recusa a solução confortável dos
dois lados.

**O que a autoria não justifica:** nenhuma garantia sobre o conteúdo jurídico
produzido. O autor responde pelas escolhas de engenharia declaradas neste
repositório; não responde pela peça que o usuário assinar, nem pelo acerto da
tese que ele escolher. Ver `LIMITES.md`.

---

## Origem do método

O método nasceu da prática de quem trabalha com leitor de tela — não como
adaptação posterior, mas como condição de projeto. Documento jurídico é texto
hierárquico: seção, inciso, parágrafo, citação. Quem navega por cabeçalho sabe
onde a estrutura importa; quem vê a página costuma esquecer.

Duas consequências práticas atravessam o kit:

1. **Relatório em frase, não em selo.** "3 citações não conferidas, aqui estão"
   é lido por leitor de tela; um selo verde não é.
2. **Veredito discreto, nunca nota.** `PASSA`, `ADVERTE`, `REPROVA` são
   navegáveis e dizem o que fazer. "82 de 100" não diz nada — e é exatamente o
   número que convida a ignorar o item reprovado.

---

## Como citar este projeto

```
QUEMEL, Melhym Pereira. SJC — Sistema Jurídico Customizável (sjc-kit).
Versão 0.1, 2026. Disponível em: <URL do repositório>.
```

---

## Contribuição

Correção de defeito, nova fixture adversarial e domínio novo são bem-vindos
quando vêm com o teste que os prova. Ver `GUIA-DOMINIO.md` para o procedimento de
domínio novo.

O que não é aceito: alterar regra de reprovação para destravar uma peça. Um kit
que aprova a si mesmo não serve para nada.
