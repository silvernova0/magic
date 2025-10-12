import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import Papa from 'papaparse';
import { prisma } from '@/lib/prisma';
import { fetchScryfallCard } from '@/lib/scryfall';
import { getCurrentUser } from '@/lib/user';


export default async function ImportPage() {
  // Server action for importing collection CSV
  async function importCollection(formData: FormData) {
    'use server';
    const user = await getCurrentUser();
    const parsed = Papa.parse(text, { header: true, skipEmptyLines: true });
    // @ts-ignore
    const data: any[] = parsed.data;
    for (const row of data) {
      const count = parseInt(row['Count'] || row['count'] || '1');
      const name = row['Name'] || row['name'];
      if (!name) continue;
      const setName = row['Edition'] || row['edition'] || '';

      let scry = null;
      if (enrich) {
        // prefer set code if present; otherwise fuzzy search by name
        const setCodeMatch = (row['Edition'] || row['edition'] || '').match(/[A-Za-z0-9]+/);
        const setCode = setCodeMatch ? setCodeMatch[0] : undefined;
        scry = await fetchScryfallCard(name, setCode);
      }

      const existing = await prisma.userCard.findFirst({ where: { name, setName, userId: user.id } });
      if (existing) {
        await prisma.userCard.update({ where: { id: existing.id }, data: { quantity: existing.quantity + count } });
      } else {
        await prisma.userCard.create({ data: {
          userId: user.id,
        } });
      }
    }
  }

  // Server action for importing deck text
  async function importDeck(formData: FormData) {
    'use server';
    const text = formData.get('deck') as string;
    const enrich = formData.get('enrichDeck') === 'on';
    if (!text) return;

    const user = await getCurrentUser();
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    for (const line of lines) {
      // Expected formats: "1 Card Name (SET) 123" or "8 Snow-Covered Forest (KHM) 284"
      const match = line.match(/^(\d+)\s+(.+?)(?:\s+\(([^)]+)\))?(?:\s+(\S+))?$/);
      if (!match) continue;
      const qty = parseInt(match[1]);
      const name = match[2];
      const edition = match[3] || '';
      const setName = edition;

      let scry = null;
      if (enrich) {
        scry = await fetchScryfallCard(name, edition || undefined);
      }

      const existing = await prisma.userCard.findFirst({ where: { name, setName, userId: user.id } });
      if (existing) {
        await prisma.card.update({ where: { id: existing.id }, data: { quantity: existing.quantity + qty } });
      } else {
        await prisma.card.create({ data: {
          name,
          manaCost: scry?.mana_cost || '',
          cmc: scry?.cmc || 0,
          colors: (scry?.colors || []).join(','),
          type_line: scry?.type_line || '',
          oracleText: scry?.oracle_text || '',
          power: scry?.power || '',
          toughness: scry?.toughness || '',
          setName: scry?.set_name || setName,
          rarity: scry?.rarity || '',
          imageUrl: scry?.image_uri || '',
          quantity: qty,
          userId: user.id,
        } });
      }
    }
  }

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-4xl font-bold mb-8">Import / Export</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Import Collection</CardTitle>
            <CardDescription>
              Paste your collection data here. The expected format is a CSV with "Count" and "Name" columns.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form action={importCollection} className="flex flex-col">
              <Textarea name="collection" placeholder="Paste your collection data here..." className="min-h-[200px] mb-4" />
              <label className="flex items-center gap-2 mb-4">
                <input type="checkbox" name="enrich" />
                <span>Enrich with Scryfall data</span>
              </label>
              <Button type="submit">Import Collection</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Import Deck</CardTitle>
            <CardDescription>
              Paste your decklist here. The expected format is one card per line, like "1 Sol Ring".
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form action={importDeck} className="flex flex-col">
              <Textarea name="deck" placeholder="Paste your decklist here..." className="min-h-[200px] mb-4" />
              <label className="flex items-center gap-2 mb-4">
                <input type="checkbox" name="enrichDeck" />
                <span>Enrich with Scryfall data</span>
              </label>
              <Button type="submit">Import Deck</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}