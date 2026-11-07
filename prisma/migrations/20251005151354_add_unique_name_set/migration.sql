/*
  Warnings:

  - A unique constraint covering the columns `[name,setName]` on the table `Card` will be added. If there are existing duplicate values, this will fail.

*/
-- CreateIndex
CREATE UNIQUE INDEX "name_set_unique" ON "Card"("name", "setName");
