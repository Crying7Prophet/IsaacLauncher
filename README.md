# 🛠️ PyIsaac Mod Manager v0.1

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-CustomTkinter-orange)
![Game](https://img.shields.io/badge/Game-The_Binding_of_Isaac-red)

**PyIsaac** is an advanced mod manager for *The Binding of Isaac: Repentance* developed in Python. Inspired by the efficiency of **RimPy**, this manager integrates Steam Workshop navigation with the power of SteamCMD to provide a seamless and centralized installation experience.

---

## 🚀 Key Features

* **"RimPy Style" Interface:** A modern, professional dark-themed UI built with `CustomTkinter`.
* **Integrated Browser:** Browse the Steam Workshop directly within the application—no need for an external browser.
* **Smart Installation:** Automatically detects Mod IDs from URLs and manages downloads with a single click.
* **Full Automation:** Seamlessly downloads, extracts, and moves files to the game's mod folder.
* **Data Persistence:** Managed via `config.json` so you only have to set your file paths once.

---

## 🛠️ Prerequisites

To ensure proper functionality, please make sure you meet the following requirements:

1.  **Python 3.10+**: Versions 3.11 or 3.12 are recommended for optimal stability.
2.  **SteamCMD**: Must be installed in an accessible directory (e.g., `D:\steamcmd`).
3.  **Required Libraries**:
    ```bash
    pip install customtkinter tkinterweb pyperclip
    ```

---