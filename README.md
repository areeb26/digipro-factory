# 🏭 Digital Product Factory

An automated platform for creating, publishing, and managing digital products at scale. Monitor trends, generate products with AI, publish to marketplaces, and track analytics—all automatically.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Digital Product Factory automates the entire lifecycle of digital product creation and sales:

1. **Trend Monitoring** - Analyzes Google Trends to find profitable opportunities
2. **Content Generation** - Uses AI (Claude/Gemini) to create products
3. **Marketing Automation** - Generates descriptions, titles, tags, and images
4. **Multi-Platform Publishing** - Publishes to Etsy, Gumroad automatically
5. **Analytics & Optimization** - Tracks performance and suggests improvements

### What Can It Create?

- 📝 Notion templates
- 📅 Digital planners (PDF)
- 💡 ChatGPT/AI prompt packs
- 🎨 Midjourney prompt collections
- ✅ Productivity worksheets
- 📊 Business templates

## ✨ Features

### Core Features

- ✅ **Automated Trend Discovery** - Google Trends integration with opportunity scoring
- ✅ **AI Content Generation** - Anthropic Claude & Google Gemini support
- ✅ **Multi-Platform Publishing** - Etsy & Gumroad integration
- ✅ **Review Dashboard** - Web interface for approving products
- ✅ **Scheduled Automation** - Daily generation, hourly publishing
- ✅ **Comprehensive Analytics** - Performance tracking, revenue reports
- ✅ **System Monitoring** - Health checks, alerts, circuit breakers
- ✅ **Backup & Recovery** - Automated backups with point-in-time restore

### Security Features

- 🔒 Input sanitization (SQL injection & XSS prevention)
- 🔐 Credential encryption
- 🚦 Rate limiting
- 📝 Security audit logging
- ✅ File upload validation

### Developer Features

- 🧪 Integration testing suite
- 📚 Comprehensive documentation
- 🛠️ CLI with 8 commands
- 🎨 Interactive setup wizard
- 📦 One-click deployment scripts

## 🚀 Quick Start

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/digipro-factory.git
cd digipro-factory

# 2. Run one-click deployment
./deploy.sh

# 3. Create your first product
source venv/bin/activate
python cli.py create-product --type=notion --niche=productivity
```

### Requirements

- **Python** 3.10 or higher
- **Anthropic API key** (required) - [Get one here](https://console.anthropic.com/)
- **Etsy API credentials** (optional) - [Developer Portal](https://www.etsy.com/developers/)
- **Gumroad access token** (optional) - [App Settings](https://app.gumroad.com/settings/advanced)

## 📦 Installation

### Option 1: One-Click Deployment (Recommended)

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

The deployment script will:
- ✅ Check system requirements
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Run interactive setup wizard
- ✅ Initialize database
- ✅ Run validation tests
- ✅ Configure automated scheduling

### Option 2: Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python setup_wizard.py

# Initialize database
cd digital-product-factory
python -c "from database import ProductDB; ProductDB()"

# Verify installation
cd ..
python integration_test.py --quick
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ============================================================================
# REQUIRED: AI Services
# ============================================================================

# Anthropic Claude API (required for content generation)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Optional: Google Gemini API (alternative AI provider)
# GOOGLE_API_KEY=your_google_api_key_here


# ============================================================================
# OPTIONAL: E-commerce Platforms
# ============================================================================

# Etsy API
ETSY_API_KEY=your_etsy_api_key_here
ETSY_SHOP_ID=your_shop_id_here

# Gumroad API
GUMROAD_ACCESS_TOKEN=your_gumroad_token_here


# ============================================================================
# Shop Preferences
# ============================================================================

# Target niches (comma-separated)
TARGET_NICHES=productivity,wellness,business

# Product types to create
PRODUCT_TYPES=notion,planner,chatgpt

# Price range
MIN_PRODUCT_PRICE=4.99
MAX_PRODUCT_PRICE=19.99


# ============================================================================
# Automation Settings
# ============================================================================

# Product generation schedule
DAILY_GENERATION_TIME=02:00
PROCESS_APPROVED_INTERVAL_HOURS=1
UPDATE_ANALYTICS_INTERVAL_HOURS=6

# Products to generate per day
PRODUCTS_PER_DAY=3

# Minimum opportunity score (0-100)
MIN_OPPORTUNITY_SCORE=60


# ============================================================================
# Monitoring & Alerts
# ============================================================================

# Email alerts (SMTP)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your_email@gmail.com
# SMTP_PASSWORD=your_app_password
# ALERT_EMAIL=your_email@gmail.com

# Slack alerts
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL


# ============================================================================
# Application Settings
# ============================================================================

# Flask secret key (for review dashboard)
FLASK_SECRET_KEY=your-secret-key-here

# Database path
DATABASE_PATH=data/products.db
```

