#include "SkymodsDialog.h"

#include "Common.h"
#include "MainWindow.h"

#include <QDesktopServices>
#include <QDir>
#include <QFrame>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPointer>
#include <QProgressBar>
#include <QScrollArea>
#include <QTextBrowser>
#include <QVBoxLayout>
#include <QUrl>

namespace {
const QString SKYMODS_BASE = QStringLiteral("https://catalogue.smods.ru");
const QString SKYMODS_APP = QStringLiteral("250900");

const QString cardStyle =
    QStringLiteral("QFrame { background-color:#252525; border:1px solid #3d3d3d; border-radius:6px; }");
const QString inputStyle =
    QStringLiteral("QLineEdit { background-color:#252525; color:#ffffff; border:1px solid #3d3d3d; "
                   "border-radius:4px; padding:6px 10px; } "
                   "QLineEdit:focus { border:1px solid #1f538d; }");
const QString btnStyle =
    QStringLiteral("QPushButton { background-color:transparent; color:#ffffff; border:1px solid #555555; "
                   "border-radius:4px; padding:5px 10px; } "
                   "QPushButton:hover { background-color:#3d3d3d; border-color:#3d3d3d; } "
                   "QPushButton:disabled { color:#555555; border-color:#333333; }");
const QString primaryBtnStyle =
    QStringLiteral("QPushButton { background-color:transparent; color:#ffffff; border:1px solid #1f538d; "
                   "border-radius:4px; padding:5px 10px; font-weight:bold; } "
                   "QPushButton:hover { background-color:#1f538d; border-color:#1f538d; } "
                   "QPushButton:disabled { color:#555555; border-color:#333333; }");
const QString progressStyle =
    QStringLiteral("QProgressBar { background-color:#252525; border:1px solid #3d3d3d; "
                   "border-radius:4px; text-align:center; color:#ffffff; } "
                   "QProgressBar::chunk { background-color:#1f538d; border-radius:3px; }");
const QString dlGreenStyle =
    QStringLiteral("QPushButton { background-color:transparent; color:#ffffff; border:1px solid #2d5a27; "
                   "border-radius:4px; padding:4px 10px; font-weight:bold; } "
                   "QPushButton:hover { background-color:#2d5a27; border-color:#2d5a27; }");
const QString dlQueuedStyle =
    QStringLiteral("QPushButton { background-color:transparent; color:#ffffff; border:1px solid #8b6914; "
                   "border-radius:4px; padding:4px 10px; font-weight:bold; } "
                   "QPushButton:hover { background-color:#8b6914; border-color:#8b6914; }");
const QString thumbnailStyle =
    QStringLiteral("background-color:#1e1e1e; border-radius:4px;");
const QString chipStyle =
    QStringLiteral("background-color:transparent; color:#ffffff; border:1px solid #1f538d; "
                   "border-radius:3px; padding:1px 6px; font-size:10px;");
const QString detailStyle =
    QStringLiteral("QTextBrowser { background-color:#1e1e1e; color:#cccccc; border:1px solid #3d3d3d; "
                   "border-radius:6px; padding:10px; }");
const QString cancelStyle =
    QStringLiteral("QPushButton { background-color:transparent; color:#ffffff; border:1px solid #5a2d2d; "
                   "border-radius:4px; padding:5px 10px; } "
                   "QPushButton:hover { background-color:#5a2d2d; border-color:#5a2d2d; }");

QStringList categoryChips(const SkymodItem &item, QHBoxLayout *layout, int max = 4) {
    QStringList texts;
    for (int i = 0; i < qMin<int>(item.categories.size(), max); ++i) {
        QLabel *chip = new QLabel(item.categories[i]);
        chip->setStyleSheet(chipStyle);
        layout->addWidget(chip);
        texts.append(item.categories[i]);
    }
    layout->addStretch();
    return texts;
}

} // namespace

// ---------------------------------------------------------------- DownloadProgressDialog

