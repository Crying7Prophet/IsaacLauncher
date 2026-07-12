#!/usr/bin/env python3
import sys
import subprocess
import platform
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(APP_DIR, "venv")


def get_linux_distro():
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.split("=")[1].strip().strip('"')
    except Exception:
        pass
    return ""


def install_system_deps():
    system = platform.system()

    if system == "Linux":
        distro = get_linux_distro()

        if distro in ["ubuntu", "debian", "linuxmint", "pop"]:
            print("[setup] Installing Qt6 dependencies for Ubuntu/Debian...")
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y",
                "libxcb-cursor0", "libxcb-icccm4", "libxcb-image0", "libxcb-keysyms1",
                "libxcb-render-util0", "libxcb-shape0", "libegl1", "libopengl0",
                "libxkbcommon0", "libxcb-xinerama0", "libxcb-xfixes0"], check=False)

        elif distro in ["fedora", "rhel", "centos"]:
            print("[setup] Installing Qt6 dependencies for Fedora/RHEL...")
            subprocess.run(["sudo", "dnf", "install", "-y",
                "xcb-util-cursor", "xcb-util-image", "xcb-util-keysyms",
                "xcb-util-renderutil", "xcb-util-xkbutils"], check=False)

        elif distro in ["arch", "manjaro", "endeavouros"]:
            print("[setup] Installing Qt6 dependencies for Arch Linux...")
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "qt6-base"], check=False)

        else:
            print(f"[setup] Unknown Linux distribution: {distro}")

    elif system == "Darwin":
        print("[setup] Installing Qt6 for macOS...")
        subprocess.run(["brew", "install", "qt6"], check=False)

    elif system == "Windows":
        print("[setup] No system dependencies required for Windows.")


def create_venv():
    if not os.path.isdir(VENV_DIR):
        print("[setup] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    else:
        print("[setup] Virtual environment already exists.")


def install_python_deps():
    if platform.system() == "Windows":
        pip_exe = os.path.join(VENV_DIR, "Scripts", "pip")
    else:
        pip_exe = os.path.join(VENV_DIR, "bin", "pip")
    print("[setup] Installing Python dependencies...")
    subprocess.run([pip_exe, "install", "-r", os.path.join(APP_DIR, "requirements.txt")], check=True)
    print("[setup] Done!")


def venv_python():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def main_setup():
    install_system_deps()
    create_venv()
    install_python_deps()
    print("[setup] Re-launching launcher...")
    main_py = os.path.join(APP_DIR, "main.py")
    if platform.system() == "Windows":
        subprocess.Popen([venv_python(), main_py], cwd=APP_DIR)
        sys.exit(0)
    else:
        os.execv(venv_python(), [venv_python(), main_py])


if __name__ == "__main__":
    main_setup()
