import { useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { PlaytestCard, Zone, GameState } from '@/types/playtest';

// Helper to shuffle array
const shuffle = <T>(array: T[]): T[] => {
    const newArray = [...array];
    for (let i = newArray.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
    }
    return newArray;
};

export function usePlaytestState(initialDeck: any) {
    const [gameState, setGameState] = useState<GameState>({
        cards: [],
        life: 40,
        turn: 1,
        poison: 0,
        commanderDamage: 0,
    });

    const [history, setHistory] = useState<GameState[]>([]);
    const [historyIndex, setHistoryIndex] = useState(-1);

    // Initialize Game
    const initializeGame = useCallback(() => {
        if (!initialDeck) return;

        const cards: PlaytestCard[] = [];

        // Process Main Deck
        // The decklist is likely stored as JSON in the database. 
        // We need to parse it. Assuming it's an array of card objects or similar.
        // For now, let's assume the passed `initialDeck` has a `cards` array or we parse the `decklist` JSON.

        // NOTE: The `deck` object from Prisma has `decklist` as Json. 
        // We need to handle the specific structure.
        // Let's assume the caller passes a normalized list of cards with quantities.

        // We'll rely on the caller to pass a flat list of card data for now, 
        // or we can parse it here if we know the structure.
        // Let's assume `initialDeck` is the Prisma Deck object.

        // Actually, to keep this hook pure, let's assume `initialDeck` is an array of card data objects 
        // that includes quantity.

        // ... logic to populate cards ...
        // This part depends heavily on how we pass data to the hook.
        // I'll implement a `setupGame` function that takes the processed card list.
    }, [initialDeck]);

    const setupGame = useCallback((deckCards: any[], commander?: any) => {
        const newCards: PlaytestCard[] = [];

        // Add Commander
        if (commander) {
            newCards.push({
                id: commander.id,
                instanceId: uuidv4(),
                name: commander.name,
                manaCost: commander.manaCost,
                typeLine: commander.type_line || commander.typeLine,
                imageUrl: commander.imageUrl || commander.image_uris?.normal,
                zone: 'COMMAND_ZONE',
                isTapped: false,
                isFlipped: false,
                counters: 0,
            });
        }

        // Add Deck Cards
        deckCards.forEach(card => {
            const quantity = card.quantity || 1;
            for (let i = 0; i < quantity; i++) {
                newCards.push({
                    id: card.id,
                    instanceId: uuidv4(),
                    name: card.name,
                    manaCost: card.manaCost,
                    typeLine: card.type_line || card.typeLine,
                    imageUrl: card.imageUrl || card.image_uris?.normal,
                    zone: 'LIBRARY', // Start in library
                    isTapped: false,
                    isFlipped: false,
                    counters: 0,
                });
            }
        });

        // Shuffle Library
        const shuffledCards = newCards.map(card =>
            card.zone === 'LIBRARY' ? card : card
        );

        // We need to shuffle only the library cards.
        // Actually, let's just shuffle the array of library cards and re-assign.
        const libraryCards = newCards.filter(c => c.zone === 'LIBRARY');
        const otherCards = newCards.filter(c => c.zone !== 'LIBRARY');
        const shuffledLibrary = shuffle(libraryCards);

        const finalCards = [...otherCards, ...shuffledLibrary];

        // Draw 7
        const hand = finalCards.filter(c => c.zone === 'LIBRARY').slice(0, 7);
        const library = finalCards.filter(c => c.zone === 'LIBRARY').slice(7);

        hand.forEach(c => c.zone = 'HAND');

        // Reconstruct state
        const startingState = {
            cards: [...otherCards, ...hand, ...library],
            life: 40,
            turn: 1,
            poison: 0,
            commanderDamage: 0,
        };

        setGameState(startingState);
        setHistory([startingState]);
        setHistoryIndex(0);
    }, []);

    // Actions
    const drawCard = useCallback(() => {
        setGameState(prev => {
            const library = prev.cards.filter(c => c.zone === 'LIBRARY');
            if (library.length === 0) return prev;

            const cardToDraw = library[0];
            const newCards = prev.cards.map(c =>
                c.instanceId === cardToDraw.instanceId ? { ...c, zone: 'HAND' as Zone } : c
            );

            return { ...prev, cards: newCards };
        });
    }, []);

    const moveCard = useCallback((instanceId: string, toZone: Zone) => {
        setGameState(prev => {
            const newCards = prev.cards.map(c =>
                c.instanceId === instanceId ? { ...c, zone: toZone, isTapped: false } : c
            );
            return { ...prev, cards: newCards };
        });
    }, []);

    const toggleTap = useCallback((instanceId: string) => {
        setGameState(prev => {
            const newCards = prev.cards.map(c =>
                c.instanceId === instanceId ? { ...c, isTapped: !c.isTapped } : c
            );
            return { ...prev, cards: newCards };
        });
    }, []);

    const untapAll = useCallback(() => {
        setGameState(prev => ({
            ...prev,
            cards: prev.cards.map(c =>
                c.zone === 'BATTLEFIELD' ? { ...c, isTapped: false } : c
            ),
            turn: prev.turn + 1
        }));
    }, []);

    const shuffleLibrary = useCallback(() => {
        setGameState(prev => {
            const library = prev.cards.filter(c => c.zone === 'LIBRARY');
            const others = prev.cards.filter(c => c.zone !== 'LIBRARY');
            const shuffled = shuffle(library);
            return { ...prev, cards: [...others, ...shuffled] };
        });
    }, []);

    return {
        gameState,
        setupGame,
        drawCard,
        moveCard,
        toggleTap,
        untapAll,
        shuffleLibrary,
    };
}
