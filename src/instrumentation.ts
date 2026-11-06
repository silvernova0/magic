export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { initializeScheduledJobs } = await import('./lib/scheduled-scraper');
    initializeScheduledJobs();
  }
}
