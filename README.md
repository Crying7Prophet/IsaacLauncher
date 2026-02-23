<div align="center">
  <img src="assets/logo.svg" alt="PyIsaac Launcher" width="200" />
  
  ### A mod manager for The Binding of Isaac: Repentance+

  ![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
  ![UI](https://img.shields.io/badge/UI-CustomTkinter-orange)
  ![License](https://img.shields.io/badge/License-MIT-green)
  ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgray)

</div>

---

## About

**PyIsaac Launcher** is a modern mod manager for *The Binding of Isaac: Repentance* built in Python. It features an integrated browser for browsing mod sites directly within the app and provides seamless mod installation.

---

## Features

| Feature | Description |
|---------|-------------|
| **Integrated Browser** | Navigate Steam Workshop, NexusMods, ModDB, and Modding of Isaac without leaving the app |
| **Mod Management** | View installed mods with metadata and images fetched automatically from Steam |
| **Direct Downloads** | Download mods by Steam Workshop ID or URL |
| **Modern UI** | Sleek dark theme built with CustomTkinter |
| **Cross-Platform** | Works on Windows and Linux |

---

## Installation

### Prerequisites

- Python 3.10 or higher (3.11+ recommended)
- System dependencies for CairoSVG:
  - **Windows**: [GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Builder/releases)
  - **Linux**: `libcairo2-dev`, `libgirepository1.0-dev`, `python3-dev`

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/IsaacLauncher.git
cd IsaacLauncher

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
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

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern Tkinter widgets
- [tkinterweb](https://github.com/Andereoo/TkinterWeb) - HTML renderer for Tkinter
- [requests](https://docs.python-requests.org/) - HTTP library
- [Pillow](https://python-pillow.org/) - Image processing
- [cairosvg](https://cairosvg.org/) - SVG rendering

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
