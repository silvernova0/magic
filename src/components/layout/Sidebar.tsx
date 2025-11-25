'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserNav from '@/components/UserNav';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const navItems = [
    { href: '/', label: 'Home', icon: '🏠' },
    { href: '/deckbuilder', label: 'Deck Builder', icon: '✨' },
    { href: '/decks', label: 'My Decks', icon: '🎴' },
    { href: '/collection', label: 'Collection', icon: '📚' },
    { href: '/import', label: 'Import / Export', icon: '📥' },
    { href: '/commander', label: 'Commander Search', icon: '🔍' },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-64 h-screen sticky top-0 hidden md:flex flex-col border-r border-white/10 bg-black/20 backdrop-blur-xl shadow-2xl z-40">
            {/* Mystic Background Effect */}
            <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-secondary/5 pointer-events-none" />

            <div className="p-6 relative">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="mb-2"
                >
                    <h2 className="text-2xl font-serif font-bold text-purple-300 dark:text-purple-300 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]">
                        JankBuild
                    </h2>
                    <p className="text-xs text-muted-foreground/80 tracking-wider uppercase">Winning Through Obscurity</p>
                </motion.div>
            </div>

            <nav className="flex-1 px-4 relative">
                <ul className="space-y-2">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <li key={item.href}>
                                <Link
                                    href={item.href}
                                    className={cn(
                                        "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 group relative overflow-hidden",
                                        isActive
                                            ? "bg-primary/20 text-primary-foreground shadow-[0_0_15px_-5px_var(--primary)] border border-primary/30"
                                            : "hover:bg-white/5 hover:text-primary text-muted-foreground border border-transparent"
                                    )}
                                >
                                    {isActive && (
                                        <motion.div
                                            layoutId="activeNav"
                                            className="absolute inset-0 bg-primary/10"
                                            initial={false}
                                            transition={{ type: "spring", stiffness: 500, damping: 30 }}
                                        />
                                    )}
                                    <span className="text-lg group-hover:scale-110 transition-transform duration-300">{item.icon}</span>
                                    <span className={cn("font-medium relative z-10", isActive ? "font-bold" : "")}>
                                        {item.label}
                                    </span>
                                    {isActive && (
                                        <motion.div
                                            className="absolute right-2 w-1.5 h-1.5 rounded-full bg-primary blur-[1px]"
                                            layoutId="activeDot"
                                        />
                                    )}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            <div className="p-4 border-t border-white/10 relative bg-black/20">
                <UserNav />
            </div>
        </aside>
    );
}
