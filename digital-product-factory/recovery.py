"""
Digital Product Factory - Recovery & Backup Module

This module provides backup, recovery, and maintenance features:
- Automated database backups
- Point-in-time recovery
- Failed operation retry
- Orphaned file cleanup
- Backup rotation and compression

Usage:
    from recovery import auto_backup, recover_from_backup, retry_failed_operations
    from recovery import clean_orphaned_files

    # Create backup
    backup_path = auto_backup()

    # Restore from backup
    recover_from_backup('2025-01-15')

    # Retry failed operations
    retry_failed_operations()

    # Clean orphaned files
    clean_orphaned_files()
"""

import os
import sys
import shutil
import sqlite3
import json
import gzip
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'recovery.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
BACKUP_DIR = Path(__file__).parent.parent / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = Path(__file__).parent.parent / os.getenv('DATABASE_PATH', 'data/products.db')
OUTPUT_DIR = Path(__file__).parent.parent / 'output'

# Backup retention
DAILY_BACKUPS_TO_KEEP = 30  # Keep 30 days of daily backups
WEEKLY_BACKUPS_TO_KEEP = 12  # Keep 12 weeks of weekly backups
MONTHLY_BACKUPS_TO_KEEP = 12  # Keep 12 months of monthly backups

# Compression age (days)
COMPRESS_AFTER_DAYS = 7


def auto_backup(compress: bool = False) -> Path:
    """
    Create automatic backup of database.

    Creates daily backups and manages retention policy:
    - Daily backups: Last 30 days
    - Weekly backups: Last 12 weeks (every Sunday)
    - Monthly backups: Last 12 months (1st of month)
    - Compresses backups older than 7 days

    Args:
        compress: Whether to compress the backup immediately

    Returns:
        Path to backup file

    Usage:
        backup_path = auto_backup()
        logger.info(f"Backup created: {backup_path}")
    """
    logger.info("Starting automatic backup...")

    if not DATABASE_PATH.exists():
        logger.error(f"Database not found: {DATABASE_PATH}")
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    # Create backup filename with timestamp
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')
    backup_filename = f"products_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_filename

    try:
        # Copy database
        shutil.copy2(DATABASE_PATH, backup_path)
        logger.info(f"Database backed up to: {backup_path}")

        # Verify backup
        if not _verify_backup(backup_path):
            logger.error("Backup verification failed")
            backup_path.unlink()
            raise Exception("Backup verification failed")

        # Compress if requested or if old enough
        if compress:
            backup_path = _compress_backup(backup_path)

        # Create backup metadata
        _save_backup_metadata(backup_path, {
            'timestamp': now.isoformat(),
            'size_bytes': backup_path.stat().st_size,
            'db_path': str(DATABASE_PATH),
            'compressed': str(backup_path).endswith('.gz')
        })

        # Cleanup old backups
        _cleanup_old_backups()

        logger.info(f"Backup completed successfully: {backup_path.name}")
        return backup_path

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        raise


def _verify_backup(backup_path: Path) -> bool:
    """
    Verify backup integrity.

    Args:
        backup_path: Path to backup file

    Returns:
        True if backup is valid, False otherwise
    """
    try:
        # Try to open and query backup
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = {'products', 'trends'}
        if not expected_tables.issubset(set(tables)):
            logger.error(f"Backup missing expected tables: {expected_tables - set(tables)}")
            conn.close()
            return False

        # Count records
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]

        conn.close()

        logger.info(f"Backup verification passed: {product_count} products")
        return True

    except Exception as e:
        logger.error(f"Backup verification failed: {str(e)}")
        return False


