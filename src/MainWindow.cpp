#include "MainWindow.h"

#include "Common.h"
#include "ModManager.h"
#include "SkymodsDialog.h"

#include <QApplication>
#include <QBuffer>
#include <QDateTime>
#include <QDesktopServices>
#include <QFileDialog>
#include <QFileInfo>
#include <QFrame>
#include <QHBoxLayout>
#include <QIcon>
#include <QImage>
#include <QJsonArray>
#include <QJsonObject>
#include <QLabel>
#include <QLineEdit>
#include <QMenu>
#include <QMessageBox>
#include <QPixmap>
#include <QProcess>
#include <QProgressBar>
#include <QScrollArea>
#include <QSizePolicy>
#include <QTextBrowser>
#include <QUrl>
#include <QVBoxLayout>

namespace {

const QString qssHeader = QStringLiteral(
    "QFrame { background-color:#252525; border-bottom:1px solid #3d3d3d; padding:6px; }");
const QString qssFooter = QStringLiteral(
    "QFrame { background-color:#252525; border-top:1px solid #3d3d3d; padding:4px 12px; }");
const QString qssModsContent = QStringLiteral("background-color:#1e1e1e;");
const QString qssGrayButton = QStringLiteral(
    "QPushButton { background-color:transparent; color:#ffffff; border:1px solid #555555; "
    "border-radius:4px; padding:5px 10px; } "
    "QPushButton:hover { background-color:#3d3d3d; border-color:#3d3d3d; }");
const QString qssPrimaryButton = QStringLiteral(
    "QPushButton { background-color:transparent; color:#ffffff; border:1px solid #1f538d; "
    "border-radius:4px; padding:5px 10px; font-weight:bold; } "
    "QPushButton:hover { background-color:#1f538d; border-color:#1f538d; }");
const QString qssDangerButton = QStringLiteral(
    "QPushButton { background-color:transparent; color:#ffffff; border:1px solid #8d1f1f; "
    "border-radius:4px; padding:5px 10px; } "
    "QPushButton:hover { background-color:#8d1f1f; border-color:#8d1f1f; }");
const QString qssRunButton = QStringLiteral(
    "QPushButton { background-color:transparent; color:#ffffff; border:1px solid #2d5a27; "
    "border-radius:4px; padding:5px 10px; font-weight:bold; } "
    "QPushButton:hover { background-color:#2d5a27; border-color:#2d5a27; }");
const QString qssSearchInput = QStringLiteral(
    "QLineEdit { background-color:#252525; color:#ffffff; border:1px solid #3d3d3d; "
    "border-radius:4px; padding:6px 10px; } "
    "QLineEdit:focus { border:1px solid #1f538d; }");
const QString qssCard = QStringLiteral(
    "QFrame { background-color:#252525; border:1px solid #3d3d3d; border-radius:6px; }");
const QString qssMenu = QStringLiteral(
    "QMenu { background-color:#2a2a2a; color:#ffffff; border:1px solid #3d3d3d; padding:4px; } "
    "QMenu::item { padding:6px 20px; border-radius:3px; } "
    "QMenu::item:selected { background-color:#3d7a37; }");
const QString qssDetail = QStringLiteral(
    "QTextBrowser { background-color:#1e1e1e; color:#cccccc; border:1px solid #3d3d3d; "
    "border-radius:6px; padding:10px; }");
const QString qssProgress = QStringLiteral(
    "QProgressBar { background-color:#252525; border:1px solid #3d3d3d; border-radius:4px; "
    "height:20px; text-align:center; color:#ffffff; } "
    "QProgressBar::chunk { background-color:#1f538d; border-radius:3px; }");

QString imageToDataUri(const QString &path, int maxWidth = 600) {
    QImage img(path);
    if (img.isNull())
        return QString();
    if (img.width() > maxWidth)
        img = img.scaledToWidth(maxWidth, Qt::SmoothTransformation);
    QBuffer buffer;
    buffer.open(QIODevice::WriteOnly);
    if (!img.save(&buffer, "PNG"))
        return QString();
    return QStringLiteral("data:image/png;base64,") +
           QString::fromLatin1(buffer.data().toBase64());
}

QPushButton *makeButton(const QString &text, int w, int h, const QString &style,
                        const QString &icon = QString()) {
    auto *btn = new QPushButton(text);
    btn->setFixedSize(w, h);
    btn->setStyleSheet(style);
    if (!icon.isEmpty()) {
        btn->setIcon(QIcon(icon));
        btn->setIconSize(QSize(w >= 32 ? 16 : 14, 16));
    }
    return btn;
}

} // namespace

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent) {
    loadConfig(m_config);

    setWindowTitle(QStringLiteral("IsaacLauncher"));
    setGeometry(100, 100, 1000, 580);

    setupHeader();
    setupModsTab();
    setupFooter();
}

