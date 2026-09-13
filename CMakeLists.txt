cmake_minimum_required(VERSION 3.21)
project(IsaacLauncherCpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Svg Network)

add_executable(IsaacLauncherCpp
    resources.qrc
    src/main.cpp
    src/Common.h
    src/Common.cpp
    src/Config.h
    src/Config.cpp
    src/ModManager.h
    src/ModManager.cpp
    src/Workers.h
    src/Workers.cpp
    src/SkymodsDialog.h
    src/SkymodsDialog.cpp
    src/MainWindow.h
    src/MainWindow.cpp
)

target_link_libraries(IsaacLauncherCpp PRIVATE Qt6::Widgets Qt6::Svg Qt6::Network)

if(WIN32)
    set_target_properties(IsaacLauncherCpp PROPERTIES WIN32_EXECUTABLE ON)
endif()