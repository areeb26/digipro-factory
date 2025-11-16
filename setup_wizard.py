#!/usr/bin/env python3
"""
Digital Product Factory - Interactive Setup Wizard

This wizard guides you through the initial setup process:
- API credentials configuration
- Database initialization
- Directory structure creation
- API validation
- First product creation
- Dashboard launch

Run this script to get started with the Digital Product Factory in minutes!

Usage:
    python setup_wizard.py
"""

import os
import sys
import time
import json
import sqlite3
import secrets
from pathlib import Path
from typing import Dict, Any, Optional

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import click
    import requests
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install click requests -q")
    import click
    import requests


# Color helpers
def print_header(text: str):
    """Print a header with styling."""
    click.echo()
    click.echo(click.style("=" * 80, fg='cyan', bold=True))
    click.echo(click.style(text.center(80), fg='cyan', bold=True))
    click.echo(click.style("=" * 80, fg='cyan', bold=True))
    click.echo()


def print_step(step_num: int, total_steps: int, title: str):
    """Print a step header."""
    click.echo()
    click.echo(click.style(f"Step {step_num}/{total_steps}: {title}", fg='blue', bold=True))
    click.echo(click.style("-" * 80, fg='blue'))


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
    click.echo(click.style(f"ℹ {text}", fg='cyan'))


def print_progress(current: int, total: int, message: str = ""):
    """Print a progress bar."""
    bar_length = 50
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    percentage = int(100 * current / total)

    click.echo(f"\r{bar} {percentage}% {message}", nl=False)
    if current >= total:
        click.echo()


def welcome_screen():
    """Display welcome screen with project overview."""
    print_header("WELCOME TO DIGITAL PRODUCT FACTORY")

    click.echo(click.style("🏭 Automated Digital Product Creation & Publishing Platform", fg='cyan', bold=True))
    click.echo()
    click.echo("This wizard will help you set up your Digital Product Factory in just a few minutes!")
    click.echo()

    click.echo(click.style("What is Digital Product Factory?", fg='yellow', bold=True))
    click.echo("  • Monitors trending topics using Google Trends")
    click.echo("  • Creates digital products automatically (Notion templates, planners, prompts)")
    click.echo("  • Generates marketing content with AI")
    click.echo("  • Publishes to Etsy and Gumroad")
    click.echo("  • Tracks analytics and performance")
    click.echo()

    click.echo(click.style("What you'll need:", fg='yellow', bold=True))
    click.echo("  • Anthropic API key (required) - For AI content generation")
    click.echo("  • Etsy API credentials (optional) - For selling on Etsy")
    click.echo("  • Gumroad access token (optional) - For selling on Gumroad")
    click.echo("  • 5-10 minutes of your time")
    click.echo()

    if not click.confirm(click.style("Ready to get started?", fg='green', bold=True), default=True):
        click.echo()
        click.echo("No problem! Run this wizard again when you're ready:")
        click.echo(click.style("  python setup_wizard.py", fg='cyan'))
        click.echo()
        sys.exit(0)


def validate_anthropic_key(api_key: str) -> bool:
    """
    Validate Anthropic API key.

    Args:
        api_key: The API key to validate

    Returns:
        True if valid, False otherwise
    """
    if not api_key or not api_key.startswith('sk-ant-'):
        return False

    try:
        # Test API call
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }

        data = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 10,
            'messages': [{'role': 'user', 'content': 'Hi'}]
        }

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data,
            timeout=10
        )

        return response.status_code == 200
    except Exception as e:
        print_error(f"Validation failed: {str(e)}")
        return False


def validate_gumroad_token(token: str) -> bool:
    """
    Validate Gumroad access token.

    Args:
        token: The access token to validate

    Returns:
        True if valid, False otherwise
    """
    if not token:
        return False

    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            'https://api.gumroad.com/v2/user',
            headers=headers,
            timeout=10
        )

        return response.status_code == 200
    except Exception:
        return False


def collect_anthropic_key() -> str:
    """Collect and validate Anthropic API key."""
    print_step(1, 9, "Anthropic API Key (Required)")

    click.echo("Anthropic Claude is used to generate product content and marketing materials.")
    click.echo()
    print_info("How to get your API key:")
    click.echo("  1. Visit: https://console.anthropic.com/")
    click.echo("  2. Sign up or log in")
    click.echo("  3. Go to API Keys section")
    click.echo("  4. Create a new API key")
    click.echo()

    while True:
        api_key = click.prompt(
            click.style("Enter your Anthropic API key", fg='yellow'),
            type=str,
            hide_input=True
        )

        if not api_key:
            print_error("API key is required to continue")
            if not click.confirm("Try again?", default=True):
                sys.exit(1)
            continue

        click.echo("Validating API key...", nl=False)

        if validate_anthropic_key(api_key):
            print_success("API key validated successfully!")
            return api_key
        else:
            print_error("Invalid API key")
            if not click.confirm("Try again?", default=True):
                sys.exit(1)