QString MainWindow::modsPath() const {
    if (m_entryMods && !m_entryMods->text().isEmpty())
        return m_entryMods->text();
    return m_config.isaacModsPath;
}

void MainWindow::openInSystemBrowser(const QString &url) {
    QDesktopServices::openUrl(QUrl(url));
}

// ------------------------------------------------------------------------- Header

void MainWindow::setupHeader() {
    auto *frame = new QFrame(this);
    frame->setStyleSheet(qssHeader);
    auto *layout = new QHBoxLayout(frame);
    layout->setContentsMargins(8, 4, 8, 4);
    layout->setSpacing(8);

    m_entryMods = new QLineEdit(frame);
    m_entryMods->setText(m_config.isaacModsPath);
    m_entryMods->setVisible(false);

    m_entryIsaac = new QLineEdit(frame);
    m_entryIsaac->setText(m_config.isaacExePath);
    m_entryIsaac->setVisible(false);

    auto *btnSettings = makeButton(QStringLiteral("Settings"), 80, 28, qssGrayButton,
                                   QStringLiteral(":/icons/settings.svg"));
    connect(btnSettings, &QPushButton::clicked, this, &MainWindow::showSettingsDialog);
    layout->addWidget(btnSettings);

    auto *btnAbout = makeButton(QStringLiteral("About"), 70, 28, qssGrayButton,
                                QStringLiteral(":/icons/info.svg"));
    connect(btnAbout, &QPushButton::clicked, this, &MainWindow::showAboutDialog);
    layout->addWidget(btnAbout);

    layout->addStretch();
    setMenuWidget(frame);
}

// ------------------------------------------------------------------------- Mods tab

