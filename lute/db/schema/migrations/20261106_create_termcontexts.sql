-- The sentence a term was saved from (or, for terms saved before this was kept, the first sentence of your books that has it),
-- with where it is: the book and the page. TcSentence is the sentence as text, without the markers the parser puts in.

CREATE TABLE IF NOT EXISTS "termcontexts" (
       "TcWoID" INTEGER NOT NULL PRIMARY KEY,
       "TcBkID" INTEGER,
       "TcPage" INTEGER,
       "TcSentence" TEXT NOT NULL,
       "TcFound" BOOLEAN NOT NULL DEFAULT 0,
       FOREIGN KEY ("TcWoID") REFERENCES "words" ("WoID") ON UPDATE NO ACTION ON DELETE CASCADE,
       FOREIGN KEY ("TcBkID") REFERENCES "books" ("BkID") ON UPDATE NO ACTION ON DELETE SET NULL
);