DownloadProgressDialog::DownloadProgressDialog(MainWindow *parent,
                                               const QVector<SkymodItem> &queue)
    : QDialog(parent), m_parent(parent), m_queue(queue) {
    setWindowTitle(QStringLiteral("Downloading Mods"));
    setMinimumSize(450, 160);
    setFixedSize(450, 160);
    setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));
    setWindowFlags(windowFlags() & ~Qt::WindowContextHelpButtonHint);

    auto *layout = new QVBoxLayout(this);
    layout->setContentsMargins(16, 16, 16, 16);
    layout->setSpacing(10);

    m_lblStatus = new QLabel(QStringLiteral("Preparing... (0/%1)").arg(m_queue.size()), this);
    m_lblStatus->setStyleSheet(QStringLiteral("color:#ffffff; font-size:13px; font-weight:bold;"));
    layout->addWidget(m_lblStatus);

    m_lblDetail = new QLabel(QString(), this);
    m_lblDetail->setStyleSheet(QStringLiteral("color:#888888; font-size:11px;"));
    layout->addWidget(m_lblDetail);

    m_progressBar = new QProgressBar(this);
    m_progressBar->setRange(0, m_queue.size());
    m_progressBar->setValue(0);
    m_progressBar->setFixedHeight(20);
    m_progressBar->setStyleSheet(progressStyle);
    layout->addWidget(m_progressBar);

    auto *btnLayout = new QHBoxLayout();
    btnLayout->addStretch();
    m_btnCancel = new QPushButton(QStringLiteral("Cancel"), this);
    m_btnCancel->setFixedSize(80, 28);
    m_btnCancel->setStyleSheet(cancelStyle);
    connect(m_btnCancel, &QPushButton::clicked, this, &DownloadProgressDialog::cancel);
    btnLayout->addWidget(m_btnCancel);
    layout->addLayout(btnLayout);
}

void DownloadProgressDialog::start() {
    processNext();
}

void DownloadProgressDialog::processNext() {
    if (m_cancelled) {
        finish();
        return;
    }
    int idx = m_succeeded.size() + m_failed.size();
    if (idx >= m_queue.size()) {
        finish();
        return;
    }

    const SkymodItem item = m_queue[idx];
    m_lblStatus->setText(QStringLiteral("Downloading %1/%2: %3")
                             .arg(idx + 1)
                             .arg(m_queue.size())
                             .arg(item.title));
    m_lblDetail->setText(QStringLiteral("Fetching download page..."));

    auto *worker = new DownloadWorker(QUrl(item.downloadUrl));
    m_currentWorker = worker;

    connect(worker, &DownloadWorker::progress, this,
            [this](const QString &text) {
                if (!m_cancelled)
                    m_lblDetail->setText(text);
            });

    connect(worker, &DownloadWorker::finished, this,
            [this, item, worker](const QString &filepath) {
                m_currentWorker = nullptr;
                worker->deleteLater();
                if (m_cancelled)
                    return;
                m_lblDetail->setText(QStringLiteral("Installing..."));
                bool ok = m_parent && m_parent->processDownloadedZip(filepath, true);
                if (ok)
                    m_succeeded.append(item);
                else
                    m_failed.append({item, QStringLiteral("installation failed")});
                m_progressBar->setValue(m_succeeded.size() + m_failed.size());
                processNext();
            });

    connect(worker, &DownloadWorker::error, this,
            [this, item, worker](const QString &msg) {
                m_currentWorker = nullptr;
                worker->deleteLater();
                if (m_cancelled)
                    return;
                m_failed.append({item, msg});
                m_progressBar->setValue(m_succeeded.size() + m_failed.size());
                processNext();
            });

    worker->start();
}

void DownloadProgressDialog::cancel() {
    m_cancelled = true;
    if (m_currentWorker)
        m_currentWorker->terminate();
    finish();
}

