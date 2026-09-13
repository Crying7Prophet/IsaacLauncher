#include "Common.h"

#include <QRegularExpression>
#include <QMouseEvent>

QString htmlEscape(const QString &text) {
    QString s = text;
    s.replace("&", "&amp;");
    s.replace("<", "&lt;");
    s.replace(">", "&gt;");
    s.replace("\"", "&quot;");
    s.replace("'", "&#39;");
    return s;
}

QString regexReplace(const QString &input, const QRegularExpression &re,
                     const std::function<QString(const QRegularExpressionMatch &)> &repl) {
    QString out;
    qsizetype last = 0;
    QRegularExpressionMatchIterator it = re.globalMatch(input);
    while (it.hasNext()) {
        QRegularExpressionMatch m = it.next();
        out += input.mid(last, m.capturedStart(0) - last);
        out += repl(m);
        last = m.capturedEnd(0);
    }
    out += input.mid(last);
    return out;
}

QString htmlUnescape(const QString &text) {
    QString s = text;

    s = regexReplace(s, QRegularExpression("&#(\\d+);"),
                     [](const QRegularExpressionMatch &m) {
                         return QString(QChar(m.captured(1).toInt()));
                     });
    s = regexReplace(s, QRegularExpression("&#x([0-9a-fA-F]+);"),
                     [](const QRegularExpressionMatch &m) {
                         return QString(QChar(m.captured(1).toInt(nullptr, 16)));
                     });

    s.replace("&lt;", "<");
    s.replace("&gt;", ">");
    s.replace("&quot;", "\"");
    s.replace("&apos;", "'");
    s.replace("&#39;", "'");
    s.replace("&nbsp;", " ");
    s.replace("&amp;", "&");
    return s;
}

ClickableFrame::ClickableFrame(QWidget *parent)
    : QFrame(parent) {}

void ClickableFrame::setClickHandler(std::function<void()> handler) {
    m_handler = std::move(handler);
}

void ClickableFrame::mousePressEvent(QMouseEvent *event) {
    if (event->button() == Qt::LeftButton && m_handler)
        m_handler();
    QFrame::mousePressEvent(event);
}