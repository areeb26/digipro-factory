# Digital Product Factory - Automation Guide

This guide explains how to use the automated orchestration system.

## Overview

The `main.py` script orchestrates the entire Digital Product Factory workflow:

1. **Daily Product Generation** (2:00 AM) - Discovers trends and creates products
2. **Hourly Publishing** - Publishes approved products to marketplaces
3. **6-Hour Analytics** - Updates sales data and generates reports

## Quick Start

### Run Automated Scheduler

```bash
# Start the automated scheduler (runs continuously)
python main.py
```

The scheduler will:
- Run product generation at 2:00 AM every day
- Check for approved products every hour and publish them
- Update analytics every 6 hours

Press `Ctrl+C` to stop gracefully.

### Run Individual Tasks

For testing or manual runs:

```bash
# Generate products once (test the workflow)
python main.py --generate

# Publish approved products once
python main.py --publish

# Update analytics once
python main.py --analytics

# Run all tasks once (for testing the complete workflow)
python main.py --once
```

## Workflow Details

### 1. Daily Product Generation

**Schedule**: 2:00 AM daily

**What it does**:
1. Analyzes trending topics using Google Trends + Claude AI
2. Selects top 3 opportunities (scoring >60)
3. For each opportunity:
   - Creates appropriate product (Midjourney prompts, ChatGPT prompts, etc.)
   - Generates complete marketing content (Etsy, Instagram, Facebook, Pinterest)
   - Creates preview images and PDF guides
   - Saves to database with status "pending"
4. Logs all progress
5. Sends summary notification

**Output**:
- Products saved to database (status: "pending")
- Files in `output/products/`
- Marketing content in `output/marketing/`
- Stats in `logs/generation_stats_YYYYMMDD.json`

**Review Process**:
After generation, review products in the dashboard:
```bash
cd digital-product-factory/review_dashboard
flask run
# Visit http://localhost:5000
```

Approve products you want to publish.

### 2. Hourly Publishing

**Schedule**: Every hour

**What it does**:
1. Queries database for all "approved" products
2. For each approved product:
   - Publishes to Gumroad (if configured)
   - Publishes to Etsy (if configured)
   - Updates database with listing URLs
   - Changes status to "published"
3. Logs successes and failures
4. Sends notifications for completed/failed publishes

**Output**:
- Products published to marketplaces
- Database updated with URLs and status
- Stats in `logs/publishing_stats_YYYYMMDD_HHMM.json`

### 3. 6-Hour Analytics Update

**Schedule**: Every 6 hours

**What it does**:
1. Fetches all published products from database
2. For each product:
   - Queries Gumroad API for sales data
   - Queries Etsy API for views/sales (if implemented)
   - Updates database with latest stats
3. Generates daily performance report
4. Sends summary notification

**Output**:
- Database updated with analytics
- Daily report in `logs/analytics_report_YYYYMMDD.json`

## Logs and Monitoring

All activity is logged to multiple files:

```
logs/
├── main.log                        # All activity (INFO and DEBUG)
├── errors.log                      # Errors only
├── notifications.json              # System notifications
├── generation_stats_YYYYMMDD.json  # Daily generation stats
├── publishing_stats_*.json         # Publishing stats (hourly)
└── analytics_report_YYYYMMDD.json  # Daily analytics report
```

### View Logs in Real-Time

```bash
# Watch main log
tail -f logs/main.log

# Watch errors
tail -f logs/errors.log

# View notifications
cat logs/notifications.json | python -m json.tool
```

### Check Recent Notifications

```bash
# Last 5 notifications
tail -n 20 logs/notifications.json
```

## Configuration

### Environment Variables

Required in `.env`:

```bash
# AI Providers (at least one required)
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here

# Marketplace Credentials (optional)
GUMROAD_ACCESS_TOKEN=your_token_here
ETSY_CLIENT_ID=your_client_id
ETSY_CLIENT_SECRET=your_secret
ETSY_SHOP_ID=your_shop_id

# Flask (for review dashboard)
FLASK_SECRET_KEY=your_secret_key
```

### Scheduling Configuration

To change schedules, edit `main.py`:

```python
# Current schedule
schedule.every().day.at("02:00").do(daily_product_generation)
schedule.every().hour.do(process_approved_products)
schedule.every(6).hours.do(update_analytics)

# Examples of custom schedules:
# schedule.every(30).minutes.do(process_approved_products)
# schedule.every().monday.at("10:00").do(daily_product_generation)
# schedule.every().day.at("09:00").do(update_analytics)
```

## Running in Production

### Using systemd (Recommended for Linux servers)

