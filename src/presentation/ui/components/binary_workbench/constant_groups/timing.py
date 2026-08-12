class BINARY_WORKBENCH_TIMING:
    STATUS_MESSAGE_VISIBLE_MS: int = 3000
    EDITOR_COMPLETION_NAVIGATION_DEBOUNCE_MS: int = 1500
    EDITOR_SYMBOL_COMPLETION_INSERT_DEBOUNCE_MS: int = 400
    EDITOR_SYMBOL_COMPLETION_DELETE_DEBOUNCE_MS: int = 600
    INCREMENTAL_PROPAGATION_MS: int = 80
    CONSISTENCY_VISUAL_DEBOUNCE_MS: int = 80
    CONSISTENCY_VISUAL_MAX_LATENCY_MS: int = 280
    # Global labels/branches/references are eventual. A longer quiet window
    # keeps their Python worker from competing with active typing for the GIL;
    # edited lines and the viewport retain their separate immediate path.
    CONSISTENCY_SCROLL_FRAME_MS: int = 16
    CONSISTENCY_FOLD_VIEWPORT_MS: int = 50
    CONSISTENCY_SELECTION_DEBOUNCE_MS: int = 70
    CONSISTENCY_PREFETCH_DELAY_MS: int = 50
    VERSION_AUTOSAVE_DEBOUNCE_MS: int = 5_000
    EDITOR_NO_OP_HISTORY_LIMIT: int = 16
