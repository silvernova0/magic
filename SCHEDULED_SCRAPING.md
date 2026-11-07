# Scheduled Scraping System

Automated data collection from EDHREC, MTGTop8, and Moxfield using scheduled jobs.

## Features

- **Automated Scheduling**: Cron-like job scheduling with node-schedule
- **Job Tracking**: All jobs are logged in the database with status, duration, and errors
- **Manual Triggers**: Run jobs on-demand for testing or immediate updates
- **API Endpoints**: Monitor job history and statistics via REST API
- **Error Handling**: Failed jobs are tracked with error messages for debugging

## Schedule

| Source | Frequency | Time | Reasoning |
|--------|-----------|------|-----------|
| **EDHREC** | Weekly | Sunday 3:00 AM | Synergy data changes slowly |
| **MTGTop8** | Every 3 days | 2:00 AM | Tournament data updates regularly |
| **Moxfield** | Daily | 1:00 AM | Community decks update frequently |

## Usage

### Start the Scheduler

Run the scheduler as a background service:

```bash
npm run scheduler
```

This starts the scheduled scraping service. Jobs will run automatically at their scheduled times. Press `Ctrl+C` to stop.

### Manual Triggers

Run specific jobs on-demand:

```bash
# Run a single job
npm run scrape:now -- edhrec
npm run scrape:now -- mtgtop8
npm run scrape:now -- moxfield

# Run all jobs
npm run scrape:now -- all
```

### API Endpoints

#### Get Job History

```http
GET /api/scrape/jobs?limit=50
```

Returns recent scrape job history with status, duration, and items scraped.

#### Get Job Statistics

```http
GET /api/scrape/jobs?action=stats
```

Returns statistics for all job types (success rate, avg duration, etc).

```http
GET /api/scrape/jobs?action=stats&jobType=moxfield
```

Returns statistics for a specific job type.

#### Trigger Job Manually

```http
POST /api/scrape/jobs
Content-Type: application/json

{
  "jobType": "moxfield"
}
```

Triggers a scrape job immediately. Valid types: `edhrec`, `mtgtop8`, `moxfield`.

## Database Schema

```prisma
model ScrapeJob {
  id          String   @id @default(cuid())
  jobType     String   // "edhrec", "mtgtop8", "moxfield"
  status      String   // "pending", "running", "completed", "failed"
  itemsScraped Int     @default(0)
  errors      String?  // JSON array of errors
  startedAt   DateTime @default(now())
  completedAt DateTime?
  duration    Int?     // milliseconds
}
```

## Production Deployment

### Option 1: PM2 (Recommended)

```bash
# Install PM2
npm install -g pm2

# Start scheduler
pm2 start npm --name "mtg-scheduler" -- run scheduler

# View logs
pm2 logs mtg-scheduler

# Stop scheduler
pm2 stop mtg-scheduler

# Auto-restart on reboot
pm2 startup
pm2 save
```

### Option 2: Systemd Service

Create `/etc/systemd/system/mtg-scheduler.service`:

```ini
[Unit]
Description=MTG Deck Builder Scheduler
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/magicapp
ExecStart=/usr/bin/npm run scheduler
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable mtg-scheduler
sudo systemctl start mtg-scheduler
sudo systemctl status mtg-scheduler
```

### Option 3: Docker

Add to `docker-compose.yml`:

```yaml
services:
  scheduler:
    build: .
    command: npm run scheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped
    depends_on:
      - db
```

### Option 4: Vercel Cron (Next.js)

For Vercel deployments, use Vercel Cron in `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/scrape/cron/edhrec",
      "schedule": "0 3 * * 0"
    },
    {
      "path": "/api/scrape/cron/mtgtop8",
      "schedule": "0 2 */3 * *"
    },
    {
      "path": "/api/scrape/cron/moxfield",
      "schedule": "0 1 * * *"
    }
  ]
}
```

## Monitoring

### View Recent Jobs

```bash
# Using API
curl http://localhost:3000/api/scrape/jobs?limit=10

# Using database
npx prisma studio
# Navigate to ScrapeJob table
```

### Check Statistics

```bash
# Using API
curl http://localhost:3000/api/scrape/jobs?action=stats

# Or run a manual job with stats
npm run scrape:now -- moxfield
```

### Error Tracking

Failed jobs store error messages in the `errors` field (JSON array). Check recent failures:

```sql
SELECT * FROM ScrapeJob 
WHERE status = 'failed' 
ORDER BY startedAt DESC 
LIMIT 10;
```

## Troubleshooting

### Jobs Not Running

1. Check if scheduler is running: `ps aux | grep scheduler`
2. Check logs: `pm2 logs mtg-scheduler` (if using PM2)
3. Verify cron syntax: [crontab.guru](https://crontab.guru/)

### Rate Limiting

If scrapers are being rate-limited:

1. Increase delays in scraper files (`RATE_LIMIT_DELAY`)
2. Reduce frequency of scheduled jobs
3. Add exponential backoff for retries

### Memory Issues

If scheduler consumes too much memory:

1. Reduce concurrent scraping operations
2. Process items in smaller batches
3. Add memory limits to PM2: `pm2 start --max-memory-restart 500M`

## Development

### Testing Schedule Without Waiting

Override schedule times in `scheduled-scraper.ts`:

```typescript
// Run every minute (for testing)
const moxfieldJob = schedule.scheduleJob('0 * * * * *', () => {
  runMoxfieldJob();
});
```

### Adding New Scrapers

1. Create scraper in `src/lib/scrapers/`
2. Add job function in `scheduled-scraper.ts`
3. Add to schedule in `initializeScheduledJobs()`
4. Add job type to API endpoint validation
5. Update documentation

## Best Practices

- **Rate Limiting**: Always respect source websites with appropriate delays
- **Error Handling**: Log all errors for debugging
- **Job Tracking**: Use ScrapeJob model to track all scraping operations
- **Monitoring**: Regularly check job statistics and failure rates
- **Graceful Shutdown**: Handle SIGINT/SIGTERM to cancel jobs cleanly
- **Idempotency**: Ensure jobs can be safely re-run without duplicating data