def _compress_backup(backup_path: Path) -> Path:
    """
    Compress backup file with gzip.

    Args:
        backup_path: Path to backup file

    Returns:
        Path to compressed backup
    """
    logger.info(f"Compressing backup: {backup_path.name}")

    compressed_path = backup_path.with_suffix(backup_path.suffix + '.gz')

    try:
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed backup
        backup_path.unlink()

        original_size = backup_path.stat().st_size if backup_path.exists() else 0
        compressed_size = compressed_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

        logger.info(f"Backup compressed: {compressed_size / 1024:.1f} KB (saved {ratio:.1f}%)")
        return compressed_path

    except Exception as e:
        logger.error(f"Compression failed: {str(e)}")
        if compressed_path.exists():
            compressed_path.unlink()
        return backup_path


def _save_backup_metadata(backup_path: Path, metadata: Dict[str, Any]):
    """Save backup metadata to JSON file."""
    metadata_path = backup_path.with_suffix('.json')

    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save backup metadata: {str(e)}")


def _cleanup_old_backups():
    """
    Cleanup old backups according to retention policy.

    Retention policy:
    - Keep all backups from last 30 days (daily)
    - Keep weekly backups (Sundays) from last 12 weeks
    - Keep monthly backups (1st of month) from last 12 months
    - Delete everything else
    """
    logger.info("Cleaning up old backups...")

    now = datetime.now()
    backups = sorted(BACKUP_DIR.glob('products_backup_*.db*'))

    # Categorize backups
    daily_cutoff = now - timedelta(days=DAILY_BACKUPS_TO_KEEP)
    weekly_cutoff = now - timedelta(weeks=WEEKLY_BACKUPS_TO_KEEP)
    monthly_cutoff = now - timedelta(days=MONTHLY_BACKUPS_TO_KEEP * 30)

    backups_to_keep = set()
    backups_to_delete = []
    backups_to_compress = []

    for backup_path in backups:
        # Parse timestamp from filename
        try:
            filename = backup_path.stem.replace('.db', '')  # Remove .db if present
            timestamp_str = filename.replace('products_backup_', '')
            backup_date = datetime.strptime(timestamp_str, '%Y-%m-%d_%H-%M-%S')
        except ValueError:
            logger.warning(f"Could not parse backup timestamp: {backup_path.name}")
            continue

        # Check if should keep
        age = now - backup_date

        # Keep all backups from last 30 days
        if backup_date >= daily_cutoff:
            backups_to_keep.add(backup_path)

            # Compress if older than 7 days and not already compressed
            if age.days >= COMPRESS_AFTER_DAYS and not str(backup_path).endswith('.gz'):
                backups_to_compress.append(backup_path)

        # Keep weekly backups (Sundays)
        elif backup_date >= weekly_cutoff and backup_date.weekday() == 6:
            backups_to_keep.add(backup_path)

        # Keep monthly backups (1st of month)
        elif backup_date >= monthly_cutoff and backup_date.day == 1:
            backups_to_keep.add(backup_path)

        else:
            backups_to_delete.append(backup_path)

    # Compress old backups
    for backup_path in backups_to_compress:
        try:
            if backup_path.exists():  # Check if still exists
                _compress_backup(backup_path)
        except Exception as e:
            logger.error(f"Failed to compress {backup_path.name}: {str(e)}")

    # Delete old backups
    for backup_path in backups_to_delete:
        try:
            backup_path.unlink()
            # Also delete metadata
            metadata_path = backup_path.with_suffix('.json')
            if metadata_path.exists():
                metadata_path.unlink()
            logger.info(f"Deleted old backup: {backup_path.name}")
        except Exception as e:
            logger.error(f"Failed to delete {backup_path.name}: {str(e)}")

    logger.info(f"Cleanup complete: kept {len(backups_to_keep)}, deleted {len(backups_to_delete)}")


