PyIsaac Mod Manager v0.1
PyIsaac es un gestor de mods para The Binding of Isaac: Repentance diseñado en Python. Está fuertemente inspirado en la interfaz y funcionalidad de RimPy, permitiendo a los usuarios navegar por la Steam Workshop de forma integrada y descargar mods directamente usando SteamCMD.

🚀 Características
Interfaz RimPy Style: Diseño oscuro y profesional basado en CustomTkinter.

Navegador Integrado: Explora la Workshop de Steam sin salir del programa.

Descarga con un clic: Detecta automáticamente el ID del mod desde la URL y gestiona la descarga.

Gestión Automática: Descarga, extrae y mueve los mods a la carpeta de instalación del juego.

Configuración Persistente: Guarda tus rutas de SteamCMD y del juego en un archivo config.json para facilitar su uso.

🛠️ Requisitos Previos
Antes de ejecutar el launcher, asegúrate de tener instalado lo siguiente:

Python 3.10+ (Recomendado 3.11 o 3.12 para mayor estabilidad).

SteamCMD: Descargado y actualizado en una carpeta accesible (ej. D:\steamcmd).

Librerías de Python:

Bash

pip install customtkinter tkinterweb pyperclip
⚙️ Configuración Inicial
Al abrir el programa por primera vez, se generará un archivo config.json. Asegúrate de que las rutas sean correctas:

JSON

{
    "steamcmd_path": "D:/steamcmd/steamcmd.exe",
    "isaac_mods_path": "C:/Ruta/A/Tu/Juego/mods",
    "temp_download_path": "./temp_downloads"
}
🔑 Importante: El Login de SteamCMD
Para descargar mods de juegos de pago como The Binding of Isaac, SteamCMD requiere una cuenta válida. Si recibes el error Cached credentials not found:

Abre steamcmd.exe manualmente.

Escribe login TU_USUARIO.

Introduce tu contraseña y el código de Steam Guard.

Una vez leas Logged in OK, ya puedes cerrar la consola y usar el launcher.

📖 Uso
Ejecuta main.py.

Ve a la pestaña Downloader.

Navega hasta el mod que desees.

Pulsa el botón Detectar para capturar la URL.

Pulsa INSTALAR y espera a que el proceso termine.

⚠️ Problemas Conocidos
Web de Steam "bugeada": El motor del navegador integrado es ligero y puede tener errores visuales con JavaScript pesado. Si falla, copia el link desde Chrome y pégalo manualmente en el launcher.
