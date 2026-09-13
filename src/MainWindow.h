#pragma once

#include "Config.h"

#include <QMainWindow>
#include <QString>
#include <QStringList>
#include <QVector>

class QFrame;
class QLabel;
class QLineEdit;
class QMenu;
class QProcess;
class QPushButton;
class QScrollArea;
class QTextBrowser;
class QVBoxLayout;
class QWidget;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);

    // Procesa un ZIP descargado (instantaneo) y lo instala en la carpeta de mods.
    bool processDownloadedZip(const QString &filepath, bool silent = false);

    // Abre un modulo agrupado por una lista de zips con dialogo de progreso.
    void refreshMods();

    void openInSystemBrowser(const QString &url);

private:
    void setupHeader();
    void setupModsTab();
    void setupFooter();
    void launchGame();
    void onGameExit();

    void showSettingsDialog();
    void showAboutDialog();

    void addModCard(const QString &modName);
    void clearModCards();
    void showModDetail(const QString &modName);
    void filterMods(const QString &text);
    void deleteSelectedMod();
    void openSelectedModFolder();
    void openModsFolder();
    void selectLocalFiles();
    void saveConfigInternal();

    QString modsPath() const;

    LauncherConfig m_config;
    QString m_selectedMod;
    QStringList m_modsList;
    qint64 m_sessionStart = 0;
    QProcess *m_gameProcess = nullptr;

    QWidget *m_modsContent = nullptr;
    QVBoxLayout *m_modsLayout = nullptr;
    QLineEdit *m_searchEntry = nullptr;
    QScrollArea *m_scrollArea = nullptr;
    QWidget *m_modsContainer = nullptr;
    QTextBrowser *m_detailBrowser = nullptr;
    QLabel *m_lblStatusBar = nullptr;
    QPushButton *m_btnRun = nullptr;

    // Entradas ocultas que guardan las rutas (como en la version Python).
    QLineEdit *m_entryMods = nullptr;
    QLineEdit *m_entryIsaac = nullptr;
};