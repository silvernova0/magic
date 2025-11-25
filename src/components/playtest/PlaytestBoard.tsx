import { DndContext, DragEndEvent, DragOverlay, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { useState } from 'react';
import { PlaytestCard, Zone, GameState } from '@/types/playtest';
import { CardZone } from './CardZone';
import { DraggableCard } from './DraggableCard';
import { Button } from '@/components/ui/button';
import { RefreshCw, RotateCcw, Play } from 'lucide-react';

interface PlaytestBoardProps {
    gameState: GameState;
    onMoveCard: (instanceId: string, toZone: Zone) => void;
    onTapCard: (instanceId: string) => void;
    onDrawCard: () => void;
    onUntapAll: () => void;
    onShuffle: () => void;
}

export function PlaytestBoard({
    gameState,
    onMoveCard,
    onTapCard,
    onDrawCard,
    onUntapAll,
    onShuffle
}: PlaytestBoardProps) {
    const [activeId, setActiveId] = useState<string | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        })
    );

    const handleDragStart = (event: any) => {
        setActiveId(event.active.id);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveId(null);

        if (over && active.id !== over.id) {
            // If dropped on a zone
            const toZone = over.id as Zone;
            onMoveCard(active.id as string, toZone);
        }
    };

    const getCardsInZone = (zone: Zone) =>
        gameState.cards.filter(c => c.zone === zone);

    const activeCard = gameState.cards.find(c => c.instanceId === activeId);

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="flex flex-col h-full gap-4 p-4">
                {/* Top Row: Command Zone, Battlefield (Opponent/Global?), Exile, Graveyard */}
                <div className="flex h-1/4 gap-4">
                    <CardZone id="COMMAND_ZONE" title="Command Zone" className="w-48" orientation="vertical">
                        {getCardsInZone('COMMAND_ZONE').map(card => (
                            <DraggableCard key={card.instanceId} card={card} onClick={() => onTapCard(card.instanceId)} />
                        ))}
                    </CardZone>

                    <CardZone id="EXILE" title="Exile" className="w-32" orientation="vertical">
                        {getCardsInZone('EXILE').map(card => (
                            <DraggableCard key={card.instanceId} card={card} />
                        ))}
                    </CardZone>

                    <CardZone id="GRAVEYARD" title="Graveyard" className="w-32" orientation="vertical">
                        {getCardsInZone('GRAVEYARD').map(card => (
                            <DraggableCard key={card.instanceId} card={card} />
                        ))}
                    </CardZone>

                    <div className="flex-1 flex flex-col gap-2 items-end justify-start p-4 bg-black/20 rounded-xl border border-white/5">
                        <div className="text-right">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Life Total</div>
                            <div className="text-4xl font-bold text-primary">{gameState.life}</div>
                        </div>
                        <div className="text-right">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">Turn</div>
                            <div className="text-2xl font-bold">{gameState.turn}</div>
                        </div>

                        <div className="mt-auto flex gap-2">
                            <Button variant="outline" size="sm" onClick={onUntapAll}>
                                <RotateCcw className="w-4 h-4 mr-2" /> Untap All
                            </Button>
                            <Button variant="outline" size="sm" onClick={onShuffle}>
                                <RefreshCw className="w-4 h-4 mr-2" /> Shuffle Lib
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Middle: Battlefield */}
                <CardZone id="BATTLEFIELD" title="Battlefield" className="flex-1">
                    {getCardsInZone('BATTLEFIELD').map(card => (
                        <DraggableCard
                            key={card.instanceId}
                            card={card}
                            onClick={() => onTapCard(card.instanceId)}
                        />
                    ))}
                </CardZone>

                {/* Bottom: Hand & Library */}
                <div className="flex h-1/4 gap-4">
                    <CardZone id="LIBRARY" title={`Library (${getCardsInZone('LIBRARY').length})`} className="w-32 flex items-center justify-center bg-primary/5 cursor-pointer hover:bg-primary/10 transition-colors" orientation="vertical">
                        {/* Click library to draw */}
                        <div className="w-full h-full absolute inset-0 z-10" onClick={onDrawCard} />
                        <div className="w-24 h-32 bg-gradient-to-br from-primary/40 to-purple-900/40 rounded border-2 border-white/10 flex items-center justify-center shadow-xl">
                            <span className="font-serif font-bold text-white/50">Deck</span>
                        </div>
                    </CardZone>

                    <CardZone id="HAND" title={`Hand (${getCardsInZone('HAND').length})`} className="flex-1 border-primary/30 bg-black/40">
                        {getCardsInZone('HAND').map(card => (
                            <DraggableCard key={card.instanceId} card={card} className="-ml-12 first:ml-0 hover:z-50 hover:-translate-y-4 transition-transform" />
                        ))}
                    </CardZone>
                </div>
            </div>

            <DragOverlay>
                {activeCard ? (
                    <div className="opacity-80 rotate-3 scale-105">
                        <img
                            src={activeCard.imageUrl || ''}
                            alt={activeCard.name}
                            className="w-32 rounded-lg shadow-2xl"
                        />
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
}
