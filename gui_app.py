import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frida_manager import (
    FridaConfig,
    check_adb,
    install_frida_to_computer,
    push_frida_server_to_phone,
    start_frida_server,
    uninstall_frida_to_computer,
)
from workers import CommandWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Frida Manager")
        self.resize(1100, 700)
        self.thread_pool = QThreadPool.globalInstance()
        self.log_path = self._ensure_log_path()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 10))
        self.log_output.setPlaceholderText("Run an action to see output here...")

        central = QWidget()
        main_layout = QHBoxLayout(central)

        left_panel = QScrollArea()
        left_panel.setWidgetResizable(True)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setAlignment(Qt.AlignTop)

        left_layout.addWidget(self._build_config_group())
        left_layout.addWidget(self._build_action_group())
        left_layout.addWidget(self._build_help_group())
        left_layout.addStretch(1)
        left_panel.setWidget(left_container)

        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(self.log_output, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self._set_status("Ready")

    def _build_config_group(self) -> QGroupBox:
        group = QGroupBox("Configuration")
        layout = QVBoxLayout(group)

        self.frida_version = self._add_labeled_input(layout, "Frida Version", "16.5.7")
        self.frida_tools_version = self._add_labeled_input(
            layout, "Frida Tools Version", "12.3.0"
        )
        self.frida_server_name = self._add_labeled_input(
            layout, "Frida Server Name", "frida-server-16.5.7-android-arm64"
        )
        self.frida_server_path = self._add_labeled_input(
            layout, "Device Server Path", "/data/local/tmp/fs"
        )
        self.frida_server_port = self._add_labeled_input(layout, "Device Port", "27042")
        self.win_frida_port = self._add_labeled_input(layout, "Windows Port", "27042")
        self.adb_path = self._add_labeled_input(layout, "ADB Path", "adb")

        browse_row = QHBoxLayout()
        browse_label = QLabel("Local Server Dir")
        self.server_local_dir = QLineEdit(os.getcwd())
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_server_file)
        browse_row.addWidget(browse_label)
        browse_row.addWidget(self.server_local_dir)
        browse_row.addWidget(browse_button)
        layout.addLayout(browse_row)
        return group

    def _build_action_group(self) -> QGroupBox:
        group = QGroupBox("Actions")
        layout = QVBoxLayout(group)

        self.install_button = QPushButton("Install Frida")
        self.uninstall_button = QPushButton("Uninstall Frida")
        self.push_button = QPushButton("Push frida-server")
        self.start_button = QPushButton("Start frida-server")
        self.adb_button = QPushButton("Check ADB")
        self.clear_button = QPushButton("Clear Output")

        self.install_button.clicked.connect(self._on_install)
        self.uninstall_button.clicked.connect(self._on_uninstall)
        self.push_button.clicked.connect(self._on_push)
        self.start_button.clicked.connect(self._on_start)
        self.adb_button.clicked.connect(self._on_check_adb)
        self.clear_button.clicked.connect(self.log_output.clear)

        layout.addWidget(self.install_button)
        layout.addWidget(self.uninstall_button)
        layout.addWidget(self.push_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.adb_button)
        layout.addWidget(self.clear_button)
        return group

    def _build_help_group(self) -> QGroupBox:
        group = QGroupBox("Quick Commands")
        layout = QVBoxLayout(group)
        info = QLabel(
            "frida-ps -Ua  List processes\n"
            "frida -U -f <package> -l hook.js  Attach and hook"
        )
        info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(info)
        return group

    def _add_labeled_input(
        self, layout: QVBoxLayout, label: str, value: str
    ) -> QLineEdit:
        row = QHBoxLayout()
        row_label = QLabel(label)
        row_input = QLineEdit(value)
        row.addWidget(row_label)
        row.addWidget(row_input)
        layout.addLayout(row)
        return row_input

    def _browse_server_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select frida-server", os.getcwd()
        )
        if not file_path:
            return
        self.server_local_dir.setText(os.path.dirname(file_path))
        self.frida_server_name.setText(os.path.basename(file_path))

    def _build_config(self) -> FridaConfig:
        return FridaConfig(
            frida_version=self.frida_version.text().strip(),
            frida_tools_version=self.frida_tools_version.text().strip(),
            frida_server_port=self.frida_server_port.text().strip(),
            win_frida_port=self.win_frida_port.text().strip(),
            frida_server_path=self.frida_server_path.text().strip(),
            frida_server_name=self.frida_server_name.text().strip(),
            adb_path=self.adb_path.text().strip() or "adb",
            server_local_dir=self.server_local_dir.text().strip() or os.getcwd(),
        )

    def _ensure_log_path(self) -> str:
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "app.log")

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.log_output.append(line)
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _set_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _set_busy(self, busy: bool) -> None:
        for button in (
            self.install_button,
            self.uninstall_button,
            self.push_button,
            self.start_button,
            self.adb_button,
        ):
            button.setEnabled(not busy)
        self._set_status("Running..." if busy else "Ready")

    def _run_task(self, func) -> None:
        config = self._build_config()
        worker = CommandWorker(func, config)
        worker.signals.message.connect(self._append_log)
        worker.signals.error.connect(self._handle_error)
        worker.signals.finished.connect(self._handle_finished)
        self._set_busy(True)
        self.thread_pool.start(worker)

    def _handle_error(self, message: str) -> None:
        self._append_log(f"Error: {message}")
        QMessageBox.critical(self, "Error", message)

    def _handle_finished(self, exit_code: int) -> None:
        self._append_log(f"Task completed with exit code {exit_code}.")
        self._set_busy(False)

    def _on_install(self) -> None:
        self._run_task(install_frida_to_computer)

    def _on_uninstall(self) -> None:
        self._run_task(uninstall_frida_to_computer)

    def _on_push(self) -> None:
        self._run_task(push_frida_server_to_phone)

    def _on_start(self) -> None:
        self._run_task(start_frida_server)

    def _on_check_adb(self) -> None:
        self._run_task(check_adb)


def run_gui() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Frida Manager")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_gui())