### Using the Setup Wizard

The interactive setup wizard guides you through configuration:

```bash
python setup_wizard.py
```

The wizard will:
1. Validate your Anthropic API key
2. Configure Etsy/Gumroad (optional)
3. Set shop preferences (niches, product types, pricing)
4. Create `.env` file
5. Initialize database
6. Run API tests
7. Create a test product

## 💻 Usage Examples

### Command-Line Interface

The CLI provides 8 commands for manual operations:

```bash
# Create a single product
python cli.py create-product --type=notion --niche=productivity

# Check trending opportunities
python cli.py check-trends

# Review products in web dashboard
python cli.py review-dashboard

# Publish a specific product
python cli.py publish --id=123 --platforms=etsy,gumroad

# View business statistics
python cli.py stats

# Test API connections
python cli.py test-api

# Backup database
python cli.py backup

# Get help
python cli.py --help
```

See [CLI_GUIDE.md](CLI_GUIDE.md) for detailed command documentation.

### Automated Mode

Run the main orchestrator for fully automated operation:

```bash
python main.py
```

This will:
- Generate 3 products daily at 2 AM
- Process approved products every hour
- Update analytics every 6 hours
- Send notifications on completion/errors
- Run continuously with graceful shutdown

See [AUTOMATION.md](AUTOMATION.md) for scheduling and production deployment.

### Python API

Use the factory programmatically:

```python
from digital_product_factory.factory import DigitalProductFactory

# Initialize factory
factory = DigitalProductFactory()

# Discover and create products
products = factory.discover_and_create(
    count=3,
    min_opportunity_score=60,
    publish_immediately=False
)

# Create from specific opportunity
opportunity = {
    'keyword': 'productivity planner',
    'niche': 'productivity',
    'opportunity_score': 85
}

product = factory.create_product_from_opportunity(opportunity)

# Publish product
result = factory.publish_product(product['id'], platforms=['etsy', 'gumroad'])
```

### Analytics & Reporting

```python
from digital_product_factory.analytics import Analytics

analytics = Analytics()

# Get product performance
performance = analytics.get_product_performance(days=30)
print(performance.head())

# Analyze by niche
niche_stats = analytics.get_niche_performance()
print(niche_stats.sort_values('total_revenue', ascending=False))

# Compare platforms
comparison = analytics.get_platform_comparison()
print(f"Gumroad profit: ${comparison['net_profit']['Gumroad']:.2f}")

# Generate PDF report
analytics.generate_weekly_report(
    output_path='reports/weekly_report.pdf',
    email_to='you@example.com'  # Optional
)

# Predict trends
predictions = analytics.predict_trends(days_ahead=7)
for pred in predictions['predictions']:
    print(f"{pred['niche']}: {pred['confidence']} confidence")
```

### Monitoring & Health

