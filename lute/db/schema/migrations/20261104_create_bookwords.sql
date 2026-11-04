-- A word index per book (each distinct word and how often it occurs), so the book list can show how much of a
-- book you know without rendering its pages. Built and refreshed by the app in the background.

CREATE TABLE IF NOT EXISTS "bookwords" (
       "BwBkID" INTEGER NOT NULL,
       "BwWord" VARCHAR(250) NOT NULL,
       "BwCount" INTEGER NOT NULL,
       PRIMARY KEY ("BwBkID", "BwWord"),
       FOREIGN KEY ("BwBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE CASCADE
);

-- One row per indexed book; the signature says which text the index was built from.
CREATE TABLE IF NOT EXISTS "bookindex" (
       "BiBkID" INTEGER NOT NULL,
       "BiSignature" VARCHAR(64) NOT NULL,
       "BiTotal" INTEGER NOT NULL,
       PRIMARY KEY ("BiBkID"),
       FOREIGN KEY ("BiBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE CASCADE
);
