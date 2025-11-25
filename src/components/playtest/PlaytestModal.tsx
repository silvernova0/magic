import { useEffect } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PlaytestBoard } from './PlaytestBoard';
import { usePlaytestState } from '@/hooks/usePlaytestState';
import { motion, AnimatePresence } from 'framer-motion';

interface PlaytestModalProps {
    isOpen: boolean;
    onClose: () => void;
    deck: any; // Prisma deck object
}

export function PlaytestModal({ isOpen, onClose, deck }: PlaytestModalProps) {
    const {
        gameState,
        setupGame,
        drawCard,
        moveCard,
        toggleTap,
        untapAll,
        shuffleLibrary
    } = usePlaytestState(deck);

    // Initialize game when modal opens
    useEffect(() => {
        if (isOpen && deck) {
            // We need to process the deck data.
            // Assuming deck.cards (UserCard[]) or deck.decklist (JSON)
            // For now, let's try to use the decklist JSON if available, or fallback to something else.
            // Actually, the `getDeck` in page.tsx includes `user` but not `cards` relation if it's just the Deck model.
            // But `Deck` model has `decklist` JSON.

            // Let's parse the decklist JSON.
            let cards = [];
            try {
                if (typeof deck.decklist === 'string') {
                    cards = JSON.parse(deck.decklist);
                } else {
                    cards = deck.decklist;
                }
            } catch (e) {
                console.error("Failed to parse decklist", e);
            }

            // We also need the commander.
            // The commander is stored in `deck.description` or `deck.name`? No.
            // The `Deck` model has `commander` field? No.
            // Wait, looking at schema.prisma:
            // model Deck { ... decklist Json ... }
            // It doesn't have explicit commander field. It's likely inside the decklist or metadata.
            // Let's assume the first card marked as commander in the list, or we just load the decklist.

            setupGame(cards);
        }
    }, [isOpen, deck, setupGame]);

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 bg-background/95 backdrop-blur-sm flex flex-col"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/20">
                    <div className="flex items-center gap-4">
                        <h2 className="text-xl font-serif font-bold text-gradient-mystic">Playtesting: {deck.name}</h2>
                        <span className="text-xs px-2 py-1 bg-primary/20 rounded text-primary">Goldfish Mode</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" onClick={onClose}>
                            <X className="w-5 h-5" />
                        </Button>
                    </div>
                </div>

                {/* Game Board */}
                <div className="flex-1 overflow-hidden bg-[url('/bg-pattern.png')] bg-cover bg-center">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" />
                    <div className="relative z-10 h-full">
                        <PlaytestBoard
                            gameState={gameState}
                            onMoveCard={moveCard}
                            onTapCard={toggleTap}
                            onDrawCard={drawCard}
                            onUntapAll={untapAll}
                            onShuffle={shuffleLibrary}
                        />
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
