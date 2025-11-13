"""
Review Dashboard - Flask Application

A web-based dashboard for reviewing, approving, and managing digital products
before publishing to marketplaces.

Features:
- Product review grid with thumbnails
- Detailed product preview with marketing content
- Approve/Edit/Reject workflow
- Dashboard statistics with charts
- CSRF protection and session management
- Download links for generated files

Author: Digital Product Factory
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import ProductDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize database
db = ProductDB()

# Configuration
PRODUCTS_DIR = Path(__file__).parent.parent / "output"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'json', 'txt', 'csv'}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_datetime(dt_string: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_string


def get_product_files(product_id: int) -> Dict[str, List[Path]]:
    """
    Get all files associated with a product.

    Args:
        product_id: Product ID

    Returns:
        Dictionary with categorized file paths
    """
    product = db.get_product_by_id(product_id)
    if not product or not product.get('file_path'):
        return {'pdfs': [], 'images': [], 'data': [], 'other': []}

    product_dir = Path(product['file_path'])
    if not product_dir.exists():
        return {'pdfs': [], 'images': [], 'data': [], 'other': []}

    files = {
        'pdfs': [],
        'images': [],
        'data': [],
        'other': []
    }

    for file_path in product_dir.rglob('*'):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            if ext == '.pdf':
                files['pdfs'].append(file_path)
            elif ext in ['.png', '.jpg', '.jpeg']:
                files['images'].append(file_path)
            elif ext in ['.json', '.txt', '.csv']:
                files['data'].append(file_path)
            else:
                files['other'].append(file_path)

    return files


def get_marketing_content(product_id: int) -> Dict[str, Any]:
    """
    Get marketing content for a product from database.

    Args:
        product_id: Product ID

    Returns:
        Dictionary of marketing content by platform
    """
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT platform, content_type, content, created_at
                FROM marketing_content
                WHERE product_id = ?
                ORDER BY created_at DESC
            """, (product_id,))

            rows = cursor.fetchall()

            marketing = {}
            for row in rows:
                platform = row['platform']
                try:
                    content = json.loads(row['content'])
                except:
                    content = row['content']

                if platform not in marketing:
                    marketing[platform] = []

                marketing[platform].append({
                    'type': row['content_type'],
                    'content': content,
                    'created_at': row['created_at']
                })

            return marketing
    except Exception as e:
        logger.error(f"Error fetching marketing content: {e}")
        return {}