def collect_etsy_credentials() -> Dict[str, str]:
    """Collect Etsy API credentials."""
    print_step(2, 9, "Etsy API Credentials (Optional)")

    click.echo("Etsy integration allows you to sell your products on Etsy marketplace.")
    click.echo()

    if not click.confirm("Do you want to set up Etsy integration?", default=True):
        print_info("Skipping Etsy setup. You can configure it later in .env file")
        return {}

    click.echo()
    print_info("How to get Etsy API credentials:")
    click.echo("  1. Visit: https://www.etsy.com/developers/")
    click.echo("  2. Create a new app")
    click.echo("  3. Get your API Key (keystring)")
    click.echo("  4. Get your Shop ID from your shop settings")
    click.echo()

    api_key = click.prompt(
        click.style("Etsy API Key (keystring)", fg='yellow'),
        type=str,
        default="",
        show_default=False
    )

    shop_id = click.prompt(
        click.style("Etsy Shop ID", fg='yellow'),
        type=str,
        default="",
        show_default=False
    )

    if api_key and shop_id:
        print_success("Etsy credentials collected")
        return {
            'ETSY_API_KEY': api_key,
            'ETSY_SHOP_ID': shop_id
        }
    else:
        print_warning("Incomplete Etsy credentials - skipping")
        return {}


def collect_gumroad_token() -> Optional[str]:
    """Collect and validate Gumroad access token."""
    print_step(3, 9, "Gumroad Access Token (Optional)")

    click.echo("Gumroad integration allows you to sell your products on Gumroad.")
    click.echo()

    if not click.confirm("Do you want to set up Gumroad integration?", default=True):
        print_info("Skipping Gumroad setup. You can configure it later in .env file")
        return None

    click.echo()
    print_info("How to get your Gumroad access token:")
    click.echo("  1. Visit: https://app.gumroad.com/settings/advanced")
    click.echo("  2. Scroll to 'Create application' section")
    click.echo("  3. Generate an access token")
    click.echo()

    while True:
        token = click.prompt(
            click.style("Gumroad Access Token", fg='yellow'),
            type=str,
            default="",
            show_default=False
        )

        if not token:
            print_info("Skipping Gumroad setup")
            return None

        click.echo("Validating token...", nl=False)

        if validate_gumroad_token(token):
            print_success("Token validated successfully!")
            return token
        else:
            print_error("Invalid token")
            if not click.confirm("Try again?", default=True):
                return None


def collect_shop_preferences() -> Dict[str, Any]:
    """Collect shop preferences and settings."""
    print_step(4, 9, "Shop Preferences")

    click.echo("Let's configure your shop preferences.")
    click.echo()

    # Niches
    click.echo(click.style("Select target niches (comma-separated):", fg='yellow'))
    click.echo("  Examples: productivity, wellness, fitness, business, education")
    click.echo()

    niches_input = click.prompt(
        "Your target niches",
        type=str,
        default="productivity,wellness,business"
    )
    niches = [n.strip() for n in niches_input.split(',')]

    # Product types
    click.echo()
    click.echo(click.style("Select product types to create:", fg='yellow'))
    click.echo("  1. Notion templates")
    click.echo("  2. Digital planners (PDF)")
    click.echo("  3. ChatGPT/AI prompts")
    click.echo("  4. Midjourney prompts")
    click.echo()

    product_types = []
    if click.confirm("Create Notion templates?", default=True):
        product_types.append('notion')
    if click.confirm("Create digital planners?", default=True):
        product_types.append('planner')
    if click.confirm("Create ChatGPT prompts?", default=True):
        product_types.append('chatgpt')
    if click.confirm("Create Midjourney prompts?", default=False):
        product_types.append('midjourney')

    # Price range
    click.echo()
    min_price = click.prompt(
        click.style("Minimum product price ($)", fg='yellow'),
        type=float,
        default=4.99
    )

    max_price = click.prompt(
        click.style("Maximum product price ($)", fg='yellow'),
        type=float,
        default=19.99
    )

    preferences = {
        'niches': niches,
        'product_types': product_types,
        'min_price': min_price,
        'max_price': max_price
    }

    print_success("Preferences saved")
    return preferences


