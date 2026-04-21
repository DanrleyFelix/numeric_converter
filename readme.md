# Numeric WorkBench

Numeric WorkBench e uma calculadora numerica com duas frentes integradas:

- um conversor ao vivo entre Decimal, Binary, Hex (BE) e Hex (LE);
- uma command window para expressoes, atribuicoes, reutilizacao de variaveis e historico operacional.

O objetivo do projeto e oferecer uma bancada de trabalho para manipulacao numerica, analise bitwise e persistencia de contexto sem perder clareza visual.

## O que a calculadora faz

- Converte automaticamente entre Decimal, Binary, Hex Big-Endian e Hex Little-Endian.
- Restringe cada input do converter aos caracteres validos da sua base.
- Mantem o cursor no fim do input do converter para preservar digitacao e backspace previsiveis.
- Aceita digitacao pelo teclado principal e pelo numpad.
- Aplica `group size` e `zero padding` por campo, definidos em `Preferences`.
- Trata hexadecimal digitado de forma progressiva, completando o byte com zero a esquerda quando necessario.
- Separa o conteudo digitado do padding de exibicao para evitar corrupcao durante a edicao.
- Avalia expressoes na command window com operadores numericos e bitwise.
- Permite atribuicoes de variaveis com nomes compativeis com Python.
- Aceita prefixos como `0x` e `0b`.
- Aceita operadores textuais como `NOT`, `AND`, `OR` e `XOR`.
- Faz autocomplete de variaveis salvas no contexto.
- Corrige expressoes invalidas a partir do ultimo caractere digitado.
- Exibe resultado da command window na label superior.
- Pode enviar o resultado decimal da command window diretamente para o converter por meio do toggle `Convert`.
- Mantem `History` e `Log`, com persistencia em JSON.
- Salva e carrega contextos especificos.
- Salva e carrega logs especificos.
- Mantem `default context` e `default log` automaticamente.
- Possui key panel integrado com `LOG`, `CLEAR` e `ENTER`.
- Possui janela interna de ajuda paginada em PySide, acessivel pelo botao `Help`.

## Converter

### Bases aceitas

- `Decimal`: apenas `0-9`
- `Binary`: apenas `0` e `1`
- `Hex (BE)` e `Hex (LE)`: apenas `0-9` e `A-F`

### Regras importantes

- O converter bloqueia teclas invalidas no proprio input.
- O valor bruto digitado e mantido separado da exibicao formatada.
- O valor convertido considera a representacao efetiva com zero padding.
- Em hexadecimal, quando a quantidade de digitos nao completa um byte, um zero a esquerda e usado para completar a entrada.
- O comportamento de `Hex (LE)` continua estavel mesmo quando o usuario adiciona mais digitos depois de um padding visual.

### Exemplo

Se `Hex (LE)` estiver com `group size = 4` e `zero pad = true`:

```text
raw: 45
display: 0045

raw: 454
display: 0454
```

## Command Window

### O que pode ser digitado

- numeros decimais;
- valores em hexadecimal com `0x`;
- valores em binario com `0b`;
- variaveis;
- atribuicoes;
- operadores aritmeticos e bitwise.

### Exemplos

```text
mask = 0xFF
base = 0b1010
mask AND base
NOT 0x0F
gp = 0x89823A
gp >> 3
```

### Comportamento

- Enquanto o usuario digita, a expressao e validada continuamente.
- Se o final da expressao estiver incorreto, o sistema remove apenas o trecho invalido do fim.
- Variaveis presentes no contexto aparecem no autocomplete.
- O historico nao mostra o prompt `>>`.
- O log registra as linhas no formato `expressao -> resultado`.
- O resultado validado aparece em verde na label superior.

## Contexto e Log

### Contexto

Contexto representa o estado de trabalho do usuario:

- variaveis salvas;
- historico de comandos;
- linha ativa da command window;
- estado atual do converter;
- visibilidade do key panel.

### Log

Log representa as execucoes realizadas:

- comando executado;
- resultado ou mensagem associada;
- persistencia em JSON.

### Persistencia

Todos os dados ficam dentro da pasta `data`:

- `data/contexts`
- `data/logs`

Arquivos importantes:

- `default_context.json`
- `default_log.json`

## Preferences

O menu `Preferences` permite:

- abrir a configuracao do converter;
- mostrar ou ocultar o key panel.

Dentro da janela de preferencias, cada campo do converter pode configurar:

- `group size`
- `zero pad`

## Key Panel

O key panel digita diretamente na command window.

### Acoes especiais

- `LOG`: alterna entre `History` e `Log`
- `CLEAR`: apaga o ultimo caractere da linha ativa ou remove uma linha do painel ativo
- `ENTER`: executa a expressao atual

## Help interno

O botao `Help` abre uma janela dedicada dentro do programa com paginas de manual. Ela foi feita em Python/PySide e cobre:

- visao geral;
- converter;
- command window;
- contexto e logs;
- preferencias.

## Estrutura do projeto

O projeto segue uma arquitetura organizada por responsabilidades:

- `src/core`: regras centrais de conversao, tokenizer, validator e contexto
- `src/application`: contratos, DTOs, servicos e casos de uso
- `src/controllers`: ponte entre UI e casos de uso
- `src/presentation`: presenters, repositorios, formatters e componentes de interface
- `src/main`: composicao da aplicacao
- `tests`: cobertura automatizada
- `data`: persistencia local de contextos e logs

## Dependencias

Dependencias principais do projeto:

```text
packaging==25.0
PySide6==6.10.1
PySide6_Addons==6.10.1
PySide6_Essentials==6.10.1
QtAwesome==1.4.0
QtPy==2.4.3
shiboken6==6.10.1
pytest
```

## Executar

```bash
python -m src
```

Se o bootstrap principal do projeto estiver apontando para outro entrypoint local, basta usar o ponto de entrada configurado no ambiente.

## Testes

```bash
pytest
```

## Resumo

Numeric WorkBench foi pensado para ser mais do que um conversor simples. Ele une:

- conversao numerica orientada a bases;
- calculo com expressoes e variaveis;
- persistencia de contexto;
- log operacional;
- preferencias de formatacao;
- documentacao interna integrada a interface.
