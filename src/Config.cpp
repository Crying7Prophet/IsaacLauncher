#include "Config.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocale>

QString appRootDir() {
    QString start = QCoreApplication::applicationDirPath();
    QDir dir(start);
    for (int i = 0; i < 4; ++i) {
        if (QFile::exists(dir.filePath("config.json")))
            return dir.absolutePath();
        dir.cdUp();
    }
    return start;
}

QString configFilePath() {
    return QDir(appRootDir()).filePath("config.json");
}

bool loadConfig(LauncherConfig &out) {
    QFile file(configFilePath());
    if (!file.exists()) {
        out = LauncherConfig();
        saveConfig(out);
        return true;
    }
    if (!file.open(QIODevice::ReadOnly))
        return false;

    QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
    file.close();
    if (!doc.isObject())
        return false;

    QJsonObject root = doc.object();
    out.isaacModsPath = root.value("isaac_mods_path").toString();
    out.isaacExePath = root.value("isaac_exe_path").toString();

    out.playHistory.clear();
    QJsonArray arr = root.value("play_history").toArray();
    for (const QJsonValue &v : arr) {
        QJsonObject o = v.toObject();
        PlaySession s;
        s.start = QDateTime::fromString(o.value("start").toString(), Qt::ISODate);
        s.end = QDateTime::fromString(o.value("end").toString(), Qt::ISODate);
        s.duration = o.value("duration").toInt();
        out.playHistory.append(s);
    }
    return true;
}

bool saveConfig(const LauncherConfig &cfg) {
    QJsonObject root;
    root.insert("isaac_mods_path", cfg.isaacModsPath);
    root.insert("isaac_exe_path", cfg.isaacExePath);

    QJsonArray arr;
    for (const PlaySession &s : cfg.playHistory) {
        QJsonObject o;
        o.insert("start", s.start.toString(Qt::ISODate));
        o.insert("end", s.end.toString(Qt::ISODate));
        o.insert("duration", s.duration);
        arr.append(o);
    }
    root.insert("play_history", arr);

    QFile file(configFilePath());
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate))
        return false;
    file.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
    file.close();
    return true;
}

QString formatLastPlayed(const QVector<PlaySession> &history) {
    if (history.isEmpty())
        return QStringLiteral("Never");
    const PlaySession &last = history.last();
    return QLocale::c().toString(last.end, QStringLiteral("MMM d, yyyy HH:mm"));
}

QString formatTotalTime(const QVector<PlaySession> &history) {
    int total = 0;
    for (const PlaySession &s : history)
        total += s.duration;
    int hours = total / 3600;
    int minutes = (total % 3600) / 60;
    if (hours > 0)
        return QStringLiteral("%1h %2m").arg(hours).arg(minutes);
    return QStringLiteral("%1m").arg(minutes);
}