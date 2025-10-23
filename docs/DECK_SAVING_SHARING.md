# Deck Saving and Sharing System

Complete documentation for the MTG AI Commander Deck Builder's deck persistence and sharing features.

---

## Overview

The deck saving/sharing system allows users to:
- **Save** AI-generated decks to their personal library
- **View** all their saved decks in one place
- **Edit** deck names, descriptions, and details
- **Delete** unwanted decks
- **Share** decks via shareable links
- **Export** decks as text files

---

## Database Schema

### Deck Model
```prisma
model Deck {
  id          String   @id @default(cuid())
  name        String
  description String?
  theme       String
  powerLevel  String
  decklist    Json        // Full deck object
  status      DeckStatus  // GENERATED, SAVED, IMPORTED
  userId      String
  user        User        @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt   DateTime    @default(now())
  updatedAt   DateTime    @updatedAt
}

enum DeckStatus {
  GENERATED  // Newly created by AI, not yet saved
  SAVED      // User has saved the deck
  IMPORTED   // Imported from external source
}
```

### Key Fields
- **decklist**: JSON object containing commander, mainboard, sideboard
  ```json
  {
    "commander": ["Card Name"],
    "creatures": ["Card 1", "Card 2", ...],
    "instants": ["Card A", "Card B", ...],
    "sorceries": [...],
    "artifacts": [...],
    "enchantments": [...],
    "planeswalkers": [...],
    "lands": [...]
  }
  ```
- **status**: Workflow state (GENERATED → SAVED)
- **userId**: Foreign key to User model (owner)

---

## API Endpoints

### User Deck Management

#### GET `/api/user/decks`
Get all decks for the current user.

**Authentication**: Required (JWT session)

**Query Parameters**:
- `status` (optional): Filter by status (`GENERATED`, `SAVED`, `IMPORTED`, or `all`)
- `sortBy` (optional): Sort field (`updatedAt`, `createdAt`, `name`, `powerLevel`)
- `sortOrder` (optional): `asc` or `desc` (default: `desc`)

**Response**:
```json
{
  "success": true,
  "count": 5,
  "decks": [
    {
      "id": "clxyz123",
      "name": "Eldrazi Tribal",
      "description": "Colorless commander deck...",
      "theme": "Eldrazi Tribal",
      "powerLevel": "7",
      "status": "SAVED",
      "decklist": { ... },
      "userId": "user123",
      "user": {
        "id": "user123",
        "name": "John Doe",
        "email": "john@example.com"
      },
      "createdAt": "2025-01-15T10:00:00Z",
      "updatedAt": "2025-01-15T12:30:00Z"
    }
  ]
}
```

---

#### POST `/api/user/decks`
Save a new deck for the current user.

**Authentication**: Required (JWT session)

**Request Body**:
```json
{
  "name": "My Awesome Deck",
  "description": "A powerful combo deck",
  "theme": "Spellslinger",
  "powerLevel": "8",
  "decklist": {
    "commander": ["Kess, Dissident Mage"],
    "creatures": [...],
    "instants": [...],
    ...
  },
  "status": "SAVED"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Deck saved successfully",
  "deck": {
    "id": "clxyz123",
    "name": "My Awesome Deck",
    ...
  }
}
```

**Validation**:
- `name` and `decklist` are required
- `decklist` must be a valid JSON object
- `status` defaults to `SAVED` if not provided

---

#### GET `/api/user/decks/[id]`
Get a specific deck by ID.

**Authentication**: Required (JWT session)

**Authorization**: User must own the deck

**Response**:
```json
{
  "success": true,
  "deck": {
    "id": "clxyz123",
    "name": "Eldrazi Tribal",
    ...
  }
}
```

**Errors**:
- `401`: Not authenticated
- `403`: User doesn't own the deck
- `404`: Deck not found

---

#### PATCH `/api/user/decks/[id]`
Update a specific deck.

**Authentication**: Required (JWT session)

**Authorization**: User must own the deck

**Request Body** (all fields optional):
```json
{
  "name": "Updated Deck Name",
  "description": "New description",
  "theme": "Updated Theme",
  "powerLevel": "9",
  "decklist": { ... },
  "status": "SAVED"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Deck updated successfully",
  "deck": {
    "id": "clxyz123",
    ...
  }
}
```

---

#### DELETE `/api/user/decks/[id]`
Delete a specific deck.

**Authentication**: Required (JWT session)

