import os
import sys
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


LogCallback = Callable[[str], None]


@dataclass
class FridaConfig:
    frida_version: str = "16.5.7"
    frida_tools_version: str = "12.3.0"
    frida_server_port: str = "27042"
    win_frida_port: str = "27042"
    frida_server_path: str = "/data/local/tmp/fs"
    frida_server_name: str = "frida-server-16.5.7-android-arm64"
    adb_path: str = "adb"
    server_local_dir: str = os.getcwd()


def _format_command(args: list) -> str:
    return " ".join(str(a) for a in args)


def _emit(log_cb: Optional[LogCallback], message: str) -> None:
    if log_cb:
        log_cb(message)


def run_command(
    args: list, log_cb: Optional[LogCallback] = None, cwd: Optional[str] = None
) -> int:
    _emit(log_cb, f"$ {_format_command(args)}")
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    if process.stdout:
        for line in process.stdout:
            _emit(log_cb, line.rstrip())
    return process.wait()


def run_command_capture(
    args: list, log_cb: Optional[LogCallback] = None, cwd: Optional[str] = None
) -> Tuple[int, str]:
    _emit(log_cb, f"$ {_format_command(args)}")
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if output:
        for line in output.splitlines():
            _emit(log_cb, line)
    return result.returncode, output


def _adb(config: FridaConfig, *args: str) -> list:
    return [config.adb_path, *args]


def install_frida_to_computer(
    config: FridaConfig, log_cb: Optional[LogCallback] = None
) -> int:
    code = run_command(
        [sys.executable, "-m", "pip", "install", f"frida=={config.frida_version}"],
        log_cb=log_cb,
    )
    if code != 0:
        return code
    code = run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"frida-tools=={config.frida_tools_version}",
        ],
        log_cb=log_cb,
    )
    if code != 0:
        return code
    return run_command(
        [sys.executable, "-m", "pip", "install", "frida-dexdump"], log_cb=log_cb
    )


def uninstall_frida_to_computer(
    config: FridaConfig, log_cb: Optional[LogCallback] = None
) -> int:
    code = run_command(
        [sys.executable, "-m", "pip", "uninstall", "-y", "frida"], log_cb=log_cb
    )
    if code != 0:
        return code
    return run_command(
        [sys.executable, "-m", "pip", "uninstall", "-y", "frida-tools"], log_cb=log_cb
    )


def push_frida_server_to_phone(
    config: FridaConfig, log_cb: Optional[LogCallback] = None
) -> int:
    local_path = os.path.join(config.server_local_dir, config.frida_server_name)
    if not os.path.exists(local_path):
        _emit(log_cb, f"Local frida-server not found: {local_path}")
        return 1
    code = run_command(
        _adb(config, "push", local_path, "/data/local/tmp/"), log_cb=log_cb
    )
    if code != 0:
        return code
    code = run_command(
        _adb(config, "shell", f"chmod 755 /data/local/tmp/{config.frida_server_name}"),
        log_cb=log_cb,
    )
    if code != 0:
        return code
    return run_command(
        _adb(
            config,
            "shell",
            f"mv /data/local/tmp/{config.frida_server_name} {config.frida_server_path}",
        ),
        log_cb=log_cb,
    )


def start_frida_server(
    config: FridaConfig, log_cb: Optional[LogCallback] = None
) -> int:
    code = run_command(
        _adb(config, "shell", f"su -c '{config.frida_server_path} &'"),
        log_cb=log_cb,
    )
    if code != 0:
        return code
    code = run_command(
        _adb(
            config,
            "forward",
            f"tcp:{config.frida_server_port}",
            f"tcp:{config.win_frida_port}",
        ),
        log_cb=log_cb,
    )
    if code == 0:
        return 0
    _emit(log_cb, "Port forward failed. Attempting to clear the port...")
    netstat_cmd = f"netstat -antp | grep {config.frida_server_port}"
    status, output = run_command_capture(
        _adb(config, "shell", netstat_cmd), log_cb=log_cb
    )
    if status == 0 and output:
        parts = output.split()
        if len(parts) >= 8 and "/" in parts[7]:
            pid = parts[7].split("/")[0]
            _emit(log_cb, f"Killing process on port {config.frida_server_port}: {pid}")
            run_command(_adb(config, "shell", f"kill -9 {pid}"), log_cb=log_cb)
    return run_command(
        _adb(
            config,
            "forward",
            f"tcp:{config.frida_server_port}",
            f"tcp:{config.win_frida_port}",
        ),
        log_cb=log_cb,
    )


def check_adb(config: FridaConfig, log_cb: Optional[LogCallback] = None) -> int:
    return run_command(_adb(config, "devices"), log_cb=log_cb)
