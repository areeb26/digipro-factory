#!/usr/bin/env python3
"""
Digital Product Factory - Command Line Interface

A user-friendly CLI for managing the Digital Product Factory.

Usage:
    python cli.py --help
    python cli.py create-product --type=prompts --niche=photography
    python cli.py check-trends
    python cli.py review-dashboard
    python cli.py publish --id=123 --platforms=etsy,gumroad
    python cli.py stats
    python cli.py init
    python cli.py test-api
    python cli.py backup
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
import json
import shutil

# Add digital-product-factory to path
sys.path.insert(0, str(Path(__file__).parent / 'digital-product-factory'))

import click
from dotenv import load_dotenv, set_key

# Import factory components
from factory import DigitalProductFactory
from database import ProductDB
from trend_monitor.trend_scraper import TrendMonitor
from platform_publishers.gumroad_publisher import GumroadPublisher
from platform_publishers.etsy_publisher import EtsyPublisher

# Load environment variables
load_dotenv()

# Color scheme
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a styled header."""
    click.echo()
    click.echo(click.style("=" * 80, fg='cyan'))
    click.echo(click.style(text.center(80), fg='cyan', bold=True))
    click.echo(click.style("=" * 80, fg='cyan'))
    click.echo()


def print_success(text: str):
    """Print success message."""
    click.echo(click.style(f"✓ {text}", fg='green', bold=True))


def print_error(text: str):
    """Print error message."""
    click.echo(click.style(f"✗ {text}", fg='red', bold=True))


def print_warning(text: str):
    """Print warning message."""
    click.echo(click.style(f"⚠ {text}", fg='yellow'))


def print_info(text: str):
    """Print info message."""
    click.echo(click.style(f"ℹ {text}", fg='blue'))


def confirm_action(message: str) -> bool:
    """Ask for confirmation."""
    return click.confirm(click.style(message, fg='yellow', bold=True))


@click.group()
@click.version_option(version='1.0.0', prog_name='Digital Product Factory')
def cli():
    """
    🏭 Digital Product Factory - Command Line Interface

    An intelligent system for creating, marketing, and publishing digital products.

    \b
    Quick Start:
        python cli.py init              # Setup for first time
        python cli.py check-trends      # Discover opportunities
        python cli.py create-product    # Create a product
        python cli.py review-dashboard  # Review in web UI
        python cli.py publish --id=123  # Publish to marketplaces
        python cli.py stats             # View statistics

    \b
    For detailed help on any command:
        python cli.py COMMAND --help
    """
    pass


@cli.command()
@click.option('--type', '-t',
              type=click.Choice(['prompts', 'midjourney', 'chatgpt', 'planner', 'notion'], case_sensitive=False),
              help='Type of product to create')
@click.option('--niche', '-n',
              help='Target niche/category (e.g., photography, marketing)')
@click.option('--title',
              help='Product title (optional, auto-generated if not provided)')
@click.option('--price', type=float,
              help='Product price in dollars (e.g., 12.99)')
@click.option('--count', type=int, default=50,
              help='Number of prompts/items to generate (default: 50)')
@click.option('--publish-now', is_flag=True,
              help='Publish immediately without review')
