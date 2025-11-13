"""
Database Manager Module

This module handles all database operations for the Digital Product Factory.
Provides thread-safe SQLite operations with proper error handling and indexing.

Features:
- Thread-safe database operations
- SQL injection prevention via parameterized queries
- Automatic schema initialization
- Indexes for performance optimization
- Comprehensive error handling
- Dashboard statistics

Author: Digital Product Factory
"""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_thread_local = threading.local()


def init_database(db_path: str = "data/products.db") -> None:
    """
    Initialize the SQLite database with all required tables and indexes.

    Creates the following tables:
    - products: Store product information
    - marketing_content: Store marketing content by platform
    - listings: Track published listings across platforms
    - trends: Store trend analysis data

    Args:
        db_path: Path to SQLite database file

    Raises:
        sqlite3.Error: If database initialization fails
    """
    logger.info(f"Initializing database at: {db_path}")

    # Ensure directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create products table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            niche TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            price REAL,
            file_path TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create marketing_content table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS marketing_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
        """)

        # Create listings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            listing_id TEXT,
            url TEXT,
            published_at TIMESTAMP,
            views INTEGER DEFAULT 0,
            sales INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
        """)

        # Create trends table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            demand_score INTEGER,
            competition_score INTEGER,
            search_volume INTEGER,
            category TEXT,
            source TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create indexes for performance
        logger.info("Creating database indexes...")

        # Products indexes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_status
        ON products (status)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_type
        ON products (type)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_niche
        ON products (niche)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_created_at
        ON products (created_at)
        """)

        # Marketing content indexes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_marketing_product_id
        ON marketing_content (product_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_marketing_platform
        ON marketing_content (platform)
        """)

        # Listings indexes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_listings_product_id
        ON listings (product_id)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_listings_platform
        ON listings (platform)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_listings_status
        ON listings (status)
        """)

        # Trends indexes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_keyword
        ON trends (keyword)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_demand_score
        ON trends (demand_score DESC)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trends_discovered_at
        ON trends (discovered_at)
        """)

        conn.commit()
        logger.info("✓ Database initialized successfully")
        logger.info("✓ Tables created: products, marketing_content, listings, trends")
        logger.info("✓ Indexes created for optimized queries")

    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    finally:
        conn.close()