void DownloadProgressDialog::finish() {
    m_btnCancel->setEnabled(false);
    int total = m_queue.size();
    int ok = m_succeeded.size();
    int fail = m_failed.size();

    if (m_parent)
        m_parent->refreshMods();

    QDir tempDir(QDir::current().absoluteFilePath(QStringLiteral("temp_downloads")));
    if (tempDir.exists())
        tempDir.removeRecursively();

    if (m_cancelled) {
        m_lblStatus->setText(QStringLiteral("Cancelled"));
        m_lblDetail->setText(QStringLiteral("Completed: %1 | Failed: %2 | Remaining: %3")
                                 .arg(ok).arg(fail).arg(total - ok - fail));
    } else {
        m_lblStatus->setText(QStringLiteral("All done!"));
        if (fail > 0) {
            QStringList names;
            for (int i = 0; i < qMin(fail, 5); ++i)
                names.append(m_failed[i].second);
            QString extra = fail > 5 ? QStringLiteral(" (+%1 more)").arg(fail - 5) : QString();
            m_lblDetail->setText(QStringLiteral("Installed: %1 | Failed: %2: %3%4")
                                     .arg(ok).arg(fail).arg(names.join(QStringLiteral(", "))).arg(extra));
        } else {
            m_lblDetail->setText(QStringLiteral("Successfully installed %1 mod(s)").arg(ok));
        }
    }

    disconnect(m_btnCancel, nullptr, nullptr, nullptr);
    m_btnCancel->setText(QStringLiteral("Close"));
    m_btnCancel->setEnabled(true);
    connect(m_btnCancel, &QPushButton::clicked, this, &QDialog::accept);
}

// ---------------------------------------------------------------- SkymodsDialog

SkymodsDialog::SkymodsDialog(MainWindow *parent)
    : QDialog(parent), m_parent(parent) {
    setWindowTitle(QStringLiteral("Skymods - Mod Browser"));
    setMinimumSize(1100, 550);
    resize(1200, 600);
    setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));

    auto *layout = new QVBoxLayout(this);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    auto *searchLayout = new QHBoxLayout();

    m_searchEntry = new QLineEdit(this);
    m_searchEntry->setPlaceholderText(QStringLiteral("Search mods..."));
    m_searchEntry->setStyleSheet(inputStyle);
    connect(m_searchEntry, &QLineEdit::returnPressed, this, &SkymodsDialog::search);
    searchLayout->addWidget(m_searchEntry);

    auto *btnSearch = new QPushButton(QStringLiteral("Search"), this);
    btnSearch->setFixedSize(70, 30);
    btnSearch->setStyleSheet(primaryBtnStyle);
    connect(btnSearch, &QPushButton::clicked, this, &SkymodsDialog::search);
    searchLayout->addWidget(btnSearch);

    auto *btnBrowser = new QPushButton(QStringLiteral("Browser"), this);
    btnBrowser->setFixedSize(70, 30);
    btnBrowser->setStyleSheet(btnStyle);
    connect(btnBrowser, &QPushButton::clicked, this, [this]() {
        if (m_parent)
            m_parent->openInSystemBrowser(QStringLiteral("https://steamcommunity.com/app/250900/workshop/"));
    });
    searchLayout->addWidget(btnBrowser);

    layout->addLayout(searchLayout);

    auto *contentLayout = new QHBoxLayout();
    contentLayout->setContentsMargins(0, 0, 0, 0);
    contentLayout->setSpacing(8);

    m_scrollArea = new QScrollArea(this);
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setStyleSheet(QStringLiteral("border:none;"));
    m_modsContainer = new QWidget(this);
    m_modsContainer->setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));
    m_modsLayout = new QVBoxLayout(m_modsContainer);
    m_modsLayout->setContentsMargins(0, 0, 0, 0);
    m_modsLayout->setSpacing(6);
    m_modsLayout->addStretch();
    m_scrollArea->setWidget(m_modsContainer);
    contentLayout->addWidget(m_scrollArea, 1);

    m_detailBrowser = new QTextBrowser(this);
    m_detailBrowser->setOpenExternalLinks(true);
    m_detailBrowser->setStyleSheet(detailStyle);
    m_detailBrowser->setHtml(
        QStringLiteral("<p style='color:#888;text-align:center;margin-top:40px;'>"
                       "Select a mod to view details</p>"));
    contentLayout->addWidget(m_detailBrowser, 1);

    layout->addLayout(contentLayout, 1);

    auto *navLayout = new QHBoxLayout();

    m_btnPrev = new QPushButton(QStringLiteral("< Prev"), this);
    m_btnPrev->setFixedSize(70, 28);
    m_btnPrev->setStyleSheet(btnStyle);
    connect(m_btnPrev, &QPushButton::clicked, this, &SkymodsDialog::prevPage);
    navLayout->addWidget(m_btnPrev);

    m_lblPage = new QLabel(QStringLiteral("Page 1"), this);
    m_lblPage->setAlignment(Qt::AlignCenter);
    m_lblPage->setStyleSheet(QStringLiteral("color:#cccccc;"));
    navLayout->addWidget(m_lblPage);

    m_btnDownloadAll = new QPushButton(QStringLiteral("Download All (0)"), this);
    m_btnDownloadAll->setFixedSize(130, 28);
    m_btnDownloadAll->setEnabled(false);
    m_btnDownloadAll->setStyleSheet(primaryBtnStyle);
    connect(m_btnDownloadAll, &QPushButton::clicked, this, &SkymodsDialog::startQueueDownload);
    navLayout->addWidget(m_btnDownloadAll);

    m_btnNext = new QPushButton(QStringLiteral("Next >"), this);
    m_btnNext->setFixedSize(70, 28);
    m_btnNext->setStyleSheet(btnStyle);
    connect(m_btnNext, &QPushButton::clicked, this, &SkymodsDialog::nextPage);
    navLayout->addWidget(m_btnNext);

    layout->addLayout(navLayout);

    m_lblStatus = new QLabel(QStringLiteral("Loading..."), this);
    m_lblStatus->setStyleSheet(QStringLiteral("color:#888888; font-size:11px;"));
    layout->addWidget(m_lblStatus);

    loadPage();
}

