# Database Models Reference

## User Model
```prisma
model User {
  id            String    @id @default(cuid())
  name          String?
  email         String?   @unique
  emailVerified DateTime?
  image         String?
  accounts      Account[]
  sessions      Session[]
  decks         Deck[]
  cards         UserCard[]
}
```

## UserCard Model (Per-User Card Collection)
```prisma
model UserCard {
  id         String   @id @default(cuid())
  name       String
  manaCost   String
  cmc        Float
  colors     String   // Comma-separated color identifiers
  type_line  String
  oracleText String?
  power      String?
  toughness  String?
  setName    String
  rarity     String
  imageUrl   String?
  quantity   Int
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
  user       User     @relation(fields: [userId], references: [id])
  userId     String
}
```

## Deck Model
```prisma
model Deck {
  id          String     @id @default(cuid())
  name        String
  description String?
  theme       String
  powerLevel  String
  decklist    Json       // Stored as JSON array of cards
  status      DeckStatus @default(GENERATED)
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt
  user        User       @relation(fields: [userId], references: [id])
  userId      String
}

enum DeckStatus {
  GENERATED  // AI-generated, not yet saved
  SAVED      // User has saved this deck
}
```

## Common Queries

### Get Current User's Cards
```typescript
const cards = await prisma.userCard.findMany({
  where: { userId: user.id }
});
```

### Get Current User's Decks
```typescript
const decks = await prisma.deck.findMany({
  where: { userId: user.id },
  orderBy: { updatedAt: 'desc' }
});
```

### Add Card to User's Collection
```typescript
await prisma.userCard.create({
  data: {
    name: "Lightning Bolt",
    manaCost: "{R}",
    cmc: 1,
    colors: "R",
    type_line: "Instant",
    oracleText: "Lightning Bolt deals 3 damage to any target.",
    setName: "M11",
    rarity: "common",
    quantity: 4,
    userId: user.id
  }
});
```

### Create a Deck for User
```typescript
await prisma.deck.create({
  data: {
    name: "Mono-Red Aggro",
    description: "Fast burn deck",
    theme: "Aggro",
    powerLevel: "7",
    decklist: JSON.stringify(cardList),
    status: "SAVED",
    userId: user.id
  }
});
```

## Helper Functions

### Get Current Authenticated User
```typescript
import { getCurrentUser } from '@/lib/user';

const user = await getCurrentUser();
if (!user) {
  throw new Error('Not authenticated');
}
```

### Prisma Client Singleton
```typescript
import { prisma } from '@/lib/prisma';

// Use prisma throughout your app
const cards = await prisma.userCard.findMany();
```