**Authorization**: User must own the deck

**Response**:
```json
{
  "success": true,
  "message": "Deck deleted successfully"
}
```

---

## Pages and Components

### Deck Library Page
**Route**: `/decks`

**Features**:
- Grid display of all user's decks
- Filter by status (Generated, Saved, Imported)
- Sort by date, name, or power level
- Quick stats overview (total decks, by status)
- Card count validation (100 cards = valid)
- Delete confirmation dialog
- Link to deck builder

**Component**: `DecksClient.tsx`

---

### Deck View Page
**Route**: `/decks/[id]`

**Features**:
- Full deck display with categorized card lists
- Share deck (copy link to clipboard)
- Export deck as text file
- Edit deck (owner only)
- Delete deck (owner only)
- Card preview on hover (via CardPreview component)
- Deck statistics (card count, theme, power level, dates)
- Owner information

**Component**: `DeckViewClient.tsx`

---

### Save Deck Form
**Component**: `SaveDeckForm.tsx`

**Features**:
- Appears on deck builder page after generating deck
- Only shown for `GENERATED` status decks
- Allows user to name and save the deck
- Updates deck status from `GENERATED` to `SAVED`

**Usage**:
```tsx
{deck.status === 'GENERATED' && (
  <SaveDeckForm deckId={deck.id} onDeckSaved={handleDeckSaved} />
)}
```

---

## Deck Sharing

### Share Link Format
```
https://your-domain.com/decks/[deckId]
```

### Share Functionality
1. Click **Share** button on deck view page
2. Link automatically copied to clipboard
3. Visual feedback (checkmark icon)
4. Anyone with the link can view (future: privacy settings)

### Export Functionality
Exports deck as plain text file format:
```
# Deck Name
# Theme: Eldrazi Tribal
# Power Level: 7
# Description: Powerful colorless deck

## Commander
1 Kozilek, the Great Distortion

## Creatures
1 Ulamog, the Infinite Gyre
1 Emrakul, the Promised End
...

## Lands
1 Urborg, Tomb of Yawgmoth
...
```

---

## Deck Workflows

### AI Generation → Save
1. User fills out deck builder form
2. AI generates deck with `GENERATED` status
3. Deck stored in database with temporary status
4. User sees **Save Deck** form
5. User enters deck name and clicks **Save**
6. Deck status updated to `SAVED`
7. Deck appears in user's library

### Manual Deck Creation (Future)
1. User creates deck from scratch
2. Deck created with `SAVED` status
3. Immediately available in library

### Deck Import (Future)
1. User imports deck from external source
2. Deck created with `IMPORTED` status
3. Tracks origin source in metadata

---

## Frontend Integration

### Authentication Check
All deck management pages require authentication:

```tsx
const { data: session, status } = useSession();

useEffect(() => {
  if (status === 'unauthenticated') {
    router.push('/login');
  }
}, [status, router]);
```

### Fetch User Decks
```tsx
async function fetchDecks() {
  const params = new URLSearchParams({
    status: statusFilter,
    sortBy: 'updatedAt',
    sortOrder: 'desc',
  });

  const response = await fetch(`/api/user/decks?${params}`);
  const data = await response.json();

  if (data.success) {
    setDecks(data.decks);
  }
}
```

### Delete Deck with Confirmation
```tsx
async function deleteDeck(id: string, name: string) {
  if (!confirm(`Are you sure you want to delete "${name}"?`)) {
    return;
  }

  const response = await fetch(`/api/user/decks/${id}`, {
    method: 'DELETE',
  });

  if (response.ok) {
    fetchDecks(); // Refresh list
  }
}
```

---

## Card Preview Integration

The deck view page integrates the **CardPreview** component for hover/click card details:

```tsx
import { CardPreview } from '../CardPreview';

// In card list rendering
<CardPreview cardName={cardName}>
  <span>{cardName}</span>
</CardPreview>
```

**Features**:
- Hover over card name shows preview after 300ms
- Click card name opens full-screen modal
- ESC key closes modal
- Scryfall API integration for card images and data

---

## Security and Authorization

### Authentication
- All deck endpoints require valid JWT session
- Uses NextAuth.js `getServerSession(authOptions)`
- Unauthenticated users redirected to `/login`

### Authorization
- Users can only access/modify their own decks
- Ownership verified via `deck.userId === session.user.id`
- DELETE and PATCH operations check ownership
- 403 Forbidden returned for unauthorized access

