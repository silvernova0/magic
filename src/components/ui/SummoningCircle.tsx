'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface SummoningCircleProps {
    className?: string;
    size?: number;
    color?: string;
}

export function SummoningCircle({
    className,
    size = 200,
    color = "var(--primary)"
}: SummoningCircleProps) {
    // WUBRG colors
    const colors = [
        '#F0E68C', // White (Khaki/Gold)
        '#4682B4', // Blue (Steel Blue)
        '#2F4F4F', // Black (Dark Slate Gray)
        '#CD5C5C', // Red (Indian Red)
        '#228B22', // Green (Forest Green)
    ];

    return (
        <div
            className={cn("relative flex items-center justify-center", className)}
            style={{ width: size, height: size }}
        >
            {/* Outer rotating ring */}
            <motion.div
                className="absolute inset-0 rounded-full border-4 border-dashed border-purple-500/30"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            />

            {/* Inner counter-rotating ring */}
            <motion.div
                className="absolute inset-4 rounded-full border-2 border-dotted border-amber-500/30"
                animate={{ rotate: -360 }}
                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
            />

            {/* Pulsing core */}
            <motion.div
                className="absolute w-32 h-32 rounded-full bg-gradient-to-br from-purple-600/20 to-amber-600/20 blur-xl"
                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            />

            {/* Central rune */}
            <div className="relative z-10 text-4xl">✨</div>

            {/* Orbiting WUBRG Mana Symbols */}
            {/* Orbiting WUBRG Mana Symbols */}
            {colors.map((color, index) => {
                const symbols = ['☀', '💧', '💀', '🔥', '🌳'];
                return (
                    <motion.div
                        key={`orbit-${index}`}
                        className="absolute inset-0"
                        initial={{ rotate: (index * 360) / 5 }}
                        animate={{ rotate: ((index * 360) / 5) + 360 }}
                        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                    >
                        <div
                            className="absolute top-0 left-1/2 -translate-x-1/2 flex items-center justify-center w-6 h-6 rounded-full bg-slate-900 border border-white/20 shadow-[0_0_10px_currentColor]"
                            style={{ color: color, borderColor: color }}
                        >
                            <span className="text-xs font-bold">{symbols[index]}</span>
                        </div>
                    </motion.div>
                );
            })}

            {/* Loading text */}
            {/* Loading text removed to prevent overlap with parent component */}
        </div>
    );
}
