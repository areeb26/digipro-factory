# Digital Product Factory 🏭

An intelligent, end-to-end automated system for discovering, creating, marketing, and publishing digital products to multiple marketplaces.

## 🌟 Features

### Complete Automation Pipeline
- **Trend Discovery**: Automatically identifies profitable opportunities using Google Trends + AI analysis
- **Product Creation**: Generates high-quality digital products (Midjourney prompts, ChatGPT prompts, planners, templates)
- **Marketing Generation**: Creates SEO-optimized listings, social media content, and 30-day content calendars
- **Quality Review**: Built-in review dashboard with approve/edit/reject workflow
- **Multi-Platform Publishing**: Publishes to Etsy and Gumroad with one click

### Multi-Provider AI Support
- **Anthropic Claude** (primary)
- **Google Gemini** (fallback)
- **OpenAI GPT-4** (optional)
- Automatic failover ensures reliability

### Professional Output
- PDF guides with table of contents
- Preview images for marketplace listings
- JSON data for developers
- Marketing copy for multiple platforms
- Social media calendars

## 📁 Project Structure

```
digital-product-factory/
├── factory.py                     # Main orchestration layer
├── database.py                    # Thread-safe SQLite database
├── config.yaml                    # Configuration settings
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
│
├── trend_monitor/                 # Trend discovery & analysis
│   ├── trend_scraper.py          # Google Trends + Claude analysis
│   └── etsy_trends.py            # Etsy-specific trend tracking
│
├── product_creators/              # Digital product generation
│   ├── prompt_creator.py         # Midjourney/ChatGPT prompt packs
│   ├── planner_creator.py        # Digital planners
│   └── notion_creator.py         # Notion templates
│
├── marketing_gen/                 # Marketing content generation
│   └── content_creator.py        # Listings, social media, ads
│
├── review_dashboard/              # Flask web application
│   ├── app.py                    # Review dashboard server
│   └── templates/                # HTML templates
│       ├── index.html            # Product grid
│       ├── product_detail.html   # Review page
│       └── stats.html            # Analytics dashboard
│
├── platform_publishers/           # Marketplace publishers
│   ├── etsy_publisher.py         # Etsy API v3 integration
│   └── gumroad_publisher.py      # Gumroad API v2 integration
│
├── data/                          # Data storage
│   └── products.db               # SQLite database
│
├── output/                        # Generated products
│   ├── products/                 # Product files
│   ├── marketing/                # Marketing content
│   └── prompts/                  # Prompt packs
│
└── logs/                          # Application logs
    ├── factory.log               # Main factory logs
    └── trend_monitor.log         # Trend monitoring logs
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/digital-product-factory.git
cd digital-product-factory

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Configuration

Edit `.env` with your API keys:

```bash
# Required: At least one AI provider
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional

# Optional: Marketplace integration
ETSY_CLIENT_ID=your_etsy_client_id
ETSY_CLIENT_SECRET=your_etsy_secret
ETSY_SHOP_ID=your_shop_id
GUMROAD_ACCESS_TOKEN=your_gumroad_token

# Flask settings
FLASK_SECRET_KEY=your_secret_key_here
```

### 3. Run the Factory

**Automatic Mode** (discover and create from trends):

```bash
python factory.py
```

**Manual Mode** (Python API):

```python
from factory import DigitalProductFactory

# Initialize
factory = DigitalProductFactory()

# Auto-discover and create 5 products
products = factory.discover_and_create(
    count=5,
    min_opportunity_score=60,
    publish_immediately=False  # Save for review
)

# Or create specific product
product = factory.create_product_from_opportunity(
    opportunity={
        'keyword': 'Product photography prompts',
        'product_type': 'midjourney_prompts',
        'niche': 'photography',
        'recommended_price': 12.00
    }
)
```

### 4. Review Dashboard

Start the review dashboard:

```bash
cd review_dashboard
flask --app app run --debug
```

Visit: `http://localhost:5000`

Features:
- View all pending products
- Filter by type, niche, status
- Review product details and marketing
- Approve, edit, or reject products
- Download product files
- View analytics and statistics

## 📊 Workflow

### Automated Discovery & Creation

