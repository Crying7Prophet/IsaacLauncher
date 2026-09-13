<div align="center">
  <img src="assets/logo.svg" alt="IsaacLauncher" width="300" />

  # IsaacLauncher

  A mod manager for *The Binding of Isaac: Repentance*, written in C++ with Qt 6.

  ![C++](https://img.shields.io/badge/C%2B%2B-17-blue?logo=cplusplus&logoColor=white)
  ![UI](https://img.shields.io/badge/UI-Qt%206-blue)
  ![License](https://img.shields.io/badge/License-MIT-green)
  ![Platform](https://img.shields.io/badge/Platform-Windows-lightgray)

</div>

## Features

- Lists the mods installed in the Isaac `mods` folder with thumbnails, metadata and descriptive text
- Installs mods from local ZIP files or from whole folders (ZIP is extracted with the system `tar`, Windows 10+)

- Launches the game and records a play-history (session dates + total play time)
- Settings dialog to point at the Isaac exe/mods folders; About dialog
- Persistent configuration in `config.json`

## Project layout

```
assets/             SVG icons (embedded via resources.qrc)
src/
  main.cpp          Entry point (dark Fusion palette)
  MainWindow.*      Main launcher window
  ModManager.*      Mod detection, ZIP install, metadata reading
  Workers.*         Network workers (list, thumbnails, details, downloads)
  Config.*          config.json load/save + play history
  Common.*          HTML escape/unescape helpers, clickable links
CMakeLists.txt
resources.qrc
build.bat           One-click build script (Windows)
config.json         Launcher configuration
```

## Configuration

`config.json` sits in the same directory as the executable (the launcher also looks
up to 4 parent folders up, so a `config.json` at the repo root is picked up when
running from `build/`):

```jsonc
{
  "isaac_mods_path": "C:/path/to/The Binding of Isaac Rebirth/mods",
  "isaac_exe_path":  "C:/path/to/isaac-ng.exe",
  "play_history":    [ { "start": "...", "end": "...", "duration": "..." } ]
}
```

## Building

### Requirements

- Windows 10 or later
- [MSYS2](https://www.msys2.org/) with the **UCRT64** toolchain (`g++`, `cmake`, `mingw32-make`)
- Qt 6 (Widgets + SVG): `mingw-w64-ucrt-x86_64-qt6-base`, `mingw-w64-ucrt-x86_64-qt6-svg`

### Install Qt (MSYS2 UCRT64 terminal)

```sh
pacman -S --needed mingw-w64-ucrt-x86_64-qt6-base mingw-w64-ucrt-x86_64-qt6-svg
```

### Build (double-click)

Run `build.bat` from the project root. It adds `C:\msys64\ucrt64\bin` to `PATH`,
configures CMake for MinGW, and builds `build\IsaacLauncherCpp.exe`.

### Build (manual, in a cmd prompt)

```cmd
cmake -S . -B build -G "MinGW Makefiles" ^
      -DCMAKE_BUILD_TYPE=Release ^
      -DCMAKE_PREFIX_PATH=C:/msys64/ucrt64 ^
      -DCMAKE_MAKE_PROGRAM=C:/msys64/ucrt64/bin/mingw32-make.exe
cmake --build build -j 8
```

### Run

Run `build\IsaacLauncherCpp.exe`. Qt DLLs come from `C:\msys64\ucrt64\bin`
(make sure it is on your `PATH`, or run it from the MSYS2 terminal).

## Notes / limitations

- ZIP extraction relies on the system `tar` (bundled with Windows 10 17063+ / 11). On older systems provide `tar` on `PATH`.
- No WebView is embedded: Workshop/ModDB links open in your default browser.
- Play sessions are recorded when the game process exits.

## Contributing

Bug fixes and improvements are welcome:

1. Fork the repository and create a feature branch.
2. Keep changes small and focused; follow the surrounding code style (no comments unless they add real value).
3. Rebuild and verify with `build.bat` before opening a pull request.