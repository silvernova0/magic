# Card Preview Component Usage

## Basic Usage

### In React Components

```tsx
import { CardPreview, CardLink } from '@/components/CardPreview';

// Simple card link with hover preview
<CardLink cardName="Sol Ring" />

// Custom wrapper
<CardPreview cardName="Lightning Bolt">
  <span className="font-bold">Lightning Bolt</span>
</CardPreview>

// Disable hover preview (only click to expand)
<CardPreview cardName="Counterspell" showOnHover={false}>
  Counterspell
</CardPreview>
```

### In Generated Deck Lists

```tsx
function DeckList({ decklist }: { decklist: string[] }) {
  return (
    <ul>
      {decklist.map((card, index) => (
        <li key={index}>
          <CardLink cardName={card} />
        </li>
      ))}
    </ul>
  );
}
```

### In Card Search Results

```tsx
function SearchResults({ cards }: { cards: Card[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div key={card.id} className="p-4 border rounded">
          <CardPreview cardName={card.name}>
            <h3 className="text-lg font-bold">{card.name}</h3>
          </CardPreview>
          <p className="text-sm text-gray-600">{card.type}</p>
        </div>
      ))}
    </div>
  );
}
```

## Features

### Hover Preview
- **Delay**: 300ms before showing (prevents flickering on quick mouse movements)
- **Auto-fetch**: Card data fetched from Scryfall on first hover
- **Image Display**: Shows high-quality card image if available
- **Text Fallback**: Shows formatted text version if image fails to load

### Click to Expand
- **Full Screen Modal**: Click any card preview to see larger version
- **Keyboard Support**: Press ESC to close modal
- **External Link**: Link to view card on Scryfall
- **Click Outside**: Click backdrop to close

### Card Data Display

**With Image:**
- High-resolution card image (488x680px in expanded view)
- Rounded corners and shadow

**Text Fallback:**
- Card name and mana cost
- Type line
- Oracle text (rules text)
- Power/Toughness or Loyalty
- Rarity
- Set name
- Current price (if available)

## Styling

### Hover Indicator
Cards have a dotted underline and change color on hover:
```css
border-b border-dotted border-current
hover:text-blue-500
```

### Custom Styling
Pass custom classes via `className`:
```tsx
<CardPreview cardName="Black Lotus" className="text-yellow-400">
  Black Lotus
</CardPreview>
```

## Performance

### Caching
- Card data is cached in component state
- Only fetches once per card per session
- Image loading uses Next.js Image component for optimization

### Rate Limiting
- Scryfall API: ~10 requests per second allowed
- Component delays hover by 300ms to reduce unnecessary fetches
- Consider implementing global cache for frequently viewed cards

## Advanced Usage

### With TypeScript
```tsx
import { CardPreview } from '@/components/CardPreview';

interface DeckCardProps {
  cardName: string;
  quantity: number;
}

const DeckCard: React.FC<DeckCardProps> = ({ cardName, quantity }) => (
  <div className="flex items-center gap-2">
    <span className="text-gray-500">{quantity}x</span>
    <CardPreview cardName={cardName}>
      <span className="font-medium">{cardName}</span>
    </CardPreview>
  </div>
);
```

### In Deck Builder
```tsx
function GeneratedDeck({ mainboard, sideboard }: DeckProps) {
  return (
    <div className="grid grid-cols-2 gap-8">
      <div>
        <h3 className="text-xl font-bold mb-4">Mainboard</h3>
        <ul className="space-y-1">
          {mainboard.map((card, i) => (
            <li key={i}>
              <CardLink cardName={card} />
            </li>
          ))}
        </ul>
      </div>
      
      <div>
        <h3 className="text-xl font-bold mb-4">Sideboard</h3>
        <ul className="space-y-1">
          {sideboard.map((card, i) => (
            <li key={i}>
              <CardLink cardName={card} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

### In Collection Management
```tsx
function CollectionCard({ card }: { card: UserCard }) {
  return (
    <div className="border rounded-lg p-4">
      <CardPreview cardName={card.name}>
        <div className="flex items-center justify-between">
          <h4 className="font-bold">{card.name}</h4>
          <span className="text-sm text-gray-500">{card.quantity}x</span>
        </div>
      </CardPreview>
      <p className="text-sm text-gray-600">{card.setName}</p>
      <p className="text-xs text-gray-500">{card.rarity}</p>
    </div>
  );
}
```

## Keyboard Shortcuts

- **ESC**: Close expanded card view
- **Click outside**: Close modal
- **Click card**: Expand to full view

## Accessibility

- Proper ARIA labels on close button
- Keyboard navigation support
- Screen reader friendly
- Focus management in modal

## Future Enhancements

- [ ] Add mana symbol icons instead of text
- [ ] Cache card data globally (Redis/localStorage)
- [ ] Support for double-faced cards
- [ ] Add price history chart
- [ ] Show related cards / similar effects
- [ ] Add to deck / collection buttons in preview
- [ ] Support for localized card names
- [ ] Offline support with service worker