void MainWindow::setupModsTab() {
    auto *content = new QWidget(this);
    auto *layout = new QVBoxLayout(content);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(8);

    auto *contentLayout = new QHBoxLayout();
    contentLayout->setContentsMargins(0, 0, 0, 0);
    contentLayout->setSpacing(8);

    auto *leftColumn = new QVBoxLayout();
    leftColumn->setContentsMargins(0, 0, 0, 0);
    leftColumn->setSpacing(6);

    m_searchEntry = new QLineEdit(content);
    m_searchEntry->setPlaceholderText(QStringLiteral("Search installed mods..."));
    m_searchEntry->setStyleSheet(qssSearchInput);
    connect(m_searchEntry, &QLineEdit::textChanged, this, &MainWindow::filterMods);
    leftColumn->addWidget(m_searchEntry);

    auto *actionsRow = new QHBoxLayout();
    actionsRow->setContentsMargins(0, 0, 0, 0);
    actionsRow->setSpacing(6);

    auto *btnAdd = makeButton(QStringLiteral("Add"), 90, 28, qssPrimaryButton,
                              QStringLiteral(":/icons/plus-circle.svg"));
    auto *menu = new QMenu(btnAdd);
    menu->setStyleSheet(qssMenu);
    auto *actionLocal = menu->addAction(QStringLiteral("Add Local..."));
    connect(actionLocal, &QAction::triggered, this, &MainWindow::selectLocalFiles);
    auto *actionDownload = menu->addAction(QStringLiteral("Download..."));
    connect(actionDownload, &QAction::triggered, this,
            [this]() { abrirSkymods(this); });
    btnAdd->setMenu(menu);
    actionsRow->addWidget(btnAdd);

    auto *btnDelete = makeButton(QStringLiteral("Delete"), 90, 28, qssDangerButton,
                                 QStringLiteral(":/icons/trash.svg"));
    connect(btnDelete, &QPushButton::clicked, this, &MainWindow::deleteSelectedMod);
    actionsRow->addWidget(btnDelete);

    auto *btnFolder = makeButton(QStringLiteral("Folder"), 90, 28, qssGrayButton,
                                 QStringLiteral(":/icons/folder.svg"));
    connect(btnFolder, &QPushButton::clicked, this, &MainWindow::openSelectedModFolder);
    actionsRow->addWidget(btnFolder);

    actionsRow->addStretch();
    leftColumn->addLayout(actionsRow);

    m_scrollArea = new QScrollArea(content);
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setStyleSheet(QStringLiteral("border:none;"));
    m_modsContainer = new QWidget(m_scrollArea);
    m_modsContainer->setStyleSheet(qssModsContent);
    m_modsLayout = new QVBoxLayout(m_modsContainer);
    m_modsLayout->setContentsMargins(0, 0, 0, 0);
    m_modsLayout->setSpacing(6);
    m_modsLayout->addStretch();
    m_scrollArea->setWidget(m_modsContainer);
    leftColumn->addWidget(m_scrollArea, 1);

    contentLayout->addLayout(leftColumn, 1);

    m_detailBrowser = new QTextBrowser(content);
    m_detailBrowser->setOpenExternalLinks(true);
    m_detailBrowser->setStyleSheet(qssDetail);
    m_detailBrowser->setHtml(
        QStringLiteral("<p style='color:#888;text-align:center;margin-top:40px;'>"
                       "Select a mod to view details</p>"));
    contentLayout->addWidget(m_detailBrowser, 1);

    layout->addLayout(contentLayout, 1);
    m_modsContent = content;
}

// ------------------------------------------------------------------------- Footer

void MainWindow::setupFooter() {
    auto *frame = new QFrame(this);
    frame->setStyleSheet(qssFooter);
    auto *layout = new QHBoxLayout(frame);
    layout->setContentsMargins(8, 4, 8, 4);

    m_lblStatusBar = new QLabel(
        QStringLiteral("Last played: %1 | Total: %2")
            .arg(formatLastPlayed(m_config.playHistory),
                 formatTotalTime(m_config.playHistory)),
        frame);
    m_lblStatusBar->setStyleSheet(QStringLiteral("color:#888888; font-size:11px;"));
    layout->addWidget(m_lblStatusBar);
    layout->addStretch();

    m_btnRun = makeButton(QStringLiteral("Launch"), 110, 32, qssRunButton,
                          QStringLiteral(":/icons/play.svg"));
    connect(m_btnRun, &QPushButton::clicked, this, &MainWindow::launchGame);
    layout->addWidget(m_btnRun);

    auto *central = new QWidget(this);
    auto *v = new QVBoxLayout(central);
    v->setContentsMargins(0, 0, 0, 0);
    v->setSpacing(0);
    v->addWidget(m_modsContent, 1);
    v->addWidget(frame);
    setCentralWidget(central);

    refreshMods();
}

// ------------------------------------------------------------------------- Launch

void MainWindow::launchGame() {
    QString exe = m_entryIsaac->text();
    if (exe.isEmpty())
        exe = m_config.isaacExePath;

    if (!exe.isEmpty() && QFile::exists(exe)) {
        m_gameProcess = new QProcess(this);
        m_gameProcess->setProgram(QDir::toNativeSeparators(exe));
        m_gameProcess->setWorkingDirectory(QFileInfo(exe).absolutePath());
        connect(m_gameProcess, &QProcess::finished, this,
                [this](int, QProcess::ExitStatus) { onGameExit(); });
        m_gameProcess->start();
        m_sessionStart = QDateTime::currentSecsSinceEpoch();
        m_lblStatusBar->setText(
            QStringLiteral("Game running... | Last played: %1 | Total: %2")
                .arg(formatLastPlayed(m_config.playHistory),
                     formatTotalTime(m_config.playHistory)));
    } else {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Game executable not found."));
    }
}

