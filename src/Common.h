#pragma once

#include <QFrame>
#include <QRegularExpression>
#include <QString>
#include <QStringList>
#include <functional>

// Escapa texto para insertarlo dentro de HTML (como html.escape + apostrofes).
QString htmlEscape(const QString &text);

// Decodifica entidades HTML (nombres comunes y referencias numericas).
QString htmlUnescape(const QString &text);

// Reemplaza globalmente cada coincidencia de `re` usando una funcion que
// recibe la coincidencia y devuelve el texto de reemplazo (como re.sub en Python).
QString regexReplace(const QString &input, const QRegularExpression &re,
                     const std::function<QString(const QRegularExpressionMatch &)> &repl);

// QFrame que emite una pulsacion de raton (para tarjetas clicables de mods).
class ClickableFrame : public QFrame {
    Q_OBJECT
public:
    explicit ClickableFrame(QWidget *parent = nullptr);
    void setClickHandler(std::function<void()> handler);

protected:
    void mousePressEvent(QMouseEvent *event) override;

private:
    std::function<void()> m_handler;
};