# Template filters
app.jinja_env.filters['datetime'] = format_datetime


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('error.html',
                         error_code=404,
                         error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500


# Routes
@app.route('/')
def index():
    """
    Display grid of all pending products.

    Shows:
    - Product thumbnail (first image or placeholder)
    - Title, type, niche
    - Price
    - Link to detailed view
    """
    try:
        # Get pending products (draft or pending status)
        products = db.get_pending_products(limit=100)

        # Enhance products with thumbnail info
        for product in products:
            product_files = get_product_files(product['id'])
            if product_files['images']:
                product['thumbnail'] = product_files['images'][0]
            else:
                product['thumbnail'] = None

        return render_template('index.html',
                             products=products,
                             title="Product Review Dashboard")

    except Exception as e:
        logger.error(f"Error loading index: {e}")
        flash("Error loading products", "error")
        return render_template('index.html', products=[], title="Product Review Dashboard")


@app.route('/product/<int:product_id>')
def product_detail(product_id: int):
    """
    Show complete product preview with all details.

    Displays:
    - Product information
    - All marketing content
    - Generated files with download links
    - Approve/Edit/Reject buttons

    Args:
        product_id: ID of product to display
    """
    try:
        # Get product details
        product = db.get_product_by_id(product_id)
        if not product:
            flash("Product not found", "error")
            return redirect(url_for('index'))

        # Get associated files
        files = get_product_files(product_id)

        # Get marketing content
        marketing = get_marketing_content(product_id)

        # Get listings if any
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM listings
                WHERE product_id = ?
                ORDER BY created_at DESC
            """, (product_id,))
            listings = [dict(row) for row in cursor.fetchall()]

        return render_template('product_detail.html',
                             product=product,
                             files=files,
                             marketing=marketing,
                             listings=listings,
                             title=f"Review: {product['title']}")

    except Exception as e:
        logger.error(f"Error loading product {product_id}: {e}")
        flash("Error loading product details", "error")
        return redirect(url_for('index'))


@app.route('/approve/<int:product_id>', methods=['POST'])
def approve_product(product_id: int):
    """
    Approve a product and queue for publishing.

    Updates product status to 'approved' and prepares it for
    publishing to marketplaces.

    Args:
        product_id: ID of product to approve

    Returns:
        JSON response with success status
    """
    try:
        # Verify product exists
        product = db.get_product_by_id(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404

        # Update status to approved
        db.update_product_status(product_id, 'approved')

        logger.info(f"Product {product_id} approved: {product['title']}")

        return jsonify({
            'success': True,
            'message': 'Product approved successfully',
            'product_id': product_id,
            'new_status': 'approved'
        })

    except Exception as e:
        logger.error(f"Error approving product {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id: int):
    """
    Update product data with edited information.

    Accepts form data with updated product fields and
    updates the database accordingly.

    Args:
        product_id: ID of product to edit

    Returns:
        JSON response with success status
    """
    try:
        # Verify product exists
        product = db.get_product_by_id(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404

        # Get updated data from request
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Build update query dynamically
        allowed_fields = ['title', 'description', 'price', 'niche', 'type']
        updates = []
        params = []

        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])

        if not updates:
            return jsonify({
                'success': False,
                'error': 'No valid fields to update'
            }), 400

        # Add updated timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(product_id)

        # Execute update
        with db._lock:
            with db._get_connection() as conn:
                cursor = conn.cursor()
                query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)

        logger.info(f"Product {product_id} updated: {', '.join(allowed_fields)}")

        # Log edit reason if provided
        if 'edit_reason' in data:
            logger.info(f"Edit reason for product {product_id}: {data['edit_reason']}")

        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'product_id': product_id,
            'updated_fields': [f for f in allowed_fields if f in data]
        })

    except Exception as e:
        logger.error(f"Error editing product {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/reject/<int:product_id>', methods=['POST'])
def reject_product(product_id: int):
    """
    Reject a product with reason.

    Marks product as rejected and logs the rejection reason
    for review and improvement.

    Args:
        product_id: ID of product to reject

    Returns:
        JSON response with success status
    """
    try:
        # Verify product exists
        product = db.get_product_by_id(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404

        # Get rejection reason
        data = request.get_json() if request.is_json else request.form.to_dict()
        reason = data.get('reason', 'No reason provided')

        # Update status to rejected
        db.update_product_status(product_id, 'archived')

        # Log rejection reason
        logger.warning(f"Product {product_id} rejected: {product['title']}")
        logger.warning(f"Rejection reason: {reason}")

        # Store rejection reason in a log file
        rejection_log = Path(__file__).parent / "rejections.log"
        with open(rejection_log, 'a') as f:
            f.write(f"\n[{datetime.now().isoformat()}] Product ID: {product_id}\n")
            f.write(f"Title: {product['title']}\n")
            f.write(f"Reason: {reason}\n")
            f.write("-" * 80 + "\n")

        return jsonify({
            'success': True,
            'message': 'Product rejected',
            'product_id': product_id,
            'new_status': 'archived',
            'reason': reason
        })

    except Exception as e:
        logger.error(f"Error rejecting product {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/stats')
def stats():
    """
    Display dashboard statistics and performance charts.

    Shows:
    - Total products by status
    - Listings performance (views, sales, revenue)
    - Top performing products
    - Recent activity
    - Trend analysis
    """
    try:
        # Get comprehensive statistics
        stats_data = db.get_stats()

        # Get top trends
        trends = db.get_top_trends(limit=10, min_demand_score=50)
        stats_data['top_trends'] = trends

        # Calculate conversion rates
        if stats_data['total_views'] > 0:
            stats_data['conversion_rate'] = (stats_data['total_sales'] / stats_data['total_views']) * 100
        else:
            stats_data['conversion_rate'] = 0.0

        # Calculate average order value
        if stats_data['total_sales'] > 0:
            stats_data['avg_order_value'] = stats_data['total_revenue'] / stats_data['total_sales']
        else:
            stats_data['avg_order_value'] = 0.0

        # Get status distribution for chart
        status_labels = []
        status_values = []
        for status, count in stats_data.get('products_by_status', {}).items():
            status_labels.append(status.capitalize())
            status_values.append(count)

        stats_data['status_chart'] = {
            'labels': status_labels,
            'values': status_values
        }

        return render_template('stats.html',
                             stats=stats_data,
                             title="Dashboard Statistics")

    except Exception as e:
        logger.error(f"Error loading statistics: {e}")
        flash("Error loading statistics", "error")
        return redirect(url_for('index'))


@app.route('/download/<int:product_id>/<path:filename>')
def download_file(product_id: int, filename: str):
    """
    Download a file associated with a product.

    Args:
        product_id: ID of the product
        filename: Name of the file to download

    Returns:
        File download response
    """
    try:
        # Verify product exists
        product = db.get_product_by_id(product_id)
        if not product or not product.get('file_path'):
            flash("Product or file not found", "error")
            return redirect(url_for('index'))

        # Sanitize filename
        safe_filename = secure_filename(filename)

        # Construct file path
        product_dir = Path(product['file_path'])
        file_path = None

        # Search for file in product directory
        for f in product_dir.rglob(safe_filename):
            if f.is_file():
                file_path = f
                break

        if not file_path or not file_path.exists():
            flash("File not found", "error")
            return redirect(url_for('product_detail', product_id=product_id))

        # Check if file extension is allowed
        if not allowed_file(file_path.name):
            flash("File type not allowed for download", "error")
            return redirect(url_for('product_detail', product_id=product_id))

        logger.info(f"Downloading file: {file_path.name} for product {product_id}")

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    except Exception as e:
        logger.error(f"Error downloading file {filename} for product {product_id}: {e}")
        flash("Error downloading file", "error")
        return redirect(url_for('product_detail', product_id=product_id))


@app.route('/api/products')
def api_products():
    """
    API endpoint to get all products as JSON.

    Returns:
        JSON array of products
    """
    try:
        products = db.get_pending_products(limit=100)
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        })
    except Exception as e:
        logger.error(f"Error in API products endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/product/<int:product_id>')
def api_product_detail(product_id: int):
    """
    API endpoint to get product details as JSON.

    Args:
        product_id: ID of product

    Returns:
        JSON object with product details
    """
    try:
        product = db.get_product_by_id(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404

        marketing = get_marketing_content(product_id)

        return jsonify({
            'success': True,
            'product': product,
            'marketing': marketing
        })
    except Exception as e:
        logger.error(f"Error in API product detail endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# CLI commands
@app.cli.command()
def init_db():
    """Initialize the database."""
    from database import init_database
    init_database()
    print("✓ Database initialized")


@app.cli.command()
def run_dev():
    """Run development server."""
    print("=" * 60)
    print("Review Dashboard - Development Server")
    print("=" * 60)
    print()
    print("Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print()
    app.run(debug=True, host='0.0.0.0', port=5000)


def main():
    """Main entry point."""
    print("=" * 60)
    print("Digital Product Factory - Review Dashboard")
    print("=" * 60)
    print()
    print("Starting server...")
    print("Access dashboard at: http://localhost:5000")
    print()

    # Run in production mode
    app.run(debug=False, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