void MainWindow::onGameExit() {
    if (m_sessionStart != 0) {
        qint64 now = QDateTime::currentSecsSinceEpoch();
        PlaySession session;
        session.start = QDateTime::fromSecsSinceEpoch(m_sessionStart);
        session.end = QDateTime::fromSecsSinceEpoch(now);
        session.duration = static_cast<int>(now - m_sessionStart);
        m_config.playHistory.append(session);
        saveConfigInternal();
    }
    if (m_gameProcess) {
        m_gameProcess->deleteLater();
        m_gameProcess = nullptr;
    }
    m_sessionStart = 0;
    m_lblStatusBar->setText(
        QStringLiteral("Last played: %1 | Total: %2")
            .arg(formatLastPlayed(m_config.playHistory),
                 formatTotalTime(m_config.playHistory)));
}

// ------------------------------------------------------------------------- Mods list

void MainWindow::refreshMods() {
    QString path = modsPath();
    if (path.isEmpty() || !QDir().mkpath(path)) {
        clearModCards();
        auto *errorCard = new ClickableFrame(m_modsContainer);
        errorCard->setStyleSheet(qssCard);
        auto *errLayout = new QVBoxLayout(errorCard);
        errLayout->setContentsMargins(10, 10, 10, 10);
        errLayout->addWidget(new QLabel(QStringLiteral("Mods folder not found"), errorCard));
        errLayout->addWidget(new QLabel(QStringLiteral("Path: %1").arg(path), errorCard));
        errLayout->addWidget(new QLabel(QStringLiteral("Set a valid path in Settings"), errorCard));
        for (int i = 0; i < errLayout->count(); ++i) {
            auto *lbl = qobject_cast<QLabel *>(errLayout->itemAt(i)->widget());
            if (lbl)
                lbl->setStyleSheet(QStringLiteral("color:#cccccc;"));
        }
        m_modsLayout->insertWidget(m_modsLayout->count() - 1, errorCard);
        return;
    }

    mods::installZipsInFolder(path);
    clearModCards();

    m_modsList = mods::listMods(path);
    for (const QString &modName : m_modsList)
        addModCard(modName);

    if (!m_modsList.isEmpty())
        showModDetail(m_modsList.first());
}

void MainWindow::clearModCards() {
    while (m_modsLayout->count()) {
        QLayoutItem *child = m_modsLayout->takeAt(0);
        if (child->widget())
            child->widget()->deleteLater();
        delete child;
    }
    m_modsLayout->addStretch();
}

