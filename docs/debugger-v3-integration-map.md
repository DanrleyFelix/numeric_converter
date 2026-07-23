# Debugger v3.0 — mapa de integração (Task 1)

## Escopo

Este documento registra os pontos existentes que o Debugger deve reutilizar. Nesta task não foram criados contratos do Debugger, parser de diretivas, backend, janela ou fluxo alternativo de montagem.

## Fluxo atual de assembly

1. Um `.asm` é reconhecido em `tabs/source_rows.py:12-16`. `create_assembly_tab()` lê o arquivo e cria um `BinaryWorkbenchTabContextDTO` em `tabs/tab_context_factory.py:78`.
2. `rows_from_path()` lê as linhas e chama `build_rows_from_instructions()` em `tabs/source_rows.py:44`.
3. O ponto abstrato por arquitetura é `CPUArchCodec.build_source_line_rows()` em `src/modules/contracts.py:67`; a seleção concreta passa por `binary_workbench_codec_for()` em `src/core/binary_workbench/codec_registry.py:6`.
4. Para PSX R3000A, `build_source_line_rows()` em `src/core/binary_workbench/mips_r3000a/source_line_rows.py:14`:
   - expande pseudo-instruções;
   - calcula Labels provisórios e estabiliza seus offsets;
   - chama `raw_mips_instruction()` para pré-processar cada linha;
   - chama `codec.assemble()`;
   - grava o resultado em `BinaryWorkbenchRowDTO.bytes_text`;
   - só incrementa o offset quando foram gerados bytes.
5. `preprocess_instruction()` em `src/core/binary_workbench/mips_r3000a/preprocessor.py:37` remove comentário/Label, expande formas curtas, resolve Variables, Equates e Labels, normaliza pseudos e converte branches. `raw_mips_instruction()` em `preprocessor.py:80` aceita apenas instruções do núcleo reconhecido.
6. A implementação de montagem é `PsxMipsR3000ACodec.assemble()` em `src/core/binary_workbench/mips_r3000a/codec.py:50`. Ela usa Keystone quando disponível e o assembler interno como fallback, mantendo little-endian.

### Raw Instructions

`GridRawInstructionsMixin._raw_instruction_lines()` em `src/presentation/ui/components/binary_workbench/editor/grid_raw_instructions.py:24` é o renderizador atual. Ele prefere desassemblar `row.bytes_text` por `_raw_instruction_from_bytes()` e usa `raw_mips_instruction()` como fallback. Portanto, a coluna reflete prioritariamente os bytes efetivamente montados, não uma segunda montagem.

## Contexto, arquitetura e workspace

O agregado de uma aba é `BinaryWorkbenchTabContextDTO` em `src/modules/binary_workbench_dtos.py:106`. Os campos relevantes são:

- `source_path` (`:110`): arquivo associado;
- `cpu_arch` (`:111`): arquitetura selecionada;
- `workspace_path` e `module_paths` (`:133-134`): manifesto e recursos do workspace;
- `labels`, `symbols`, `variables`, `equates` e `rows`: ambiente e resultado materializado.

`Preferences → Advanced Configuration` recebe `current.cpu_arch` em `window_environment_actions.py:33`, devolve `selected_arch()` em `preferences/advanced_config_dialog.py:143` e atualiza o contexto por `TabConfigurationMixin.set_current_advanced_config()` em `tabs/tab_configuration.py:23`. O acesso correto para o Debugger é, portanto, `tabs.current_context().cpu_arch`, seguido de `binary_workbench_codec_for(cpu_arch)`.

Observação: `cpu_arch` é persistido no estado geral do Binary Workbench (`binary_workbench_payload.py:460`), mas não no manifesto individual criado por `binary_workbench_workspace/manifest.py:47`. Um `.asm` carregado apenas pelo manifesto recebe hoje a arquitetura padrão do contexto recém-criado.

### Associação arquivo ↔ workspace