Create `/etc/systemd/system/digipro-factory.service`:

```ini
[Unit]
Description=Digital Product Factory Automation
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/digipro-factory
ExecStart=/usr/bin/python3 /path/to/digipro-factory/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable digipro-factory
sudo systemctl start digipro-factory
sudo systemctl status digipro-factory
```

View logs:
```bash
sudo journalctl -u digipro-factory -f
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -r digital-product-factory/requirements.txt

CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t digipro-factory .
docker run -d --name factory --env-file .env digipro-factory
docker logs -f factory
```

### Using Screen (Quick solution)

```bash
# Start in background
screen -dmS factory python main.py

# Attach to see output
screen -r factory

# Detach: Ctrl+A then D

# Stop
screen -X -S factory quit
```

## Notifications

### Current Notifications

Notifications are logged to `logs/notifications.json` and console.

### Add Email Notifications

Edit `send_notification()` in `main.py`:

```python
def send_notification(title: str, message: str, level: str = "info"):
    # ... existing code ...

    # Add email for errors
    if level == "error":
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg['Subject'] = f"[Factory] {title}"
        msg['From'] = "factory@yourdomain.com"
        msg['To'] = "your@email.com"
        msg.set_content(message)

        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login('your@email.com', 'your_app_password')
            smtp.send_message(msg)
```

### Add Slack Notifications

```python
import requests

def send_notification(title: str, message: str, level: str = "info"):
    # ... existing code ...

    # Send to Slack
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    if slack_webhook and level in ['warning', 'error']:
        requests.post(slack_webhook, json={
            'text': f"*{title}*\n{message}"
        })
```

## Troubleshooting

### No products being generated

**Check**:
1. API keys are valid: `python main.py --generate`
2. Logs for errors: `tail -f logs/errors.log`
3. Trend monitoring is working: Check `logs/main.log`

### Products not publishing

**Check**:
1. Products are approved in database
2. Marketplace credentials are configured
3. Publishing logs: `logs/publishing_stats_*.json`

**Manual check**:
```bash
python main.py --publish
```

### Analytics not updating

**Check**:
1. Products have been published
2. Gumroad token is valid
3. Product IDs are stored in metadata

**Manual check**:
```bash
python main.py --analytics
```

### Scheduler not running at correct times

**Check**:
1. System time: `date`
2. Timezone: `timedatectl` (Linux) or `date` (Mac)
3. Logs for schedule execution: `grep "STARTING" logs/main.log`

## Monitoring Best Practices

### Daily Checks

```bash
# Check if running
ps aux | grep main.py

# Check recent errors
tail -n 50 logs/errors.log

# Check today's generation
cat logs/generation_stats_$(date +%Y%m%d).json

# Check notifications
tail -n 10 logs/notifications.json
```

### Weekly Review

1. Review analytics reports in `logs/analytics_report_*.json`
2. Check total products created vs published
3. Review error patterns in `logs/errors.log`
4. Adjust opportunity score threshold if needed

### Monthly Tasks

1. Archive old logs
2. Review and update trend keywords in `config.yaml`
3. Analyze top-performing niches
4. Optimize pricing based on sales data

## Performance Tuning

### Adjust Product Generation Count

In `main.py`, change the count:

```python
products = factory.discover_and_create(
    count=5,  # Generate more products
    min_opportunity_score=70,  # Raise bar for quality
    publish_immediately=False
)
```

### Adjust Publishing Frequency

```python
# Publish more frequently
schedule.every(30).minutes.do(process_approved_products)

# Or less frequently
schedule.every(2).hours.do(process_approved_products)
```

### Batch Processing

For high volume, modify `process_approved_products()`:

```python
# Limit batch size
approved_products = db.get_products_by_status('approved', limit=10)
```

## Safety Features

### Graceful Shutdown

The script handles `SIGINT` (Ctrl+C) and `SIGTERM` signals gracefully:

- Completes current task before exiting
- Saves all data
- Sends shutdown notification

### Error Recovery

- Automatic retries with exponential backoff
- Failed products marked in database
- Errors logged for review
- Continues processing remaining products

### Rate Limiting

All API calls include rate limiting:
- Google Trends: 100 requests/hour
- Anthropic: 50 requests/minute
- Gumroad: 60 requests/minute
- Etsy: 10 requests/second

## Support

For issues:
1. Check logs in `logs/` directory
2. Review this guide
3. Test individual components with `--generate`, `--publish`, `--analytics`
4. Check GitHub issues

---

**Built with ❤️ by Digital Product Factory**

*Automate. Create. Profit.*