void MainWindow::addModCard(const QString &modName) {
    ModMetadata data = mods::readMetadata(modsPath(), modName);

    auto *card = new ClickableFrame(m_modsContainer);
    card->setStyleSheet(qssCard);
    auto *cardLayout = new QHBoxLayout(card);
    cardLayout->setContentsMargins(10, 10, 10, 10);
    cardLayout->setSpacing(12);

    auto *thumbLabel = new QLabel(card);
    thumbLabel->setFixedSize(120, 68);
    thumbLabel->setStyleSheet(QStringLiteral("background-color:#1e1e1e; border-radius:4px;"));
    thumbLabel->setAlignment(Qt::AlignCenter);
    thumbLabel->setText(QStringLiteral("No img"));
    cardLayout->addWidget(thumbLabel);

    if (!data.images.isEmpty()) {
        QPixmap pixmap(data.images.first());
        if (!pixmap.isNull()) {
            thumbLabel->setPixmap(pixmap.scaled(
                120, 68, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        }
    }

    auto *infoLayout = new QVBoxLayout();
    infoLayout->setSpacing(3);

    auto *titleLabel = new QLabel(data.name, card);
    titleLabel->setStyleSheet(QStringLiteral("color:#ffffff; font-weight:bold; font-size:13px;"));
    titleLabel->setWordWrap(true);
    infoLayout->addWidget(titleLabel);

    if (!data.version.isEmpty()) {
        auto *metaLabel = new QLabel(QStringLiteral("v%1").arg(data.version), card);
        metaLabel->setStyleSheet(QStringLiteral("color:#aaaaaa; font-size:11px;"));
        infoLayout->addWidget(metaLabel);
    }

    if (!data.tags.isEmpty()) {
        auto *catLayout = new QHBoxLayout();
        catLayout->setSpacing(4);
        for (int i = 0; i < qMin<int>(data.tags.size(), 4); ++i) {
            auto *chip = new QLabel(data.tags[i], card);
            chip->setStyleSheet(QStringLiteral(
                "background-color:transparent; color:#ffffff; border:1px solid #1f538d; "
                "border-radius:3px; padding:1px 6px; font-size:10px;"));
            catLayout->addWidget(chip);
        }
        catLayout->addStretch();
        infoLayout->addLayout(catLayout);
    }

    infoLayout->addStretch();
    cardLayout->addLayout(infoLayout, 1);

    card->setProperty("mod_name", modName);
    card->setCursor(Qt::PointingHandCursor);
    card->setClickHandler([this, modName]() { showModDetail(modName); });

    m_modsLayout->insertWidget(m_modsLayout->count() - 1, card);
}

void MainWindow::showModDetail(const QString &modName) {
    m_selectedMod = modName;
    m_detailBrowser->setHtml(
        QStringLiteral("<p style='color:#888;text-align:center;margin-top:40px;'>Loading...</p>"));

    ModMetadata data = mods::readMetadata(modsPath(), modName);

    QStringList parts;
    parts.append(QStringLiteral("<h2 style=\"color:#ffffff;margin:0 0 12px 0;\">%1</h2>")
                     .arg(htmlEscape(data.name)));

    QStringList metaItems;
    if (!data.version.isEmpty())
        metaItems.append(QStringLiteral("Version: %1").arg(htmlEscape(data.version)));
    if (!data.tags.isEmpty())
        metaItems.append(QStringLiteral("Tags: %1")
                             .arg(htmlEscape(data.tags.join(QStringLiteral(", ")))));

    if (!metaItems.isEmpty()) {
        QString lines;
        for (const QString &it : metaItems)
            lines += QStringLiteral("<li style=\"margin:3px 0;color:#cccccc;\">%1</li>").arg(it);
        parts.append(QStringLiteral(
                         "<div style=\"background:#252525;border:1px solid #3d3d3d;border-radius:6px;"
                         "padding:8px 12px;margin:0 0 12px 0;\"><ul style=\"list-style:none;padding:0;margin:0;\">"
                         "%1</ul></div>")
                         .arg(lines));
    }

    for (int i = 0; i < qMin<int>(data.images.size(), 10); ++i) {
        QString dataUri = imageToDataUri(data.images[i]);
        if (!dataUri.isEmpty())
            parts.append(QStringLiteral("<p><img src=\"%1\" style=\"max-width:100%;border-radius:6px;margin:4px 0;\"></p>")
                             .arg(dataUri));
    }

    if (!data.description.isEmpty()) {
        QString desc = htmlEscape(data.description);
        desc.replace(QStringLiteral("\n"), QStringLiteral("<br>"));
        parts.append(QStringLiteral(
                         "<div style=\"margin-top:12px;padding:10px;background:#252525;"
                         "border:1px solid #3d3d3d;border-radius:6px;\">"
                         "<p style=\"color:#cccccc;line-height:1.5;\">%1</p></div>")
                         .arg(desc));
    }

    if (parts.isEmpty())
        parts.append(QStringLiteral(
            "<p style='color:#888;text-align:center;margin-top:40px;'>No details available.</p>"));

    m_detailBrowser->setHtml(parts.join(QStringLiteral("\n")));
}

void MainWindow::filterMods(const QString &text) {
    QString needle = text.trimmed().toLower();
    for (int i = 0; i < m_modsLayout->count(); ++i) {
        QWidget *widget = m_modsLayout->itemAt(i)->widget();
        if (!widget)
            continue;
        QString name = widget->property("mod_name").toString();
        widget->setVisible(needle.isEmpty() || name.toLower().contains(needle));
    }
}

void MainWindow::deleteSelectedMod() {
    if (m_selectedMod.isEmpty()) {
        QMessageBox::information(this, QStringLiteral("Info"),
                                 QStringLiteral("Select a mod first"));
        return;
    }

    QString modPath = QDir(modsPath()).filePath(m_selectedMod);
    QMessageBox::StandardButton reply = QMessageBox::question(
        this, QStringLiteral("Confirm"),
        QStringLiteral("Delete mod: %1?").arg(m_selectedMod),
        QMessageBox::Yes | QMessageBox::No);

    if (reply == QMessageBox::Yes && QFileInfo::exists(modPath)) {
        QDir(modPath).removeRecursively();
        m_selectedMod.clear();
        refreshMods();
    }
}

void MainWindow::openSelectedModFolder() {
    QString path = modsPath();
    if (!m_selectedMod.isEmpty()) {
        QString modPath = QDir(path).filePath(m_selectedMod);
        if (QDir(modPath).exists()) {
            QDesktopServices::openUrl(QUrl::fromLocalFile(modPath));
            return;
        }
    }
    if (!path.isEmpty() && QDir(path).exists())
        QDesktopServices::openUrl(QUrl::fromLocalFile(path));
    else
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Mods folder not found"));
}

void MainWindow::openModsFolder() {
    openSelectedModFolder();
}

// ------------------------------------------------------------------------- Config

void MainWindow::saveConfigInternal() {
    m_config.isaacModsPath = m_entryMods ? m_entryMods->text() : m_config.isaacModsPath;
    m_config.isaacExePath = m_entryIsaac ? m_entryIsaac->text() : m_config.isaacExePath;
    saveConfig(m_config);
}

// ------------------------------------------------------------------------- Zap de descarga

bool MainWindow::processDownloadedZip(const QString &filepath, bool silent) {
    QString path = modsPath();
    if (path.isEmpty() || !QDir().mkpath(path)) {
        if (!silent)
            QMessageBox::warning(this, QStringLiteral("Error"),
                                 QStringLiteral("Mods folder not found: %1\n"
                                                "Set a valid path in the settings tab")
                                     .arg(path));
        return false;
    }

    if (!QFile::exists(filepath))
        return false;

    QString err = mods::installZip(filepath, path);
    if (!err.isEmpty()) {
        if (!silent)
            QMessageBox::warning(this, QStringLiteral("Error"), err);
        return false;
    }

    if (QFile::exists(filepath))
        QFile::remove(filepath);

    refreshMods();
    return true;
}

// ------------------------------------------------------------------------- Add Local

void MainWindow::selectLocalFiles() {
    const QStringList filePaths = QFileDialog::getOpenFileNames(
        this, QStringLiteral("Select mod files"), QString(),
        QStringLiteral("ZIP files (*.zip);;All files (*.*)"));
    if (filePaths.isEmpty())
        return;

    QStringList zipFiles;
    QStringList nonZip;
    for (const QString &f : filePaths) {
        if (f.endsWith(QStringLiteral(".zip"), Qt::CaseInsensitive))
            zipFiles.append(f);
        else
            nonZip.append(f);
    }

    if (!nonZip.isEmpty()) {
        QStringList names;
        for (int i = 0; i < qMin<int>(nonZip.size(), 3); ++i)
            names.append(QFileInfo(nonZip[i]).fileName());
        if (nonZip.size() > 3)
            names.append(QStringLiteral("and %1 more").arg(nonZip.size() - 3));
        QMessageBox::warning(this, QStringLiteral("Skipped files"),
                             QStringLiteral("The following files are not ZIP and were skipped:\n%1")
                                 .arg(names.join(QStringLiteral(", "))));
    }

    if (zipFiles.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("No valid ZIP files selected"));
        return;
    }

    QString path = modsPath();
    if (path.isEmpty() || !QDir().mkpath(path)) {
        QMessageBox::warning(this, QStringLiteral("Error"),
                             QStringLiteral("Mods folder not found: %1\n"
                                            "Set a valid path in the settings tab")
                                 .arg(path));
        return;
    }

    auto *dialog = new QDialog(this);
    dialog->setWindowTitle(QStringLiteral("Installing mods"));
    dialog->setFixedSize(420, 120);
    dialog->setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));
    dialog->setWindowFlags(dialog->windowFlags() & ~Qt::WindowContextHelpButtonHint);

    auto *dl = new QVBoxLayout(dialog);
    dl->setContentsMargins(16, 16, 16, 16);
    dl->setSpacing(10);

    auto *statusLabel = new QLabel(QStringLiteral("[1/%1] Preparing...").arg(zipFiles.size()), dialog);
    statusLabel->setStyleSheet(QStringLiteral("color:#ffffff; font-weight:bold;"));
    dl->addWidget(statusLabel);

    auto *progressBar = new QProgressBar(dialog);
    progressBar->setRange(0, zipFiles.size());
    progressBar->setValue(0);
    progressBar->setTextVisible(true);
    progressBar->setFormat(QStringLiteral("%v / %m"));
    progressBar->setStyleSheet(qssProgress);
    dl->addWidget(progressBar);

    dialog->show();
    QApplication::processEvents();

    QStringList installed;
    QStringList failed;

    for (int i = 0; i < zipFiles.size(); ++i) {
        QString filepath = zipFiles[i];
        statusLabel->setText(QStringLiteral("[%1/%2] Installing: %3")
                                 .arg(i + 1).arg(zipFiles.size()).arg(QFileInfo(filepath).fileName()));
        progressBar->setValue(i);
        QApplication::processEvents();

        QString err = mods::installZip(filepath, path);
        if (err.isEmpty())
            installed.append(QFileInfo(filepath).fileName());
        else
            failed.append(QStringLiteral("%1: %2").arg(QFileInfo(filepath).fileName(), err));
    }

    progressBar->setValue(zipFiles.size());
    statusLabel->setText(QStringLiteral("Done!"));
    QApplication::processEvents();
    dialog->close();
    dialog->deleteLater();

    refreshMods();

    if (failed.isEmpty()) {
        QMessageBox::information(this, QStringLiteral("Success"),
                                 QStringLiteral("Successfully installed %1 mod(s)")
                                     .arg(installed.size()));
    } else {
        QStringList shown;
        for (int i = 0; i < qMin<int>(failed.size(), 10); ++i)
            shown.append(failed[i]);
        if (failed.size() > 10)
            shown.append(QStringLiteral("...and %1 more").arg(failed.size() - 10));
        QMessageBox::warning(
            this, QStringLiteral("Import complete"),
            QStringLiteral("Installed: %1 mod(s)\nFailed: %2 mod(s)\n\n%3")
                .arg(installed.size()).arg(failed.size()).arg(shown.join(QStringLiteral("\n"))));
    }
}

