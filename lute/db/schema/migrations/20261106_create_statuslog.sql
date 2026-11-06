-- Every change of a term's status, so the app can tell the words you worked on (and reached Known) from the ones that were
-- marked known in bulk or were known before. SlHow is "hand" for what you do, and "skip" while "Finish and mark the rest as known"
-- runs (the app sets statuscontext for the length of that call). The triggers write the rows, whichever code changes a status.

CREATE TABLE IF NOT EXISTS "statuscontext" (
       "how" VARCHAR(10) NOT NULL
);

INSERT INTO "statuscontext" ("how") SELECT 'hand' WHERE NOT EXISTS (SELECT 1 FROM "statuscontext");

CREATE TABLE IF NOT EXISTS "statuslog" (
       "SlID" INTEGER NOT NULL PRIMARY KEY,
       "SlWoID" INTEGER NOT NULL,
       "SlLgID" INTEGER NOT NULL,
       "SlFrom" INTEGER,
       "SlTo" INTEGER NOT NULL,
       "SlAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       "SlHow" VARCHAR(10) NOT NULL,
       FOREIGN KEY ("SlWoID") REFERENCES "words" ("WoID") ON UPDATE NO ACTION ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "statuslog_word" ON "statuslog" ("SlWoID");
CREATE INDEX IF NOT EXISTS "statuslog_language" ON "statuslog" ("SlLgID", "SlTo");

CREATE TRIGGER IF NOT EXISTS "ocarina_statuslog_insert" AFTER INSERT ON "words" WHEN NEW."WoStatus" != 0
BEGIN
  INSERT INTO "statuslog" ("SlWoID", "SlLgID", "SlFrom", "SlTo", "SlHow")
  VALUES (NEW."WoID", NEW."WoLgID", NULL, NEW."WoStatus", (SELECT "how" FROM "statuscontext" LIMIT 1));
END;

CREATE TRIGGER IF NOT EXISTS "ocarina_statuslog_update" AFTER UPDATE OF "WoStatus" ON "words" WHEN OLD."WoStatus" != NEW."WoStatus"
BEGIN
  INSERT INTO "statuslog" ("SlWoID", "SlLgID", "SlFrom", "SlTo", "SlHow")
  VALUES (NEW."WoID", NEW."WoLgID", OLD."WoStatus", NEW."WoStatus", (SELECT "how" FROM "statuscontext" LIMIT 1));
END;
