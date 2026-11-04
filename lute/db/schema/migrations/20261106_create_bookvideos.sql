-- The YouTube video a book was made from, to play it in the reader. BvAnchors is a JSON list of [number of words before, seconds]:
-- where in the video the words of the text are said (from its captions, or from what Whisper heard). Sentence start times are worked out from it.

CREATE TABLE IF NOT EXISTS "bookvideos" (
       "BvBkID" INTEGER NOT NULL PRIMARY KEY,
       "BvVideoId" VARCHAR(20) NOT NULL,
       "BvAnchors" TEXT NOT NULL,
       "BvCreated" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY ("BvBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE CASCADE
);
