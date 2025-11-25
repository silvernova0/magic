
import React from 'react';
import {
    calculateManaCurve,
    calculateTypeDistribution,
    calculateColorStats,
    calculateAverageCmc
} from '@/lib/deck-utils';
import { Card } from '@/components/ui/card';

interface DeckStatsProps {
    decklist: any;
}

export function DeckStats({ decklist }: DeckStatsProps) {
    const manaCurve = calculateManaCurve(decklist);
    const typeDistribution = calculateTypeDistribution(decklist);
    const colorStats = calculateColorStats(decklist);
    const avgCmc = calculateAverageCmc(decklist);

    const maxCurveHeight = Math.max(...manaCurve, 1);
    const totalCards = Object.values(typeDistribution).reduce((a, b) => a + b, 0);
    const totalPips = Object.values(colorStats).reduce((a, b) => a + b, 0);

    return (
        <div className="space-y-6 p-4 bg-black/20 rounded-xl border border-white/10 backdrop-blur-sm">
            <h3 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Deck Statistics
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Mana Curve */}
                <div className="space-y-2">
                    <div className="flex justify-between items-end">
                        <h4 className="text-sm font-medium text-gray-300">Mana Curve</h4>
                        <span className="text-xs text-gray-500">Avg CMC: {avgCmc}</span>
                    </div>
                    <div className="h-40 flex items-end gap-2 pt-4 pb-2">
                        {manaCurve.map((count, cmc) => (
                            <div key={cmc} className="flex-1 flex flex-col items-center gap-1 group">
                                <div className="relative w-full flex items-end h-full">
                                    <div
                                        className="w-full bg-indigo-500/50 hover:bg-indigo-400/70 rounded-t transition-all duration-300 group-hover:shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                                        style={{ height: `${(count / maxCurveHeight) * 100}%` }}
                                    >
                                        <div className="opacity-0 group-hover:opacity-100 absolute -top-6 left-1/2 -translate-x-1/2 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded pointer-events-none transition-opacity">
                                            {count}
                                        </div>
                                    </div>
                                </div>
                                <span className="text-[10px] text-gray-400">{cmc === 8 ? '8+' : cmc}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Type Distribution */}
                <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-300">Card Types</h4>
                    <div className="space-y-1.5">
                        {Object.entries(typeDistribution).map(([type, count]) => {
                            if (count === 0) return null;
                            const percentage = Math.round((count / totalCards) * 100);
                            return (
                                <div key={type} className="flex items-center gap-2 text-xs">
                                    <span className="w-20 text-gray-400">{type}</span>
                                    <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-emerald-500/50 rounded-full"
                                            style={{ width: `${percentage}%` }}
                                        />
                                    </div>
                                    <span className="w-8 text-right text-gray-500">{count}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Color Distribution */}
            <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-300">Color Distribution (Pips)</h4>
                <div className="flex h-3 rounded-full overflow-hidden">
                    {Object.entries(colorStats).map(([color, count]) => {
                        if (count === 0) return null;
                        const percentage = (count / totalPips) * 100;
                        const colorClass = {
                            W: 'bg-yellow-100',
                            U: 'bg-blue-500',
                            B: 'bg-gray-800',
                            R: 'bg-red-500',
                            G: 'bg-green-500',
                            C: 'bg-gray-400'
                        }[color] || 'bg-gray-500';

                        return (
                            <div
                                key={color}
                                className={`${colorClass} h-full transition-all hover:brightness-110`}
                                style={{ width: `${percentage}%` }}
                                title={`${color}: ${count} (${Math.round(percentage)}%)`}
                            />
                        );
                    })}
                </div>
                <div className="flex gap-4 justify-center text-xs text-gray-400">
                    {Object.entries(colorStats).map(([color, count]) => {
                        if (count === 0) return null;
                        return (
                            <div key={color} className="flex items-center gap-1">
                                <div className={`w-2 h-2 rounded-full ${{
                                    W: 'bg-yellow-100',
                                    U: 'bg-blue-500',
                                    B: 'bg-gray-800',
                                    R: 'bg-red-500',
                                    G: 'bg-green-500',
                                    C: 'bg-gray-400'
                                }[color]}`} />
                                <span>{Math.round((count / totalPips) * 100)}%</span>
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    );
}