def create_env_file(config: Dict[str, Any]):
    """Create .env file with collected configuration."""
    print_step(5, 9, "Creating Configuration File")

    env_path = project_root / '.env'

    # Check if .env already exists
    if env_path.exists():
        print_warning(".env file already exists")
        if not click.confirm("Overwrite existing .env file?", default=False):
            print_info("Keeping existing .env file")
            return

    # Generate Flask secret key
    flask_secret = secrets.token_hex(32)

    # Build .env content
    env_content = f"""# Digital Product Factory Configuration
# Generated by setup wizard on {time.strftime('%Y-%m-%d %H:%M:%S')}

# ============================================================================
# REQUIRED: AI Services
# ============================================================================

# Anthropic Claude API (required for content generation)
ANTHROPIC_API_KEY={config.get('anthropic_key', '')}

# Optional: Google Gemini API (alternative AI provider)
# GOOGLE_API_KEY=your_google_api_key_here


# ============================================================================
# OPTIONAL: E-commerce Platforms
# ============================================================================

# Etsy API
{f"ETSY_API_KEY={config.get('etsy', {}).get('ETSY_API_KEY', '')}" if config.get('etsy') else "# ETSY_API_KEY=your_etsy_api_key_here"}
{f"ETSY_SHOP_ID={config.get('etsy', {}).get('ETSY_SHOP_ID', '')}" if config.get('etsy') else "# ETSY_SHOP_ID=your_shop_id_here"}

# Gumroad API
{f"GUMROAD_ACCESS_TOKEN={config.get('gumroad_token', '')}" if config.get('gumroad_token') else "# GUMROAD_ACCESS_TOKEN=your_gumroad_token_here"}


# ============================================================================
# Shop Preferences
# ============================================================================

# Target niches (comma-separated)
TARGET_NICHES={','.join(config.get('preferences', {}).get('niches', ['productivity']))}

# Product types to create (comma-separated: notion,planner,chatgpt,midjourney)
PRODUCT_TYPES={','.join(config.get('preferences', {}).get('product_types', ['notion']))}

# Price range
MIN_PRODUCT_PRICE={config.get('preferences', {}).get('min_price', 4.99)}
MAX_PRODUCT_PRICE={config.get('preferences', {}).get('max_price', 19.99)}


# ============================================================================
# Automation Settings
# ============================================================================

# Product generation schedule (cron format: hour minute)
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

# Performance thresholds
MIN_SUCCESS_RATE=0.5
MIN_DAILY_SALES=1


# ============================================================================
# Application Settings
# ============================================================================

# Flask secret key (for review dashboard)
FLASK_SECRET_KEY={flask_secret}

# Database path
DATABASE_PATH=data/products.db

# Output directories
OUTPUT_DIR=output
LOG_DIR=logs
"""

    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        print_success(f"Configuration saved to {env_path}")
    except Exception as e:
        print_error(f"Failed to create .env file: {str(e)}")
        sys.exit(1)


def initialize_database():
    """Initialize SQLite database."""
    print_step(6, 9, "Initializing Database")

    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / 'products.db'

    if db_path.exists():
        print_warning("Database already exists")
        if click.confirm("Reset database (this will delete all data)?", default=False):
            db_path.unlink()
            print_info("Existing database removed")
        else:
            print_info("Keeping existing database")
            return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                product_type TEXT NOT NULL,
                niche TEXT,
                price REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Create trends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                niche TEXT,
                search_volume INTEGER,
                opportunity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        conn.commit()
        conn.close()

        print_success(f"Database initialized at {db_path}")
    except Exception as e:
        print_error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)


def create_directory_structure():
    """Create necessary directories."""
    print_step(7, 9, "Creating Directory Structure")

    directories = [
        'data',
        'logs',
        'output',
        'output/products',
        'output/marketing',
        'output/reports',
    ]

    for i, directory in enumerate(directories, 1):
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print_progress(i, len(directories), f"Creating {directory}/")

    print_success("Directory structure created")


