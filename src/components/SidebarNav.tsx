'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Wand2,
  Layers,
  Library,
  Compass,
  Upload,
  Shield,
  Cpu,
  Menu,
  X,
  Sparkles,
} from 'lucide-react';
import { APP_VERSION } from '@/lib/constants';
import UserNav from './UserNav';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/deckbuilder', label: 'AI Deck Builder', icon: Wand2 },
  { href: '/decks', label: 'My Decks', icon: Layers },
  { href: '/collection', label: 'Card Collection', icon: Library },
  { href: '/commander', label: 'Commander Search', icon: Compass },
  { href: '/import', label: 'Import / Export', icon: Upload },
  { href: '/admin', label: 'Scrapers & Admin', icon: Shield },
];

export default function SidebarNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const renderNavLinks = (onClick?: () => void) => (
    <ul className="space-y-1.5">
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.href === '/' ? pathname === '/' : pathname?.startsWith(item.href);

        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onClick}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-lg shadow-purple-900/30 border border-purple-400/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-purple-200' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );

  return (
    <>
      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 h-16 bg-slate-950/90 backdrop-blur-xl border-b border-slate-800 px-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center shadow-md shadow-purple-900/40">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
              JankBuild
            </span>
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-500/30">
              v{APP_VERSION}
            </span>
          </div>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg text-slate-300 hover:bg-slate-800"
          aria-label="Toggle Menu"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-30 bg-slate-950/95 backdrop-blur-xl pt-20 px-6 pb-6 flex flex-col justify-between">
          <nav>{renderNavLinks(() => setMobileOpen(false))}</nav>
          <div className="space-y-4 pt-6 border-t border-slate-800">
            <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-emerald-950/50 border border-emerald-500/30 text-xs text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <Cpu className="h-3.5 w-3.5" />
              <span>Local AI Active (jankbuild-commander)</span>
            </div>
            <UserNav />
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside className="w-68 bg-slate-950/80 backdrop-blur-xl border-r border-slate-800/80 hidden md:flex flex-col justify-between p-5 shrink-0 sticky top-0 h-screen">
        <div>
          <Link href="/" className="flex items-center gap-3 px-2 mb-8 group">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-900/40 group-hover:scale-105 transition-transform">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight text-white">JankBuild</h2>
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-500/30">
                  v{APP_VERSION}
                </span>
              </div>
              <p className="text-xs text-slate-400">Commander AI Suite</p>
            </div>
          </Link>

          <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Navigation
          </div>
          <nav>{renderNavLinks()}</nav>
        </div>

        <div className="space-y-4 pt-5 border-t border-slate-800/80">
          <div className="px-3 py-2.5 rounded-xl bg-gradient-to-r from-emerald-950/60 to-teal-950/40 border border-emerald-500/25">
            <div className="flex items-center gap-2 text-xs font-medium text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <Cpu className="h-3.5 w-3.5" />
              <span>Local AI Online</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 truncate">
              Model: jankbuild-commander
            </p>
          </div>

          <UserNav />
        </div>
      </aside>
    </>
  );
}