QString SkymodsDialog::buildUrl(int page) const {
    if (!m_searchQuery.isEmpty()) {
        if (page > 1)
            return QStringLiteral("%1/page/%2/?s=%3&app=%4")
                .arg(SKYMODS_BASE).arg(page).arg(m_searchQuery).arg(SKYMODS_APP);
        return QStringLiteral("%1/?s=%2&app=%3")
            .arg(SKYMODS_BASE).arg(m_searchQuery).arg(SKYMODS_APP);
    }
    if (page > 1)
        return QStringLiteral("%1/page/%2/?app=%3").arg(SKYMODS_BASE).arg(page).arg(SKYMODS_APP);
    return QStringLiteral("%1/?app=%2").arg(SKYMODS_BASE).arg(SKYMODS_APP);
}

void SkymodsDialog::loadPage() {
    m_lblStatus->setText(QStringLiteral("Loading mods..."));
    m_btnPrev->setEnabled(false);
    m_btnNext->setEnabled(false);

    QString url = buildUrl(m_currentPage);
    auto *worker = new SkymodsListWorker(QUrl(url));
    m_activeListWorker = worker;
    m_listWorkers.append(worker);
    connect(worker, &SkymodsListWorker::finished, this, &SkymodsDialog::onLoaded);
    connect(worker, &SkymodsListWorker::error, this, &SkymodsDialog::onError);
    worker->start();
}

void SkymodsDialog::onLoaded(const QVector<SkymodItem> &items) {
    if (m_activeListWorker) {
        m_listWorkers.removeOne(m_activeListWorker);
        m_activeListWorker->deleteLater();
        m_activeListWorker = nullptr;
    }

    m_items = items;
    clearMods();

    if (!items.isEmpty())
        m_lblPage->setText(QStringLiteral("Page %1").arg(m_currentPage));

    for (const SkymodItem &item : items)
        addModCard(item);

    m_lblStatus->setText(QStringLiteral("Loaded %1 mods").arg(items.size()));
    m_btnPrev->setEnabled(m_currentPage > 1);
    m_btnNext->setEnabled(items.size() >= 10);
}

void SkymodsDialog::onError(const QString &message) {
    if (m_activeListWorker) {
        m_listWorkers.removeOne(m_activeListWorker);
        m_activeListWorker->deleteLater();
        m_activeListWorker = nullptr;
    }
    m_lblStatus->setText(QStringLiteral("Error: %1").arg(message));
    m_btnPrev->setEnabled(m_currentPage > 1);
    m_btnNext->setEnabled(false);
}

