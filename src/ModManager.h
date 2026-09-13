#pragma once

#include <QString>
#include <QStringList>

struct ModMetadata {
    QString name;
    QString description;
    QString version;
    QStringList tags;
    QStringList images;
};

namespace mods {

QString sanitizeName(const QString &name);

// Busca recursivamente un archivo de metadatos y extrae el nombre oficial.
QString findNameInMetadata(const QString &folder);

ModMetadata readMetadata(const QString &modsPath, const QString &modName);

QStringList listMods(const QString &modsPath);

// Instala un ZIP en la carpeta de mods (extrae, detecta carpeta unica, renombra,
// elimina destino previo y copia). Vacia = exito, si no devuelve mensaje de error.
QString installZip(const QString &zipPath, const QString &modsPath);

// Procesa todos los .zip dentro de la carpeta de mods (borrando el zip al terminar).
void installZipsInFolder(const QString &modsPath);

bool ensureDir(const QString &path);

} // namespace mods