class ProductDB:
    """
    Thread-safe database manager for Digital Product Factory.

    This class provides methods for managing products, marketing content,
    listings, and trends. All operations use parameterized queries to
    prevent SQL injection.

    Attributes:
        db_path: Path to SQLite database file
    """

    def __init__(self, db_path: str = "data/products.db"):
        """
        Initialize the ProductDB manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()

        # Initialize database if it doesn't exist
        if not Path(db_path).exists():
            init_database(db_path)

        logger.info(f"ProductDB initialized with database: {db_path}")

    @contextmanager
    def _get_connection(self):
        """
        Context manager for thread-safe database connections.

        Yields:
            sqlite3.Connection: Database connection

        Raises:
            sqlite3.Error: If connection fails
        """
        # Get or create thread-local connection
        if not hasattr(_thread_local, 'connection'):
            _thread_local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            _thread_local.connection.row_factory = sqlite3.Row

        conn = _thread_local.connection

        try:
            yield conn
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            conn.commit()

    def save_product(self, product_data: Dict[str, Any]) -> int:
        """
        Save a new product to the database.

        Args:
            product_data: Dictionary containing product information:
                - type: Product type (required)
                - niche: Product niche (required)
                - title: Product title (required)
                - description: Product description (optional)
                - price: Product price (optional)
                - file_path: Path to product files (optional)
                - status: Product status (default: 'draft')

        Returns:
            int: ID of the newly created product

        Raises:
            ValueError: If required fields are missing
            sqlite3.Error: If database operation fails

        Example:
            >>> db = ProductDB()
            >>> product_id = db.save_product({
            ...     'type': 'planner',
            ...     'niche': 'productivity',
            ...     'title': 'Daily Planner 2025',
            ...     'price': 12.00
            ... })
        """
        # Validate required fields
        required_fields = ['type', 'niche', 'title']
        for field in required_fields:
            if field not in product_data:
                raise ValueError(f"Missing required field: {field}")

        logger.info(f"Saving product: {product_data.get('title', 'Unknown')}")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                INSERT INTO products (type, niche, title, description, price, file_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    product_data.get('type'),
                    product_data.get('niche'),
                    product_data.get('title'),
                    product_data.get('description'),
                    product_data.get('price'),
                    product_data.get('file_path'),
                    product_data.get('status', 'draft')
                ))

                product_id = cursor.lastrowid
                logger.info(f"✓ Product saved with ID: {product_id}")
                return product_id

    def get_pending_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get products awaiting review (status='draft' or 'pending').

        Args:
            limit: Maximum number of products to return

        Returns:
            List of product dictionaries

        Example:
            >>> db = ProductDB()
            >>> pending = db.get_pending_products(limit=10)
            >>> print(f"Found {len(pending)} pending products")
        """
        logger.info("Fetching pending products...")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT * FROM products
            WHERE status IN ('draft', 'pending')
            ORDER BY created_at DESC
            LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            products = [dict(row) for row in rows]

            logger.info(f"✓ Found {len(products)} pending products")
            return products

    def update_product_status(self, product_id: int, status: str) -> bool:
        """
        Update the status of a product.

        Args:
            product_id: ID of the product to update
            status: New status ('draft', 'pending', 'approved', 'published', 'archived')

        Returns:
            bool: True if update was successful

        Raises:
            ValueError: If product_id doesn't exist

        Example:
            >>> db = ProductDB()
            >>> db.update_product_status(1, 'approved')
            True
        """
        valid_statuses = ['draft', 'pending', 'approved', 'published', 'archived']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        logger.info(f"Updating product {product_id} status to: {status}")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                UPDATE products
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (status, product_id))

                if cursor.rowcount == 0:
                    raise ValueError(f"Product with ID {product_id} not found")

                logger.info(f"✓ Product {product_id} status updated to {status}")
                return True

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a product by its ID.

        Args:
            product_id: ID of the product to retrieve

        Returns:
            Product dictionary or None if not found

        Example:
            >>> db = ProductDB()
            >>> product = db.get_product_by_id(1)
            >>> if product:
            ...     print(f"Found: {product['title']}")
        """
        logger.info(f"Fetching product with ID: {product_id}")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT * FROM products
            WHERE id = ?
            """, (product_id,))

            row = cursor.fetchone()

            if row:
                product = dict(row)
                logger.info(f"✓ Product found: {product['title']}")
                return product
            else:
                logger.warning(f"Product {product_id} not found")
                return None

    def save_marketing_content(self, product_id: int, content_dict: Dict[str, Any]) -> int:
        """
        Save marketing content for a product.

        Args:
            product_id: ID of the product
            content_dict: Dictionary containing marketing content:
                - platform: Platform name ('etsy', 'instagram', 'facebook', etc.)
                - content_type: Type of content ('listing', 'caption', 'ad', etc.)
                - content: The actual content (can be JSON string)

        Returns:
            int: Number of content items saved

        Raises:
            ValueError: If product doesn't exist

        Example:
            >>> db = ProductDB()
            >>> content = {
            ...     'etsy': {'title': 'My Product', 'description': '...'},
            ...     'instagram': {'captions': [...]}
            ... }
            >>> count = db.save_marketing_content(1, content)
        """
        logger.info(f"Saving marketing content for product {product_id}")

        # Verify product exists
        if not self.get_product_by_id(product_id):
            raise ValueError(f"Product with ID {product_id} not found")

        saved_count = 0

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Save content for each platform
                for platform, content in content_dict.items():
                    if platform == 'metadata':
                        continue  # Skip metadata

                    # Convert content to JSON string if it's a dict
                    import json
                    content_str = json.dumps(content) if isinstance(content, dict) else str(content)

                    cursor.execute("""
                    INSERT INTO marketing_content (product_id, platform, content_type, content)
                    VALUES (?, ?, ?, ?)
                    """, (product_id, platform, 'listing', content_str))

                    saved_count += 1

                logger.info(f"✓ Saved {saved_count} marketing content items for product {product_id}")
                return saved_count

    def save_listing(self, listing_data: Dict[str, Any]) -> int:
        """
        Save a published listing to the database.

        Args:
            listing_data: Dictionary containing listing information:
                - product_id: ID of the product (required)
                - platform: Platform name (required)
                - listing_id: Platform-specific listing ID (optional)
                - url: URL to the listing (optional)
                - published_at: Publication timestamp (optional)

        Returns:
            int: ID of the newly created listing

        Raises:
            ValueError: If required fields are missing

        Example:
            >>> db = ProductDB()
            >>> listing_id = db.save_listing({
            ...     'product_id': 1,
            ...     'platform': 'etsy',
            ...     'listing_id': '123456789',
            ...     'url': 'https://etsy.com/listing/123456789'
            ... })
        """
        required_fields = ['product_id', 'platform']
        for field in required_fields:
            if field not in listing_data:
                raise ValueError(f"Missing required field: {field}")

        logger.info(f"Saving listing for product {listing_data['product_id']} on {listing_data['platform']}")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                INSERT INTO listings (product_id, platform, listing_id, url, published_at)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    listing_data.get('product_id'),
                    listing_data.get('platform'),
                    listing_data.get('listing_id'),
                    listing_data.get('url'),
                    listing_data.get('published_at', datetime.now().isoformat())
                ))

                listing_id = cursor.lastrowid
                logger.info(f"✓ Listing saved with ID: {listing_id}")
                return listing_id

    def update_listing_stats(self, listing_id: int, views: Optional[int] = None,
                           sales: Optional[int] = None, revenue: Optional[float] = None) -> bool:
        """
        Update statistics for a listing.

        Args:
            listing_id: ID of the listing
            views: Number of views (optional)
            sales: Number of sales (optional)
            revenue: Total revenue (optional)

        Returns:
            bool: True if update was successful

        Example:
            >>> db = ProductDB()
            >>> db.update_listing_stats(1, views=150, sales=5, revenue=60.00)
            True
        """
        logger.info(f"Updating stats for listing {listing_id}")

        updates = []
        params = []

        if views is not None:
            updates.append("views = ?")
            params.append(views)

        if sales is not None:
            updates.append("sales = ?")
            params.append(sales)

        if revenue is not None:
            updates.append("revenue = ?")
            params.append(revenue)

        if not updates:
            logger.warning("No stats to update")
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(listing_id)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = f"UPDATE listings SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)

                if cursor.rowcount == 0:
                    raise ValueError(f"Listing with ID {listing_id} not found")

                logger.info(f"✓ Listing {listing_id} stats updated")
                return True

    def save_trend(self, trend_data: Dict[str, Any]) -> int:
        """
        Save trend analysis data to the database.

        Args:
            trend_data: Dictionary containing trend information:
                - keyword: Trend keyword (required)
                - demand_score: Demand score 0-100 (optional)
                - competition_score: Competition score 0-100 (optional)
                - search_volume: Estimated search volume (optional)
                - category: Trend category (optional)
                - source: Data source (optional)

        Returns:
            int: ID of the newly created trend

        Example:
            >>> db = ProductDB()
            >>> trend_id = db.save_trend({
            ...     'keyword': 'digital planner 2025',
            ...     'demand_score': 85,
            ...     'competition_score': 45,
            ...     'category': 'productivity'
            ... })
        """
        if 'keyword' not in trend_data:
            raise ValueError("Missing required field: keyword")

        logger.info(f"Saving trend: {trend_data['keyword']}")

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                INSERT INTO trends (keyword, demand_score, competition_score, search_volume, category, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    trend_data.get('keyword'),
                    trend_data.get('demand_score'),
                    trend_data.get('competition_score'),
                    trend_data.get('search_volume'),
                    trend_data.get('category'),
                    trend_data.get('source')
                ))

                trend_id = cursor.lastrowid
                logger.info(f"✓ Trend saved with ID: {trend_id}")
                return trend_id

    def get_top_trends(self, limit: int = 20, min_demand_score: int = 60) -> List[Dict[str, Any]]:
        """
        Get top trending keywords based on demand score.

        Args:
            limit: Maximum number of trends to return
            min_demand_score: Minimum demand score threshold

        Returns:
            List of trend dictionaries sorted by demand score

        Example:
            >>> db = ProductDB()
            >>> trends = db.get_top_trends(limit=10, min_demand_score=70)
            >>> for trend in trends:
            ...     print(f"{trend['keyword']}: {trend['demand_score']}")
        """
        logger.info(f"Fetching top {limit} trends (min demand: {min_demand_score})")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT * FROM trends
            WHERE demand_score >= ?
            ORDER BY demand_score DESC, discovered_at DESC
            LIMIT ?
            """, (min_demand_score, limit))

            rows = cursor.fetchall()
            trends = [dict(row) for row in rows]

            logger.info(f"✓ Found {len(trends)} top trends")
            return trends

    def get_stats(self) -> Dict[str, Any]:
        """
        Get dashboard statistics for all products and listings.

        Returns:
            Dictionary containing:
                - total_products: Total number of products
                - products_by_status: Count of products by status
                - total_listings: Total number of listings
                - active_listings: Number of active listings
                - total_views: Sum of all listing views
                - total_sales: Sum of all sales
                - total_revenue: Sum of all revenue
                - top_performing: Top 5 products by sales
                - recent_products: 5 most recent products

        Example:
            >>> db = ProductDB()
            >>> stats = db.get_stats()
            >>> print(f"Total products: {stats['total_products']}")
            >>> print(f"Total revenue: ${stats['total_revenue']:.2f}")
        """
        logger.info("Generating dashboard statistics...")

        stats = {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total products
            cursor.execute("SELECT COUNT(*) as count FROM products")
            stats['total_products'] = cursor.fetchone()['count']

            # Products by status
            cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM products
            GROUP BY status
            """)
            stats['products_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}

            # Total listings
            cursor.execute("SELECT COUNT(*) as count FROM listings")
            stats['total_listings'] = cursor.fetchone()['count']

            # Active listings
            cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'active'")
            stats['active_listings'] = cursor.fetchone()['count']

            # Total views
            cursor.execute("SELECT SUM(views) as total FROM listings")
            result = cursor.fetchone()
            stats['total_views'] = result['total'] if result['total'] else 0

            # Total sales
            cursor.execute("SELECT SUM(sales) as total FROM listings")
            result = cursor.fetchone()
            stats['total_sales'] = result['total'] if result['total'] else 0

            # Total revenue
            cursor.execute("SELECT SUM(revenue) as total FROM listings")
            result = cursor.fetchone()
            stats['total_revenue'] = result['total'] if result['total'] else 0.0

            # Top performing products
            cursor.execute("""
            SELECT p.id, p.title, p.type, SUM(l.sales) as total_sales, SUM(l.revenue) as total_revenue
            FROM products p
            JOIN listings l ON p.id = l.product_id
            GROUP BY p.id
            ORDER BY total_sales DESC
            LIMIT 5
            """)
            stats['top_performing'] = [dict(row) for row in cursor.fetchall()]

            # Recent products
            cursor.execute("""
            SELECT id, title, type, niche, status, created_at
            FROM products
            ORDER BY created_at DESC
            LIMIT 5
            """)
            stats['recent_products'] = [dict(row) for row in cursor.fetchall()]

            # Total trends
            cursor.execute("SELECT COUNT(*) as count FROM trends")
            stats['total_trends'] = cursor.fetchone()['count']

            logger.info("✓ Dashboard statistics generated")
            return stats

    def search_products(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search products with optional filters.

        Args:
            query: Search query (searches title and description)
            filters: Optional filters:
                - type: Product type
                - niche: Product niche
                - status: Product status
                - min_price: Minimum price
                - max_price: Maximum price

        Returns:
            List of matching products

        Example:
            >>> db = ProductDB()
            >>> results = db.search_products("planner", filters={
            ...     'type': 'planner',
            ...     'status': 'published'
            ... })
        """
        logger.info(f"Searching products: '{query}'")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            sql = """
            SELECT * FROM products
            WHERE (title LIKE ? OR description LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]

            if filters:
                if 'type' in filters:
                    sql += " AND type = ?"
                    params.append(filters['type'])

                if 'niche' in filters:
                    sql += " AND niche = ?"
                    params.append(filters['niche'])

                if 'status' in filters:
                    sql += " AND status = ?"
                    params.append(filters['status'])

                if 'min_price' in filters:
                    sql += " AND price >= ?"
                    params.append(filters['min_price'])

                if 'max_price' in filters:
                    sql += " AND price <= ?"
                    params.append(filters['max_price'])

            sql += " ORDER BY created_at DESC LIMIT 50"

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]

            logger.info(f"✓ Found {len(results)} matching products")
            return results

    def close(self):
        """Close the thread-local database connection."""
        if hasattr(_thread_local, 'connection'):
            _thread_local.connection.close()
            delattr(_thread_local, 'connection')
            logger.info("Database connection closed")


def main():
    """Main function for testing and demonstration."""
    print("=" * 60)
    print("Digital Product Factory - Database Manager")
    print("=" * 60)
    print()

    try:
        # Initialize database
        print("Initializing database...")
        init_database()
        print("✓ Database initialized\n")

        # Create ProductDB instance
        print("Creating ProductDB instance...")
        db = ProductDB()
        print("✓ ProductDB created\n")

        # Save a test product
        print("Saving test product...")
        product_id = db.save_product({
            'type': 'planner',
            'niche': 'productivity',
            'title': 'Ultimate Daily Planner 2025',
            'description': 'A comprehensive daily planning system',
            'price': 15.00,
            'status': 'draft'
        })
        print(f"✓ Product saved with ID: {product_id}\n")

        # Save marketing content
        print("Saving marketing content...")
        content_count = db.save_marketing_content(product_id, {
            'etsy': {'title': 'Daily Planner', 'description': 'Amazing planner'},
            'instagram': {'captions': ['Caption 1', 'Caption 2']}
        })
        print(f"✓ Saved {content_count} marketing content items\n")

        # Save a listing
        print("Saving listing...")
        listing_id = db.save_listing({
            'product_id': product_id,
            'platform': 'etsy',
            'listing_id': '123456789',
            'url': 'https://etsy.com/listing/123456789'
        })
        print(f"✓ Listing saved with ID: {listing_id}\n")

        # Update listing stats
        print("Updating listing stats...")
        db.update_listing_stats(listing_id, views=150, sales=5, revenue=75.00)
        print("✓ Stats updated\n")

        # Save a trend
        print("Saving trend...")
        trend_id = db.save_trend({
            'keyword': 'digital planner 2025',
            'demand_score': 85,
            'competition_score': 45,
            'category': 'productivity'
        })
        print(f"✓ Trend saved with ID: {trend_id}\n")

        # Get statistics
        print("Generating statistics...")
        stats = db.get_stats()
        print("✓ Statistics generated\n")

        # Display statistics
        print("=" * 60)
        print("DASHBOARD STATISTICS")
        print("=" * 60)
        print(f"Total Products: {stats['total_products']}")
        print(f"Total Listings: {stats['total_listings']}")
        print(f"Active Listings: {stats['active_listings']}")
        print(f"Total Views: {stats['total_views']}")
        print(f"Total Sales: {stats['total_sales']}")
        print(f"Total Revenue: ${stats['total_revenue']:.2f}")
        print(f"Total Trends: {stats['total_trends']}")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