def create_product(type, niche, title, price, count, publish_now):
    """
    Create a single digital product.

    \b
    Examples:
        python cli.py create-product --type=prompts --niche=photography
        python cli.py create-product --type=chatgpt --niche=marketing --price=15.99
        python cli.py create-product --type=midjourney --niche=product-photography --count=100
    """
    print_header("CREATE DIGITAL PRODUCT")

    try:
        # Interactive prompts for missing parameters
        if not type:
            type = click.prompt(
                'Product type',
                type=click.Choice(['prompts', 'midjourney', 'chatgpt', 'planner', 'notion'], case_sensitive=False)
            )

        if not niche:
            niche = click.prompt('Target niche/category', type=str)
            niche = niche.strip()

        if not price:
            price = click.prompt('Product price (USD)', type=float, default=12.99)

        # Map type to internal format
        product_type_map = {
            'prompts': 'prompt_pack',
            'midjourney': 'midjourney_prompts',
            'chatgpt': 'chatgpt_prompts',
            'planner': 'digital_planner',
            'notion': 'notion_template'
        }
        internal_type = product_type_map.get(type.lower(), 'prompt_pack')

        # Auto-generate title if not provided
        if not title:
            title = f"Professional {type.title()} - {niche.title()}"

        # Show summary
        print_info(f"Creating {type} product for '{niche}' niche")
        print_info(f"Title: {title}")
        print_info(f"Price: ${price:.2f}")
        print_info(f"Count: {count} items")
        print_info(f"Publish immediately: {'Yes' if publish_now else 'No'}")
        click.echo()

        if not confirm_action("Proceed with product creation?"):
            print_warning("Cancelled")
            return

        # Initialize factory
        click.echo()
        with click.progressbar(length=100, label='Initializing factory') as bar:
            factory = DigitalProductFactory()
            bar.update(100)

        # Create opportunity data
        opportunity = {
            'keyword': title,
            'product_type': internal_type,
            'niche': niche,
            'recommended_price': price,
            'demand_score': 75,
            'opportunity_score': 75,
            'competition_score': 50
        }

        # Create product with progress updates
        click.echo()
        click.echo(click.style("Creating product...", fg='cyan', bold=True))

        with click.progressbar(length=100, label='Generating content') as bar:
            bar.update(20)
            product = factory.create_product_from_opportunity(
                opportunity=opportunity,
                publish_immediately=publish_now
            )
            bar.update(80)

        # Show results
        click.echo()
        print_success("Product created successfully!")
        click.echo()
        click.echo(f"  Product ID: {click.style(str(product['id']), fg='cyan', bold=True)}")
        click.echo(f"  Title: {product.get('title', 'Unknown')}")
        click.echo(f"  Type: {product.get('type', 'Unknown')}")
        click.echo(f"  Price: ${product.get('price', 0):.2f}")
        click.echo(f"  Status: {click.style(product.get('status', 'Unknown'), fg='yellow', bold=True)}")

        # Parse metadata for file locations
        metadata = json.loads(product.get('metadata', '{}'))
        product_files = metadata.get('product_files', {})

        if product_files.get('package_dir'):
            click.echo(f"  Files: {product_files['package_dir']}")

        click.echo()
        if not publish_now:
            print_info("Product saved for review. Use 'python cli.py review-dashboard' to review.")
            print_info(f"To publish: python cli.py publish --id={product['id']}")

    except Exception as e:
        print_error(f"Failed to create product: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--limit', '-l', type=int, default=10,
              help='Number of trends to analyze (default: 10)')
@click.option('--min-score', type=int, default=60,
              help='Minimum opportunity score (default: 60)')
@click.option('--save', is_flag=True,
              help='Save results to file')
def check_trends(limit, min_score, save):
    """
    Analyze current trends and identify opportunities.

    \b
    Examples:
        python cli.py check-trends
        python cli.py check-trends --limit=20 --min-score=70
        python cli.py check-trends --save
    """
    print_header("TREND ANALYSIS")

    try:
        # Initialize trend monitor
        with click.progressbar(length=100, label='Initializing') as bar:
            monitor = TrendMonitor()
            bar.update(100)

        # Fetch trends
        click.echo()
        click.echo(click.style("Analyzing trending topics...", fg='cyan'))

        with click.progressbar(length=100, label='Analyzing trends') as bar:
            bar.update(30)
            trends = monitor.get_top_trends(limit=min(limit, 5), min_opportunity_score=min_score)
            bar.update(70)

        # Display results
        click.echo()
        if not trends:
            print_warning(f"No trends found with score >= {min_score}")
            return

        print_success(f"Found {len(trends)} opportunities")
        click.echo()

        for i, trend in enumerate(trends, 1):
            click.echo(click.style(f"{i}. {trend.get('keyword', 'Unknown')}", fg='cyan', bold=True))
            click.echo(f"   Product Type: {trend.get('product_type', 'N/A')}")
            click.echo(f"   Niche: {trend.get('niche', 'N/A')}")
            click.echo(f"   Opportunity Score: {click.style(str(trend.get('opportunity_score', 0)) + '/100', fg='green', bold=True)}")
            click.echo(f"   Demand: {trend.get('demand_score', 0)}/100")
            click.echo(f"   Competition: {trend.get('competition_score', 0)}/100")
            click.echo(f"   Recommended Price: ${trend.get('recommended_price', 0):.2f}")

            reasoning = trend.get('reasoning', '')
            if reasoning:
                click.echo(f"   Reasoning: {reasoning[:150]}...")
            click.echo()

        # Save option
        if save:
            filename = f"trends_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(trends, f, indent=2)
            print_success(f"Results saved to {filename}")

    except Exception as e:
        print_error(f"Trend analysis failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--port', '-p', type=int, default=5000,
              help='Port to run on (default: 5000)')
@click.option('--host', default='127.0.0.1',
              help='Host to bind to (default: 127.0.0.1)')
@click.option('--debug', is_flag=True,
              help='Run in debug mode')
