#pragma once

#include "Workers.h"

#include <QDialog>
#include <QHash>
#include <QPushButton>
#include <QVector>

class MainWindow;
class QLabel;
class QLineEdit;
class QPushButton;
class QScrollArea;
class QTextBrowser;
class QVBoxLayout;
class QProgressBar;

// Despliega la descarga de una cola de mods y los instala al terminar.
class DownloadProgressDialog : public QDialog {
    Q_OBJECT
public:
    DownloadProgressDialog(MainWindow *parent, const QVector<SkymodItem> &queue);
    void start();

private:
    void processNext();
    void cancel();
    void finish();

    MainWindow *m_parent;
    QVector<SkymodItem> m_queue;
    QVector<SkymodItem> m_succeeded;
    QVector<QPair<SkymodItem, QString>> m_failed;
    bool m_cancelled = false;
    DownloadWorker *m_currentWorker = nullptr;

    QLabel *m_lblStatus = nullptr;
    QLabel *m_lblDetail = nullptr;
    QProgressBar *m_progressBar = nullptr;
    QPushButton *m_btnCancel = nullptr;
};

// Explorador de mods de Skymods (busqueda, paginacion, descarga en cola).
class SkymodsDialog : public QDialog {
    Q_OBJECT
public:
    explicit SkymodsDialog(MainWindow *parent);

private:
    QString buildUrl(int page = 1) const;
    void loadPage();
    void onLoaded(const QVector<SkymodItem> &items);
    void onError(const QString &message);
    void clearMods();
    void addModCard(const SkymodItem &item);
    void setThumbnail(QLabel *label, const QPixmap &pixmap);
    void showModDetail(const QString &url);
    void search();
    void prevPage();
    void nextPage();
    void toggleQueue(const SkymodItem &item, QPushButton *btn);
    void updateDownloadAllButton();
    void restoreQueuedButtons();
    void startQueueDownload();

    MainWindow *m_parent;
    QVector<SkymodItem> m_items;
    QVector<SkymodItem> m_downloadQueue;
    QHash<QString, QPushButton *> m_cardButtons;
    QVector<SkymodsListWorker *> m_listWorkers;
    QVector<ThumbnailWorker *> m_thumbWorkers;
    DetailWorker *m_detailWorker = nullptr;
    SkymodsListWorker *m_activeListWorker = nullptr;

    int m_currentPage = 1;
    QString m_searchQuery;

    QLineEdit *m_searchEntry = nullptr;
    QScrollArea *m_scrollArea = nullptr;
    QWidget *m_modsContainer = nullptr;
    QVBoxLayout *m_modsLayout = nullptr;
    QTextBrowser *m_detailBrowser = nullptr;
    QPushButton *m_btnPrev = nullptr;
    QPushButton *m_btnNext = nullptr;
    QPushButton *m_btnDownloadAll = nullptr;
    QLabel *m_lblPage = nullptr;
    QLabel *m_lblStatus = nullptr;
};

// Abre el dialogo de Skymods de forma modal.
void abrirSkymods(MainWindow *parent);