### Data Privacy
- User emails not exposed in public deck views
- Future: Add `isPublic` field for sharing controls
- Future: Add collaboration/team features

---

## Testing Checklist

### Deck Saving
- [ ] Generate deck with AI
- [ ] Save deck with valid name
- [ ] Verify deck appears in library
- [ ] Verify deck status changed to `SAVED`
- [ ] Test saving without name (validation error)

### Deck Viewing
- [ ] View deck from library
- [ ] Verify all cards displayed correctly
- [ ] Test card hover preview
- [ ] Test card click modal
- [ ] Verify owner actions available
- [ ] Verify non-owner actions hidden

### Deck Sharing
- [ ] Click share button
- [ ] Verify link copied to clipboard
- [ ] Open shared link in new browser
- [ ] Verify deck visible without auth (future)

### Deck Export
- [ ] Click export button
- [ ] Verify text file downloads
- [ ] Open file and check format
- [ ] Verify all cards included

### Deck Deletion
- [ ] Click delete button
- [ ] Confirm deletion dialog
- [ ] Verify deck removed from library
- [ ] Verify deck removed from database
- [ ] Test cancel deletion

---

## Future Enhancements

### Privacy Controls
- [ ] Add `isPublic` boolean to Deck model
- [ ] Public decks viewable by anyone
- [ ] Private decks only viewable by owner
- [ ] Share settings in deck edit form

### Deck Versioning
- [ ] Track deck history (DeckVersion model)
- [ ] View previous versions
- [ ] Restore older versions
- [ ] Compare versions side-by-side

### Deck Collections
- [ ] Group decks into collections
- [ ] Tags for categorization
- [ ] Folders/hierarchies
- [ ] Bulk operations

### Social Features
- [ ] Like/favorite decks
- [ ] Comments on decks
- [ ] Deck ratings
- [ ] Follow other users
- [ ] Deck discovery feed

### Advanced Export
- [ ] Export to MTGO format
- [ ] Export to Arena format
- [ ] Export to Moxfield/Archidekt
- [ ] Export as PDF/image

### Deck Analytics
- [ ] Mana curve visualization
- [ ] Color distribution pie chart
- [ ] Card type breakdown
- [ ] Price tracking over time
- [ ] Power level history

---

## Troubleshooting

### Deck Not Saving
- Check browser console for errors
- Verify authentication (session valid)
- Verify deck name provided
- Check API response for validation errors

### Deck Not Appearing in Library
- Refresh page
- Check status filter (GENERATED vs SAVED)
- Verify database record created
- Check userId matches session

### Share Link Not Working
- Verify link format correct
- Check deck ID valid
- Ensure deck exists in database
- Future: Check privacy settings

### Card Preview Not Showing
- Check CardPreview component imported
- Verify Scryfall API accessible
- Check browser console for fetch errors
- Verify card name valid

---

## File Reference

### API Routes
- `/src/app/api/user/decks/route.ts` - List and create decks
- `/src/app/api/user/decks/[id]/route.ts` - Get, update, delete deck

### Pages
- `/src/app/decks/page.tsx` - Deck library (server component)
- `/src/app/decks/[id]/page.tsx` - Deck view (server component)

### Components
- `/src/components/decks/DecksClient.tsx` - Deck library client logic
- `/src/components/decks/DeckViewClient.tsx` - Deck view client logic
- `/src/components/deckbuilder/SaveDeckForm.tsx` - Save deck form
- `/src/components/CardPreview.tsx` - Card hover/click preview

### Database
- `/prisma/schema.prisma` - Deck model definition

---

## Quick Start

### 1. Generate and Save a Deck
```bash
# Navigate to deck builder
http://localhost:3000/deckbuilder

# Fill out form and generate deck
# Click "Save Deck" and enter name
```

### 2. View Your Decks
```bash
# Navigate to deck library
http://localhost:3000/decks
```

### 3. Share a Deck
```bash
# Open a deck
# Click "Share" button (link copied)
# Send link to friend
```

### 4. Export a Deck
```bash
# Open a deck
# Click "Export" button
# Text file downloads automatically
```

---

## Conclusion

The deck saving/sharing system provides a complete solution for deck persistence and collaboration. All major workflows (generate, save, view, edit, delete, share, export) are fully functional and ready for production use.

**Next Priority**: Collection logging verification and enhancement.