def review_dashboard(port, host, debug):
    """
    Start the web-based review dashboard.

    \b
    The dashboard allows you to:
    - View all pending products
    - Preview product details and marketing
    - Approve, edit, or reject products
    - View statistics and analytics

    \b
    Example:
        python cli.py review-dashboard
        python cli.py review-dashboard --port=8080 --debug
    """
    print_header("REVIEW DASHBOARD")

    try:
        print_info(f"Starting dashboard on http://{host}:{port}")
        print_info("Press Ctrl+C to stop")
        click.echo()

        # Change to dashboard directory
        dashboard_dir = Path(__file__).parent / 'digital-product-factory' / 'review_dashboard'
        os.chdir(dashboard_dir)

        # Import and run Flask app
        from app import app
        app.run(host=host, port=port, debug=debug)

    except KeyboardInterrupt:
        click.echo()
        print_info("Dashboard stopped")
    except Exception as e:
        print_error(f"Failed to start dashboard: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--id', 'product_id', type=int, required=True,
              help='Product ID to publish')
@click.option('--platforms', default='gumroad,etsy',
              help='Comma-separated platforms (default: gumroad,etsy)')
@click.option('--force', is_flag=True,
              help='Force publish even if already published')
def publish(product_id, platforms, force):
    """
    Publish a product to marketplaces.

    \b
    Examples:
        python cli.py publish --id=123
        python cli.py publish --id=123 --platforms=gumroad
        python cli.py publish --id=123 --platforms=etsy,gumroad --force
    """
    print_header("PUBLISH PRODUCT")

    try:
        # Initialize components
        db = ProductDB()
        factory = DigitalProductFactory()

        # Get product
        product = db.get_product_by_id(product_id)
        if not product:
            print_error(f"Product {product_id} not found")
            sys.exit(1)

        # Check status
        current_status = product.get('status', 'unknown')
        if current_status == 'published' and not force:
            print_warning(f"Product is already published")
            if not confirm_action("Publish again anyway?"):
                return

        # Show product info
        print_info(f"Product: {product.get('title', 'Unknown')}")
        print_info(f"Type: {product.get('type', 'Unknown')}")
        print_info(f"Price: ${product.get('price', 0):.2f}")
        print_info(f"Platforms: {platforms}")
        click.echo()

        if not confirm_action("Proceed with publishing?"):
            print_warning("Cancelled")
            return

        # Parse platforms
        platform_list = [p.strip().lower() for p in platforms.split(',')]

        # Publish
        click.echo()
        with click.progressbar(length=100, label='Publishing') as bar:
            bar.update(20)
            result = factory._publish_product(product_id)
            bar.update(80)

        # Show results
        click.echo()
        published_to = []

        if result.get('gumroad_url') and 'gumroad' in platform_list:
            published_to.append('Gumroad')
            print_success(f"Published to Gumroad: {result['gumroad_url']}")

        if result.get('etsy_url') and 'etsy' in platform_list:
            published_to.append('Etsy')
            print_success(f"Published to Etsy: {result['etsy_url']}")

        if result.get('errors'):
            click.echo()
            print_warning("Some errors occurred:")
            for error in result['errors']:
                print_error(f"  {error}")

        if published_to:
            click.echo()
            print_success(f"Successfully published to: {', '.join(published_to)}")

    except Exception as e:
        print_error(f"Publishing failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--detailed', is_flag=True,
              help='Show detailed statistics')
@click.option('--export', type=click.Path(),
              help='Export statistics to JSON file')
