-- Several audio versions per book (your own recordings and generated ones). books.BkAudioFilename stays
-- as the selected version; rows for audio that existed before this table are added by the app when it opens.

CREATE TABLE IF NOT EXISTS "bookaudios" (
       "BaID" INTEGER NOT NULL,
       "BaBkID" INTEGER NOT NULL,
       "BaFilename" VARCHAR(255) NOT NULL,
       "BaLabel" VARCHAR(100) NOT NULL,
       "BaKind" VARCHAR(10) NOT NULL,
       "BaModel" VARCHAR(100),
       "BaVoice" VARCHAR(100),
       "BaPause" REAL,
       "BaCreated" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY ("BaID"),
       FOREIGN KEY ("BaBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "bookaudios_book" ON "bookaudios" ("BaBkID");
