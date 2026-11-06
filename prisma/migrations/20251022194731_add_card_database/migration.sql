-- CreateTable
CREATE TABLE "Card" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "oracleId" TEXT,
    "name" TEXT NOT NULL,
    "manaCost" TEXT,
    "cmc" REAL NOT NULL,
    "colors" TEXT NOT NULL,
    "colorIdentity" TEXT NOT NULL,
    "typeLine" TEXT NOT NULL,
    "oracleText" TEXT,
    "power" TEXT,
    "toughness" TEXT,
    "loyalty" TEXT,
    "keywords" TEXT,
    "legalities" TEXT NOT NULL,
    "rarity" TEXT NOT NULL,
    "setCode" TEXT NOT NULL,
    "setName" TEXT NOT NULL,
    "collectorNumber" TEXT NOT NULL,
    "imageUris" TEXT,
    "prices" TEXT,
    "edhrecRank" INTEGER,
    "edhrecSaltiness" REAL,
    "artist" TEXT,
    "flavorText" TEXT,
    "releasedAt" DATETIME,
    "isCommander" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "CommanderDeck" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "commander" TEXT NOT NULL,
    "commanderId" TEXT,
    "colors" TEXT NOT NULL,
    "theme" TEXT,
    "powerLevel" INTEGER,
    "source" TEXT NOT NULL,
    "sourceUrl" TEXT,
    "decklist" TEXT NOT NULL,
    "popularity" INTEGER,
    "winRate" REAL,
    "avgTurns" REAL,
    "scrapedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "CommanderDeck_commanderId_fkey" FOREIGN KEY ("commanderId") REFERENCES "Card" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "CardSynergy" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "cardId" TEXT NOT NULL,
    "synergyId" TEXT NOT NULL,
    "score" REAL NOT NULL,
    "source" TEXT NOT NULL,
    "commander" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "CardSynergy_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "Card" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Combo" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "colors" TEXT NOT NULL,
    "steps" TEXT NOT NULL,
    "result" TEXT NOT NULL,
    "popularity" INTEGER NOT NULL DEFAULT 0,
    "source" TEXT NOT NULL,
    "sourceUrl" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "ComboCard" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "comboId" TEXT NOT NULL,
    "cardId" TEXT NOT NULL,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT "ComboCard_comboId_fkey" FOREIGN KEY ("comboId") REFERENCES "Combo" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "ComboCard_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "Card" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ScrapeJob" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "jobType" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "itemsScraped" INTEGER NOT NULL DEFAULT 0,
    "errors" TEXT,
    "startedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAt" DATETIME,
    "duration" INTEGER
);

-- CreateIndex
CREATE INDEX "Card_name_idx" ON "Card"("name");

-- CreateIndex
CREATE INDEX "Card_oracleId_idx" ON "Card"("oracleId");

-- CreateIndex
CREATE INDEX "Card_colors_idx" ON "Card"("colors");

-- CreateIndex
CREATE INDEX "Card_typeLine_idx" ON "Card"("typeLine");

-- CreateIndex
CREATE INDEX "Card_isCommander_idx" ON "Card"("isCommander");

-- CreateIndex
CREATE INDEX "CommanderDeck_commander_idx" ON "CommanderDeck"("commander");

-- CreateIndex
CREATE INDEX "CommanderDeck_source_idx" ON "CommanderDeck"("source");

-- CreateIndex
CREATE INDEX "CommanderDeck_powerLevel_idx" ON "CommanderDeck"("powerLevel");

-- CreateIndex
CREATE INDEX "CardSynergy_cardId_idx" ON "CardSynergy"("cardId");

-- CreateIndex
CREATE INDEX "CardSynergy_score_idx" ON "CardSynergy"("score");

-- CreateIndex
CREATE UNIQUE INDEX "CardSynergy_cardId_synergyId_commander_key" ON "CardSynergy"("cardId", "synergyId", "commander");

-- CreateIndex
CREATE INDEX "Combo_colors_idx" ON "Combo"("colors");

-- CreateIndex
CREATE UNIQUE INDEX "ComboCard_comboId_cardId_key" ON "ComboCard"("comboId", "cardId");

-- CreateIndex
CREATE INDEX "ScrapeJob_jobType_idx" ON "ScrapeJob"("jobType");

-- CreateIndex
CREATE INDEX "ScrapeJob_status_idx" ON "ScrapeJob"("status");
