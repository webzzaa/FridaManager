import io
import sys

from frida_manager import (
    FridaConfig,
    install_frida_to_computer,
    push_frida_server_to_phone,
    start_frida_server,
    uninstall_frida_to_computer,
)
from gui_app import run_gui


def _run_cli() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    config = FridaConfig()
    print(
        "By 邻家小明\n"
        "警告：本脚本仅用于安全测试，不建议在生产环境中使用\n"
        "脚本支持python3.8以上版本\n"
        "请选择要执行的操作:\n"
        "1. 安装frida到电脑中(需要先将python以及他下面的Scripts目录添加到环境变量中)\n"
        "2. 卸载frida到电脑中\n"
        "3. 推送frida-server到手机端\n"
        "4. 启动frida-server并进行端口转发"
    )
    choice = input("请输入你的选择 (1/2/3/4): ")
    if choice == "1":
        install_frida_to_computer(config, log_cb=print)
    elif choice == "2":
        uninstall_frida_to_computer(config, log_cb=print)
    elif choice == "3":
        push_frida_server_to_phone(config, log_cb=print)
    elif choice == "4":
        start_frida_server(config, log_cb=print)
    else:
        print("无效的选择")
    print("Frida常用语法:")
    print("frida-ps -Ua  列出所有进程")
    print("frida -U -f 包名 -l hook.js  对指定进程进行hook")


def main() -> int:
    if "--cli" in sys.argv:
        _run_cli()
        return 0
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
