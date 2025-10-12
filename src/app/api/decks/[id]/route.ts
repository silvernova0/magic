import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

// export async function PATCH(
//   req: NextRequest,
//   context: { params: { id: string } }
// ) {
//   try {
//     const { name } = await req.json();
//     const { id: deckId } = await Promise.resolve(context.params);

//     if (!name) {
//       return NextResponse.json({ error: 'Deck name is required' }, { status: 400 });
//     }

//     const updatedDeck = await prisma.deck.update({
//       where: { id: deckId },
//       data: {
//         name,
//         status: 'SAVED',
//       },
//     });

//     return NextResponse.json(updatedDeck);
//   } catch (error) {
//     console.error(`Error updating deck ${context.params.id}:`, error);
//     return NextResponse.json({ error: 'Failed to save deck' }, { status: 500 });
//   }
// }