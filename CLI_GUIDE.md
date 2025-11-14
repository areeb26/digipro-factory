# Digital Product Factory - CLI Guide

A comprehensive command-line interface for managing the Digital Product Factory.

## Installation

```bash
# Install dependencies
pip install -r digital-product-factory/requirements.txt

# Make CLI executable (Linux/Mac)
chmod +x cli.py
```

## Quick Start

```bash
# First-time setup
python cli.py init

# Check trending opportunities
python cli.py check-trends

# Create a product
python cli.py create-product --type=prompts --niche=photography

# Review products in web UI
python cli.py review-dashboard

# Publish a product
python cli.py publish --id=1

# View statistics
python cli.py stats
```

## Commands

### 1. init - Setup Wizard

Initialize the Digital Product Factory for first-time use.

```bash
python cli.py init
```

**What it does:**
- Creates `.env` file with API keys (interactive prompts)
- Creates necessary directories (logs/, data/, output/)
- Initializes database
- Tests API connections

**Interactive prompts:**
- Anthropic API key (required)
- Gemini API key (optional)
- Gumroad access token (optional)

**Example output:**
```
================================================================================
                                 SETUP WIZARD
================================================================================

Welcome to Digital Product Factory!

This wizard will guide you through the initial setup.

Step 1: API Configuration

Anthropic Claude (Required - at least one AI provider needed)
Enter Anthropic API key: sk-ant-xxxxx

✓ .env file created
✓ Directories created
✓ Database initialized

Step 3: Testing API connections
Testing Anthropic Claude...
✓ Anthropic Claude: Connected

================================================================================
                               SETUP COMPLETE!
================================================================================

✓ Digital Product Factory is ready to use!

Next steps:
  1. python cli.py check-trends       # Discover opportunities
  2. python cli.py create-product     # Create your first product
  3. python cli.py review-dashboard   # Review products
  4. python cli.py publish --id=1     # Publish to marketplaces
```

### 2. create-product - Create Digital Product

Create a single digital product with marketing content.

```bash
# Interactive mode (prompts for missing values)
python cli.py create-product

# With all parameters
python cli.py create-product \
  --type=midjourney \
  --niche=product-photography \
  --price=15.99 \
  --count=100

# Create and publish immediately
python cli.py create-product \
  --type=chatgpt \
  --niche=marketing \
  --publish-now
```

**Options:**
- `--type, -t` - Product type: `prompts`, `midjourney`, `chatgpt`, `planner`, `notion`
- `--niche, -n` - Target niche/category (e.g., photography, marketing)
- `--title` - Product title (auto-generated if not provided)
- `--price` - Price in dollars (e.g., 12.99)
- `--count` - Number of prompts/items (default: 50)
- `--publish-now` - Publish immediately without review

**Interactive prompts:**
If you don't provide options, the CLI will prompt you:

```bash
python cli.py create-product

Product type (prompts, midjourney, chatgpt, planner, notion): prompts
Target niche/category: product-photography
Product price (USD) [12.99]: 15.99
Proceed with product creation? [y/N]: y
```

**Progress indicators:**
```
Initializing factory ████████████████████ 100%
Generating content   ████████████████████ 100%

✓ Product created successfully!

  Product ID: 42
  Title: Professional Prompts - Product Photography
  Type: midjourney_prompts
  Price: $15.99
  Status: pending

  Files: output/products/professional_prompts_20250114_153045/

ℹ Product saved for review. Use 'python cli.py review-dashboard' to review.
ℹ To publish: python cli.py publish --id=42
```

### 3. check-trends - Analyze Trends

Discover trending opportunities for digital products.

```bash
# Basic analysis
python cli.py check-trends

# Analyze more trends
python cli.py check-trends --limit=20

# Set minimum opportunity score
python cli.py check-trends --min-score=70

# Save results to file
python cli.py check-trends --save
```

**Options:**
- `--limit, -l` - Number of trends to analyze (default: 10, max: 5 per request)
- `--min-score` - Minimum opportunity score 0-100 (default: 60)
- `--save` - Save results to JSON file

**Example output:**
```
================================================================================
                              TREND ANALYSIS
================================================================================

Initializing      ████████████████████ 100%

Analyzing trending topics...
Analyzing trends  ████████████████████ 100%

✓ Found 3 opportunities

1. Product Photography Prompts
   Product Type: midjourney_prompts
   Niche: photography
   Opportunity Score: 85/100
   Demand: 90/100
   Competition: 45/100
   Recommended Price: $12.99
   Reasoning: High demand for photography-related AI prompts with moderate...

2. Social Media Marketing Templates
   Product Type: notion_template
   Niche: marketing
   Opportunity Score: 78/100
   Demand: 85/100
   Competition: 55/100
   Recommended Price: $9.99
   Reasoning: Growing interest in social media management tools...
```

