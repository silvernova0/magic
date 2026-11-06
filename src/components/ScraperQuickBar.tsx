'use client';

import React, { useState, useEffect } from 'react';
import { RefreshCw, Database, Trophy, Flame, Layers, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ScrapeJob {
  id: string;
  jobType: string;
  status: string;
  itemsScraped: number;
  startedAt: string;
  duration: number | null;
}

const SCRAPER_SOURCES = [
  {
    id: 'scryfall',
    label: 'Scryfall New Releases',
    desc: 'Latest Commander-legal paper sets & cards',
    schedule: 'Daily 4:00 AM',
    icon: Database,
    color: 'from-amber-500/20 to-orange-500/10 border-amber-500/30 text-amber-300',
  },
  {
    id: 'edhrec',
    label: 'EDHREC Synergies',
    desc: 'Top commanders & high-synergy card pairings',
    schedule: 'Sundays 3:00 AM',
    icon: Flame,
    color: 'from-purple-500/20 to-indigo-500/10 border-purple-500/30 text-purple-300',
  },
  {
    id: 'mtgtop8',
    label: 'MTGTop8 Tournaments',
    desc: 'Competitive Commander tournament top-8 lists',
    schedule: 'Every 3 Days',
    icon: Trophy,
    color: 'from-blue-500/20 to-cyan-500/10 border-blue-500/30 text-blue-300',
  },
  {
    id: 'moxfield',
    label: 'Moxfield Brackets',
    desc: 'Community decks across Brackets 1–5',
    schedule: 'Daily 1:00 AM',
    icon: Layers,
    color: 'from-emerald-500/20 to-teal-500/10 border-emerald-500/30 text-emerald-300',
  },
];

export default function ScraperQuickBar() {
  const [runningJob, setRunningJob] = useState<string | null>(null);
  const [recentJobs, setRecentJobs] = useState<ScrapeJob[]>([]);
  const [statusMsg, setStatusMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const loadJobs = async () => {
    try {
      const res = await fetch('/api/scrape/jobs?limit=8');
      if (res.ok) {
        const data = await res.json();
        setRecentJobs(data.jobs || []);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const triggerScraper = async (jobType: string) => {
    setRunningJob(jobType);
    setStatusMsg(null);
    try {
      const res = await fetch('/api/scrape/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobType }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStatusMsg({ type: 'ok', text: `${jobType.toUpperCase()} sync finished!` });
        await loadJobs();
      } else {
        setStatusMsg({ type: 'err', text: data.error || 'Sync failed' });
      }
    } catch (err: any) {
      setStatusMsg({ type: 'err', text: err?.message || 'Network error' });
    } finally {
      setRunningJob(null);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800/80 p-6 backdrop-blur-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <RefreshCw className={`h-5 w-5 text-purple-400 ${runningJob ? 'animate-spin' : ''}`} />
            Automated Card & Meta Scrapers
          </h2>
          <p className="text-sm text-slate-400">
            Background scheduler runs automatically inside the server — or trigger any source on demand below
          </p>
        </div>
        {statusMsg && (
          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium border ${
              statusMsg.type === 'ok'
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                : 'bg-red-950/60 border-red-500/40 text-red-300'
            }`}
          >
            {statusMsg.type === 'ok' ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <span>{statusMsg.text}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {SCRAPER_SOURCES.map((src) => {
          const Icon = src.icon;
          const isRunning = runningJob === src.id;
          const lastJob = recentJobs.find((j) => j.jobType === src.id);

          return (
            <div
              key={src.id}
              className={`rounded-xl bg-gradient-to-br ${src.color} border p-4 flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold uppercase tracking-wider opacity-80">
                    {src.schedule}
                  </span>
                  <Icon className="h-4 w-4 opacity-90" />
                </div>
                <h3 className="font-bold text-white text-base">{src.label}</h3>
                <p className="text-xs text-slate-300/80 mt-1">{src.desc}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between gap-2">
                <div className="text-[11px] text-slate-300/90 truncate">
                  {lastJob ? (
                    <span>
                      Last: {lastJob.status} ({lastJob.itemsScraped} items)
                    </span>
                  ) : (
                    <span>Scheduled</span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={runningJob !== null}
                  onClick={() => triggerScraper(src.id)}
                  className="h-7 px-2.5 text-xs bg-white/10 hover:bg-white/20 text-white border-0 shrink-0"
                >
                  {isRunning ? 'Syncing...' : 'Sync Now'}
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
