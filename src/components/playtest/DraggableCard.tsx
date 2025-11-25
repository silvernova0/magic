import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { PlaytestCard } from '@/types/playtest';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface DraggableCardProps {
    card: PlaytestCard;
    className?: string;
    onClick?: () => void;
}

export function DraggableCard({ card, className, onClick }: DraggableCardProps) {
    const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
        id: card.instanceId,
        data: card,
    });

    const style = {
        transform: CSS.Translate.toString(transform),
        zIndex: isDragging ? 100 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...listeners}
            {...attributes}
            className={cn("relative group touch-none", className)}
            onClick={onClick}
        >
            <motion.div
                className={cn(
                    "relative w-32 aspect-[2.5/3.5] rounded-lg shadow-md transition-all duration-200",
                    "bg-card border border-border overflow-hidden",
                    card.isTapped && "rotate-90",
                    isDragging && "scale-110 shadow-2xl ring-2 ring-primary z-50 cursor-grabbing",
                    !isDragging && "cursor-grab hover:scale-105 hover:shadow-lg hover:border-primary/50"
                )}
                layoutId={card.instanceId}
            >
                {card.imageUrl ? (
                    <img
                        src={card.imageUrl}
                        alt={card.name}
                        className="w-full h-full object-cover pointer-events-none"
                    />
                ) : (
                    <div className="p-2 flex flex-col h-full justify-between bg-gradient-to-br from-gray-800 to-gray-900">
                        <span className="text-xs font-bold text-white leading-tight">{card.name}</span>
                        <span className="text-[10px] text-gray-400">{card.typeLine}</span>
                        <span className="text-xs font-mono text-white self-end">{card.manaCost}</span>
                    </div>
                )}

                {/* Tapped Overlay */}
                {card.isTapped && (
                    <div className="absolute inset-0 bg-black/20 pointer-events-none" />
                )}
            </motion.div>
        </div>
    );
}
