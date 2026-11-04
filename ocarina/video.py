"""
The YouTube video a book was made from: which video, and when its words are said (see ocarina/youtube.py).

Sentence start times are worked out when the book is read, not stored: the anchors say at what second the n-th word is spoken, and a
sentence starts where its first word does (between two anchors, in proportion to the words). So the text can be edited a little
and the sentences still follow the video.
"""

import json
import re

from sqlalchemy import text as sql

from lute.db import db

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def starts_for(sentences, anchors):
    "Start time (seconds) of each sentence [{text, ...}], from anchors [[words before, seconds], ...] closed by [all the words, end]."
    if not sentences or not anchors:
        return []
    counts = [len(s["text"].split()) for s in sentences]
    total_sentences = sum(counts) or 1
    total_anchors = anchors[-1][0] or 1  # the last anchor closes the list: all the words, and when the last line ends
    scale = total_anchors / total_sentences
    starts, before = [], 0
    for n in counts:
        position = before * scale
        before += n
        # the last anchor at or before the position, and the one after it
        i = max((k for k, a in enumerate(anchors) if a[0] <= position), default=0)
        here = anchors[i]
        after = anchors[i + 1] if i + 1 < len(anchors) else None
        if after and after[0] > here[0]:
            starts.append(round(here[1] + (after[1] - here[1]) * (position - here[0]) / (after[0] - here[0]), 2))
        else:
            starts.append(round(here[1], 2))
    return starts


def save(book_id, video_id, anchors):
    "Remember the video of a book (replacing an earlier one)."
    if not VIDEO_ID.match(video_id or "") or not anchors:
        raise ValueError("That video cannot be saved.")
    db.session.execute(sql("delete from bookvideos where BvBkID = :b"), {"b": book_id})
    db.session.execute(
        sql("insert into bookvideos (BvBkID, BvVideoId, BvAnchors) values (:b, :v, :a)"),
        {"b": book_id, "v": video_id, "a": json.dumps(anchors)},
    )
    db.session.commit()


def find(book_id):
    "{videoId, anchors} of the book's video, or None."
    row = db.session.execute(sql("select BvVideoId, BvAnchors from bookvideos where BvBkID = :b"), {"b": book_id}).first()
    return {"videoId": row.BvVideoId, "anchors": json.loads(row.BvAnchors)} if row else None


def remove(book_id):
    db.session.execute(sql("delete from bookvideos where BvBkID = :b"), {"b": book_id})
    db.session.commit()