void SkymodsDialog::clearMods() {
    for (ThumbnailWorker *w : m_thumbWorkers)
        w->disconnect();
    m_thumbWorkers.clear();

    m_cardButtons.clear();
    while (m_modsLayout->count()) {
        QLayoutItem *child = m_modsLayout->takeAt(0);
        if (child->widget())
            child->widget()->deleteLater();
        delete child;
    }
    m_modsLayout->addStretch();
}

void SkymodsDialog::addModCard(const SkymodItem &item) {
    auto *card = new ClickableFrame(m_modsContainer);
    card->setStyleSheet(cardStyle);
    auto *cardLayout = new QHBoxLayout(card);
    cardLayout->setContentsMargins(10, 10, 10, 10);
    cardLayout->setSpacing(12);

    auto *thumbLabel = new QLabel(card);
    thumbLabel->setFixedSize(120, 68);
    thumbLabel->setStyleSheet(thumbnailStyle);
    thumbLabel->setAlignment(Qt::AlignCenter);
    thumbLabel->setText(QStringLiteral("No img"));
    cardLayout->addWidget(thumbLabel);

    if (!item.thumbnailUrl.isEmpty()) {
        auto *worker = new ThumbnailWorker(QUrl(item.thumbnailUrl));
        auto *weakLabel = new QPointer<QLabel>(thumbLabel);
        connect(worker, &ThumbnailWorker::finished, this,
                [this, worker, weakLabel](const QPixmap &pixmap) {
                    if (!pixmap.isNull() && *weakLabel) {
                        (*weakLabel)->setPixmap(pixmap.scaled(
                            120, 68, Qt::KeepAspectRatio, Qt::SmoothTransformation));
                    }
                    m_thumbWorkers.removeOne(worker);
                    worker->deleteLater();
                    delete weakLabel;
                });
        m_thumbWorkers.append(worker);
        worker->start();
    }

    auto *infoLayout = new QVBoxLayout();
    infoLayout->setSpacing(3);

    auto *titleLabel = new QLabel(item.title, card);
    titleLabel->setStyleSheet(QStringLiteral("color:#ffffff; font-weight:bold; font-size:13px;"));
    titleLabel->setWordWrap(true);
    infoLayout->addWidget(titleLabel);

    QStringList metaParts;
    if (!item.author.isEmpty())
        metaParts.append(QStringLiteral("Author: %1").arg(item.author));
    if (!item.fileSize.isEmpty())
        metaParts.append(QStringLiteral("Size: %1").arg(item.fileSize));
    if (!metaParts.isEmpty()) {
        auto *metaLabel = new QLabel(metaParts.join(QStringLiteral("  |  ")), card);
        metaLabel->setStyleSheet(QStringLiteral("color:#aaaaaa; font-size:11px;"));
        infoLayout->addWidget(metaLabel);
    }

    if (!item.categories.isEmpty()) {
        auto *catLayout = new QHBoxLayout();
        catLayout->setSpacing(4);
        categoryChips(item, catLayout);
        infoLayout->addLayout(catLayout);
    }

    infoLayout->addStretch();

    auto *btnRow = new QHBoxLayout();
    btnRow->addStretch();

    auto *btnDownload = new QPushButton(QStringLiteral("Download"), card);
    btnDownload->setFixedSize(80, 26);

    bool isQueued = false;
    for (const SkymodItem &q : m_downloadQueue)
        if (q.downloadUrl == item.downloadUrl)
            isQueued = true;
    if (isQueued) {
        btnDownload->setText(QStringLiteral("Queued"));
        btnDownload->setStyleSheet(dlQueuedStyle);
    } else {
        btnDownload->setStyleSheet(dlGreenStyle);
    }

    auto *btnPtr = btnDownload;
    connect(btnDownload, &QPushButton::clicked, this,
            [this, item, btnPtr]() { toggleQueue(item, btnPtr); });

    m_cardButtons.insert(item.downloadUrl, btnDownload);
    btnRow->addWidget(btnDownload);
    infoLayout->addLayout(btnRow);

    cardLayout->addLayout(infoLayout, 1);

    card->setCursor(Qt::PointingHandCursor);
    card->setClickHandler([this, item]() { showModDetail(item.pageUrl); });

    m_modsLayout->insertWidget(m_modsLayout->count() - 1, card);
}