```
1. Trend Discovery
   ↓ Google Trends API
   ↓ Claude AI Analysis
   → Identifies profitable opportunities

2. Product Creation
   ↓ AIPromptCreator
   → Generates 50+ prompts
   → Creates PDF guide
   → Generates preview images

3. Marketing Generation
   ↓ MarketingContentGenerator
   → Etsy listing (SEO-optimized)
   → Instagram captions (5 variations)
   → Facebook ads (3 variations)
   → Pinterest content
   → 30-day social calendar

4. Database Storage
   ↓ ProductDB
   → Saves all product data
   → Status: pending (awaits review)

5. Review & Approval
   ↓ Review Dashboard
   → Manual review
   → Approve/Edit/Reject

6. Publishing
   ↓ Publishers
   → Etsy (via OAuth 2.0)
   → Gumroad (via API)
   → Status: published
```

## 🔧 Components

### Factory (Main Orchestration)

**File**: `factory.py`

The main entry point that coordinates all components:

```python
class DigitalProductFactory:
    def discover_and_create(count, min_score, publish)
    def create_product_from_opportunity(opportunity)
    def get_statistics()
```

**Key Features**:
- End-to-end automation
- Error recovery and retry logic
- Statistics tracking
- Multi-marketplace support

### Trend Monitor

**File**: `trend_monitor/trend_scraper.py`

Discovers profitable opportunities:

```python
class TrendMonitor:
    def fetch_google_trends(keywords, timeframe, geo)
    def analyze_with_claude(trend_data)
    def get_top_trends(limit, min_score)
```

**Analyzes**:
- Search volume and momentum
- Competition level
- Market demand
- Profitability potential

### Product Creators

**File**: `product_creators/prompt_creator.py`

Creates digital products:

```python
class AIPromptCreator:
    def create_midjourney_prompts(category, count)
    def create_chatgpt_prompts(niche, count)
    def create_prompt_pdf(prompts, title)
    def create_preview_images(prompts)
```

**Generates**:
- 50+ professional prompts
- PDF guide with TOC
- Preview images (3-5)
- JSON data export
- README documentation

### Marketing Generator

**File**: `marketing_gen/content_creator.py`

Creates all marketing content:

```python
class MarketingContentGenerator:
    def generate_listing_content(product_data)
    def generate_social_calendar(product_data, days)
    def optimize_seo(title, tags)
```

**Creates**:
- Etsy listings (800-1000 words, 13 tags)
- Instagram captions (5 variations)
- Facebook ads (3 variations)
- Pinterest pins
- 30-day content calendar

### Database

**File**: `database.py`

Thread-safe SQLite database:

```python
class ProductDB:
    def save_product(product_data)
    def get_pending_products(limit)
    def update_product_status(product_id, status)
    def get_stats()
```

**Features**:
- Thread-safe operations
- Parameterized queries (SQL injection prevention)
- Indexes for performance
- Comprehensive product metadata

### Review Dashboard

**File**: `review_dashboard/app.py`

Flask web application for product review:

**Routes**:
- `GET /` - Product grid with filters
- `GET /product/<id>` - Detailed review page
- `POST /approve/<id>` - Approve product
- `POST /edit/<id>` - Edit product
- `POST /reject/<id>` - Reject product
- `GET /stats` - Analytics dashboard

**Security**:
- CSRF protection (Flask-WTF)
- Secure file downloads
- Input validation
- Session management

### Publishers

**Etsy Publisher** (`platform_publishers/etsy_publisher.py`):
- OAuth 2.0 authentication
- Automatic token refresh
- Draft listing creation
- Digital file uploads
- Image uploads with ranking
- Rate limiting (10 req/sec)

**Gumroad Publisher** (`platform_publishers/gumroad_publisher.py`):
- Simple token authentication
- Product creation
- File uploads
- Cover image uploads
- Enable/disable products
- Rate limiting (60 req/min)

## 🎯 Use Cases

### 1. Passive Income Generation
```bash
# Run factory to discover and create 10 products
python factory.py

# Review in dashboard
cd review_dashboard && flask run

# Approve and publish
# Monitor sales on Etsy/Gumroad
```

### 2. Trend-Based Product Launch
```python
from factory import DigitalProductFactory

factory = DigitalProductFactory()

# Find trending opportunities
trends = factory.trend_monitor.get_top_trends(limit=10)

# Create products for top 3 trends
for trend in trends[:3]:
    factory.create_product_from_opportunity(
        opportunity=trend,
        publish_immediately=True
    )
```