- `source_payload()` e `source_matches()` em `binary_workbench_workspace/payloads.py:44` e `:53` criam/comparam a identidade da origem.
- `BinaryWorkbenchWorkspaceRepository.find_for_source()` em `repository.py:95` procura o manifesto correspondente e aceita um manifesto preferido.
- `load_tab_workspace()` em `repository.py:114` carrega Symbols, versões, overlays e demais módulos para o contexto.
- `save_tab_workspace()` em `repository.py:225` persiste o manifesto e atualiza `workspace_path`/módulos.
- `BinaryWorkbenchProgramContextUseCase.remember_workspace()` e `preferred_workspace()` em `src/modules/binary_workbench_use_cases.py:40` e `:54` resolvem ambiguidade lembrando o último workspace usado por origem.
- A composição usada ao abrir arquivos está em `TabWorkspaceMixin._apply_matching_workspace()` (`tabs/tab_workspace.py:168`), e a lembrança da associação em `_remember_workspace_for_source()` (`:204`).

## Como obter os bytes montados

### Arquivo atual

1. Chamar `tabs.current_context()`. `TabStateMixin.current_context()` (`tabs/tab_state.py:125`) passa por `_fresh_context_at()` (`:206`), que obtém o contexto da página; `BinaryWorkbenchEditorPage.current_context()` (`editor/page.py:111`) descarrega alterações pendentes do grid.
2. Usar `context.rows`. Linhas sem bytes representam Labels, comentários, vazios ou assembly inválido.
3. Concatenar somente `row.bytes_text` válidos. Já existe `rows_to_bytes()` em `tabs/tab_state_payload.py:42`, mas ele está na camada de apresentação e não retorna diagnóstico. O serviço futuro do Debugger deve reutilizar a montagem do codec no `core` e expor bytes/erros sem depender desse helper de UI.

### Outro `.asm` já aberto

Localizar a aba por `source_path` em `BinaryWorkbenchStateDTO.tabs`. `context_at()` (`tabs/tab_state.py:131`) retorna o contexto armazenado, mas não força a atualização da página como `_fresh_context_at()`; hoje não há API pública para obter por caminho um contexto não ativo garantidamente atualizado. Esse é um seam a encapsular na integração futura, sem trocar a aba visível.

### Outro `.asm` fechado ou de outro workspace

O pipeline atual é:

1. criar o contexto com `create_assembly_tab()`;
2. obter o workspace preferido pelo `ProgramContextUseCase`;
3. procurar o manifesto com `find_for_source()`;
4. carregar o manifesto com `load_tab_workspace()`;
5. reconstruir as linhas com Symbols pelo mesmo `build_source_line_rows()` — hoje isso ocorre no helper privado `_with_symbol_offsets()`/`_rows_with_loaded_symbols()` em `tabs/tab_workspace.py:246` e `:270`;
6. selecionar o codec por `context.cpu_arch` e coletar os bytes somente se toda linha exigida for válida.

Esse fluxo permite alcançar arquivos associados a qualquer workspace conhecido pelo repositório, sem precisar abrir uma aba. Porém, sua composição está hoje em mixins privados da UI. A Task 5 deverá colocá-la em um serviço reutilizável e transacional, preservando exatamente o preprocessor, Symbols, arquitetura e assembler existentes.

## Componentes reutilizáveis