void SkymodsDialog::setThumbnail(QLabel *label, const QPixmap &pixmap) {
    Q_UNUSED(label);
    Q_UNUSED(pixmap);
}

void SkymodsDialog::showModDetail(const QString &url) {
    m_detailBrowser->setHtml(
        QStringLiteral("<p style='color:#888;text-align:center;margin-top:40px;'>Loading...</p>"));

    if (m_detailWorker) {
        m_detailWorker->disconnect();
        m_detailWorker->deleteLater();
        m_detailWorker = nullptr;
    }

    m_detailWorker = new DetailWorker(QUrl(url));
    connect(m_detailWorker, &DetailWorker::finished, this,
            [this](const QString &html) { m_detailBrowser->setHtml(html); });
    connect(m_detailWorker, &DetailWorker::error, this,
            [this](const QString &msg) {
                m_detailBrowser->setHtml(
                    QStringLiteral("<p style=\"color:#ff6666;text-align:center;margin-top:40px;\">"
                                   "Error loading details: %1</p>")
                        .arg(htmlEscape(msg)));
            });
    m_detailWorker->start();
}

void SkymodsDialog::search() {
    m_searchQuery = m_searchEntry->text().trimmed();
    m_currentPage = 1;
    loadPage();
}

void SkymodsDialog::prevPage() {
    if (m_currentPage > 1) {
        --m_currentPage;
        loadPage();
    }
}

void SkymodsDialog::nextPage() {
    ++m_currentPage;
    loadPage();
}

void SkymodsDialog::toggleQueue(const SkymodItem &item, QPushButton *btn) {
    bool queued = false;
    for (const SkymodItem &q : m_downloadQueue)
        if (q.downloadUrl == item.downloadUrl)
            queued = true;

    if (queued) {
        QVector<SkymodItem> newQueue;
        for (const SkymodItem &q : m_downloadQueue)
            if (q.downloadUrl != item.downloadUrl)
                newQueue.append(q);
        m_downloadQueue = newQueue;
        btn->setText(QStringLiteral("Download"));
        btn->setStyleSheet(dlGreenStyle);
    } else {
        m_downloadQueue.append(item);
        btn->setText(QStringLiteral("Queued"));
        btn->setStyleSheet(dlQueuedStyle);
    }
    updateDownloadAllButton();
}

void SkymodsDialog::updateDownloadAllButton() {
    m_btnDownloadAll->setText(QStringLiteral("Download All (%1)").arg(m_downloadQueue.size()));
    m_btnDownloadAll->setEnabled(!m_downloadQueue.isEmpty());
}

void SkymodsDialog::restoreQueuedButtons() {
    QSet<QString> queuedUrls;
    for (const SkymodItem &q : m_downloadQueue)
        queuedUrls.insert(q.downloadUrl);

    for (auto it = m_cardButtons.keyBegin(); it != m_cardButtons.keyEnd(); ++it) {
        QPushButton *btn = m_cardButtons.value(*it);
        if (queuedUrls.contains(*it)) {
            btn->setText(QStringLiteral("Queued"));
            btn->setStyleSheet(dlQueuedStyle);
        } else {
            btn->setText(QStringLiteral("Download"));
            btn->setStyleSheet(dlGreenStyle);
        }
    }
}

void SkymodsDialog::startQueueDownload() {
    if (m_downloadQueue.isEmpty())
        return;
    DownloadProgressDialog dialog(m_parent, m_downloadQueue);
    dialog.start();
    dialog.exec();
    m_downloadQueue.clear();
    restoreQueuedButtons();
    m_cardButtons.clear();
    updateDownloadAllButton();
}

void abrirSkymods(MainWindow *parent) {
    SkymodsDialog dialog(parent);
    dialog.exec();
}