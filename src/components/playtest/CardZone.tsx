import { useDroppable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';
import { Zone } from '@/types/playtest';

interface CardZoneProps {
    id: Zone;
    title?: string;
    className?: string;
    children: React.ReactNode;
    orientation?: 'horizontal' | 'vertical';
}

export function CardZone({ id, title, className, children, orientation = 'horizontal' }: CardZoneProps) {
    const { setNodeRef, isOver } = useDroppable({
        id: id,
    });

    return (
        <div
            ref={setNodeRef}
            className={cn(
                "relative rounded-xl border-2 border-dashed transition-colors duration-200",
                isOver ? "border-primary bg-primary/10" : "border-white/10 bg-black/20",
                className
            )}
        >
            {title && (
                <div className="absolute -top-3 left-4 px-2 bg-background text-xs font-bold text-muted-foreground uppercase tracking-wider border border-white/10 rounded">
                    {title}
                </div>
            )}

            <div className={cn(
                "p-4 w-full h-full flex gap-2 overflow-auto",
                orientation === 'horizontal' ? "flex-row flex-wrap items-start content-start" : "flex-col items-center"
            )}>
                {children}
            </div>
        </div>
    );
}
