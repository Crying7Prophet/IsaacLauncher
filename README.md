<div align="center">
  <img src="assets/logo.svg" alt="PyIsaac Launcher" width="300" />
  
  ### A mod manager for The Binding of Isaac: Repentance+

  ![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
  ![UI](https://img.shields.io/badge/UI-PyQt6-orange)
  ![License](https://img.shields.io/badge/License-MIT-green)
  ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgray)

</div>

---

## About

**PyIsaac Launcher** is a modern mod manager for *The Binding of Isaac: Repentance+* built in Python. It features an integrated browser for browsing mod sites directly within the app and provides seamless mod installation.

---

## Features

| Feature | Description |
|---------|-------------|
| **Integrated Browser** | Navigate Steam Workshop, NexusMods, ModDB, and Modding of Isaac without leaving the app |
| **Mod Management** | View installed mods with metadata and images fetched automatically from Steam |
| **Direct Downloads** | Download mods by Steam Workshop ID or URL |
| **Modern UI** | Sleek dark theme built with PyQt6 |
| **Cross-Platform** | Works on Windows and Linux |

---

## Installation

### Prerequisites

- Python 3.10 or higher (3.11+ recommended)
- System dependencies for PyQt6 WebEngine:

#### Linux (Ubuntu/Debian)
```bash
sudo apt install libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-render-util0 libxcb-shape0 libegl1 libopengl0 libxkbcommon0 \
    libxcb-xinerama0 libxcb-xfixes0
```

#### Linux (Fedora)
```bash
sudo dnf install xcb-util-cursor xcb-util-image xcb-util-keysyms \
    xcb-util-renderutil xcb-util-xkbutils
```

#### Linux (Arch)
```bash
sudo pacman -S qt6-base
```

#### Windows
No additional dependencies required (install PyQt6-WebEngine via pip)

### Setup

```bash
# Run setup script (installs system + python dependencies)
python setup.py
```

---

## Usage

1. **Configure Mods Path**: Set the path to your Isaac mods folder
2. **Browse Mods**: Use the integrated browser to find mods on Steam Workshop, NexusMods, etc.
3. **Download**: Copy the mod URL or Steam Workshop ID and use the download feature
4. **Manage**: View and organize your installed mods

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt + Left` | Navigate back |
| `Alt + Right` | Navigate forward |
| `F5` | Refresh page |
| `Ctrl + L` | Focus URL bar |

---

## Dependencies

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [PyQt6-WebEngine](https://www.riverbankcomputing.com/software/pyqtwebengine/) - Chromium-based browser
- [requests](https://docs.python-requests.org/) - HTTP library
- [Pillow](https://python-pillow.org/) - Image processing

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [The Binding of Isaac](https://store.steampowered.com/app/250900/The_Binding_of_Isaac_Repentance/) by Edmund McMillen
- [Modding of Isaac](https://moddingofisaac.com/) community
