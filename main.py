#!/usr/bin/env python3
"""
Digital Product Factory - Main Orchestration Script

This script orchestrates the entire automated workflow:
- Daily trend monitoring and product creation
- Hourly processing of approved products for publishing
- Regular analytics updates

Usage:
    python main.py              # Run scheduled automation
    python main.py --once       # Run once and exit (for testing)
    python main.py --generate   # Run product generation once
    python main.py --publish    # Run publishing once
    python main.py --analytics  # Run analytics once
"""

import os
import sys
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import time
import json

# Add digital-product-factory to path
sys.path.insert(0, str(Path(__file__).parent / 'digital-product-factory'))

import schedule
from dotenv import load_dotenv

# Import factory components
from factory import DigitalProductFactory
from database import ProductDB

# Load environment variables
load_dotenv()

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Create formatters
console_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler (INFO and above)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler (DEBUG and above)
file_handler = logging.FileHandler(LOG_DIR / 'main.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Error handler (separate file for errors)
error_handler = logging.FileHandler(LOG_DIR / 'errors.log')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(file_formatter)
logger.addHandler(error_handler)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_flag = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def send_notification(title: str, message: str, level: str = "info"):
    """
    Send notification about important events.

    Args:
        title: Notification title
        message: Notification message
        level: Notification level (info, warning, error)
    """
    # Log the notification
    log_func = getattr(logger, level, logger.info)
    log_func(f"NOTIFICATION: {title} - {message}")

    # Save to notifications log
    notification_file = LOG_DIR / 'notifications.json'

    notification = {
        'timestamp': datetime.now().isoformat(),
        'title': title,
        'message': message,
        'level': level
    }

    try:
        # Append to notifications file
        notifications = []
        if notification_file.exists():
            with open(notification_file, 'r') as f:
                notifications = json.load(f)

        notifications.append(notification)

        # Keep only last 100 notifications
        notifications = notifications[-100:]

        with open(notification_file, 'w') as f:
            json.dump(notifications, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to save notification: {e}")

    # TODO: Add email/SMS/Slack integration here
    # Example:
    # if level == "error":
    #     send_email(title, message)


def daily_product_generation():
    """
    Daily product generation workflow.

    - Runs trend monitoring
    - Selects top 3 trends
    - Creates products for each trend
    - Generates marketing content
    - Saves to database as "pending"
    - Sends summary notification
    """
    logger.info("=" * 80)
    logger.info("STARTING DAILY PRODUCT GENERATION")
    logger.info("=" * 80)

    start_time = datetime.now()
    stats = {
        'trends_analyzed': 0,
        'products_created': 0,
        'products_failed': 0,
        'errors': []
    }

    try:
        # Initialize factory
        logger.info("Initializing Digital Product Factory...")
        factory = DigitalProductFactory()

        # Run discovery and creation
        logger.info("Discovering trending opportunities...")
        products = factory.discover_and_create(
            count=3,  # Top 3 trends
            min_opportunity_score=60,
            publish_immediately=False  # Save for review
        )

        stats['products_created'] = len(products)
        stats['trends_analyzed'] = 3

        # Log created products
        logger.info(f"\n{'=' * 80}")
        logger.info("PRODUCT GENERATION SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Products created: {len(products)}")

        for i, product in enumerate(products, 1):
            logger.info(f"\n{i}. {product.get('title', 'Unknown')}")
            logger.info(f"   Type: {product.get('type', 'N/A')}")
            logger.info(f"   Niche: {product.get('niche', 'N/A')}")
            logger.info(f"   Price: ${product.get('price', 0)}")
            logger.info(f"   Status: {product.get('status', 'N/A')}")

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nGeneration completed in {duration:.1f} seconds")

        # Send success notification
        send_notification(
            title="Daily Product Generation Complete",
            message=f"Successfully created {len(products)} products in {duration:.1f}s",
            level="info"
        )

    except Exception as e:
        error_msg = f"Daily product generation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)

        # Send error notification
        send_notification(
            title="Product Generation Failed",
            message=error_msg,
            level="error"
        )

    finally:
        # Save stats
        stats_file = LOG_DIR / f"generation_stats_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            with open(stats_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds(),
                    **stats
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

        logger.info("=" * 80)


def process_approved_products():
    """
    Process and publish approved products.

    - Gets all approved products from database
    - Publishes to selected platforms (Etsy, Gumroad)
    - Updates database with listing URLs
    - Changes status to "published"
    - Logs success/failure
    """
    logger.info("=" * 80)
    logger.info("PROCESSING APPROVED PRODUCTS")
    logger.info("=" * 80)

    start_time = datetime.now()
    stats = {
        'products_processed': 0,
        'products_published': 0,
        'products_failed': 0,
        'platforms': {'etsy': 0, 'gumroad': 0},
        'errors': []
    }

    try:
        # Initialize components
        logger.info("Initializing components...")
        db = ProductDB()
        factory = DigitalProductFactory()

        # Get approved products
        logger.info("Fetching approved products...")
        approved_products = db.get_products_by_status('approved')

        if not approved_products:
            logger.info("No approved products to process")
            return

        logger.info(f"Found {len(approved_products)} approved products")

        # Process each product
        for i, product in enumerate(approved_products, 1):
            product_id = product['id']
            product_title = product.get('title', 'Unknown')

            logger.info(f"\n[{i}/{len(approved_products)}] Processing: {product_title}")

            try:
                # Publish product
                result = factory._publish_product(product_id)

                # Update database with URLs
                metadata = json.loads(product.get('metadata', '{}'))
                metadata['publishing'] = {
                    'etsy_url': result.get('etsy_url'),
                    'gumroad_url': result.get('gumroad_url'),
                    'published_at': datetime.now().isoformat(),
                    'errors': result.get('errors', [])
                }

                db.update_product(product_id, {
                    'status': 'published',
                    'metadata': json.dumps(metadata)
                })

                # Update stats
                stats['products_processed'] += 1
                if result.get('etsy_url') or result.get('gumroad_url'):
                    stats['products_published'] += 1

                if result.get('etsy_url'):
                    stats['platforms']['etsy'] += 1
                if result.get('gumroad_url'):
                    stats['platforms']['gumroad'] += 1

                logger.info(f"✓ Published successfully")
                if result.get('etsy_url'):
                    logger.info(f"  Etsy: {result['etsy_url']}")
                if result.get('gumroad_url'):
                    logger.info(f"  Gumroad: {result['gumroad_url']}")

            except Exception as e:
                error_msg = f"Failed to publish {product_title}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                stats['products_failed'] += 1
                stats['errors'].append(error_msg)

                # Update status to failed
                try:
                    metadata = json.loads(product.get('metadata', '{}'))
                    metadata['publishing_error'] = {
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    db.update_product(product_id, {
                        'status': 'failed',
                        'metadata': json.dumps(metadata)
                    })
                except Exception as update_error:
                    logger.error(f"Failed to update product status: {update_error}")

        # Summary
        logger.info(f"\n{'=' * 80}")
        logger.info("PUBLISHING SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Products processed: {stats['products_processed']}")
        logger.info(f"Successfully published: {stats['products_published']}")
        logger.info(f"Failed: {stats['products_failed']}")
        logger.info(f"Etsy listings: {stats['platforms']['etsy']}")
        logger.info(f"Gumroad listings: {stats['platforms']['gumroad']}")

        # Send notification
        if stats['products_published'] > 0:
            send_notification(
                title="Products Published",
                message=f"Published {stats['products_published']} products (Etsy: {stats['platforms']['etsy']}, Gumroad: {stats['platforms']['gumroad']})",
                level="info"
            )

        if stats['products_failed'] > 0:
            send_notification(
                title="Publishing Errors",
                message=f"{stats['products_failed']} products failed to publish",
                level="warning"
            )

    except Exception as e:
        error_msg = f"Publishing workflow failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)

        send_notification(
            title="Publishing Workflow Failed",
            message=error_msg,
            level="error"
        )

    finally:
        # Save stats
        stats_file = LOG_DIR / f"publishing_stats_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        try:
            with open(stats_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds(),
                    **stats
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

        logger.info("=" * 80)


def update_analytics():
    """
    Update analytics from platforms.

    - Fetches view/sales data from platforms
    - Updates database
    - Generates performance reports
    """
    logger.info("=" * 80)
    logger.info("UPDATING ANALYTICS")
    logger.info("=" * 80)

    start_time = datetime.now()
    stats = {
        'products_updated': 0,
        'total_sales': 0,
        'total_revenue': 0.0,
        'errors': []
    }

    try:
        # Initialize components
        logger.info("Initializing components...")
        db = ProductDB()
        factory = DigitalProductFactory()

        # Get published products
        logger.info("Fetching published products...")
        published_products = db.get_products_by_status('published')

        if not published_products:
            logger.info("No published products to analyze")
            return

        logger.info(f"Found {len(published_products)} published products")

        # Update analytics for each product
        for i, product in enumerate(published_products, 1):
            product_id = product['id']
            product_title = product.get('title', 'Unknown')

            logger.info(f"\n[{i}/{len(published_products)}] Updating: {product_title}")

            try:
                metadata = json.loads(product.get('metadata', '{}'))
                publishing_info = metadata.get('publishing', {})

                analytics = {
                    'updated_at': datetime.now().isoformat(),
                    'platforms': {}
                }

                # Get Gumroad sales
                if factory.gumroad_publisher and publishing_info.get('gumroad_url'):
                    try:
                        # Extract product ID from URL or metadata
                        gumroad_product_id = publishing_info.get('gumroad_product_id')

                        if gumroad_product_id:
                            sales = factory.gumroad_publisher.get_product_sales(gumroad_product_id)

                            analytics['platforms']['gumroad'] = {
                                'sales_count': sales['sales_count'],
                                'revenue': sales['revenue'],
                                'currency': sales['currency']
                            }

                            stats['total_sales'] += sales['sales_count']
                            stats['total_revenue'] += sales['revenue']

                            logger.info(f"  Gumroad: {sales['sales_count']} sales, ${sales['revenue']:.2f}")
                    except Exception as e:
                        logger.warning(f"  Failed to get Gumroad analytics: {e}")

                # Get Etsy sales (would need Etsy API implementation)
                if factory.etsy_publisher and publishing_info.get('etsy_url'):
                    logger.info(f"  Etsy: Analytics not yet implemented")

                # Update database
                if analytics['platforms']:
                    metadata['analytics'] = analytics
                    db.update_product(product_id, {
                        'metadata': json.dumps(metadata)
                    })
                    stats['products_updated'] += 1

            except Exception as e:
                error_msg = f"Failed to update analytics for {product_title}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)

        # Generate summary report
        logger.info(f"\n{'=' * 80}")
        logger.info("ANALYTICS SUMMARY")
        logger.info(f"{'=' * 80}")
        logger.info(f"Products updated: {stats['products_updated']}")
        logger.info(f"Total sales: {stats['total_sales']}")
        logger.info(f"Total revenue: ${stats['total_revenue']:.2f}")

        # Save daily report
        report_file = LOG_DIR / f"analytics_report_{datetime.now().strftime('%Y%m%d')}.json"
        report = {
            'date': datetime.now().isoformat(),
            'summary': stats,
            'products': []
        }

        for product in published_products:
            try:
                metadata = json.loads(product.get('metadata', '{}'))
                analytics = metadata.get('analytics', {})
                if analytics.get('platforms'):
                    report['products'].append({
                        'title': product.get('title'),
                        'type': product.get('type'),
                        'price': product.get('price'),
                        'analytics': analytics
                    })
            except Exception as e:
                logger.warning(f"Failed to add product to report: {e}")

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved: {report_file}")

        # Send notification
        if stats['total_sales'] > 0:
            send_notification(
                title="Analytics Updated",
                message=f"Total sales: {stats['total_sales']}, Revenue: ${stats['total_revenue']:.2f}",
                level="info"
            )

    except Exception as e:
        error_msg = f"Analytics update failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        stats['errors'].append(error_msg)

        send_notification(
            title="Analytics Update Failed",
            message=error_msg,
            level="error"
        )

    finally:
        logger.info("=" * 80)


def run_scheduler():
    """Run the scheduled automation."""
    logger.info("=" * 80)
    logger.info("DIGITAL PRODUCT FACTORY - SCHEDULER STARTING")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now()}")
    logger.info(f"Log directory: {LOG_DIR.absolute()}")
    logger.info("")
    logger.info("Schedule:")
    logger.info("  - Daily product generation: 2:00 AM daily")
    logger.info("  - Process approved products: Every hour")
    logger.info("  - Update analytics: Every 6 hours")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)

    # Schedule jobs
    schedule.every().day.at("02:00").do(daily_product_generation)
    schedule.every().hour.do(process_approved_products)
    schedule.every(6).hours.do(update_analytics)

    # Send startup notification
    send_notification(
        title="Factory Started",
        message="Digital Product Factory automation is now running",
        level="info"
    )

    try:
        while not shutdown_flag:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")

    finally:
        logger.info("Shutting down gracefully...")
        send_notification(
            title="Factory Stopped",
            message="Digital Product Factory automation has been stopped",
            level="info"
        )
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Digital Product Factory - Automated Orchestration"
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run all tasks once and exit (for testing)'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Run daily product generation once'
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help='Run product publishing once'
    )
    parser.add_argument(
        '--analytics',
        action='store_true',
        help='Run analytics update once'
    )

    args = parser.parse_args()

    try:
        if args.generate:
            daily_product_generation()
        elif args.publish:
            process_approved_products()
        elif args.analytics:
            update_analytics()
        elif args.once:
            logger.info("Running all tasks once...")
            daily_product_generation()
            process_approved_products()
            update_analytics()
        else:
            run_scheduler()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        send_notification(
            title="Fatal Error",
            message=str(e),
            level="error"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
