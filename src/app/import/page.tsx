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
    if (!user) throw new Error('User not found');
    
    const text = formData.get('collection') as string;
    const enrich = formData.get('enrich') === 'on';
    if (!text) return;
    
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
          quantity: count,
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
    if (!user) throw new Error('User not found');
    
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
        await prisma.userCard.update({ where: { id: existing.id }, data: { quantity: existing.quantity + qty } });
      } else {
        await prisma.userCard.create({ data: {
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
    <div className="container mx-auto max-w-7xl">
      {/* Hero Header */}
      <div className="mb-8 p-8 rounded-xl bg-gradient-to-br from-purple-500/10 via-indigo-500/10 to-blue-500/10 border border-purple-500/20">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent mb-2">
          Import / Export
        </h1>
        <p className="text-lg text-muted-foreground">
          Quickly import your collection and decklists
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="group hover:shadow-xl transition-all duration-300 border-2 hover:border-purple-500/50">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2 group-hover:text-purple-600 transition-colors">
              <span className="text-3xl">📚</span>
              Import Collection
            </CardTitle>
            <CardDescription className="text-base">
              Paste your collection data here. The expected format is a CSV with "Count" and "Name" columns.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form action={importCollection} className="flex flex-col">
              <Textarea 
                name="collection" 
                placeholder="Count,Name,Edition
1,Sol Ring,Commander 2021
4,Lightning Bolt,Alpha
..." 
                className="min-h-[250px] mb-4 font-mono text-sm" 
              />
              <label className="flex items-center gap-2 mb-4 cursor-pointer group/check">
                <input 
                  type="checkbox" 
                  name="enrich" 
                  className="w-4 h-4 cursor-pointer" 
                />
                <span className="group-hover/check:text-purple-600 transition-colors">
                  ✨ Enrich with Scryfall data (slower, but more complete)
                </span>
              </label>
              <Button type="submit" size="lg" className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700">
                Import Collection
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="group hover:shadow-xl transition-all duration-300 border-2 hover:border-indigo-500/50">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2 group-hover:text-indigo-600 transition-colors">
              <span className="text-3xl">🎴</span>
              Import Deck
            </CardTitle>
            <CardDescription className="text-base">
              Paste your decklist here. The expected format is one card per line, like "1 Sol Ring".
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form action={importDeck} className="flex flex-col">
              <Textarea 
                name="deck" 
                placeholder="1 Sol Ring (C21) 314
1 Command Tower
4 Lightning Bolt (LEA) 161
..." 
                className="min-h-[250px] mb-4 font-mono text-sm" 
              />
              <label className="flex items-center gap-2 mb-4 cursor-pointer group/check">
                <input 
                  type="checkbox" 
                  name="enrichDeck" 
                  className="w-4 h-4 cursor-pointer" 
                />
                <span className="group-hover/check:text-indigo-600 transition-colors">
                  ✨ Enrich with Scryfall data (slower, but more complete)
                </span>
              </label>
              <Button type="submit" size="lg" className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700">
                Import Deck
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Info Cards */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">💡 CSV Format</h3>
            <p className="text-sm text-muted-foreground">
              Collection imports support CSV with Count, Name, and optional Edition columns
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">⚡ Deck Format</h3>
            <p className="text-sm text-muted-foreground">
              Deck imports support standard format: "quantity cardname (SET) number"
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 border-green-500/20">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-lg mb-2">✨ Enrichment</h3>
            <p className="text-sm text-muted-foreground">
              Enable enrichment to fetch images, prices, and complete card data from Scryfall
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}