def stats(detailed, export):
    """
    Display business statistics and analytics.

    \b
    Examples:
        python cli.py stats
        python cli.py stats --detailed
        python cli.py stats --export=stats.json
    """
    print_header("BUSINESS STATISTICS")

    try:
        # Get statistics
        db = ProductDB()
        factory = DigitalProductFactory()

        with click.progressbar(length=100, label='Gathering statistics') as bar:
            bar.update(30)
            stats_data = factory.get_statistics()
            db_stats = stats_data['database_stats']
            bar.update(70)

        # Display overview
        click.echo(click.style("Overview", fg='cyan', bold=True, underline=True))
        click.echo()
        click.echo(f"  Total Products: {click.style(str(db_stats.get('total_products', 0)), fg='cyan', bold=True)}")
        click.echo(f"  Pending: {db_stats.get('pending_products', 0)}")
        click.echo(f"  Approved: {db_stats.get('approved_products', 0)}")
        click.echo(f"  Published: {click.style(str(db_stats.get('published_products', 0)), fg='green', bold=True)}")
        click.echo(f"  Rejected: {db_stats.get('rejected_products', 0)}")
        click.echo()

        # Product types
        click.echo(click.style("Product Types", fg='cyan', bold=True, underline=True))
        click.echo()
        for product_type, count in db_stats.get('products_by_type', {}).items():
            click.echo(f"  {product_type}: {count}")
        click.echo()

        # Platform status
        publishers = stats_data.get('publishers', {})
        click.echo(click.style("Platform Integration", fg='cyan', bold=True, underline=True))
        click.echo()
        gumroad_status = click.style('✓ Enabled', fg='green') if publishers.get('gumroad_enabled') else click.style('✗ Disabled', fg='red')
        etsy_status = click.style('✓ Enabled', fg='green') if publishers.get('etsy_enabled') else click.style('✗ Disabled', fg='red')
        click.echo(f"  Gumroad: {gumroad_status}")
        click.echo(f"  Etsy: {etsy_status}")
        click.echo()

        # Detailed stats
        if detailed:
            click.echo(click.style("Top Niches", fg='cyan', bold=True, underline=True))
            click.echo()
            for niche, count in list(db_stats.get('products_by_niche', {}).items())[:5]:
                click.echo(f"  {niche}: {count}")
            click.echo()

        # Export option
        if export:
            with open(export, 'w') as f:
                json.dump(stats_data, f, indent=2)
            print_success(f"Statistics exported to {export}")

    except Exception as e:
        print_error(f"Failed to get statistics: {str(e)}")
        sys.exit(1)


