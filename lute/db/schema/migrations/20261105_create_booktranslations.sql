-- A translated version of a book's text, one row per sentence. A sentence is found by its page and its place among the
-- sentences of that page that contain a word (the same numbering the audio timings use). BtSource is a hash of the
-- sentence as it was translated: when the text is edited the hash no longer matches and that sentence is translated again.

CREATE TABLE IF NOT EXISTS "booktranslations" (
       "BtBkID" INTEGER NOT NULL,
       "BtPage" INTEGER NOT NULL,
       "BtIndex" INTEGER NOT NULL,
       "BtLang" VARCHAR(8) NOT NULL,
       "BtText" TEXT NOT NULL,
       "BtSource" VARCHAR(40) NOT NULL,
       "BtProvider" VARCHAR(100),
       "BtCreated" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY ("BtBkID", "BtPage", "BtIndex", "BtLang"),
       FOREIGN KEY ("BtBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE CASCADE
);