### 4. review-dashboard - Web Dashboard

Start the Flask web dashboard for reviewing products.

```bash
# Default (localhost:5000)
python cli.py review-dashboard

# Custom port
python cli.py review-dashboard --port=8080

# Enable debug mode
python cli.py review-dashboard --debug

# Custom host (for network access)
python cli.py review-dashboard --host=0.0.0.0 --port=8080
```

**Options:**
- `--port, -p` - Port number (default: 5000)
- `--host` - Host to bind to (default: 127.0.0.1)
- `--debug` - Enable debug mode

**Example:**
```
================================================================================
                            REVIEW DASHBOARD
================================================================================

ℹ Starting dashboard on http://127.0.0.1:5000
ℹ Press Ctrl+C to stop

 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000

Press CTRL+C to quit
```

**Dashboard features:**
- View all pending products in a grid
- Filter by type, niche, status
- Search products
- Click on product to view details
- Approve, edit, or reject products
- Download product files
- View marketing content
- See analytics

### 5. publish - Publish Product

Publish a product to marketplaces.

```bash
# Publish to all configured platforms
python cli.py publish --id=123

# Publish to specific platform
python cli.py publish --id=123 --platforms=gumroad

# Publish to multiple platforms
python cli.py publish --id=123 --platforms=etsy,gumroad

# Force re-publish
python cli.py publish --id=123 --force
```

**Options:**
- `--id` - Product ID (required)
- `--platforms` - Comma-separated platforms (default: gumroad,etsy)
- `--force` - Force publish even if already published

**Example output:**
```
================================================================================
                             PUBLISH PRODUCT
================================================================================

ℹ Product: Professional Midjourney Prompts - Product Photography
ℹ Type: midjourney_prompts
ℹ Price: $15.99
ℹ Platforms: gumroad,etsy

⚠ Proceed with publishing? [y/N]: y

Publishing ████████████████████ 100%

✓ Published to Gumroad: https://gumroad.com/l/abc123
✓ Published to Etsy: https://etsy.com/listing/456789

✓ Successfully published to: Gumroad, Etsy
```

### 6. stats - Business Statistics

View statistics and analytics for your products.

```bash
# Basic statistics
python cli.py stats

# Detailed statistics
python cli.py stats --detailed

# Export to JSON
python cli.py stats --export=statistics.json
```

**Options:**
- `--detailed` - Show detailed statistics
- `--export` - Export to JSON file

**Example output:**
```
================================================================================
                           BUSINESS STATISTICS
================================================================================

Gathering statistics ████████████████████ 100%

Overview
────────────────────────────────────────

  Total Products: 42
  Pending: 15
  Approved: 5
  Published: 20
  Rejected: 2

Product Types
────────────────────────────────────────

  midjourney_prompts: 18
  chatgpt_prompts: 12
  notion_template: 8
  digital_planner: 4

Platform Integration
────────────────────────────────────────

  Gumroad: ✓ Enabled
  Etsy: ✗ Disabled
```

### 7. test-api - Test API Connections

Test all API connections and show status.

```bash
python cli.py test-api
```

**Example output:**
```
================================================================================
                          API CONNECTION TEST
================================================================================

Testing Anthropic Claude...
✓ Anthropic Claude: Connected

Testing Google Gemini...
✓ Google Gemini: Connected

Testing Gumroad...
✓ Gumroad: Connected as John Doe

Testing Etsy...
✓ Etsy: Configured (OAuth required for full access)

Summary
────────────────────────────────────────

✓ All 4 services connected successfully!
```

### 8. backup - Backup Data

Create a backup of database and product files.

```bash
# Create backup in default location
python cli.py backup

# Specify output directory
python cli.py backup --output=/path/to/backup

# Create compressed backup
python cli.py backup --compress
```

**Options:**
- `--output, -o` - Output directory (default: backups/)
- `--compress` - Compress backup into .tar.gz

**What's backed up:**
- Database (data/products.db)
- All product files (output/)
- Configuration (.env)
- Config file (config.yaml)

**Example output:**
```
================================================================================
                                BACKUP DATA
================================================================================

ℹ Creating backup in: backups/backup_20250114_153045

Backing up ████████████████████ Database

✓ Backup complete: backups/backup_20250114_153045
  Size: 125.43 MB
```