@cli.command()
def init():
    """
    Initial setup wizard for first-time configuration.

    \b
    This wizard will help you:
    - Create .env file with API keys
    - Test API connections
    - Create necessary directories
    - Initialize database
    """
    print_header("SETUP WIZARD")

    click.echo(click.style("Welcome to Digital Product Factory!", fg='cyan', bold=True))
    click.echo()
    click.echo("This wizard will guide you through the initial setup.")
    click.echo()

    # Check if .env exists
    env_file = Path('.env')
    if env_file.exists():
        if not confirm_action(".env file already exists. Overwrite?"):
            print_warning("Keeping existing .env file")
            return

    # Create .env from template
    click.echo()
    click.echo(click.style("Step 1: API Configuration", fg='cyan', bold=True))
    click.echo()

    # Anthropic API
    click.echo("Anthropic Claude (Required - at least one AI provider needed)")
    anthropic_key = click.prompt('Enter Anthropic API key', default='', show_default=False)

    # Gemini API
    click.echo()
    click.echo("Google Gemini (Optional)")
    gemini_key = click.prompt('Enter Gemini API key', default='', show_default=False)

    # Gumroad
    click.echo()
    click.echo("Gumroad (Optional - for marketplace publishing)")
    gumroad_token = click.prompt('Enter Gumroad access token', default='', show_default=False)

    # Flask secret
    click.echo()
    flask_secret = os.urandom(24).hex()
    print_info(f"Generated Flask secret key")

    # Write .env file
    env_content = f"""# Digital Product Factory - Environment Configuration
# Generated: {datetime.now().isoformat()}

# ==========================================
# AI Providers (At least one required)
# ==========================================
ANTHROPIC_API_KEY={anthropic_key}
GEMINI_API_KEY={gemini_key}
OPENAI_API_KEY=

# ==========================================
# Marketplace Publishers (Optional)
# ==========================================
GUMROAD_ACCESS_TOKEN={gumroad_token}

# Etsy OAuth Credentials
ETSY_CLIENT_ID=
ETSY_CLIENT_SECRET=
ETSY_REDIRECT_URI=http://localhost:8080/callback
ETSY_SHOP_ID=
ETSY_ACCESS_TOKEN=
ETSY_REFRESH_TOKEN=
ETSY_TOKEN_EXPIRES_AT=

# ==========================================
# Flask Configuration
# ==========================================
FLASK_SECRET_KEY={flask_secret}
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    print_success(".env file created")

    # Create directories
    click.echo()
    click.echo(click.style("Step 2: Creating directories", fg='cyan', bold=True))
    click.echo()

    directories = ['logs', 'data', 'output', 'output/products', 'output/marketing', 'output/prompts']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        click.echo(f"  ✓ {directory}/")

    print_success("Directories created")

    # Initialize database
    click.echo()
    click.echo(click.style("Step 3: Initializing database", fg='cyan', bold=True))
    click.echo()

    try:
        db = ProductDB()
        print_success("Database initialized")
    except Exception as e:
        print_error(f"Failed to initialize database: {e}")

    # Test APIs
    click.echo()
    if confirm_action("Test API connections now?"):
        click.echo()
        test_api_connections()

    # Done
    click.echo()
    print_header("SETUP COMPLETE!")
    click.echo()
    print_success("Digital Product Factory is ready to use!")
    click.echo()
    print_info("Next steps:")
    click.echo("  1. python cli.py check-trends       # Discover opportunities")
    click.echo("  2. python cli.py create-product     # Create your first product")
    click.echo("  3. python cli.py review-dashboard   # Review products")
    click.echo("  4. python cli.py publish --id=1     # Publish to marketplaces")
    click.echo()


@cli.command('test-api')
def test_api():
    """
    Test all API connections and credentials.

    \b
    Tests:
    - Anthropic Claude API
    - Google Gemini API
    - OpenAI API (if configured)
    - Gumroad API
    - Etsy API
    """
    print_header("API CONNECTION TEST")
    test_api_connections()


def test_api_connections():
    """Test all API connections."""
    results = {}

    # Test Anthropic
    click.echo(click.style("Testing Anthropic Claude...", fg='cyan'))
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print_success("Anthropic Claude: Connected")
        results['anthropic'] = True
    except Exception as e:
        print_error(f"Anthropic Claude: Failed - {str(e)}")
        results['anthropic'] = False

    # Test Gemini
    click.echo(click.style("Testing Google Gemini...", fg='cyan'))
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hi")
        print_success("Google Gemini: Connected")
        results['gemini'] = True
    except Exception as e:
        print_error(f"Google Gemini: Failed - {str(e)}")
        results['gemini'] = False

    # Test Gumroad
    click.echo(click.style("Testing Gumroad...", fg='cyan'))
    try:
        publisher = GumroadPublisher()
        user = publisher.verify_credentials()
        print_success(f"Gumroad: Connected as {user['name']}")
        results['gumroad'] = True
    except Exception as e:
        print_error(f"Gumroad: Failed - {str(e)}")
        results['gumroad'] = False

    # Test Etsy
    click.echo(click.style("Testing Etsy...", fg='cyan'))
    try:
        etsy = EtsyPublisher()
        print_success("Etsy: Configured (OAuth required for full access)")
        results['etsy'] = True
    except Exception as e:
        print_error(f"Etsy: Failed - {str(e)}")
        results['etsy'] = False

    # Summary
    click.echo()
    click.echo(click.style("Summary", fg='cyan', bold=True, underline=True))
    click.echo()

    connected = sum(1 for v in results.values() if v)
    total = len(results)

    if connected == total:
        print_success(f"All {total} services connected successfully!")
    elif connected > 0:
        print_warning(f"{connected}/{total} services connected")
    else:
        print_error("No services connected. Please check your .env configuration.")


@cli.command()
@click.option('--output', '-o', type=click.Path(),
              help='Output directory for backup (default: backups/)')
@click.option('--compress', is_flag=True,
              help='Compress backup into .tar.gz')
def backup(output, compress):
    """
    Backup database and product files.

    \b
    Creates a backup containing:
    - Database (products.db)
    - All product files
    - Marketing content
    - Configuration files

    \b
    Examples:
        python cli.py backup
        python cli.py backup --output=/path/to/backup
        python cli.py backup --compress
    """
    print_header("BACKUP DATA")

    try:
        # Create backup directory
        if not output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output = f"backups/backup_{timestamp}"

        backup_dir = Path(output)
        backup_dir.mkdir(parents=True, exist_ok=True)

        print_info(f"Creating backup in: {backup_dir}")
        click.echo()

        # Backup items
        items = [
            ('data/products.db', 'Database'),
            ('output/', 'Product files'),
            ('.env', 'Configuration'),
            ('digital-product-factory/config.yaml', 'Config file')
        ]

        with click.progressbar(items, label='Backing up', item_show_func=lambda x: x[1] if x else '') as bar:
            for source, name in bar:
                source_path = Path(source)
                if source_path.exists():
                    dest_path = backup_dir / source
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_path, dest_path)

        # Compress if requested
        if compress:
            click.echo()
            print_info("Compressing backup...")

            archive_name = f"{backup_dir}.tar.gz"
            shutil.make_archive(str(backup_dir), 'gztar', backup_dir.parent, backup_dir.name)
            shutil.rmtree(backup_dir)

            print_success(f"Backup compressed: {archive_name}")
        else:
            print_success(f"Backup complete: {backup_dir}")

        # Show size
        if compress:
            size = Path(archive_name).stat().st_size / (1024 * 1024)
            click.echo(f"  Size: {size:.2f} MB")

    except Exception as e:
        print_error(f"Backup failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