// ------------------------------------------------------------------------- Dialogs

void MainWindow::showSettingsDialog() {
    auto *dialog = new QDialog(this);
    dialog->setWindowTitle(QStringLiteral("Settings"));
    dialog->setFixedSize(520, 180);
    dialog->setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));

    auto *layout = new QVBoxLayout(dialog);
    layout->setSpacing(10);
    layout->setContentsMargins(16, 16, 16, 16);

    const QString inputStyle = QStringLiteral(
        "QLineEdit { background-color:#252525; color:#ffffff; border:1px solid #3d3d3d; "
        "border-radius:4px; padding:5px 8px; } "
        "QLineEdit:focus { border:1px solid #1f538d; }");

    auto *modsRow = new QHBoxLayout();
    auto *modsLabel = new QLabel(QStringLiteral("Mods path:"), dialog);
    modsLabel->setFixedWidth(100);
    modsLabel->setStyleSheet(QStringLiteral("color:#aaaaaa; font-weight:bold;"));
    auto *entryMods = new QLineEdit(m_entryMods->text(), dialog);
    entryMods->setStyleSheet(inputStyle);
    auto *btnBrowseMods = makeButton(QStringLiteral("..."), 70, 28, qssGrayButton);
    connect(btnBrowseMods, &QPushButton::clicked, dialog,
            [dialog, entryMods]() {
                QString path = QFileDialog::getExistingDirectory(
                    dialog, QStringLiteral("Select Mods Folder"));
                if (!path.isEmpty())
                    entryMods->setText(path);
            });
    modsRow->addWidget(modsLabel);
    modsRow->addWidget(entryMods, 1);
    modsRow->addWidget(btnBrowseMods);
    layout->addLayout(modsRow);

    auto *gameRow = new QHBoxLayout();
    auto *gameLabel = new QLabel(QStringLiteral("Game exe:"), dialog);
    gameLabel->setFixedWidth(100);
    gameLabel->setStyleSheet(QStringLiteral("color:#aaaaaa; font-weight:bold;"));
    auto *entryGame = new QLineEdit(m_entryIsaac->text(), dialog);
    entryGame->setStyleSheet(inputStyle);
    auto *btnBrowseGame = makeButton(QStringLiteral("..."), 70, 28, qssGrayButton);
    connect(btnBrowseGame, &QPushButton::clicked, dialog,
            [dialog, entryGame]() {
                QString path = QFileDialog::getOpenFileName(
                    dialog, QStringLiteral("Select Game Executable"), QString(),
                    QStringLiteral("Executable (*.exe)"));
                if (!path.isEmpty())
                    entryGame->setText(path);
            });
    gameRow->addWidget(gameLabel);
    gameRow->addWidget(entryGame, 1);
    gameRow->addWidget(btnBrowseGame);
    layout->addLayout(gameRow);

    auto *btnRow = new QHBoxLayout();
    btnRow->addStretch();
    auto *btnSave = makeButton(QStringLiteral("Save"), 70, 28, qssPrimaryButton);
    connect(btnSave, &QPushButton::clicked, dialog,
            [this, dialog, entryMods, entryGame]() {
                m_entryMods->setText(entryMods->text());
                m_entryIsaac->setText(entryGame->text());
                saveConfigInternal();
                refreshMods();
                dialog->accept();
            });
    btnRow->addWidget(btnSave);
    layout->addLayout(btnRow);

    dialog->exec();
    dialog->deleteLater();
}

