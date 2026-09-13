#include "Workers.h"

#include "Common.h"

#include <QBuffer>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QImage>
#include <QJsonArray>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QTemporaryDir>
#include <QTimer>
#include <QUrl>
#include <QUrlQuery>

namespace {

const QString UA_GENERIC = QStringLiteral("Mozilla/5.0");
const QString UA_WIN = QStringLiteral(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)");
const QString UA_CHROME = QStringLiteral(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36");

const QString MODS_BASE = QStringLiteral("https://catalogue.smods.ru");

struct HttpResult {
    bool ok = false;
    QByteArray data;
    QString error;
    QString contentDisposition;
    QString contentType;
    QUrl finalUrl;
};

// Sesion HTTP que conserva cookies entre llamadas. Debe usarse desde el mismo hilo.
class HttpSession {
public:
    HttpResult get(const QUrl &url, const QString &ua) {
        QNetworkRequest req(url);
        req.setHeader(QNetworkRequest::UserAgentHeader, ua);
        return exec(m_manager.get(req));
    }

    HttpResult post(const QUrl &url, const QByteArray &body, const QString &ua,
                    const QByteArray &contentTypeHeader) {
        QNetworkRequest req(url);
        req.setHeader(QNetworkRequest::UserAgentHeader, ua);
        req.setHeader(QNetworkRequest::ContentTypeHeader, contentTypeHeader);
        return exec(m_manager.post(req, body));
    }

private:
    static HttpResult exec(QNetworkReply *reply) {
        HttpResult result;
        QEventLoop loop;
        QTimer timeout;
        timeout.setSingleShot(true);
        QObject::connect(&timeout, &QTimer::timeout, &loop, &QEventLoop::quit);
        QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
        timeout.start(60000);
        loop.exec();

        if (reply->error() != QNetworkReply::NoError) {
            result.error = reply->errorString();
        } else {
            result.ok = true;
            result.data = reply->readAll();
            result.finalUrl = reply->url();
            result.contentDisposition =
                reply->header(QNetworkRequest::ContentDispositionHeader).toString();
            result.contentType =
                reply->header(QNetworkRequest::ContentTypeHeader).toString();
        }
        reply->deleteLater();
        return result;
    }

    QNetworkAccessManager m_manager;
};

// Se usa para la descarga de imagenes a data URIs (cadena base64).
QString fetchImageAsDataUri(HttpSession &session, const QString &url, int maxW = 600) {
    HttpResult res = session.get(QUrl(url), UA_GENERIC);
    if (!res.ok)
        return QString();
    QImage img;
    if (!img.loadFromData(res.data) || img.isNull())
        return QString();
    if (img.width() > maxW)
        img = img.scaledToWidth(maxW, Qt::SmoothTransformation);
    QBuffer buffer;
    buffer.open(QIODevice::WriteOnly);
    if (!img.save(&buffer, "PNG"))
        return QString();
    return QStringLiteral("data:image/png;base64,") +
           QString::fromLatin1(buffer.data().toBase64());
}

QVector<SkymodItem> parseSkymodItems(const QString &html) {
    QVector<SkymodItem> items;

    QRegularExpression articleRe(
        QStringLiteral("<article\\b[^>]*class=\"[^\"]*grid-item[^\"]*\"[^>]*>(.*?)</article>"),
        QRegularExpression::DotMatchesEverythingOption);

    QRegularExpression titleRe(
        QStringLiteral("<h2\\s+class=\"post-title[^\"]*\">\\s*<a\\s+href=\"([^\"]+)\"[^>]*>([^<]+)</a>"),
        QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression thumbRe(
        QStringLiteral("<div\\s+class=\"post-thumbnail\">\\s*<a[^>]*>\\s*<img\\s+src=\"([^\"]+)\""),
        QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression downloadRe(
        QStringLiteral("<a\\s+class=\"skymods-excerpt-btn[^\"]*\"\\s+href=\"([^\"]+)\"[^>]*>Download</a>"));
    QRegularExpression authorRe(
        QStringLiteral("Author:\\s*</?\\w+>?\\s*<a[^>]*>([^<]+)</a>"));
    QRegularExpression sizeRe(
        QStringLiteral("<span\\s+class=\"skymods-item-file-size\"[^>]*>([^<]+)</span>"));
    QRegularExpression categoryRe(
        QStringLiteral("<p\\s+class=\"post-category\">(.*?)</p>"),
        QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression innerRe(QStringLiteral(">([^<]+)<"));

    QRegularExpressionMatchIterator it = articleRe.globalMatch(html);
    while (it.hasNext()) {
        QRegularExpressionMatch m = it.next();
        QString article = m.captured(1);

        SkymodItem item;

        m = titleRe.match(article);
        if (m.hasMatch()) {
            item.pageUrl = m.captured(1).trimmed();
            item.title = htmlUnescape(m.captured(2).trimmed());
        }

        m = thumbRe.match(article);
        if (m.hasMatch())
            item.thumbnailUrl = m.captured(1).trimmed();

        m = downloadRe.match(article);
        if (m.hasMatch())
            item.downloadUrl = m.captured(1).trimmed();

        m = authorRe.match(article);
        if (m.hasMatch())
            item.author = htmlUnescape(m.captured(1).trimmed());

        m = sizeRe.match(article);
        if (m.hasMatch())
            item.fileSize = htmlUnescape(m.captured(1).trimmed());

        m = categoryRe.match(article);
        if (m.hasMatch()) {
            QRegularExpressionMatchIterator ci = innerRe.globalMatch(m.captured(1));
            while (ci.hasNext()) {
                QRegularExpressionMatch cm = ci.next();
                QString cat = cm.captured(1).trimmed();
                if (!cat.isEmpty() && cat != "/")
                    item.categories.append(htmlUnescape(cat));
            }
        }

        if (!item.title.isEmpty())
            items.append(item);
    }
    return items;
}

QString cleanMeta(const QString &raw) {
    QStringList items;

    QRegularExpression pRe(QStringLiteral("<p>(.*?)</p>"),
                           QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression svgRe(QStringLiteral("<svg[^>]*>.*?</svg>"),
                             QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression tagRe(QStringLiteral("<[^>]+>"));

    QRegularExpressionMatchIterator it = pRe.globalMatch(raw);
    while (it.hasNext()) {
        QRegularExpressionMatch m = it.next();
        QString inner = m.captured(1);
        inner.remove(svgRe);
        inner.replace(tagRe, QStringLiteral(" "));
        inner = inner.trimmed();
        inner = inner.simplified();
        inner = htmlUnescape(inner);
        if (!inner.isEmpty())
            items.append(inner);
    }

    if (items.isEmpty())
        return QString();

    QString lines;
    for (const QString &item : items) {
        lines += QStringLiteral("<li style=\"margin:3px 0;color:#cccccc;\">%1</li>")
                     .arg(htmlEscape(item));
    }
    return QStringLiteral(
               "<div style=\"background:#252525;border:1px solid #3d3d3d;border-radius:6px;"
               "padding:8px 12px;margin:0 0 12px 0;\"><ul style=\"list-style:none;padding:0;margin:0;\">%1</ul></div>")
        .arg(lines);
}

QString cleanDescription(QString desc) {
    desc.replace(QRegularExpression(QStringLiteral("<div\\s+class=\"[^\"]*\"[^>]*>\\s*</div>")),
                 QStringLiteral(""));
    desc.replace(QRegularExpression(QStringLiteral("<hr\\s*/?\\s*>")),
                 QStringLiteral("<hr style=\"border:0;border-top:1px solid #3d3d3d;margin:12px 0;\">"));
    desc = regexReplace(
        desc,
        QRegularExpression(QStringLiteral("<a\\s+href=\"([^\"]+)\"[^>]*>(.*?)</a>"),
                           QRegularExpression::DotMatchesEverythingOption),
        [](const QRegularExpressionMatch &m) {
            return QStringLiteral("<a href=\"%1\" style=\"color:#3b8dbd;\">%2</a>")
                .arg(htmlEscape(m.captured(1)), m.captured(2));
        });
    desc.replace(QRegularExpression(QStringLiteral("<(?:strong|b)>(.*?)</(?:strong|b)>"),
                                    QRegularExpression::DotMatchesEverythingOption),
                 QStringLiteral("<strong style=\"color:#ffffff;\">\\1</strong>"));
    desc.replace(QRegularExpression(QStringLiteral("<(?:em|i)>(.*?)</(?:em|i)>"),
                                    QRegularExpression::DotMatchesEverythingOption),
                 QStringLiteral("<em style=\"color:#dddddd;\">\\1</em>"));
    desc = regexReplace(
        desc,
        QRegularExpression(QStringLiteral("<p([^>]*)>")),
        [](const QRegularExpressionMatch &m) {
            return QStringLiteral("<p%1 style=\"color:#cccccc;margin:6px 0;line-height:1.5;\">")
                .arg(m.captured(1));
        });
    desc = regexReplace(
        desc,
        QRegularExpression(QStringLiteral("<h([1-6])([^>]*)>")),
        [](const QRegularExpressionMatch &m) {
            return QStringLiteral("<h%1%2 style=\"color:#ffffff;margin:12px 0 6px 0;\">")
                .arg(m.captured(1), m.captured(2));
        });
    return desc;
}

QString parseDetailHtml(HttpSession &session, const QString &text) {
    QString title;
    QRegularExpression titleRe(
        QStringLiteral("<h1\\s+class=\"post-title[^\"]*\"[^>]*>([^<]+)</h1>"));
    QRegularExpressionMatch m = titleRe.match(text);
    if (m.hasMatch())
        title = htmlUnescape(m.captured(1).trimmed());

    QString previewImg;
    QRegularExpression previewRe(
        QStringLiteral("<div\\s+class=\"skymods-single-preview-wrap\">\\s*<img\\s+src=\"([^\"]+)\""),
        QRegularExpression::DotMatchesEverythingOption);
    m = previewRe.match(text);
    if (m.hasMatch())
        previewImg = m.captured(1).trimmed();

    QString metaHtml;
    QRegularExpression metaRe(
        QStringLiteral("<div\\s+class=\"skymods-single-meta\">(.*?)</div>\\s*(?:<h5|<div)"),
        QRegularExpression::DotMatchesEverythingOption);
    m = metaRe.match(text);
    if (m.hasMatch())
        metaHtml = cleanMeta(m.captured(1));

    QString desc;
    QRegularExpression descRe(
        QStringLiteral("<h5>Description:</h5>(.*?)<div\\s+class=\"skymods-single-after\""),
        QRegularExpression::DotMatchesEverythingOption);
    m = descRe.match(text);
    if (m.hasMatch()) {
        desc = m.captured(1).trimmed();
        QRegularExpression imgRe(QStringLiteral("<img\\s+src=\"([^\"]+)\""));
        QRegularExpressionMatchIterator it = imgRe.globalMatch(desc);
        while (it.hasNext()) {
            QString url = it.next().captured(1);
            QString dataUri = fetchImageAsDataUri(session, url);
            if (!dataUri.isEmpty())
                desc.replace(QStringLiteral("src=\"%1\"").arg(url),
                             QStringLiteral("src=\"%1\"").arg(dataUri));
        }
        desc = cleanDescription(desc);
    }

    QStringList parts;
    if (!title.isEmpty())
        parts.append(QStringLiteral("<h2 style=\"color:#ffffff;margin:0 0 12px 0;\">%1</h2>")
                         .arg(htmlEscape(title)));
    if (!metaHtml.isEmpty())
        parts.append(metaHtml);
    if (!previewImg.isEmpty()) {
        QString dataUri = fetchImageAsDataUri(session, previewImg, 600);
        if (!dataUri.isEmpty())
            parts.append(QStringLiteral("<p><img src=\"%1\" style=\"max-width:100%;border-radius:6px;\"></p>")
                             .arg(dataUri));
    }
    if (!desc.isEmpty())
        parts.append(desc);
    if (parts.isEmpty())
        parts.append(QStringLiteral(
            "<p style=\"color:#888;text-align:center;margin-top:40px;\">No description available.</p>"));

    return parts.join("\n");
}

// Parsea el formulario de descarga y devuelve true si se encontro un campo "id".
bool parseDownloadForm(const QString &htmlText, QUrlQuery *out) {
    QUrlQuery fields;
    fields.addQueryItem(QStringLiteral("op"), QStringLiteral("download2"));

    QStringList names = {QStringLiteral("id"), QStringLiteral("rand"),
                         QStringLiteral("referer"), QStringLiteral("method_free"),
                         QStringLiteral("method_premium")};
    for (const QString &name : names) {
        QRegularExpression re(QStringLiteral("<input[^>]+name=\"%1\"[^>]+value=\"([^\"]*)\"")
                                  .arg(name));
        QRegularExpressionMatch m = re.match(htmlText);
        fields.addQueryItem(name, m.hasMatch() ? m.captured(1) : QString());
    }

    QString id = fields.queryItemValue(QStringLiteral("id"));
    if (id.isEmpty()) {
        QRegularExpression re(QStringLiteral("name=\"id\"\\s+value=\"([^\"]+)\""));
        QRegularExpressionMatch m = re.match(htmlText);
        if (m.hasMatch())
            fields.addQueryItem(QStringLiteral("id"), m.captured(1));
        id = m.hasMatch() ? m.captured(1) : QString();
    }

    if (id.isEmpty())
        return false;
    *out = fields;
    return true;
}

QString findDirectLink(const QString &htmlText) {
    static const QStringList patterns = {
        QStringLiteral("<a[^>]+href=\"([^\"]+\\.zip[^\"]*)\""),
        QStringLiteral("(https?://[^\\s\"'<>]+\\.zip\\b[^\\s\"'<>]*)"),
        QStringLiteral("<a[^>]+id=\"downloadbtn\"[^>]+href=\"([^\"]+)\""),
    };
    for (const QString &pattern : patterns) {
        QRegularExpression re(pattern, QRegularExpression::CaseInsensitiveOption);
        QRegularExpressionMatch m = re.match(htmlText);
        if (m.hasMatch()) {
            QString url = htmlUnescape(m.captured(1).trimmed());
            if (!url.startsWith("http"))
                url = QStringLiteral("https://modsbase.com") + url;
            return url;
        }
    }
    return QString();
}

QString saveResponse(const HttpResult &res, const QString &fallbackName) {
    QDir tempDir(QDir::current().absoluteFilePath(QStringLiteral("temp_downloads")));
    tempDir.mkpath(QStringLiteral("."));

    QString fname;
    QRegularExpression cdRe(QStringLiteral("filename=\"?([^\";\\s]+)\"?"));
    QRegularExpressionMatch m = cdRe.match(res.contentDisposition);
    if (m.hasMatch())
        fname = m.captured(1);

    if (fname.isEmpty()) {
        QString path = res.finalUrl.path();
        QString base = QFileInfo(path).fileName();
        if (!base.isEmpty())
            fname = QUrl::fromPercentEncoding(base.toUtf8());
        else
            fname = fallbackName;
    }

    if (!fname.endsWith(QStringLiteral(".zip"), Qt::CaseInsensitive))
        fname += QStringLiteral(".zip");

    QString filepath = tempDir.filePath(fname);
    QFile f(filepath);
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        f.close();
        return QString();
    }
    f.write(res.data);
    f.close();

    if (res.data.size() < 100) {
        QString text = QString::fromUtf8(res.data);
        if (text.contains(QStringLiteral("<html"), Qt::CaseInsensitive) ||
            text.contains(QStringLiteral("<!doctype"), Qt::CaseInsensitive)) {
            QFile::remove(filepath);
            return QString();
        }
    }
    return filepath;
}

} // namespace

SkymodsListWorker::SkymodsListWorker(const QUrl &url, QObject *parent)
    : QThread(parent), m_url(url) {}

void SkymodsListWorker::run() {
    HttpSession session;
    HttpResult res = session.get(m_url, UA_WIN);
    if (!res.ok) {
        emit error(res.error);
        return;
    }
    emit finished(parseSkymodItems(QString::fromUtf8(res.data)));
}

ThumbnailWorker::ThumbnailWorker(const QUrl &url, QObject *parent)
    : QThread(parent), m_url(url) {}

void ThumbnailWorker::run() {
    HttpSession session;
    HttpResult res = session.get(m_url, UA_GENERIC);
    if (!res.ok)
        return;
    QImage img;
    if (img.loadFromData(res.data) && !img.isNull())
        emit finished(QPixmap::fromImage(img));
}

DetailWorker::DetailWorker(const QUrl &url, QObject *parent)
    : QThread(parent), m_url(url) {}

void DetailWorker::run() {
    HttpSession session;
    HttpResult res = session.get(m_url, UA_WIN);
    if (!res.ok) {
        emit error(res.error);
        return;
    }
    emit finished(parseDetailHtml(session, QString::fromUtf8(res.data)));
}

DownloadWorker::DownloadWorker(const QUrl &url, QObject *parent)
    : QThread(parent), m_url(url) {}

void DownloadWorker::run() {
    HttpSession session;

    emit progress(QStringLiteral("Fetching download page..."));
    HttpResult resp = session.get(m_url, UA_CHROME);
    if (!resp.ok) {
        emit error(resp.error);
        return;
    }

    if (!resp.contentType.contains(QStringLiteral("text/html"))) {
        QString filepath = saveResponse(resp, QStringLiteral("mod_download.zip"));
        if (filepath.isEmpty())
            emit error(QStringLiteral("Download page returned instead of file"));
        else
            emit finished(filepath);
        return;
    }

    QUrlQuery formData;
    if (!parseDownloadForm(QString::fromUtf8(resp.data), &formData)) {
        emit error(QStringLiteral("Could not parse download page"));
        return;
    }

    emit progress(QStringLiteral("Creating download link..."));
    QByteArray body = formData.toString(QUrl::FullyEncoded).toUtf8();
    HttpResult postResp = session.post(m_url, body, UA_CHROME,
                                       "application/x-www-form-urlencoded");
    if (!postResp.ok) {
        emit error(postResp.error);
        return;
    }

    if (!postResp.contentType.contains(QStringLiteral("text/html"))) {
        QString filepath = saveResponse(postResp, QStringLiteral("mod_download.zip"));
        if (filepath.isEmpty())
            emit error(QStringLiteral("Download page returned instead of file"));
        else
            emit finished(filepath);
        return;
    }

    QString directUrl = findDirectLink(QString::fromUtf8(postResp.data));
    if (!directUrl.isEmpty()) {
        emit progress(QStringLiteral("Downloading mod..."));
        HttpResult dlResp = session.get(QUrl(directUrl), UA_CHROME);
        if (!dlResp.ok) {
            emit error(dlResp.error);
            return;
        }
        QString filepath = saveResponse(dlResp, QStringLiteral("mod_download.zip"));
        if (filepath.isEmpty())
            emit error(QStringLiteral("Download page returned instead of file"));
        else
            emit finished(filepath);
        return;
    }

    emit error(QStringLiteral("Could not obtain download link"));
}