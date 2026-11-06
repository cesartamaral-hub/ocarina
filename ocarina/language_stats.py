"""
Reading statistics per language: what you know, what your texts hold, what you have read and how your vocabulary has grown.

Words are counted the way the rest of Ocarina does: known is status 4, 5 and 99; learning 1, 2 and 3; 98 is ignored; status 0
is a word you have seen but not started on. Numbers about the words of your texts come from the word index (book_index.py).
"""

from datetime import date, datetime, timedelta

from sqlalchemy import text as sql

from lute.stats.service import get_chart_data, get_reading_streak, get_table_data
from ocarina import book_index, status_log

KNOWN, LEARNING, IGNORED = (4, 5, 99), (1, 2, 3), 98


def _terms(session):
    "{language id: {status: [terms, phrases]}} from the words table."
    found = {}
    rows = session.execute(sql("select WoLgID, WoStatus, count(*), sum(WoTokenCount > 1) from words group by WoLgID, WoStatus")).all()
    for language, status, count, phrases in rows:
        found.setdefault(language, {})[status] = [count, int(phrases or 0)]
    return found


def _term_summary(by_status):
    count = lambda statuses: sum(by_status.get(s, [0, 0])[0] for s in statuses)
    known, learning = count(KNOWN), count(LEARNING)
    return {
        "known": known,
        "learning": learning,
        "ignored": count((IGNORED,)),
        "unstarted": count((0,)),  # seen in a text, not started on
        "vocabulary": known + learning,  # words you have started on
        "phrases": sum(v[1] for s, v in by_status.items() if s not in (0, IGNORED)),
        "byStatus": {str(s): v[0] for s, v in sorted(by_status.items())},
    }


def _growth(session):
    "{language id: [{date, known}]}: how many words had reached Known by each day (by the day each one last changed status)."
    found = {}
    rows = session.execute(
        sql("select WoLgID, date(WoStatusChanged) d, count(*) from words where WoStatus in (4, 5, 99) group by WoLgID, d order by d")
    ).all()
    for language, day, count in rows:
        series = found.setdefault(language, [])
        series.append({"date": day, "known": (series[-1]["known"] if series else 0) + count})
    return found


def _streaks_and_dates(session):
    "{language id: (streak in days, first read date, last read date)}."
    days = {}
    for language, day in session.execute(sql("select distinct WrLgID, strftime('%Y-%m-%d', WrReadDate) from wordsread")).all():
        days.setdefault(language, set()).add(datetime.strptime(day, "%Y-%m-%d").date())
    found = {}
    today = date.today()
    for language, dates in days.items():
        current = today if today in dates else today - timedelta(days=1)
        streak = 0
        while current in dates:
            streak += 1
            current -= timedelta(days=1)
        found[language] = (streak, min(dates).isoformat(), max(dates).isoformat())
    return found


def _books(session, audio_dir):  # pylint: disable=unused-argument
    "{language id: [book facts]}, with the numbers of the word index where it has been built."
    stats = book_index.stats_by_book()
    found = {}
    rows = session.execute(
        sql(
            "select b.BkID, b.BkTitle, b.BkLgID, b.BkArchived, b.BkAudioFilename, b.BkCurrentTxID, "
            "(select count(*) from texts t where t.TxBkID = b.BkID), "
            "(select TxOrder from texts t where t.TxID = b.BkCurrentTxID), "
            "(select max(TxReadDate) from texts t where t.TxBkID = b.BkID) "
            "from books b"
        )
    ).all()
    for book_id, title, language, archived, audio, _current, pages, current_page, last_read in rows:
        found.setdefault(language, []).append(
            {
                "id": book_id,
                "title": title,
                "archived": bool(archived),
                "hasAudio": bool(audio),
                "pages": pages,
                "currentPage": current_page or 1,
                "lastRead": last_read[:10] if last_read else None,
                "stats": stats.get(book_id),
            }
        )
    return found


def _coverage(books):
    "What the texts of a language (books not archived) hold, and how much of it you know; minutes of reading left in them."
    counted = [b for b in books if not b["archived"]]
    total = {"words": 0, "known": 0, "learning": 0, "ignored": 0, "new": 0, "newUnique": 0}
    minutes_left = 0.0
    pending = 0
    for b in counted:
        s = b["stats"]
        if s is None:
            pending += 1
            continue
        for key in total:
            total[key] += s[key]
        unread = max(b["pages"] - (b["currentPage"] - 1), 0) / max(b["pages"], 1)
        minutes_left += s["words"] * unread / book_index.WORDS_PER_MINUTE
    counting = total["words"] - total["ignored"]
    return {
        **total,
        "knownPercent": round(100 * total["known"] / counting, 1) if counting > 0 else None,
        "minutesLeft": round(minutes_left),
        "pendingBooks": pending,
    }


def summary(session, audio_dir, prior=()):
    "Everything the Reading page shows: a summary and one entry per language that has books or reading."
    terms, growth, reading = _terms(session), _growth(session), _streaks_and_dates(session)
    books = _books(session, audio_dir)
    learned, learned_series = status_log.learned_counts(session, prior), status_log.learned_growth(session, prior)
    counts = {row["name"]: row["counts"] for row in get_table_data(session)}
    charts = get_chart_data(session)
    languages = []
    for language_id, name in session.execute(sql("select LgID, LgName from languages order by LgName")).all():
        mine = books.get(language_id, [])
        streak, first, last = reading.get(language_id, (0, None, None))
        if not mine and name not in counts:
            continue  # no texts and nothing read: not a language you are using
        languages.append(
            {
                "id": language_id,
                "name": name,
                "books": {
                    "count": sum(1 for b in mine if not b["archived"]),
                    "archived": sum(1 for b in mine if b["archived"]),
                    "withAudio": sum(1 for b in mine if b["hasAudio"] and not b["archived"]),
                    "list": sorted((b for b in mine if not b["archived"]), key=lambda b: (b["lastRead"] or "", b["title"]), reverse=True),
                },
                "terms": _term_summary(terms.get(language_id, {})),
                "coverage": _coverage(mine),
                "read": counts.get(name, {"day": 0, "week": 0, "month": 0, "year": 0, "total": 0}),
                "streak": streak,
                "firstRead": first,
                "lastRead": last,
                "growth": growth.get(language_id, []),
                "learned": learned.get(language_id, 0),
                "learnedGrowth": learned_series.get(language_id, []),
                "chart": charts.get(name, []),
            }
        )
    languages.sort(key=lambda lang: (-lang["read"]["month"], lang["name"]))
    return {
        "streak": get_reading_streak(session),
        "languages": languages,
        "totals": {
            "readWeek": sum(lang["read"]["week"] for lang in languages),
            "readToday": sum(lang["read"]["day"] for lang in languages),
            "known": sum(lang["terms"]["known"] for lang in languages),
            "learning": sum(lang["terms"]["learning"] for lang in languages),
            "books": sum(lang["books"]["count"] for lang in languages),
        },
    }