def recover_from_backup(date_or_path: str, force: bool = False) -> bool:
    """
    Recover database from backup.

    Args:
        date_or_path: Date string (YYYY-MM-DD) or full path to backup
        force: Skip confirmation prompt

    Returns:
        True if recovery successful, False otherwise

    Usage:
        # Recover from date
        recover_from_backup('2025-01-15')

        # Recover from specific backup
        recover_from_backup('/path/to/backup.db.gz', force=True)
    """
    logger.info(f"Starting recovery from: {date_or_path}")

    # Find backup file
    if Path(date_or_path).exists():
        backup_path = Path(date_or_path)
    else:
        # Search for backup by date
        pattern = f"products_backup_{date_or_path}*.db*"
        backups = list(BACKUP_DIR.glob(pattern))

        if not backups:
            logger.error(f"No backup found for date: {date_or_path}")
            return False

        # Use most recent backup if multiple found
        backup_path = sorted(backups)[-1]

    logger.info(f"Using backup: {backup_path}")

    # Verify backup
    temp_path = None
    try:
        # Decompress if needed
        if str(backup_path).endswith('.gz'):
            logger.info("Decompressing backup...")
            temp_path = backup_path.with_suffix('')

            with gzip.open(backup_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            backup_to_verify = temp_path
        else:
            backup_to_verify = backup_path

        # Verify backup integrity
        if not _verify_backup(backup_to_verify):
            logger.error("Backup verification failed - cannot restore")
            if temp_path and temp_path.exists():
                temp_path.unlink()
            return False

        # Confirmation
        if not force:
            print(f"\nWARNING: This will replace your current database!")
            print(f"Current database: {DATABASE_PATH}")
            print(f"Backup to restore: {backup_path}")
            print(f"Backup date: {backup_path.stem}")
            response = input("\nContinue with recovery? (yes/no): ")

            if response.lower() not in ['yes', 'y']:
                logger.info("Recovery cancelled by user")
                if temp_path and temp_path.exists():
                    temp_path.unlink()
                return False

        # Create backup of current database
        if DATABASE_PATH.exists():
            logger.info("Creating backup of current database...")
            current_backup = DATABASE_PATH.parent / f"products_pre_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DATABASE_PATH, current_backup)
            logger.info(f"Current database backed up to: {current_backup}")

        # Restore from backup
        logger.info("Restoring database...")
        shutil.copy2(backup_to_verify, DATABASE_PATH)

        # Verify restored database
        if not _verify_backup(DATABASE_PATH):
            logger.error("Restored database verification failed!")
            return False

        logger.info("Database restored successfully!")

        # Log recovery
        _log_recovery(backup_path, DATABASE_PATH)

        return True

    except Exception as e:
        logger.error(f"Recovery failed: {str(e)}")
        return False

    finally:
        # Cleanup temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()


def _log_recovery(backup_path: Path, restored_to: Path):
    """Log recovery operation."""
    recovery_log = LOG_DIR / 'recovery_history.json'

    recovery_entry = {
        'timestamp': datetime.now().isoformat(),
        'backup_file': str(backup_path),
        'restored_to': str(restored_to),
        'backup_date': backup_path.stem
    }

    try:
        history = []
        if recovery_log.exists():
            with open(recovery_log, 'r') as f:
                history = json.load(f)

        history.append(recovery_entry)

        with open(recovery_log, 'w') as f:
            json.dump(history, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to log recovery: {str(e)}")


def retry_failed_operations(max_retries: int = 3) -> Dict[str, Any]:
    """
    Retry failed publishing operations.

    Finds products with status 'failed' and retries publishing
    with exponential backoff.

    Args:
        max_retries: Maximum retry attempts per product

    Returns:
        Dict with retry statistics

    Usage:
        results = retry_failed_operations()
        print(f"Retried: {results['retried']}, Succeeded: {results['succeeded']}")
    """
    logger.info("Starting retry of failed operations...")

    if not DATABASE_PATH.exists():
        logger.error("Database not found")
        return {'retried': 0, 'succeeded': 0, 'failed': 0}

    stats = {
        'retried': 0,
        'succeeded': 0,
        'failed': 0,
        'errors': []
    }

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get failed products
        cursor.execute("""
            SELECT id, title, product_type, metadata
            FROM products
            WHERE status = 'failed'
            ORDER BY created_at ASC
        """)

        failed_products = cursor.fetchall()
        logger.info(f"Found {len(failed_products)} failed products to retry")

        for product in failed_products:
            product_id = product['id']
            title = product['title']

            logger.info(f"Retrying product {product_id}: {title}")
            stats['retried'] += 1

            # Parse metadata
            metadata = json.loads(product['metadata'] or '{}')
            retry_count = metadata.get('retry_count', 0)

            if retry_count >= max_retries:
                logger.warning(f"Product {product_id} exceeded max retries ({max_retries})")
                stats['failed'] += 1
                continue

            # Exponential backoff delay
            delay = 2 ** retry_count
            logger.info(f"Waiting {delay}s before retry (attempt {retry_count + 1}/{max_retries})...")
            time.sleep(delay)

            # Attempt retry
            try:
                # Import here to avoid circular dependency
                sys.path.insert(0, str(Path(__file__).parent))
                from factory import DigitalProductFactory

                factory = DigitalProductFactory()
                result = factory._publish_product(product_id)

                # Update metadata
                metadata['retry_count'] = retry_count + 1
                metadata['last_retry'] = datetime.now().isoformat()
                metadata['publishing'] = result

                # Update status to published
                cursor.execute("""
                    UPDATE products
                    SET status = 'published', metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(metadata), product_id))

                conn.commit()

                logger.info(f"Product {product_id} published successfully on retry")
                stats['succeeded'] += 1

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Retry failed for product {product_id}: {error_msg}")

                # Update metadata
                metadata['retry_count'] = retry_count + 1
                metadata['last_retry'] = datetime.now().isoformat()
                metadata['last_error'] = error_msg

                cursor.execute("""
                    UPDATE products
                    SET metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(metadata), product_id))

                conn.commit()

                stats['failed'] += 1
                stats['errors'].append({
                    'product_id': product_id,
                    'title': title,
                    'error': error_msg
                })

        conn.close()

        logger.info(f"Retry complete: {stats['succeeded']} succeeded, {stats['failed']} failed")
        return stats

    except Exception as e:
        logger.error(f"Retry operation failed: {str(e)}")
        return stats


def clean_orphaned_files(dry_run: bool = False) -> Dict[str, Any]:
    """
    Clean up orphaned files not referenced in database.

    Finds files in output directory that don't have corresponding
    database records and optionally deletes or archives them.

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with cleanup statistics

    Usage:
        # See what would be deleted
        results = clean_orphaned_files(dry_run=True)

        # Actually delete
        results = clean_orphaned_files(dry_run=False)
    """
    logger.info("Starting orphaned file cleanup...")

    if not OUTPUT_DIR.exists():
        logger.info("Output directory doesn't exist")
        return {'orphaned': 0, 'deleted': 0, 'archived': 0}

    stats = {
        'orphaned': 0,
        'deleted': 0,
        'archived': 0,
        'freed_bytes': 0,
        'files': []
    }

    try:
        # Get all product IDs from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM products")
        valid_ids = {str(row[0]) for row in cursor.fetchall()}

        conn.close()

        logger.info(f"Found {len(valid_ids)} products in database")

        # Scan output directory
        for file_path in OUTPUT_DIR.rglob('*'):
            if not file_path.is_file():
                continue

            # Try to extract product ID from filename or path
            file_str = str(file_path)
            is_orphaned = True

            for product_id in valid_ids:
                if product_id in file_str:
                    is_orphaned = False
                    break

            if is_orphaned:
                file_size = file_path.stat().st_size
                stats['orphaned'] += 1
                stats['freed_bytes'] += file_size

                logger.info(f"Orphaned file: {file_path.relative_to(OUTPUT_DIR)}")

                stats['files'].append({
                    'path': str(file_path.relative_to(OUTPUT_DIR)),
                    'size_bytes': file_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })

                if not dry_run:
                    # Archive old files, delete recent ones
                    file_age_days = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days

                    if file_age_days > 30:
                        # Archive old files
                        archive_dir = BACKUP_DIR / 'archived_files'
                        archive_dir.mkdir(exist_ok=True)

                        archive_path = archive_dir / file_path.name
                        shutil.move(str(file_path), str(archive_path))

                        stats['archived'] += 1
                        logger.info(f"Archived: {file_path.name}")
                    else:
                        # Delete recent orphans
                        file_path.unlink()
                        stats['deleted'] += 1
                        logger.info(f"Deleted: {file_path.name}")

        if dry_run:
            logger.info(f"DRY RUN: Would clean {stats['orphaned']} orphaned files ({stats['freed_bytes'] / 1024 / 1024:.1f} MB)")
        else:
            logger.info(f"Cleaned {stats['deleted']} files, archived {stats['archived']}, freed {stats['freed_bytes'] / 1024 / 1024:.1f} MB")

        return stats

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return stats


def schedule_automated_maintenance():
    """
    Schedule automated maintenance tasks.

    Sets up:
    - Daily backups at 3 AM
    - Weekly cleanup of orphaned files
    - Monthly compression of old backups

    Usage:
        # Run in main.py or as separate service
        schedule_automated_maintenance()

        while True:
            schedule.run_pending()
            time.sleep(60)
    """
    try:
        import schedule
    except ImportError:
        logger.error("schedule library not installed. Install with: pip install schedule")
        return

    # Daily backup at 3 AM
    schedule.every().day.at("03:00").do(auto_backup)

    # Retry failed operations every 6 hours
    schedule.every(6).hours.do(retry_failed_operations)

    # Clean orphaned files weekly on Sunday at 4 AM
    schedule.every().sunday.at("04:00").do(lambda: clean_orphaned_files(dry_run=False))

    logger.info("Automated maintenance scheduled:")
    logger.info("  - Daily backups at 3:00 AM")
    logger.info("  - Retry failed operations every 6 hours")
    logger.info("  - Clean orphaned files: Sundays at 4:00 AM")


def main():
    """Main function for testing recovery features."""
    print("=" * 80)
    print("DIGITAL PRODUCT FACTORY - RECOVERY MODULE TEST")
    print("=" * 80)
    print()

    # Test 1: Backup
    print("1. Creating database backup...")
    print("-" * 80)
    try:
        backup_path = auto_backup()
        print(f"✓ Backup created: {backup_path}")
        print(f"  Size: {backup_path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"✗ Backup failed: {str(e)}")
    print()

    # Test 2: List backups
    print("2. Listing available backups...")
    print("-" * 80)
    backups = sorted(BACKUP_DIR.glob('products_backup_*.db*'))
    for backup in backups[-5:]:  # Show last 5
        size = backup.stat().st_size / 1024
        print(f"  {backup.name} ({size:.1f} KB)")
    print(f"\nTotal backups: {len(backups)}")
    print()

    # Test 3: Retry failed operations
    print("3. Retrying failed operations...")
    print("-" * 80)
    results = retry_failed_operations()
    print(f"  Retried: {results['retried']}")
    print(f"  Succeeded: {results['succeeded']}")
    print(f"  Failed: {results['failed']}")
    print()

    # Test 4: Orphaned files (dry run)
    print("4. Checking for orphaned files...")
    print("-" * 80)
    cleanup_results = clean_orphaned_files(dry_run=True)
    print(f"  Orphaned files: {cleanup_results['orphaned']}")
    print(f"  Total size: {cleanup_results['freed_bytes'] / 1024 / 1024:.1f} MB")
    if cleanup_results['files']:
        print("\n  Files found:")
        for file_info in cleanup_results['files'][:5]:
            print(f"    - {file_info['path']} ({file_info['size_bytes'] / 1024:.1f} KB)")
    print()

    print("=" * 80)
    print("RECOVERY TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"Backup directory: {BACKUP_DIR}")
    print(f"Recovery log: {LOG_DIR / 'recovery_history.json'}")


if __name__ == '__main__':
    main()