```python
from digital_product_factory.monitoring import check_system_health, send_alert

# Check system health
health = check_system_health()

if not health['overall_healthy']:
    print(f"Issues found: {health['issues']}")
    send_alert('critical', 'System unhealthy', health)

# Log errors with context
from digital_product_factory.monitoring import log_error

try:
    risky_operation()
except Exception as e:
    log_error(e, {'operation': 'risky_operation', 'user_id': 123})
```

### Backup & Recovery

```python
from digital_product_factory.recovery import auto_backup, recover_from_backup

# Create backup
backup_path = auto_backup()
print(f"Backup created: {backup_path}")

# Restore from specific date
recover_from_backup('2025-01-15')

# Retry failed publishing operations
from digital_product_factory.recovery import retry_failed_operations

results = retry_failed_operations()
print(f"Succeeded: {results['succeeded']}, Failed: {results['failed']}")
```

## 🏗️ Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    Digital Product Factory                        │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Trend Monitor  │─────▶│  Product Creator │─────▶│  Publisher  │
│  (pytrends)     │      │  (Claude/Gemini) │      │ (Etsy/Gum.) │
└─────────────────┘      └──────────────────┘      └─────────────┘
        │                         │                        │
        │                         │                        │
        ▼                         ▼                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SQLite Database                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Products │  │  Trends  │  │  Status  │  │   Metadata   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
└──────────────────────────────────────────────────────────────────┘
        │                         │                        │
        ▼                         ▼                        ▼
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│    Analytics    │      │  Review Dashboard│      │  Monitoring │
│   (pandas/matplotlib) │      │    (Flask)       │      │ (Health/Alerts)│
└─────────────────┘      └──────────────────┘      └─────────────┘
```

### Components

```
digipro-factory/
├── digital-product-factory/    # Core modules
│   ├── factory.py              # Main orchestrator
│   ├── trend_scraper.py        # Google Trends monitoring
│   ├── database.py             # SQLite operations
│   ├── product_creators/       # Product generation
│   │   ├── notion_creator.py
│   │   ├── planner_creator.py
│   │   └── prompt_creator.py
│   ├── marketing_gen/          # Marketing content
│   │   └── marketing_generator.py
│   ├── platform_publishers/    # Marketplace integration
│   │   ├── etsy_publisher.py
│   │   └── gumroad_publisher.py
│   ├── analytics.py            # Performance tracking
│   ├── monitoring.py           # Health checks & alerts
│   ├── security.py             # Security features
│   └── recovery.py             # Backup & restore
├── main.py                     # Automated scheduler
├── cli.py                      # Command-line interface
├── setup_wizard.py             # Interactive setup
├── integration_test.py         # End-to-end tests
├── deploy.sh / deploy.bat      # Deployment scripts
└── docs/                       # Documentation
```

### Data Flow

1. **Trend Discovery** → `trend_scraper.py` monitors Google Trends
2. **Opportunity Scoring** → Ranks trends by search volume & competition
3. **Product Generation** → AI creates content based on top opportunities
4. **Marketing Creation** → Generates SEO-optimized titles, descriptions, tags
5. **Status: Pending** → Product saved to database for review
6. **Manual Review** → (Optional) Review in dashboard, approve/reject
7. **Status: Approved** → Ready for publishing
8. **Publishing** → Automated publishing to Etsy/Gumroad
9. **Status: Published** → Listed on marketplaces
10. **Analytics** → Track views, sales, revenue, ROI

## 📖 API Documentation

### Core Modules

- **[DigitalProductFactory](docs/API_REFERENCE.md#digitalproductfactory)** - Main orchestration class
- **[TrendScraper](docs/API_REFERENCE.md#trendscraper)** - Trend monitoring and analysis
- **[ProductDB](docs/API_REFERENCE.md#productdb)** - Database operations
- **[NotionCreator](docs/API_REFERENCE.md#notioncreator)** - Notion template generation
- **[PlannerCreator](docs/API_REFERENCE.md#plannercreator)** - PDF planner creation
- **[PromptCreator](docs/API_REFERENCE.md#promptcreator)** - AI prompt generation
- **[MarketingGenerator](docs/API_REFERENCE.md#marketinggenerator)** - Marketing content
- **[EtsyPublisher](docs/API_REFERENCE.md#etsypublisher)** - Etsy marketplace
- **[GumroadPublisher](docs/API_REFERENCE.md#gumroadpublisher)** - Gumroad marketplace
- **[Analytics](docs/API_REFERENCE.md#analytics)** - Performance analytics
- **[Monitoring](docs/API_REFERENCE.md#monitoring)** - System health
- **[Security](docs/API_REFERENCE.md#security)** - Security features
- **[Recovery](docs/API_REFERENCE.md#recovery)** - Backup & restore

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for complete API documentation.

## 🛠️ Troubleshooting

### Common Issues

**Issue: ModuleNotFoundError when running scripts**

```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Or use absolute paths
/path/to/venv/bin/python cli.py
```

**Issue: Database locked error**

```bash
# Solution: Check for multiple instances running
ps aux | grep python  # Linux/Mac
tasklist | findstr python  # Windows

