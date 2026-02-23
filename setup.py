#!/usr/bin/env python3
import sys
import subprocess
import platform
import os

def get_linux_distro():
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.split("=")[1].strip().strip('"')
    except:
        pass
    return ""

def install_system_deps():
    system = platform.system()
    
    if system == "Linux":
        distro = get_linux_distro()
        
        if distro in ["ubuntu", "debian", "linuxmint", "pop"]:
            print("Installing Qt6 dependencies for Ubuntu/Debian...")
            subprocess.run(["sudo", "apt-get", "update"])
            subprocess.run(["sudo", "apt-get", "install", "-y",
                "libxcb-cursor0", "libxcb-icccm4", "libxcb-image0", "libxcb-keysyms1",
                "libxcb-render-util0", "libxcb-shape0", "libegl1", "libopengl0",
                "libxkbcommon0", "libxcb-xinerama0", "libxcb-xfixes0"])
        
        elif distro in ["fedora", "rhel", "centos"]:
            print("Installing Qt6 dependencies for Fedora/RHEL...")
            subprocess.run(["sudo", "dnf", "install", "-y",
                "xcb-util-cursor", "xcb-util-image", "xcb-util-keysyms",
                "xcb-util-renderutil", "xcb-util-xkbutils"])
        
        elif distro in ["arch", "manjaro", "endeavouros"]:
            print("Installing Qt6 dependencies for Arch Linux...")
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "qt6-base"])
        
        else:
            print(f"Unknown Linux distribution: {distro}")
    
    elif system == "Darwin":
        print("Installing Qt6 for macOS...")
        subprocess.run(["brew", "install", "qt6"])
    
    elif system == "Windows":
        print("No system dependencies required for Windows.")

def create_venv():
    if not os.path.exists("venv"):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
    else:
        print("Virtual environment already exists.")

def install_python_deps():
    print("Installing Python dependencies...")
    pip_exe = os.path.join("venv", "bin", "pip") if platform.system() != "Windows" else os.path.join("venv", "Scripts", "pip")
    subprocess.run([pip_exe, "install", "-r", "requirements.txt"])
    print("Done!")

if __name__ == "__main__":
    install_system_deps()
    create_venv()
    install_python_deps()
