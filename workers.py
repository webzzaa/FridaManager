from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    message = Signal(str)
    error = Signal(str)
    finished = Signal(int)


class CommandWorker(QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            exit_code = self.func(
                *self.args, **self.kwargs, log_cb=self.signals.message.emit
            )
            if exit_code is None:
                exit_code = 0
            self.signals.finished.emit(exit_code)
        except Exception as exc:
            self.signals.error.emit(str(exc))
            self.signals.finished.emit(1)
