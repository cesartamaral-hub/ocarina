"""
Words you learned in Ocarina: the count behind the progress bar on the Books page.

A word is learned in Ocarina when it reached Known (status 4, 5 or 99) by something you did, coming from a status that was not Known
(unseen, or 1 to 3), and it is still Known. Words that were marked known while finishing a page ("rest as known") and words that were
known before the app kept this log do not count, unless you choose to count the ones already known (preference
`learned.prior.<language id>`). The rows come from triggers on the words table (migration 20261106_create_statuslog.sql); the app only
sets the context, for the length of a call that marks words known in bulk.

    skipping(session)        context manager: statuses changed inside it are logged as "skip"
    learned_counts(session, prior)    {language id: words learned}; prior: language ids that also count what was already known
    learned_growth(session, prior)    {language id: [{date, learned}]}: the count by day
"""

from contextlib import contextmanager

from sqlalchemy import text as sql

KNOWN = "(4, 5, 99)"

_WORKED = (
    "select w.WoLgID lg, w.WoID id, min(date(l.SlAt, 'localtime')) day from statuslog l join words w on w.WoID = l.SlWoID "
    f"where l.SlHow = 'hand' and l.SlTo in {KNOWN} and (l.SlFrom is null or l.SlFrom not in {KNOWN}) and w.WoStatus in {KNOWN} "
    "group by w.WoID"
)


@contextmanager
def skipping(session):
    "While this runs, status changes are logged as 'skip' (they do not count as learned)."
    session.execute(sql("update statuscontext set how = 'skip'"))
    try:
        yield
    finally:
        session.execute(sql("update statuscontext set how = 'hand'"))
        session.commit()


def _prior_rows(session, prior):
    "Known words with no 'worked on' row, for the languages that count what was already known."
    if not prior:
        return []
    marks = ",".join(str(int(p)) for p in prior)
    return session.execute(
        sql(f"select w.WoLgID, w.WoID, date(w.WoStatusChanged) from words w where w.WoStatus in {KNOWN} and w.WoLgID in ({marks}) and w.WoID not in (select id from ({_WORKED}))")
    ).all()


def learned_counts(session, prior=()):
    "{language id: how many words you learned in Ocarina}."
    found = {}
    for lg, _, _ in session.execute(sql(_WORKED)).all():
        found[lg] = found.get(lg, 0) + 1
    for lg, _, _ in _prior_rows(session, prior):
        found[lg] = found.get(lg, 0) + 1
    return found


def learned_growth(session, prior=()):
    "{language id: [{date, learned}]}: how many words had been learned by each day."
    per_day = {}
    for lg, _, day in [*session.execute(sql(_WORKED)).all(), *_prior_rows(session, prior)]:
        per_day.setdefault(lg, {}).setdefault(day, 0)
        per_day[lg][day] += 1
    out = {}
    for lg, days in per_day.items():
        total, series = 0, []
        for day in sorted(days):
            total += days[day]
            series.append({"date": day, "learned": total})
        out[lg] = series
    return out
