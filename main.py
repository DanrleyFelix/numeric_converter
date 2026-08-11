import sys

BUILD_SMOKE_ARGUMENT = "--build-smoke-debugger"


def main() -> int:
    """Run the private native smoke path or start the normal Qt application."""

    if BUILD_SMOKE_ARGUMENT in sys.argv[1:]:
        return _run_build_smoke()
    from PySide6.QtWidgets import QApplication

    from src.main import create_main_window
    from src.main.runtime_defaults import configure_application_defaults

    app = QApplication(sys.argv)
    configure_application_defaults(app)
    window = create_main_window()
    window.show()
    return app.exec()


def _run_build_smoke() -> int:
    """Exercise the packaged Debugger worker without creating application UI."""

    try:
        from PySide6.QtCore import QCoreApplication

        from src.core.debugger.runtime_smoke import (
            SMOKE_EXECUTION_LIMIT,
            create_debugger_native_smoke_session,
            trace_debugger_native_smoke,
            validate_debugger_native_smoke,
        )
        from src.presentation.ui.components.debugger.execution.worker import (
            DebuggerExecutionWorker,
        )

        trace_debugger_native_smoke("main:imports")
        application = QCoreApplication.instance() or QCoreApplication(sys.argv)
        debugger = create_debugger_native_smoke_session()
        trace_debugger_native_smoke("main:worker-create")
        worker = DebuggerExecutionWorker(
            lambda: debugger.run(limit=SMOKE_EXECUTION_LIMIT),
            application,
        )
        trace_debugger_native_smoke("main:worker-start")
        worker.start()
        worker.wait()
        trace_debugger_native_smoke("main:worker-finished")
        validate_debugger_native_smoke(debugger)
        trace_debugger_native_smoke("main:validated")
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
