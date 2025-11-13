"""
Etsy Publisher Module

Handles publishing digital products to Etsy marketplace using Etsy API v3.
Implements OAuth 2.0 authentication, listing creation, file uploads, and publishing.

Features:
- OAuth 2.0 authentication flow
- Token management with automatic refresh
- Draft listing creation for digital products
- Digital file uploads
- Multiple image uploads with ranking
- Listing publishing
- Comprehensive error handling and retry logic
- Rate limiting compliance

Author: Digital Product Factory
"""

import os
import time
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

from dotenv import load_dotenv, set_key
from requests_oauthlib import OAuth2Session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


class EtsyPublisher:
    """
    Publisher for Etsy marketplace using API v3.

    Handles OAuth 2.0 authentication, listing creation, file uploads,
    and publishing of digital products to Etsy.

    Attributes:
        client_id: Etsy API client ID (keystring)
        client_secret: Etsy API client secret
        redirect_uri: OAuth redirect URI
        scopes: OAuth scopes required
        api_base_url: Base URL for Etsy API v3
    """

    # Etsy API v3 endpoints
    API_BASE_URL = "https://openapi.etsy.com/v3"
    AUTH_URL = "https://www.etsy.com/oauth/connect"
    TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"

    # Required OAuth scopes
    SCOPES = [
        "listings_r",
        "listings_w",
        "listings_d",
        "shops_r",
        "shops_w"
    ]

    # Rate limiting
    MAX_REQUESTS_PER_SECOND = 10
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self):
        """
        Initialize EtsyPublisher with credentials from environment variables.

        Loads:
            - ETSY_CLIENT_ID (keystring)
            - ETSY_CLIENT_SECRET
            - ETSY_REDIRECT_URI
            - ETSY_ACCESS_TOKEN (if available)
            - ETSY_REFRESH_TOKEN (if available)
            - ETSY_TOKEN_EXPIRES_AT (if available)

        Raises:
            ValueError: If required credentials are missing
        """
        logger.info("Initializing EtsyPublisher...")

        # Load credentials
        self.client_id = os.getenv('ETSY_CLIENT_ID')
        self.client_secret = os.getenv('ETSY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('ETSY_REDIRECT_URI', 'http://localhost:8080/callback')

        if not self.client_id or not self.client_secret:
            raise ValueError("Missing Etsy API credentials. Set ETSY_CLIENT_ID and ETSY_CLIENT_SECRET in .env")

        # Load existing tokens if available
        self.access_token = os.getenv('ETSY_ACCESS_TOKEN')
        self.refresh_token = os.getenv('ETSY_REFRESH_TOKEN')
        self.token_expires_at = os.getenv('ETSY_TOKEN_EXPIRES_AT')

        # Initialize OAuth session
        self.oauth = None
        self._initialize_oauth()

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        logger.info("✓ EtsyPublisher initialized successfully")

    def _initialize_oauth(self):
        """Initialize OAuth2 session with current credentials."""
        token = None
        if self.access_token:
            token = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_type': 'Bearer',
                'expires_at': self.token_expires_at
            }

        self.oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.SCOPES,
            token=token
        )

    def get_authorization_url(self) -> str:
        """
        Get authorization URL for OAuth 2.0 flow.

        User should visit this URL and authorize the application.
        After authorization, they will be redirected to redirect_uri with code.

        Returns:
            str: Authorization URL for user to visit

        Example:
            >>> publisher = EtsyPublisher()
            >>> auth_url = publisher.get_authorization_url()
            >>> print(f"Visit: {auth_url}")
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPES),
            'state': 'random_state_string'  # Should be random for security
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info("Generated authorization URL")
        return auth_url

    def get_access_token(self, authorization_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtain access token using OAuth 2.0 authorization code flow.

        If authorization_code is provided, exchanges it for access token.
        If not provided and refresh_token exists, refreshes the token.

        Args:
            authorization_code: Authorization code from OAuth redirect

        Returns:
            dict: Token information including access_token, refresh_token, expires_in

        Raises:
            ValueError: If no authorization code and no refresh token available
            requests.HTTPError: If token request fails

        Example:
            >>> publisher = EtsyPublisher()
            >>> # After user authorizes and returns with code
            >>> token_info = publisher.get_access_token(authorization_code='xyz123')
            >>> print(f"Access token: {token_info['access_token']}")
        """
        if authorization_code:
            # Exchange authorization code for access token
            logger.info("Exchanging authorization code for access token...")

            data = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'code': authorization_code
            }

            auth = (self.client_id, self.client_secret)

        elif self.refresh_token:
            # Refresh existing token
            logger.info("Refreshing access token...")

            data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'refresh_token': self.refresh_token
            }

            auth = (self.client_id, self.client_secret)

        else:
            raise ValueError("No authorization code or refresh token available. Call get_authorization_url() first.")

        try:
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                auth=auth,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            response.raise_for_status()

            token_data = response.json()

            # Save tokens to environment
            self._save_token(token_data)

            logger.info("✓ Access token obtained successfully")
            return token_data

        except requests.HTTPError as e:
            logger.error(f"Failed to obtain access token: {e}")
            logger.error(f"Response: {e.response.text}")
            raise

    def _save_token(self, token_data: Dict[str, Any]):
        """
        Save access token to .env file and update instance variables.

        Args:
            token_data: Token information from Etsy OAuth
        """
        self.access_token = token_data['access_token']
        self.refresh_token = token_data.get('refresh_token', self.refresh_token)

        # Calculate expiration time
        expires_in = token_data.get('expires_in', 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        self.token_expires_at = expires_at.isoformat()

        # Update .env file
        env_path = Path('.env')
        if env_path.exists():
            set_key(env_path, 'ETSY_ACCESS_TOKEN', self.access_token)
            if self.refresh_token:
                set_key(env_path, 'ETSY_REFRESH_TOKEN', self.refresh_token)
            set_key(env_path, 'ETSY_TOKEN_EXPIRES_AT', self.token_expires_at)

            logger.info("✓ Tokens saved to .env file")

        # Reinitialize OAuth session with new token
        self._initialize_oauth()

    def _check_token_expiration(self):
        """Check if access token is expired and refresh if needed."""
        if not self.token_expires_at:
            return

        expires_at = datetime.fromisoformat(self.token_expires_at)
        if datetime.now() >= expires_at - timedelta(minutes=5):  # Refresh 5 mins before expiry
            logger.info("Token expiring soon, refreshing...")
            try:
                self.get_access_token()
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")

    def _rate_limit(self):
        """Implement rate limiting to respect Etsy API limits."""
        current_time = time.time()

        # Reset counter every second
        if current_time - self.last_request_time >= 1.0:
            self.request_count = 0
            self.last_request_time = current_time

        # Check if we've exceeded rate limit
        if self.request_count >= self.MAX_REQUESTS_PER_SECOND:
            sleep_time = 1.0 - (current_time - self.last_request_time)
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Etsy API with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.HTTPError: If request fails after retries
        """
        # Check and refresh token if needed
        self._check_token_expiration()

        # Prepare request
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self.access_token}'
        headers['x-api-key'] = self.client_id

        # Retry logic
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                # Rate limiting
                self._rate_limit()

                # Make request
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )

                # Handle rate limiting (429) and server errors (5xx)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.RETRY_DELAY))
                    logger.warning(f"Rate limited, retrying after {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue

                # Raise for other HTTP errors
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt == self.RETRY_ATTEMPTS - 1:
                    logger.error(f"Request failed after {self.RETRY_ATTEMPTS} attempts: {e}")
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.RETRY_ATTEMPTS}), retrying...")
                time.sleep(self.RETRY_DELAY * (attempt + 1))

        raise RuntimeError("Request failed after all retries")

    def create_draft_listing(self, product_data: Dict[str, Any]) -> int:
        """
        Create a draft digital product listing on Etsy.

        Args:
            product_data: Product information containing:
                - shop_id: Etsy shop ID (required)
                - title: Listing title, max 140 chars (required)
                - description: Listing description, max 65535 chars (required)
                - price: Price in shop currency (required)
                - tags: List of tags, max 13, each max 20 chars (required)
                - quantity: Stock quantity, default 999 for digital
                - taxonomy_id: Etsy category taxonomy ID (optional)
                - who_made: "i_did" | "collective" | "someone_else" (default "i_did")
                - when_made: Year range (default "made_to_order")
                - is_supply: Boolean (default False)

        Returns:
            int: Listing ID of created draft

        Raises:
            ValueError: If required fields are missing
            requests.HTTPError: If API request fails

        Example:
            >>> product = {
            ...     'shop_id': 12345678,
            ...     'title': 'Digital Planner 2025',
            ...     'description': 'Beautiful digital planner...',
            ...     'price': 15.00,
            ...     'tags': ['planner', 'digital', 'productivity']
            ... }
            >>> listing_id = publisher.create_draft_listing(product)
            >>> print(f"Created listing: {listing_id}")
        """
        logger.info(f"Creating draft listing: {product_data.get('title', 'Unknown')}")

        # Validate required fields
        required_fields = ['shop_id', 'title', 'description', 'price', 'tags']
        for field in required_fields:
            if field not in product_data:
                raise ValueError(f"Missing required field: {field}")

        # Prepare listing data
        listing_data = {
            'quantity': product_data.get('quantity', 999),
            'title': product_data['title'][:140],  # Max 140 chars
            'description': product_data['description'][:65535],  # Max 65535 chars
            'price': float(product_data['price']),
            'who_made': product_data.get('who_made', 'i_did'),
            'when_made': product_data.get('when_made', 'made_to_order'),
            'taxonomy_id': product_data.get('taxonomy_id', 1057),  # Default to digital downloads
            'tags': product_data['tags'][:13],  # Max 13 tags
            'type': 'download',  # Digital product
            'is_supply': False,
            'should_auto_renew': True,
            'state': 'draft'
        }

        try:
            shop_id = product_data['shop_id']
            response = self._make_request(
                'POST',
                f'/application/shops/{shop_id}/listings',
                json=listing_data
            )

            listing_info = response.json()
            listing_id = listing_info['listing_id']

            logger.info(f"✓ Draft listing created with ID: {listing_id}")
            return listing_id

        except requests.HTTPError as e:
            logger.error(f"Failed to create listing: {e}")
            logger.error(f"Response: {e.response.text}")
            raise

    def upload_digital_file(self, shop_id: int, listing_id: int, file_path: str) -> int:
        """
        Upload digital file to listing.

        Args:
            shop_id: Etsy shop ID
            listing_id: Listing ID to upload file to
            file_path: Path to file to upload

        Returns:
            int: Digital file ID

        Raises:
            FileNotFoundError: If file doesn't exist
            requests.HTTPError: If upload fails

        Example:
            >>> file_id = publisher.upload_digital_file(
            ...     shop_id=12345678,
            ...     listing_id=987654321,
            ...     file_path='/path/to/planner.pdf'
            ... )
            >>> print(f"Uploaded file ID: {file_id}")
        """
        logger.info(f"Uploading digital file to listing {listing_id}...")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file size
        file_size = file_path.stat().st_size
        logger.info(f"File size: {file_size / 1024 / 1024:.2f} MB")

        try:
            # Upload file
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/octet-stream')}

                response = self._make_request(
                    'POST',
                    f'/application/shops/{shop_id}/listings/{listing_id}/files',
                    files=files
                )

            file_info = response.json()
            file_id = file_info['listing_file_id']

            logger.info(f"✓ Digital file uploaded with ID: {file_id}")
            return file_id

        except requests.HTTPError as e:
            logger.error(f"Failed to upload digital file: {e}")
            logger.error(f"Response: {e.response.text}")
            raise

    def upload_images(self, shop_id: int, listing_id: int, image_paths: List[str]) -> List[int]:
        """
        Upload multiple images to listing with ranking.

        Args:
            shop_id: Etsy shop ID
            listing_id: Listing ID to upload images to
            image_paths: List of image file paths (max 10)

        Returns:
            list: List of image IDs in upload order

        Raises:
            ValueError: If more than 10 images provided
            FileNotFoundError: If any image file doesn't exist
            requests.HTTPError: If upload fails

        Example:
            >>> image_ids = publisher.upload_images(
            ...     shop_id=12345678,
            ...     listing_id=987654321,
            ...     image_paths=[
            ...         '/path/to/cover.png',
            ...         '/path/to/preview1.png',
            ...         '/path/to/preview2.png'
            ...     ]
            ... )
            >>> print(f"Uploaded {len(image_ids)} images")
        """
        logger.info(f"Uploading {len(image_paths)} images to listing {listing_id}...")

        if len(image_paths) > 10:
            raise ValueError("Maximum 10 images allowed per listing")

        image_ids = []

        for rank, image_path in enumerate(image_paths, start=1):
            image_path = Path(image_path)

            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}, skipping...")
                continue

            try:
                # Upload image
                with open(image_path, 'rb') as f:
                    files = {'image': (image_path.name, f, 'image/png')}
                    data = {'rank': rank}

                    response = self._make_request(
                        'POST',
                        f'/application/shops/{shop_id}/listings/{listing_id}/images',
                        files=files,
                        data=data
                    )

                image_info = response.json()
                image_id = image_info['listing_image_id']
                image_ids.append(image_id)

                logger.info(f"✓ Uploaded image {rank}/{len(image_paths)}: {image_path.name} (ID: {image_id})")

            except requests.HTTPError as e:
                logger.error(f"Failed to upload image {image_path.name}: {e}")
                logger.error(f"Response: {e.response.text}")
                # Continue with other images

        logger.info(f"✓ Uploaded {len(image_ids)} images successfully")
        return image_ids

    def publish_listing(self, shop_id: int, listing_id: int) -> str:
        """
        Publish draft listing (change state from "draft" to "active").

        Args:
            shop_id: Etsy shop ID
            listing_id: Listing ID to publish

        Returns:
            str: URL of published listing

        Raises:
            requests.HTTPError: If publish fails

        Example:
            >>> url = publisher.publish_listing(
            ...     shop_id=12345678,
            ...     listing_id=987654321
            ... )
            >>> print(f"Published at: {url}")
        """
        logger.info(f"Publishing listing {listing_id}...")

        try:
            # Update listing state to active
            response = self._make_request(
                'PUT',
                f'/application/shops/{shop_id}/listings/{listing_id}',
                json={'state': 'active'}
            )

            listing_info = response.json()
            listing_url = listing_info.get('url', f"https://www.etsy.com/listing/{listing_id}")

            logger.info(f"✓ Listing published successfully: {listing_url}")
            return listing_url

        except requests.HTTPError as e:
            logger.error(f"Failed to publish listing: {e}")
            logger.error(f"Response: {e.response.text}")
            raise

    def get_shop_id(self) -> int:
        """
        Get shop ID for the authenticated user.

        Returns:
            int: Shop ID

        Raises:
            requests.HTTPError: If request fails
        """
        logger.info("Fetching shop information...")

        try:
            response = self._make_request('GET', '/application/users/me')
            user_info = response.json()
            shop_id = user_info['shop_id']

            logger.info(f"✓ Shop ID: {shop_id}")
            return shop_id

        except requests.HTTPError as e:
            logger.error(f"Failed to fetch shop info: {e}")
            raise


def main():
    """Main function for testing and demonstration."""
    print("=" * 60)
    print("Etsy Publisher - Digital Product Factory")
    print("=" * 60)
    print()

    try:
        # Initialize publisher
        print("Initializing Etsy Publisher...")
        publisher = EtsyPublisher()
        print("✓ Publisher initialized\n")

        # Check if we have access token
        if not publisher.access_token:
            print("No access token found. Starting OAuth flow...")
            auth_url = publisher.get_authorization_url()
            print(f"\nVisit this URL to authorize:\n{auth_url}\n")
            print("After authorizing, you'll be redirected to your callback URL.")
            print("Copy the 'code' parameter from the URL and paste it here:")
            auth_code = input("Authorization code: ").strip()

            # Exchange code for token
            token_info = publisher.get_access_token(auth_code)
            print(f"✓ Access token obtained: {token_info['access_token'][:20]}...\n")
        else:
            print("✓ Using existing access token\n")

        # Get shop ID
        print("Fetching shop information...")
        shop_id = publisher.get_shop_id()
        print(f"✓ Shop ID: {shop_id}\n")

        # Example: Create draft listing
        print("Example product data structure:")
        example_product = {
            'shop_id': shop_id,
            'title': 'Digital Planner 2025 - Productivity & Goal Tracker',
            'description': 'Beautiful and functional digital planner...',
            'price': 15.00,
            'tags': ['planner', 'digital', 'productivity', '2025', 'goals'],
            'quantity': 999
        }
        print(json.dumps(example_product, indent=2))
        print()

        print("To create a listing:")
        print("listing_id = publisher.create_draft_listing(product_data)")
        print()

        print("To upload digital file:")
        print("file_id = publisher.upload_digital_file(shop_id, listing_id, 'path/to/file.pdf')")
        print()

        print("To upload images:")
        print("image_ids = publisher.upload_images(shop_id, listing_id, ['image1.png', 'image2.png'])")
        print()

        print("To publish:")
        print("url = publisher.publish_listing(shop_id, listing_id)")
        print()

    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
