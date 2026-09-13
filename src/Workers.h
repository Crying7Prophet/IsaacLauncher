#pragma once

#include <QPixmap>
#include <QString>
#include <QStringList>
#include <QThread>
#include <QUrl>
#include <QVector>

struct SkymodItem {
    QString title;
    QString pageUrl;
    QString downloadUrl;
    QString author;
    QString fileSize;
    QString thumbnailUrl;
    QStringList categories;
};

// Carga la lista de mods de la pagina de Skymods.
class SkymodsListWorker : public QThread {
    Q_OBJECT
public:
    explicit SkymodsListWorker(const QUrl &url, QObject *parent = nullptr);

signals:
    void finished(const QVector<SkymodItem> &items);
    void error(const QString &message);

protected:
    void run() override;

private:
    QUrl m_url;
};

// Descarga un thumbnail y lo convierte a QPixmap.
class ThumbnailWorker : public QThread {
    Q_OBJECT
public:
    explicit ThumbnailWorker(const QUrl &url, QObject *parent = nullptr);

signals:
    void finished(const QPixmap &pixmap);

protected:
    void run() override;

private:
    QUrl m_url;
};

// Carga la pagina de detalle de un mod y genera su HTML para el panel.
class DetailWorker : public QThread {
    Q_OBJECT
public:
    explicit DetailWorker(const QUrl &url, QObject *parent = nullptr);

signals:
    void finished(const QString &html);
    void error(const QString &message);

protected:
    void run() override;

private:
    QUrl m_url;
};

// Descarga un mod desde su pagina de descarga (incluye el POST del formulario).
class DownloadWorker : public QThread {
    Q_OBJECT
public:
    explicit DownloadWorker(const QUrl &url, QObject *parent = nullptr);

signals:
    void finished(const QString &filepath);
    void error(const QString &message);
    void progress(const QString &message);

protected:
    void run() override;

private:
    QUrl m_url;
};