| Responsabilidade | Ponto existente | Observação para o Debugger |
|---|---|---|
| Highlighter de bytes | `BytesHighlighter`, `editor/highlighters.py:49` | Alterna as cores dos tokens de byte. |
| Highlighter de assembly | `InstructionHighlighter`, `editor/highlighters.py:61` | Recebe Labels/Variables/Equates por `set_symbols()` (`:73`); a implementação atual conhece sintaxe MIPS. |
| Autocomplete | `EditorCompletionMixin`, especialmente `_current_completion_prefix()` e `_candidates_for_prefix()` em `editor/editor_completion.py:66` e `:75` | Já oferece popup e Symbols. O token atual não reconhece prefixo `*`; a extensão deve ser restrita às linhas especiais. |
| Formatação de bytes | `CPUArchCodec.bytes_text()` e `normalize_bytes_text()` em `editor/syntax_tokens.py:75` | O primeiro produz bytes canônicos; o segundo aplica agrupamento/case de exibição. |
| Preferências do formatter | `BinaryWorkbenchBytesFormatterDialog` e `TabConfigurationMixin.set_current_bytes_formatter()` | Reutilizar `group_bytes`/`uppercase_bytes`, sem duplicar regras visuais. |
| Persistência de tamanho | `BinaryWorkbenchStateDTO.window_size`, `BinaryWorkbenchWindow.export_state()` (`window.py:101`) e `sizePersistRequested` (`:58`, `:170`) | Só cobre largura/altura e é global ao Binary Workbench. |
| Recuperação em monitores | `ensure_window_on_available_screen()` em `ui/helpers/window_geometry/geometry.py:22` | Reutilizável para impedir janela fora da área disponível. |
| Erro visual por linha | `invalid_instruction()` (`editor/syntax_tokens.py:67`) + `InstructionHighlighter.highlightBlock()` (`editor/highlighters.py:107-165`) | Já pinta instrução inválida e endereços inválidos. |
| Destaques adicionais | `QTextEdit.ExtraSelection` em `editor/grid_raw_instructions.py:51` | Padrão reutilizável para backgrounds sem alterar o documento. |
| Mensagem de erro | `BinaryWorkbenchEditorPage.statusErrorRequested` (`editor/page.py:61`) → `BinaryWorkbenchTabs.statusErrorChanged` (`tabs/widget.py:77`) → footer em `window.py:90` | Canal adequado para a causa textual do erro. |

## Limites encontrados e pontos de extensão

- Não existe hoje um objeto de diagnóstico estruturado por linha. Há cor no highlighter e mensagem no footer, mas não uma associação persistente `linha → causa`; as diretivas precisarão fornecer isso sem acoplar validação ao widget.
- `build_source_line_rows(reject_invalid=True)` já oferece falha total, porém apenas como `None`; não informa a causa. A montagem transacional do Debugger precisará preservar o pipeline e envolver o resultado com erros controlados.
- Uma linha iniciada por `*` é atualmente vista como código não reconhecido. O parser futuro deve separar diretivas antes da montagem, garantindo que não cheguem a `codec.assemble()`, não incrementem offset e não apareçam em Raw Instructions.
- O autocomplete atual separa comandos `/`, Variables `_`, Equates `@` e Labels; não há categoria de diretivas especiais.
- A persistência existente não cobre posição, estado maximizado, splitters, aba inferior nem chave por workspace. A Task 9 precisará de um DTO próprio por workspace, reutilizando o repositório/identidade do workspace e o helper de geometria.
- A composição para carregar outro arquivo com seu workspace está na apresentação. A integração deve extrair uma fachada de aplicação/core, não fazer o Debugger chamar mixins privados nem criar assembler paralelo.

## Pontos recomendados para as próximas tasks

- Contratos do Debugger: novo sistema no `core`, dependente de abstrações próprias e do `CPUArchCodec`, sem tipos Qt.
- Parser de diretivas: `core`, antes de `CPUArchCodec.build_source_line_rows()`.
- Resolução de imports: serviço de aplicação/core que receba caminho principal, contexto/workspace e repositório por uma porta, retornando todos os imports ou um erro único transacional.
- Abertura por F5: coordenador na apresentação que obtém o contexto fresco, chama o serviço e envia erros pelo canal `statusErrorRequested/statusErrorChanged`.
- UI: reutilizar highlighters, completion popup, formatter, `ExtraSelection` e `ensure_window_on_available_screen()`, mantendo validação e execução fora de PySide6.