## Common Workflows

### Workflow 1: First-Time Setup

```bash
# 1. Run setup wizard
python cli.py init

# 2. Test API connections
python cli.py test-api

# 3. Check trending opportunities
python cli.py check-trends --limit=10

# 4. Create your first product
python cli.py create-product
```

### Workflow 2: Daily Product Creation

```bash
# 1. Discover trends
python cli.py check-trends --save

# 2. Create products for top trends
python cli.py create-product --type=prompts --niche=photography
python cli.py create-product --type=chatgpt --niche=marketing
python cli.py create-product --type=notion --niche=productivity

# 3. Review in dashboard
python cli.py review-dashboard

# 4. Publish approved products
python cli.py publish --id=1
python cli.py publish --id=2

# 5. Check statistics
python cli.py stats
```

### Workflow 3: Bulk Operations

```bash
# Check trends and save for review
python cli.py check-trends --limit=20 --min-score=70 --save

# Review trends and create multiple products
# (repeat for each trend)
python cli.py create-product --type=prompts --niche=trend1
python cli.py create-product --type=prompts --niche=trend2

# Bulk review in dashboard
python cli.py review-dashboard

# Publish after approval in dashboard
# (use database to get IDs of approved products)
python cli.py publish --id=1
python cli.py publish --id=2
python cli.py publish --id=3
```

## Color Coding

The CLI uses colors for better readability:

- **Green (✓)** - Success messages
- **Red (✗)** - Error messages
- **Yellow (⚠)** - Warnings and confirmations
- **Blue (ℹ)** - Information messages
- **Cyan** - Headers and titles

## Help System

Get help for any command:

```bash
# General help
python cli.py --help

# Command-specific help
python cli.py create-product --help
python cli.py check-trends --help
python cli.py publish --help
```

## Error Handling

The CLI provides clear error messages:

```bash
python cli.py publish --id=999

✗ Product 999 not found
```

```bash
python cli.py create-product --type=invalid

Error: Invalid value for '--type' / '-t': 'invalid' is not one of
'prompts', 'midjourney', 'chatgpt', 'planner', 'notion'.
```

## Tips and Tricks

### 1. Use Interactive Mode

Don't remember all the options? Just run the command without options:

```bash
python cli.py create-product
# CLI will prompt you for each required field
```

### 2. Save Trend Analysis

Save trends to review later:

```bash
python cli.py check-trends --save
cat trends_analysis_20250114_153045.json | python -m json.tool | less
```

### 3. Export Statistics

Track your progress over time:

```bash
python cli.py stats --export=stats_$(date +%Y%m%d).json
```

### 4. Regular Backups

Schedule regular backups:

```bash
# Daily backup with compression
python cli.py backup --compress

# Weekly backup to external drive
python cli.py backup --output=/mnt/backup/digipro --compress
```

### 5. Test Before Publishing

Always test APIs before publishing:

```bash
python cli.py test-api
# Ensure all services are connected
```

## Troubleshooting

### Command not found

```bash
# Make sure you're in the project root
cd /path/to/digipro-factory

# Or use absolute path
python /path/to/digipro-factory/cli.py --help
```

### Import errors

```bash
# Install dependencies
pip install -r digital-product-factory/requirements.txt
```

### API connection failures

```bash
# Test connections
python cli.py test-api

# Check .env file
cat .env

# Re-run setup
python cli.py init
```

### Database errors

```bash
# Check if database exists
ls -lh data/products.db

# Reinitialize if needed
rm data/products.db
python cli.py init
```

## Automation

### Cron Jobs (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add daily product generation at 2 AM
0 2 * * * cd /path/to/digipro-factory && python cli.py create-product --type=prompts --niche=auto >> logs/cron.log 2>&1

# Weekly backup on Sundays at 3 AM
0 3 * * 0 cd /path/to/digipro-factory && python cli.py backup --compress >> logs/backup.log 2>&1
```

### Task Scheduler (Windows)

Create a batch file `create_product.bat`:

```batch
@echo off
cd C:\path\to\digipro-factory
python cli.py create-product --type=prompts --niche=auto
```

Schedule it in Windows Task Scheduler.

## Integration with main.py

The CLI is designed to work alongside the automated `main.py` scheduler:

- Use **CLI** for manual operations and testing
- Use **main.py** for automated daily operations

```bash
# Manual control
python cli.py create-product

# Automated scheduling
python main.py
```

---

**Built with ❤️ by Digital Product Factory**

*Simple. Powerful. Automated.*
