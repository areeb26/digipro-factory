"""
Gumroad Publisher Module

This module handles publishing digital products to Gumroad marketplace.
Supports creating products, uploading files, updating pricing, and managing listings.

Gumroad API Documentation: https://help.gumroad.com/article/280-api

Features:
- Create new product listings
- Upload digital files
- Set product pricing and variants
- Update product descriptions and tags
- Manage product visibility
- Get sales data and revenue
- Rate limiting and retry logic
- Comprehensive error handling

Usage:
    publisher = GumroadPublisher()

    # Create product
    result = publisher.create_product({
        'name': 'My Digital Product',
        'price': 1000,  # $10.00 in cents
        'description': 'Product description'
    })
    product_id = result['permalink']
    product_url = result['url']

    # Upload file
    publisher.upload_file(product_id, "path/to/file.pdf")

    # Update product
    publisher.update_product(product_id, {'price': 1500})

    # Get sales data
    sales = publisher.get_product_sales(product_id)
    print(f"Sales: {sales['sales_count']}, Revenue: ${sales['revenue']}")
"""

import os
import logging
import time
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv, set_key
import json
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class GumroadPublisher:
    """
    Publisher for Gumroad marketplace.

    Handles creating and managing digital product listings on Gumroad
    using their REST API v2.
    """

    # API Configuration
    API_BASE_URL = "https://api.gumroad.com/v2"

    # Rate limiting: 60 requests per minute
    RATE_LIMIT_REQUESTS = 60
    RATE_LIMIT_PERIOD = 60  # seconds

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Gumroad publisher.

        Args:
            access_token: Optional Gumroad access token. If not provided,
                         will load from GUMROAD_ACCESS_TOKEN environment variable.

        Raises:
            ValueError: If access token is not provided or found in environment.
        """
        self.access_token = access_token or os.getenv('GUMROAD_ACCESS_TOKEN')

        if not self.access_token:
            raise ValueError(
                "Gumroad access token is required. Set GUMROAD_ACCESS_TOKEN "
                "environment variable or pass access_token to constructor."
            )

        # Rate limiting state
        self._request_times: List[float] = []

        logger.info("Gumroad publisher initialized successfully")

    def _rate_limit(self) -> None:
        """
        Implement rate limiting to avoid exceeding Gumroad API limits.
        Limits to 60 requests per minute.
        """
        current_time = time.time()

        # Remove requests older than rate limit period
        self._request_times = [
            t for t in self._request_times
            if current_time - t < self.RATE_LIMIT_PERIOD
        ]

        # If at rate limit, wait until oldest request expires
        if len(self._request_times) >= self.RATE_LIMIT_REQUESTS:
            sleep_time = self.RATE_LIMIT_PERIOD - (current_time - self._request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                current_time = time.time()

        # Record this request
        self._request_times.append(current_time)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> requests.Response:
        """
        Make HTTP request to Gumroad API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/products')
            data: Optional request data/parameters
            files: Optional files for upload
            retry_count: Current retry attempt number

        Returns:
            requests.Response object

        Raises:
            requests.exceptions.HTTPError: If request fails after all retries
        """
        self._rate_limit()

        url = f"{self.API_BASE_URL}{endpoint}"

        # Add access token to data
        if data is None:
            data = {}
        data['access_token'] = self.access_token

        try:
            logger.debug(f"Making {method} request to {url}")

            if method == 'GET':
                response = requests.get(url, params=data, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, files=files, timeout=60)
                else:
                    response = requests.post(url, data=data, timeout=30)
            elif method == 'PUT':
                if files:
                    response = requests.put(url, data=data, files=files, timeout=60)
                else:
                    response = requests.put(url, data=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, data=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check for rate limiting or server errors
            if response.status_code == 429 or response.status_code >= 500:
                if retry_count < self.MAX_RETRIES:
                    wait_time = self.RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
                    logger.warning(
                        f"Request failed with status {response.status_code}. "
                        f"Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{self.MAX_RETRIES})"
                    )
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, data, files, retry_count + 1)

            response.raise_for_status()

            logger.debug(f"Request successful: {response.status_code}")
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")

            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_DELAY * (2 ** retry_count)
                logger.warning(f"Retrying in {wait_time} seconds... (Attempt {retry_count + 1}/{self.MAX_RETRIES})")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, data, files, retry_count + 1)

            raise

    def verify_credentials(self) -> Dict[str, Any]:
        """
        Verify API credentials by fetching user information.

        Returns:
            User information dictionary

        Raises:
            requests.exceptions.HTTPError: If credentials are invalid
        """
        logger.info("Verifying Gumroad credentials...")

        try:
            response = self._make_request('GET', '/user')
            user_data = response.json()

            if user_data.get('success'):
                logger.info(f"Credentials verified for user: {user_data['user']['name']}")
                return user_data['user']
            else:
                raise ValueError(f"Failed to verify credentials: {user_data.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}")
            raise

    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create a new product listing on Gumroad.

        Args:
            product_data: Dictionary containing product information:
                - name (required): Product name (max 255 chars)
                - description (optional): Product description (markdown supported)
                - price (required): Price in cents (e.g., 1000 = $10.00)
                - currency (optional): Currency code (default: USD)
                - summary (optional): Short summary (max 160 chars)
                - tags (optional): List of tags
                - published (optional): Whether to publish immediately (default: False)

        Returns:
            Dictionary with 'url' and 'permalink' keys

        Raises:
            ValueError: If required fields are missing
            requests.exceptions.HTTPError: If request fails
        """
        # Validate required fields
        if 'name' not in product_data:
            raise ValueError("Product name is required")
        if 'price' not in product_data:
            raise ValueError("Product price is required")

        logger.info(f"Creating product: {product_data['name']}")

        # Prepare product data for API
        api_data = {
            'name': product_data['name'][:255],
            'price': int(product_data['price']),  # Price in cents
        }

        # Add optional fields
        if 'description' in product_data:
            api_data['description'] = product_data['description']

        if 'currency' in product_data:
            api_data['currency'] = product_data['currency']
        else:
            api_data['currency'] = 'USD'

        if 'summary' in product_data:
            api_data['summary'] = product_data['summary'][:160]

        if 'tags' in product_data:
            # Gumroad expects comma-separated tags
            if isinstance(product_data['tags'], list):
                api_data['tags'] = ','.join(product_data['tags'])
            else:
                api_data['tags'] = product_data['tags']

        if 'published' in product_data:
            api_data['published'] = str(product_data['published']).lower()
        else:
            api_data['published'] = 'false'  # Draft by default

        try:
            response = self._make_request('POST', '/products', data=api_data)
            result = response.json()

            if result.get('success'):
                product = result['product']
                product_id = product['id']
                product_url = product.get('short_url') or product.get('url') or f"https://gumroad.com/l/{product_id}"

                logger.info(f"Product created successfully with ID: {product_id}")
                logger.info(f"Product URL: {product_url}")

                return {
                    'url': product_url,
                    'permalink': product_id
                }
            else:
                raise ValueError(f"Failed to create product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to create product: {str(e)}")
            raise

    def update_product(self, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing product.

        Args:
            product_id: Product ID (permalink slug)
            updates: Dictionary of fields to update (same as create_product)

        Returns:
            Updated product data

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info(f"Updating product: {product_id}")

        # Prepare update data
        api_data = {}

        if 'name' in updates:
            api_data['name'] = updates['name'][:255]
        if 'description' in updates:
            api_data['description'] = updates['description']
        if 'price' in updates:
            api_data['price'] = int(updates['price'])
        if 'currency' in updates:
            api_data['currency'] = updates['currency']
        if 'summary' in updates:
            api_data['summary'] = updates['summary'][:160]
        if 'tags' in updates:
            if isinstance(updates['tags'], list):
                api_data['tags'] = ','.join(updates['tags'])
            else:
                api_data['tags'] = updates['tags']
        if 'published' in updates:
            api_data['published'] = str(updates['published']).lower()

        try:
            response = self._make_request('PUT', f'/products/{product_id}', data=api_data)
            result = response.json()

            if result.get('success'):
                logger.info(f"Product {product_id} updated successfully")
                return result['product']
            else:
                raise ValueError(f"Failed to update product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {str(e)}")
            raise

    def upload_file(self, product_id: str, file_path: str) -> Dict[str, Any]:
        """
        Upload a digital file to an existing product.

        Args:
            product_id: Product ID (permalink slug)
            file_path: Path to the file to upload

        Returns:
            Dictionary with file upload information including file reference

        Raises:
            FileNotFoundError: If file doesn't exist
            requests.exceptions.HTTPError: If upload fails
        """
        logger.info(f"Uploading file to product {product_id}: {file_path}")

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path_obj.name, f, 'application/octet-stream')}
                response = self._make_request(
                    'POST',
                    f'/products/{product_id}/file',
                    files=files
                )

            result = response.json()

            if result.get('success'):
                logger.info(f"File uploaded successfully to product {product_id}")
                return {
                    'success': True,
                    'file_name': file_path_obj.name,
                    'file_reference': result.get('file', {})
                }
            else:
                raise ValueError(f"Failed to upload file: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to upload file to product {product_id}: {str(e)}")
            raise

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get product details.

        Args:
            product_id: Product ID (permalink slug)

        Returns:
            Product data dictionary

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info(f"Fetching product: {product_id}")

        try:
            response = self._make_request('GET', f'/products/{product_id}')
            result = response.json()

            if result.get('success'):
                return result['product']
            else:
                raise ValueError(f"Failed to get product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to get product {product_id}: {str(e)}")
            raise

    def delete_product(self, product_id: str) -> bool:
        """
        Delete a product.

        Args:
            product_id: Product ID (permalink slug)

        Returns:
            True if successful

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info(f"Deleting product: {product_id}")

        try:
            response = self._make_request('DELETE', f'/products/{product_id}')
            result = response.json()

            if result.get('success'):
                logger.info(f"Product {product_id} deleted successfully")
                return True
            else:
                raise ValueError(f"Failed to delete product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to delete product {product_id}: {str(e)}")
            raise

    def enable_product(self, product_id: str) -> Dict[str, Any]:
        """
        Enable (publish) a product.

        Args:
            product_id: Product ID (permalink slug)

        Returns:
            Updated product data
        """
        logger.info(f"Enabling product: {product_id}")

        try:
            response = self._make_request('PUT', f'/products/{product_id}/enable')
            result = response.json()

            if result.get('success'):
                logger.info(f"Product {product_id} enabled successfully")
                return result['product']
            else:
                raise ValueError(f"Failed to enable product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to enable product {product_id}: {str(e)}")
            raise

    def disable_product(self, product_id: str) -> Dict[str, Any]:
        """
        Disable (unpublish) a product.

        Args:
            product_id: Product ID (permalink slug)

        Returns:
            Updated product data
        """
        logger.info(f"Disabling product: {product_id}")

        try:
            response = self._make_request('PUT', f'/products/{product_id}/disable')
            result = response.json()

            if result.get('success'):
                logger.info(f"Product {product_id} disabled successfully")
                return result['product']
            else:
                raise ValueError(f"Failed to disable product: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to disable product {product_id}: {str(e)}")
            raise

    def list_products(self) -> List[Dict[str, Any]]:
        """
        List all products in the account.

        Returns:
            List of product dictionaries

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info("Fetching product list...")

        try:
            response = self._make_request('GET', '/products')
            result = response.json()

            if result.get('success'):
                products = result.get('products', [])
                logger.info(f"Retrieved {len(products)} products")
                return products
            else:
                raise ValueError(f"Failed to list products: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to list products: {str(e)}")
            raise

    def publish_product(
        self,
        product_data: Dict[str, Any],
        file_path: Optional[str] = None,
        cover_image_path: Optional[str] = None
    ) -> str:
        """
        Complete workflow to publish a product to Gumroad.

        This is the main method that orchestrates the entire publishing process:
        1. Create product listing
        2. Upload digital file (if provided)
        3. Upload cover image (if provided)
        4. Enable the product

        Args:
            product_data: Product information (see create_product for fields)
            file_path: Optional path to digital file to upload
            cover_image_path: Optional path to cover/thumbnail image

        Returns:
            Product URL for customers

        Raises:
            ValueError: If validation fails
            requests.exceptions.HTTPError: If API requests fail
        """
        logger.info(f"Starting full publish workflow for: {product_data.get('name', 'Unknown')}")

        try:
            # Step 1: Create product (as draft)
            product_data['published'] = False
            result = self.create_product(product_data)
            product_id = result['permalink']

            # Step 2: Upload digital file if provided
            if file_path:
                logger.info(f"Uploading digital file: {file_path}")
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")

                with open(file_path, 'rb') as f:
                    files = {'file': (file_path_obj.name, f, 'application/octet-stream')}
                    response = self._make_request(
                        'POST',
                        f'/products/{product_id}/file',
                        files=files
                    )
                    result = response.json()
                    if not result.get('success'):
                        raise ValueError(f"Failed to upload file: {result.get('message', 'Unknown error')}")
                    logger.info("Digital file uploaded successfully")

            # Step 3: Upload cover image if provided
            if cover_image_path:
                logger.info(f"Uploading cover image: {cover_image_path}")
                cover_path_obj = Path(cover_image_path)
                if not cover_path_obj.exists():
                    raise FileNotFoundError(f"Cover image not found: {cover_image_path}")

                # Validate image format
                valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
                if cover_path_obj.suffix.lower() not in valid_extensions:
                    raise ValueError(f"Invalid image format. Supported: {', '.join(valid_extensions)}")

                with open(cover_image_path, 'rb') as f:
                    files = {'cover': (cover_path_obj.name, f, 'image/jpeg')}
                    response = self._make_request(
                        'PUT',
                        f'/products/{product_id}',
                        files=files
                    )
                    result = response.json()
                    if not result.get('success'):
                        raise ValueError(f"Failed to upload cover image: {result.get('message', 'Unknown error')}")
                    logger.info("Cover image uploaded successfully")

            # Step 4: Enable the product
            logger.info("Publishing product...")
            product = self.enable_product(product_id)

            # Get product URL
            product_url = product.get('short_url') or product.get('url') or f"https://gumroad.com/l/{product_id}"

            logger.info(f"Product published successfully!")
            logger.info(f"Product URL: {product_url}")

            return product_url

        except Exception as e:
            logger.error(f"Failed to publish product: {str(e)}")
            # Try to clean up the product if it was created
            if 'product_id' in locals():
                try:
                    logger.info(f"Attempting to delete incomplete product: {product_id}")
                    self.delete_product(product_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup product: {str(cleanup_error)}")
            raise

    def get_sales(self, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get sales data.

        Args:
            product_id: Optional product ID to filter sales. If not provided,
                       returns all sales.

        Returns:
            List of sale dictionaries

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info(f"Fetching sales data{f' for product {product_id}' if product_id else ''}...")

        try:
            data = {}
            if product_id:
                data['product_id'] = product_id

            response = self._make_request('GET', '/sales', data=data)
            result = response.json()

            if result.get('success'):
                sales = result.get('sales', [])
                logger.info(f"Retrieved {len(sales)} sales")
                return sales
            else:
                raise ValueError(f"Failed to get sales: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to get sales: {str(e)}")
            raise

    def get_product_sales(self, product_id: str) -> Dict[str, Any]:
        """
        Get sales count and revenue for a specific product.

        Args:
            product_id: Product ID (permalink slug)

        Returns:
            Dictionary with:
                - sales_count: Total number of sales
                - revenue: Total revenue (in dollars)
                - currency: Currency code (default: USD)

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        logger.info(f"Fetching sales statistics for product: {product_id}")

        try:
            # Get all sales for this product
            sales = self.get_sales(product_id=product_id)

            # Calculate totals
            sales_count = len(sales)
            total_revenue_cents = sum(int(sale.get('price', 0)) for sale in sales)
            total_revenue = total_revenue_cents / 100.0  # Convert cents to dollars

            result = {
                'sales_count': sales_count,
                'revenue': total_revenue,
                'currency': 'USD'
            }

            logger.info(f"Product {product_id}: {sales_count} sales, ${total_revenue:.2f} revenue")

            return result

        except Exception as e:
            logger.error(f"Failed to get sales statistics for product {product_id}: {str(e)}")
            raise


def main():
    """
    Test function demonstrating GumroadPublisher usage.
    """
    print("Gumroad Publisher Test")
    print("=" * 50)

    try:
        # Initialize publisher
        publisher = GumroadPublisher()

        # Verify credentials
        user = publisher.verify_credentials()
        print(f"\n✓ Connected as: {user['name']}")
        print(f"  Email: {user['email']}")

        # List existing products
        products = publisher.list_products()
        print(f"\n✓ Found {len(products)} existing products")

        # Example: Simple product creation workflow (commented out to avoid actually creating)
        """
        # Step 1: Create product
        product_data = {
            'name': 'Test Digital Product',
            'description': 'This is a test product created via API',
            'price': 1000,  # $10.00 in cents
            'currency': 'USD',
            'summary': 'Test product for API integration',
            'tags': ['digital', 'test', 'template']
        }

        result = publisher.create_product(product_data)
        product_id = result['permalink']
        product_url = result['url']

        print(f"\n✓ Product created!")
        print(f"  Product ID: {product_id}")
        print(f"  URL: {product_url}")

        # Step 2: Upload file
        publisher.upload_file(product_id, 'path/to/digital-file.pdf')
        print(f"  File uploaded successfully")

        # Step 3: Update product (optional)
        publisher.update_product(product_id, {
            'price': 1500,  # Change to $15.00
            'description': 'Updated description'
        })
        print(f"  Product updated")

        # Step 4: Get sales data
        sales = publisher.get_product_sales(product_id)
        print(f"  Sales: {sales['sales_count']}, Revenue: ${sales['revenue']:.2f}")
        """

        print("\n✓ All tests passed!")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
