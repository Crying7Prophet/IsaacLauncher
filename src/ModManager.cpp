#include "ModManager.h"

#include <QDir>
#include <QFileInfo>
#include <QProcess>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QStringList>
#include <QTemporaryDir>
#include <QXmlStreamReader>

namespace mods {

bool ensureDir(const QString &path) {
    return QDir().mkpath(path);
}

void removeDir(const QString &path) {
    QDir dir(path);
    if (dir.exists())
        dir.removeRecursively();
}

static bool extractZipArchive(const QString &zipPath, const QString &destDir) {
    QString tar = QStandardPaths::findExecutable("tar");
    if (tar.isEmpty())
        tar = QStringLiteral("C:/Windows/System32/tar.exe");

    QProcess proc;
    proc.start(tar, {QStringLiteral("-xf"),
                     QDir::toNativeSeparators(zipPath),
                     QStringLiteral("-C"),
                     QDir::toNativeSeparators(destDir)});
    if (!proc.waitForFinished(120000))
        return false;
    return proc.exitStatus() == QProcess::NormalExit && proc.exitCode() == 0;
}

static bool copyRecursively(const QString &src, const QString &dst) {
    QDir srcDir(src);
    QDir dstDir(dst);
    if (!dstDir.mkpath(QStringLiteral(".")))
        return false;

    const QFileInfoList entries = srcDir.entryInfoList(
        QDir::AllEntries | QDir::NoDotAndDotDot | QDir::Hidden);
    for (const QFileInfo &info : entries) {
        QString destPath = dstDir.filePath(info.fileName());
        if (info.isDir()) {
            if (!copyRecursively(info.absoluteFilePath(), destPath))
                return false;
        } else if (!QFile::copy(info.absoluteFilePath(), destPath)) {
            return false;
        }
    }
    return true;
}

QString sanitizeName(const QString &name) {
    QString s = name;
    s.replace(QRegularExpression(QStringLiteral("[\\\\/:*?\"<>|]")), "_");
    return s.trimmed();
}

QString findNameInMetadata(const QString &folder) {
    static const QStringList candidates = {
        QStringLiteral("metadata.xml"), QStringLiteral("metadata.txt"),
        QStringLiteral("info.xml"), QStringLiteral("info.txt"),
    };

    QDir dir(folder);
    QStringList stack{folder};
    while (!stack.isEmpty()) {
        QDir current(stack.takeFirst());
        const QStringList entries = current.entryList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot);
        for (const QString &entry : entries) {
            QString full = current.filePath(entry);
            if (candidates.contains(entry, Qt::CaseInsensitive)) {
                QFile f(full);
                if (!f.open(QIODevice::ReadOnly | QIODevice::Text))
                    continue;
                QString content = QString::fromUtf8(f.readAll());
                f.close();

                QRegularExpression reName(QStringLiteral("<name>([^<]+)</name>"),
                                          QRegularExpression::CaseInsensitiveOption);
                QRegularExpressionMatch m = reName.match(content);
                if (m.hasMatch())
                    return m.captured(1).trimmed();

                QRegularExpression reProp(QStringLiteral("^Name\\s*=\\s*(.+)$"),
                                          QRegularExpression::MultilineOption |
                                          QRegularExpression::CaseInsensitiveOption);
                m = reProp.match(content);
                if (m.hasMatch())
                    return m.captured(1).trimmed();
            } else if (QFileInfo(full).isDir()) {
                stack.append(full);
            }
        }
    }
    return QString();
}

ModMetadata readMetadata(const QString &modsPath, const QString &modName) {
    ModMetadata data;
    data.name = modName;

    QString modPath = QDir(modsPath).filePath(modName);
    QString metadataFile = QDir(modPath).filePath(QStringLiteral("metadata.xml"));

    if (QFile::exists(metadataFile)) {
        QFile f(metadataFile);
        if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
            QXmlStreamReader xml(&f);
            while (!xml.atEnd() && !xml.hasError()) {
                xml.readNext();
                if (xml.tokenType() == QXmlStreamReader::StartElement) {
                    if (xml.name() == QLatin1String("name")) {
                        data.name = xml.readElementText().trimmed();
                    } else if (xml.name() == QLatin1String("description")) {
                        data.description = xml.readElementText().trimmed();
                    } else if (xml.name() == QLatin1String("version")) {
                        data.version = xml.readElementText().trimmed();
                    } else if (xml.name() == QLatin1String("tag")) {
                        QString id = xml.attributes().value("id").toString();
                        if (!id.isEmpty())
                            data.tags.append(id);
                    }
                }
            }
        }
    }

    QDir modDir(modPath);
    const QStringList files = modDir.entryList(QDir::Files | QDir::NoDotAndDotDot);
    static const QStringList imageExts = {
        QStringLiteral(".png"), QStringLiteral(".jpg"), QStringLiteral(".jpeg"),
        QStringLiteral(".gif"), QStringLiteral(".bmp"), QStringLiteral(".webp"),
    };
    for (const QString &fname : files) {
        QString ext = QFileInfo(fname).suffix().toLower();
        if (imageExts.contains(QStringLiteral(".") + ext))
            data.images.append(modDir.filePath(fname));
    }
    return data;
}

QStringList listMods(const QString &modsPath) {
    QDir dir(modsPath);
    const QStringList entries = dir.entryList(QDir::Dirs | QDir::NoDotAndDotDot);
    QStringList folders;
    for (const QString &entry : entries)
        folders.append(entry);
    folders.sort(Qt::CaseInsensitive);
    return folders;
}

QString installZip(const QString &zipPath, const QString &modsPath) {
    const QString zipName = QFileInfo(zipPath).fileName();

    QTemporaryDir tempDir;
    if (!tempDir.isValid())
        return QStringLiteral("Could not create temporary directory");

    if (!extractZipArchive(zipPath, tempDir.path()))
        return QStringLiteral("Could not extract archive: %1").arg(zipName);

    QDir temp(tempDir.path());
    const QStringList content = temp.entryList(QDir::AllEntries | QDir::NoDotAndDotDot | QDir::Hidden);

    QString extractedFolder;
    if (content.size() == 1 && QFileInfo(temp.filePath(content[0])).isDir()) {
        extractedFolder = temp.filePath(content[0]);
    } else {
        extractedFolder = tempDir.path();
    }

    QString officialName = findNameInMetadata(extractedFolder);

    QString destName;
    if (!officialName.isEmpty()) {
        destName = sanitizeName(officialName);
    } else {
        destName = QFileInfo(zipName).completeBaseName();
    }

    QString dest = QDir(modsPath).filePath(destName);
    removeDir(dest);

    if (!copyRecursively(extractedFolder, dest))
        return QStringLiteral("Could not copy mod folder: %1").arg(dest);

    QFile::remove(zipPath);
    return QString();
}

void installZipsInFolder(const QString &modsPath) {
    QDir dir(modsPath);
    const QStringList entries = dir.entryList({QStringLiteral("*.zip")}, QDir::Files, QDir::Name);
    for (const QString &entry : entries) {
        QString zip = dir.filePath(entry);
        QString err = installZip(zip, modsPath);
        if (!err.isEmpty()) {
            qWarning("Error procesando %s: %s", qPrintable(entry), qPrintable(err));
        } else {
            qWarning("Mod instalado: %s", qPrintable(zip));
        }
    }
}

} // namespace mods