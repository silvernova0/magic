import { prisma } from "@/lib/prisma";
import { getCurrentUser } from "@/lib/user";
import { redirect } from "next/navigation";
import CollectionClient from "@/components/collection/CollectionClient";

export default async function CollectionPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect('/login');
  }
  
  const cards = await prisma.userCard.findMany({ 
    where: { userId: user.id },
    orderBy: { createdAt: 'desc' }
  });

  return <CollectionClient initialCards={cards as any} />;
}
