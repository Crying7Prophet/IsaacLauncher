#pragma once

#include <QDateTime>
#include <QString>
#include <QVector>

struct PlaySession {
    QDateTime start;
    QDateTime end;
    int duration = 0;
};

struct LauncherConfig {
    QString isaacModsPath;
    QString isaacExePath;
    QVector<PlaySession> playHistory;
};

// Ruta del directorio raiz de la aplicacion (el que contiene config.json).
// Busca hacia arriba desde el directorio del ejecutable (por si se corre desde /build).
QString appRootDir();
QString configFilePath();

bool loadConfig(LauncherConfig &out);
bool saveConfig(const LauncherConfig &cfg);

QString formatLastPlayed(const QVector<PlaySession> &history);
QString formatTotalTime(const QVector<PlaySession> &history);