### 3. Niche-Specific Products
```python
# Create ChatGPT prompts for social media marketing
product = factory._create_chatgpt_pack(
    niche='social media marketing',
    count=50
)

# Generate marketing
marketing = factory._generate_marketing(
    keyword='Social Media Prompts',
    product_type='chatgpt_prompts',
    niche='marketing',
    price=15.00,
    opportunity={}
)
```

## 📈 Best Practices

### Trend Discovery
1. Run trend analysis weekly
2. Focus on opportunity scores > 70
3. Monitor momentum and demand
4. Target low-competition niches

### Product Creation
1. Generate 50+ prompts for value
2. Include usage guide in PDF
3. Create eye-catching preview images
4. Organize by category

### Marketing
1. Use all 13 Etsy tags
2. A/B test Instagram captions
3. Follow social calendar consistently
4. Update SEO quarterly

### Publishing
1. Always review before publishing
2. Test products before going live
3. Monitor performance metrics
4. Iterate based on sales data

## 🔐 Security

- **Environment Variables**: Never commit `.env` file
- **API Keys**: Use read-only keys when possible
- **CSRF Protection**: Enabled on all POST endpoints
- **SQL Injection**: Parameterized queries throughout
- **File Security**: Whitelisted file types only
- **Session Security**: HttpOnly, SameSite cookies

## 📊 Monitoring & Analytics

### Factory Statistics
```python
stats = factory.get_statistics()
# Returns:
# - Products created
# - Products published
# - Error count
# - Database stats
# - Publisher status
```

### Dashboard Analytics
- Total products by status
- Approval rate
- Top-performing niches
- Revenue tracking
- Trending keywords

## 🐛 Troubleshooting

### Common Issues

**No AI provider available**
```bash
# Ensure at least one API key is set
export ANTHROPIC_API_KEY=your_key_here
```

**Database locked error**
```python
# Database is thread-safe, but check for:
# - Multiple processes accessing same database
# - File permission issues
```

**Trend data not loading**
```bash
# Check rate limits
# Google Trends: 100 requests/hour
# Clear cache if needed
```

**CSRF token errors**
```bash
# Ensure FLASK_SECRET_KEY is set
# Check browser allows cookies
```

## 📝 Configuration

Edit `config.yaml`:

```yaml
# API Rate Limits
api_rate_limits:
  anthropic:
    requests_per_minute: 50
  google_trends:
    requests_per_hour: 100

# Pricing Ranges
pricing:
  notion_templates:
    min: 5
    max: 25
  digital_planners:
    min: 8
    max: 35
  prompt_packs:
    min: 10
    max: 30

# Trend Monitoring
trend_monitoring:
  keywords:
    - notion template 2025
    - digital planner aesthetic
    - midjourney prompts
  check_interval_hours: 24

# Content Generation
content_generation:
  preferred_model: anthropic
  fallback_model: gemini
```

## 🔄 Development

### Adding New Product Types

1. Create product creator in `product_creators/`:
```python
class MyProductCreator:
    def create_product(self, data):
        # Implementation
        pass
```

2. Add to factory in `factory.py`:
```python
def _create_my_product(self, keyword, niche):
    creator = MyProductCreator()
    return creator.create_product(...)
```

3. Update trend analysis prompt to recognize new type

### Adding New Publishers

1. Create publisher in `platform_publishers/`:
```python
class MyPlatformPublisher:
    def publish_product(self, product_data):
        # API integration
        pass
```

2. Initialize in factory:
```python
self.my_publisher = self._initialize_my_platform()
```

3. Add publishing logic in `_publish_product()`

## 📚 API Reference

See individual module documentation:
- [Factory API](factory.py) - Main orchestration
- [Trend Monitor API](trend_monitor/trend_scraper.py) - Trend discovery
- [Product Creator API](product_creators/prompt_creator.py) - Product generation
- [Marketing Generator API](marketing_gen/content_creator.py) - Marketing content
- [Database API](database.py) - Data storage
- [Publishers API](platform_publishers/) - Marketplace publishing
- [Review Dashboard API](review_dashboard/README.md) - Web interface

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

[Add license information]

## 🙏 Acknowledgments

- Built with Claude 3.5 Sonnet by Anthropic
- Google Trends API via pytrends
- Flask web framework
- ReportLab for PDF generation
- Pillow for image processing

## 📞 Support

For issues or questions:
- Check logs in `logs/` directory
- Review troubleshooting section
- Open GitHub issue

---

**Built with ❤️ by Digital Product Factory**

*Automate. Create. Profit.*
