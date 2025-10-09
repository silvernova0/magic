import { prisma } from "@/lib/prisma";
import { revalidatePath } from "next/cache";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";



export default async function CollectionPage() {
  const cards = await prisma.card.findMany();

  async function addCard(formData: FormData) {
    "use server";

    const name = formData.get("name") as string;
    const manaCost = formData.get("manaCost") as string;
    const cmc = parseFloat(formData.get("cmc") as string);
    const colors = formData.get("colors") as string;
    const type_line = formData.get("type_line") as string;
    const oracleText = formData.get("oracleText") as string;
    const power = formData.get("power") as string;
    const toughness = formData.get("toughness") as string;
    const setName = formData.get("setName") as string;
    const rarity = formData.get("rarity") as string;
    const imageUrl = formData.get("imageUrl") as string;
    const quantity = parseInt(formData.get("quantity") as string);

    await prisma.card.create({
      data: {
        name,
        manaCost,
        cmc,
        colors,
        type_line,
        oracleText,
        power,
        toughness,
        setName,
        rarity,
        imageUrl,
        quantity,
      },
    });

    revalidatePath("/collection");
  }

  return (
    <main className="p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">My Collection</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Add a New Card</CardTitle>
              <CardDescription>
                Enter the details of the card you want to add to your collection.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form action={addCard} className="flex flex-col gap-4">
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    type="text"
                    id="name"
                    name="name"
                    placeholder="Card Name"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="manaCost">Mana Cost</Label>
                  <Input
                    type="text"
                    id="manaCost"
                    name="manaCost"
                    placeholder="Mana Cost"
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="cmc">CMC</Label>
                  <Input
                    type="number"
                    id="cmc"
                    name="cmc"
                    placeholder="CMC"
                    step="0.1"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="colors">Colors</Label>
                  <Input
                    type="text"
                    id="colors"
                    name="colors"
                    placeholder="Colors (comma-separated)"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="type_line">Type Line</Label>
                  <Input
                    type="text"
                    id="type_line"
                    name="type_line"
                    placeholder="Type Line"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="oracleText">Oracle Text</Label>
                  <Textarea
                    id="oracleText"
                    name="oracleText"
                    placeholder="Oracle Text"
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="power">Power</Label>
                  <Input
                    type="text"
                    id="power"
                    name="power"
                    placeholder="Power"
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="toughness">Toughness</Label>
                  <Input
                    type="text"
                    id="toughness"
                    name="toughness"
                    placeholder="Toughness"
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="setName">Set Name</Label>
                  <Input
                    type="text"
                    id="setName"
                    name="setName"
                    placeholder="Set Name"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="rarity">Rarity</Label>
                  <Input
                    type="text"
                    id="rarity"
                    name="rarity"
                    placeholder="Rarity"
                    required
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="imageUrl">Image URL</Label>
                  <Input
                    type="text"
                    id="imageUrl"
                    name="imageUrl"
                    placeholder="Image URL"
                  />
                </div>
                <div className="grid w-full max-w-sm items-center gap-1.5">
                  <Label htmlFor="quantity">Quantity</Label>
                  <Input
                    type="number"
                    id="quantity"
                    name="quantity"
                    placeholder="Quantity"
                    defaultValue="1"
                    required
                  />
                </div>
                <Button type="submit">Add Card</Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2">
          <h2 className="text-2xl font-bold mb-4">Your Collection</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cards.map((card) => (
              <Card key={card.id}>
                <CardHeader>
                  <CardTitle>{card.name}</CardTitle>
                  <CardDescription>{card.type_line}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p>{card.manaCost}</p>
                  <p>
                    {card.power}/{card.toughness}
                  </p>
                </CardContent>
                <CardFooter>
                  <p>
                    {card.setName} - {card.rarity}
                  </p>
                  <p className="ml-auto">Qty: {card.quantity}</p>
                </CardFooter>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
