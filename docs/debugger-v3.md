# Debugger v3.0

O Debugger v3.0 executa código PSX R3000A montado pelo pipeline já usado pelo Binary Workbench. A sessão trabalha sobre uma imagem virtual isolada: edições de memória, registradores, breakpoints e marcações `IGNORED` nunca modificam o arquivo, workspace ou versões persistidas.

## Iniciando uma sessão

O arquivo principal deve ser um `.asm` salvo e declarar a faixa virtual na primeira linha. Um exemplo mínimo é:

```nasm
* virtual_memory_range 0x80000000 0x801DFFFF
* import current_file 0x801D9274
* define $pc 0x801D9274
* define $sp 0x801DFF00

nop
```

Use **Debugger → Run** ou `F5`. A janela só é criada depois que diretivas, imports, montagem, colisões, registradores, PC e backend forem validados. Repetir `F5` no mesmo workspace preserva e traz a sessão existente para frente.

As ações disponíveis no Binary Workbench e na janela são as mesmas:

| Ação | Atalho | Comportamento |
|---|---:|---|
| Run | `F5` | Executa do PC atual fora da thread da interface. |
| Pause | `F6` | Preserva PC, registradores e memória. |
| Stop | `F7` | Mantém o estado final para inspeção e exige Restart. |
| Restart | `F8` | Restaura o snapshot inicial e preserva breakpoints/IGNORED. |
| Step | `F9` | Executa uma instrução lógica, incluindo regras de delay slot. |
| Step Over | `F10` | Para `jal`/`jalr`, executa até o endereço local de retorno. |

## Diretivas

- `virtual_memory_range <início> <fim>`: obrigatória na primeira linha do arquivo principal; o fim é inclusivo.
- `import <arquivo|current_file> <endereço>`: aceita `.asm`/`.s` na pasta principal ou em subpastas. Imports são recursivos e ciclos exibem a cadeia completa.
- `define <registrador> <valor>`: define o snapshot inicial. Registradores não definidos começam em zero e o PC deve apontar para uma zona carregada.
- `ignore <registrador> <endereço>`: declara um destino de controle de fluxo que deve permanecer no fluxo local.

Valores aceitam literais hexadecimais ou Symbols cujo conteúdo completo seja hexadecimal. Diretivas não geram bytes, não consomem offsets e não aparecem em Raw Instructions.

## Janela

O painel principal mostra endereço virtual, bytes, Raw Instruction, origem e estado. O gutter alterna breakpoints; o menu de contexto copia endereços ou marca instruções como `IGNORED`. Registradores alterados são destacados e podem ser editados somente em pausa.

As abas inferiores oferecem:

- **Stack View** baseada no registrador de stack informado pelo backend;
- **Memory View** com quatro grupos de quatro bytes, navegação, cópia, edição hexadecimal, refresh e acompanhamento do PC;
- **Virtual Memory Zones** com limites, origem, status e bytes carregados;
- **Breakpoints** para adicionar, ativar, desativar, remover, copiar e navegar;
- **Debug Log** com eventos de execução, memória, alinhamento, limites e ciclo de vida.

Posição, tamanho, maximização, splitters e aba inferior são persistidos por workspace em um arquivo próprio. A restauração é limitada aos monitores disponíveis.

## Execução e segurança

O backend usa Unicorn MIPS32 little-endian. Run é cooperativo, mantém Pause/Stop responsivos e possui limite padrão de 100.000 passos lógicos; ao atingir o limite, a sessão fica pausada e pode continuar ou reiniciar.

Breakpoints são metadados e interrompem antes da instrução. Instruções `IGNORED` permanecem visíveis e contabilizadas, avançam como NOP e não chegam à Unicorn. Destinos ignorados de `j`, `jal`, `jr` e `jalr` preservam o fluxo local e não alteram registradores ou memória.

Hooks contabilizam execuções, leituras e escritas por endereço. Eventos de memória incluem tamanho, valor, PC e instrução responsável; acessos inválidos e desalinhados são convertidos em erros controlados.

## Testes

Os testes dirigidos estão em `tests/debugger/` e cobrem contratos, diretivas, editor, imports, memória, Unicorn, Step, Run/Pause/Stop/Restart, Step Over, breakpoints, IGNORED, hooks, views, persistência e abertura pelo Binary Workbench.