# Kill conflicting processes or restart
```

**Issue: API rate limits exceeded**

```bash
# Solution: Check logs for rate limit errors
tail -f logs/main.log

# Adjust rate limiting in code or wait for reset
```

**Issue: Products not publishing**

```bash
# Solution: Check status and retry failed operations
python -c "from recovery import retry_failed_operations; retry_failed_operations()"

# Or check individual platform credentials
python cli.py test-api
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for complete troubleshooting guide.

## ❓ FAQ

### General Questions

**Q: How much does it cost to run?**

- Anthropic API: ~$0.01-0.05 per product (required)
- Etsy: $0.20 listing fee + 6.5% transaction fee + 3% payment processing
- Gumroad: 10% of sales
- Hosting: Free (run locally) or ~$5-20/month (VPS)

**Q: How many products can I create per day?**

- Default: 3 products per day (configurable)
- API limits: Anthropic Claude has generous limits
- Recommended: Start with 1-3 per day, scale based on success rate

**Q: Do I need coding experience?**

- Basic usage: No, use the setup wizard and CLI
- Customization: Yes, Python knowledge helpful
- Automation: No, pre-configured schedules work out of the box

**Q: Can I sell on platforms other than Etsy/Gumroad?**

- Currently: Etsy and Gumroad are officially supported
- Future: Can add more platforms (Creative Market, Shopify, etc.)
- Custom: Implement your own publisher following the pattern

**Q: Is this legal?**

- Yes, creating and selling digital products is legal
- Ensure compliance with platform terms of service
- Don't create products that infringe copyrights or trademarks
- Review AI-generated content for accuracy and quality

### Technical Questions

**Q: What database does it use?**

- SQLite for simplicity and portability
- Can be migrated to PostgreSQL/MySQL for production scale

**Q: Can I run this on a Raspberry Pi?**

- Yes, if it meets Python 3.10+ requirement
- May need to adjust memory limits for AI operations

**Q: How do I scale to 100+ products per day?**

- See [docs/SCALING.md](docs/SCALING.md) for optimization strategies
- Consider: Multiple API keys, worker pools, caching, CDN

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python integration_test.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/digipro-factory.git
cd digipro-factory

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Run tests
python integration_test.py

# Run linter
flake8 digital-product-factory/

# Format code
black digital-product-factory/
```

### Contribution Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Keep commits atomic and well-described
- Be respectful and constructive

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Digital Product Factory Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Full MIT License text...]
```

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude API
- [Google](https://trends.google.com/) for Trends data
- [Etsy](https://www.etsy.com/) & [Gumroad](https://gumroad.com/) for marketplace APIs
- All open-source libraries used in this project

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/digipro-factory/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/digipro-factory/discussions)

---

<p align="center">Made with ❤️ by the Digital Product Factory team</p>
<p align="center">⭐ Star us on GitHub if this project helped you!</p>