void MainWindow::showAboutDialog() {
    auto *dialog = new QDialog(this);
    dialog->setWindowTitle(QStringLiteral("About"));
    dialog->setFixedSize(360, 200);
    dialog->setStyleSheet(QStringLiteral("background-color:#1e1e1e;"));

    auto *layout = new QVBoxLayout(dialog);
    layout->setAlignment(Qt::AlignCenter);
    layout->setSpacing(6);

    auto addCentered = [dialog](const QString &text, const QString &style = QString()) {
        auto *label = new QLabel(text, dialog);
        label->setAlignment(Qt::AlignCenter);
        if (!style.isEmpty())
            label->setStyleSheet(style);
        return label;
    };

    layout->addWidget(addCentered(QStringLiteral("IsaacLauncher")));
    layout->addWidget(addCentered(QStringLiteral("Version 1.0")));
    layout->addWidget(addCentered(QStringLiteral("A mod manager for\nThe Binding of Isaac: Repentance"),
                                  QStringLiteral("color:#cccccc; margin:6px 0px;")));

    auto *github = new QLabel(
        QStringLiteral("<a href=\"https://github.com/Crying7Prophet/IsaacLauncher\">GitHub</a>"), dialog);
    github->setAlignment(Qt::AlignCenter);
    github->setOpenExternalLinks(true);
    layout->addWidget(github);

    layout->addStretch();

    auto *btnClose = makeButton(QStringLiteral("Close"), 70, 28, qssGrayButton);
    connect(btnClose, &QPushButton::clicked, dialog, &QDialog::accept);
    layout->addWidget(btnClose, 0, Qt::AlignHCenter);

    dialog->exec();
    dialog->deleteLater();
}