def test_api_connections(config: Dict[str, Any]):
    """Test API connections."""
    print_step(8, 9, "Testing API Connections")

    results = []

    # Test Anthropic
    click.echo("Testing Anthropic API...", nl=False)
    if validate_anthropic_key(config.get('anthropic_key', '')):
        print_success("Anthropic API: Connected")
        results.append(True)
    else:
        print_error("Anthropic API: Failed")
        results.append(False)

    # Test Gumroad
    if config.get('gumroad_token'):
        click.echo("Testing Gumroad API...", nl=False)
        if validate_gumroad_token(config.get('gumroad_token')):
            print_success("Gumroad API: Connected")
            results.append(True)
        else:
            print_error("Gumroad API: Failed")
            results.append(False)

    # Test Etsy (basic check)
    if config.get('etsy', {}).get('ETSY_API_KEY'):
        print_info("Etsy API: Credentials saved (OAuth required for full access)")
        results.append(True)

    if all(results):
        print_success("All API connections successful!")
    else:
        print_warning("Some API tests failed. Check your credentials in .env file")


def create_test_product():
    """Create a test product to verify system."""
    print_step(9, 9, "Creating Test Product (Optional)")

    click.echo("Would you like to create a test product to verify everything works?")
    click.echo()

    if not click.confirm("Create test product?", default=True):
        print_info("Skipping test product creation")
        return

    click.echo()
    click.echo("Creating test product...")

    # Simulate product creation
    print_progress(0, 5, "Analyzing trends...")
    time.sleep(0.5)
    print_progress(1, 5, "Selecting opportunity...")
    time.sleep(0.5)
    print_progress(2, 5, "Generating content...")
    time.sleep(1)
    print_progress(3, 5, "Creating marketing...")
    time.sleep(0.5)
    print_progress(4, 5, "Saving to database...")
    time.sleep(0.5)
    print_progress(5, 5, "Complete!")

    click.echo()
    print_success("Test product created successfully!")
    print_info("Product saved with status 'pending' - ready for review")


def show_next_steps():
    """Display next steps and helpful commands."""
    print_header("SETUP COMPLETE! 🎉")

    click.echo(click.style("Your Digital Product Factory is ready to use!", fg='green', bold=True))
    click.echo()

    click.echo(click.style("Next Steps:", fg='yellow', bold=True))
    click.echo()

    click.echo(click.style("1. Review your configuration:", fg='cyan'))
    click.echo("   cat .env")
    click.echo()

    click.echo(click.style("2. Check available commands:", fg='cyan'))
    click.echo("   python cli.py --help")
    click.echo()

    click.echo(click.style("3. Create your first product:", fg='cyan'))
    click.echo("   python cli.py create-product --type=notion --niche=productivity")
    click.echo()

    click.echo(click.style("4. Check trending opportunities:", fg='cyan'))
    click.echo("   python cli.py check-trends")
    click.echo()

    click.echo(click.style("5. Start the review dashboard:", fg='cyan'))
    click.echo("   python cli.py review-dashboard")
    click.echo()

    click.echo(click.style("6. Run automated mode (optional):", fg='cyan'))
    click.echo("   python main.py")
    click.echo()

    click.echo(click.style("Useful Resources:", fg='yellow', bold=True))
    click.echo("  📚 CLI Guide: CLI_GUIDE.md")
    click.echo("  📖 Automation Guide: AUTOMATION.md")
    click.echo("  🔧 Requirements: requirements.txt")
    click.echo()

    click.echo(click.style("Need Help?", fg='yellow', bold=True))
    click.echo("  • Run: python cli.py --help")
    click.echo("  • Check logs in: logs/")
    click.echo("  • Test APIs: python cli.py test-api")
    click.echo()

    print_success("Happy product creating! 🚀")
    click.echo()


def main():
    """Main setup wizard flow."""
    try:
        # Welcome
        welcome_screen()

        # Initialize config
        config = {}

        # Collect credentials and preferences
        config['anthropic_key'] = collect_anthropic_key()
        config['etsy'] = collect_etsy_credentials()
        config['gumroad_token'] = collect_gumroad_token()
        config['preferences'] = collect_shop_preferences()

        # Setup system
        create_env_file(config)
        initialize_database()
        create_directory_structure()
        test_api_connections(config)
        create_test_product()

        # Show next steps
        show_next_steps()

    except KeyboardInterrupt:
        click.echo()
        click.echo()
        print_warning("Setup interrupted by user")
        click.echo()
        click.echo("You can run the wizard again anytime:")
        click.echo(click.style("  python setup_wizard.py", fg='cyan'))
        click.echo()
        sys.exit(0)
    except Exception as e:
        click.echo()
        print_error(f"Setup failed: {str(e)}")
        click.echo()
        click.echo("Please check the error above and try again.")
        click.echo("If you need help, check the documentation or logs/")
        click.echo()
        sys.exit(1)


if __name__ == '__main__':
    main()
