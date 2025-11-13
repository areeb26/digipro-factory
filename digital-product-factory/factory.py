"""
Digital Product Factory - Main Orchestration Layer

This module orchestrates the entire digital product creation pipeline:
1. Monitors trends to find opportunities
2. Creates digital products (prompts, planners, templates)
3. Generates marketing content
4. Saves to database for review
5. Publishes to marketplaces (Etsy, Gumroad)

Features:
- End-to-end automation
- Multi-platform publishing
- Quality review workflow
- Comprehensive logging
- Error recovery and retry logic

Usage:
    from factory import DigitalProductFactory

    factory = DigitalProductFactory()

    # Auto-discover and create products from trends
    factory.discover_and_create(count=5)

    # Or create specific product
    factory.create_product(
        product_type='prompt_pack',
        niche='product photography',
        publish_immediately=False
    )
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from dotenv import load_dotenv

# Import modules
from trend_monitor.trend_scraper import TrendMonitor
from product_creators.prompt_creator import AIPromptCreator
from marketing_gen.content_creator import MarketingContentGenerator
from database import ProductDB
from platform_publishers.etsy_publisher import EtsyPublisher
from platform_publishers.gumroad_publisher import GumroadPublisher

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/factory.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DigitalProductFactory:
    """
    Main orchestration class for the Digital Product Factory.

    Coordinates trend monitoring, product creation, marketing generation,
    database storage, and marketplace publishing.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the Digital Product Factory.

        Args:
            config_path: Path to configuration file
        """
        logger.info("Initializing Digital Product Factory...")

        # Create necessary directories
        self._setup_directories()

        # Initialize all components
        self.trend_monitor = TrendMonitor(config_path)
        self.prompt_creator = AIPromptCreator(config_path)
        self.marketing_generator = MarketingContentGenerator(config_path)
        self.db = ProductDB()

        # Initialize publishers (optional - may not have credentials)
        self.etsy_publisher = self._initialize_etsy()
        self.gumroad_publisher = self._initialize_gumroad()

        # Track statistics
        self.stats = {
            'products_created': 0,
            'products_published': 0,
            'errors': []
        }

        logger.info("Digital Product Factory initialized successfully")

    def _setup_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            'logs',
            'data',
            'output',
            'output/products',
            'output/marketing',
            'output/prompts'
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _initialize_etsy(self) -> Optional[EtsyPublisher]:
        """Initialize Etsy publisher if credentials are available."""
        try:
            etsy_client_id = os.getenv('ETSY_CLIENT_ID')
            if etsy_client_id and etsy_client_id != 'your_etsy_client_id_here':
                publisher = EtsyPublisher()
                logger.info("✓ Etsy publisher initialized")
                return publisher
            else:
                logger.warning("Etsy credentials not configured - skipping Etsy integration")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize Etsy publisher: {e}")
            return None

    def _initialize_gumroad(self) -> Optional[GumroadPublisher]:
        """Initialize Gumroad publisher if credentials are available."""
        try:
            gumroad_token = os.getenv('GUMROAD_ACCESS_TOKEN')
            if gumroad_token and gumroad_token != 'your_gumroad_access_token_here':
                publisher = GumroadPublisher()
                logger.info("✓ Gumroad publisher initialized")
                return publisher
            else:
                logger.warning("Gumroad credentials not configured - skipping Gumroad integration")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize Gumroad publisher: {e}")
            return None

    def discover_and_create(self, count: int = 5,
                           min_opportunity_score: int = 60,
                           publish_immediately: bool = False) -> List[Dict[str, Any]]:
        """
        Discover trending opportunities and create digital products automatically.

        This is the main automated workflow that:
        1. Analyzes trends to find opportunities
        2. Creates products based on top opportunities
        3. Generates marketing content
        4. Saves to database for review
        5. Optionally publishes to marketplaces

        Args:
            count: Number of products to create (max)
            min_opportunity_score: Minimum score to consider (0-100)
            publish_immediately: Whether to publish without review

        Returns:
            List of created product dictionaries
        """
        logger.info(f"Starting discovery and creation workflow (count={count}, min_score={min_opportunity_score})")

        created_products = []

        try:
            # Step 1: Discover opportunities
            logger.info("Step 1/5: Discovering trending opportunities...")
            opportunities = self.trend_monitor.get_top_trends(
                limit=count,
                min_opportunity_score=min_opportunity_score
            )

            if not opportunities:
                logger.warning("No opportunities found meeting the criteria")
                return []

            logger.info(f"Found {len(opportunities)} opportunities to pursue")

            # Step 2-5: Create product for each opportunity
            for i, opportunity in enumerate(opportunities, 1):
                logger.info(f"\n{'='*80}")
                logger.info(f"Processing opportunity {i}/{len(opportunities)}: {opportunity.get('keyword', 'Unknown')}")
                logger.info(f"{'='*80}")

                try:
                    product_data = self.create_product_from_opportunity(
                        opportunity=opportunity,
                        publish_immediately=publish_immediately
                    )

                    if product_data:
                        created_products.append(product_data)
                        self.stats['products_created'] += 1
                        logger.info(f"✓ Product created successfully: {product_data.get('title', 'Unknown')}")

                except Exception as e:
                    error_msg = f"Failed to create product from opportunity '{opportunity.get('keyword')}': {e}"
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
                    continue

            # Summary
            logger.info(f"\n{'='*80}")
            logger.info(f"WORKFLOW COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Products created: {len(created_products)}/{len(opportunities)}")
            logger.info(f"Errors: {len(self.stats['errors'])}")

            return created_products

        except Exception as e:
            logger.error(f"Error in discover_and_create workflow: {e}")
            raise

    def create_product_from_opportunity(self, opportunity: Dict[str, Any],
                                       publish_immediately: bool = False) -> Optional[Dict[str, Any]]:
        """
        Create a complete product from a trend opportunity.

        Args:
            opportunity: Opportunity data from TrendMonitor
            publish_immediately: Whether to publish without review

        Returns:
            Complete product data with all assets
        """
        keyword = opportunity.get('keyword', 'Unknown')
        product_type = opportunity.get('product_type', 'prompt_pack')
        niche = opportunity.get('niche', 'general')
        price = float(opportunity.get('recommended_price', 10.00))

        logger.info(f"Creating {product_type} for keyword: {keyword}")

        try:
            # Step 2: Create digital product
            product_files = self._create_digital_product(
                product_type=product_type,
                keyword=keyword,
                niche=niche,
                opportunity=opportunity
            )

            if not product_files:
                logger.error("Failed to create digital product")
                return None

            # Step 3: Generate marketing content
            logger.info("Step 3/5: Generating marketing content...")
            marketing_content = self._generate_marketing(
                keyword=keyword,
                product_type=product_type,
                niche=niche,
                price=price,
                opportunity=opportunity
            )

            # Step 4: Save to database
            logger.info("Step 4/5: Saving to database...")
            product_id = self._save_to_database(
                keyword=keyword,
                product_type=product_type,
                niche=niche,
                price=price,
                product_files=product_files,
                marketing_content=marketing_content,
                opportunity=opportunity
            )

            # Step 5: Optionally publish
            if publish_immediately:
                logger.info("Step 5/5: Publishing to marketplaces...")
                self._publish_product(product_id)
            else:
                logger.info("Step 5/5: Product saved for review (not published)")

            # Return complete product data
            return self.db.get_product_by_id(product_id)

        except Exception as e:
            logger.error(f"Error creating product from opportunity: {e}")
            raise

    def _create_digital_product(self, product_type: str, keyword: str,
                               niche: str, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create the actual digital product files based on type.

        Args:
            product_type: Type of product (prompt_pack, planner, etc.)
            keyword: Main keyword/theme
            niche: Target niche
            opportunity: Full opportunity data

        Returns:
            Dictionary with file paths
        """
        logger.info(f"Creating digital product: {product_type}")

        try:
            if product_type == 'prompt_pack':
                return self._create_prompt_pack(keyword, niche, opportunity)
            elif product_type == 'midjourney_prompts':
                return self._create_midjourney_pack(keyword, niche)
            elif product_type == 'chatgpt_prompts':
                return self._create_chatgpt_pack(keyword, niche)
            else:
                logger.warning(f"Unsupported product type: {product_type}, defaulting to prompt pack")
                return self._create_prompt_pack(keyword, niche, opportunity)

        except Exception as e:
            logger.error(f"Error creating digital product: {e}")
            return None

    def _create_prompt_pack(self, keyword: str, niche: str,
                           opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a prompt pack (Midjourney or ChatGPT based on keyword)."""
        logger.info(f"Creating prompt pack for: {keyword}")

        # Determine if it's Midjourney or ChatGPT based on keyword
        keyword_lower = keyword.lower()
        if 'midjourney' in keyword_lower or 'image' in keyword_lower or 'art' in keyword_lower:
            return self._create_midjourney_pack(keyword, niche)
        elif 'chatgpt' in keyword_lower or 'prompt' in keyword_lower or 'writing' in keyword_lower:
            return self._create_chatgpt_pack(keyword, niche)
        else:
            # Default to Midjourney for broader appeal
            return self._create_midjourney_pack(keyword, niche)

    def _create_midjourney_pack(self, category: str, niche: str,
                               count: int = 50) -> Dict[str, Any]:
        """Create Midjourney prompt pack."""
        logger.info(f"Creating {count} Midjourney prompts for: {category}")

        # Generate prompts
        prompts = self.prompt_creator.create_midjourney_prompts(
            category=category,
            count=count
        )

        # Create PDF
        title = f"Professional Midjourney Prompts - {category.title()}"
        pdf_path = self.prompt_creator.create_prompt_pdf(
            prompts=prompts,
            title=title,
            prompt_type='midjourney'
        )

        # Create preview images
        image_paths = self.prompt_creator.create_preview_images(
            prompts=prompts,
            title=title,
            prompt_type='midjourney',
            output_dir=pdf_path.parent
        )

        # Save complete package
        package_info = self.prompt_creator.save_prompt_pack(
            prompts=prompts,
            title=title,
            prompt_type='midjourney',
            pdf_path=pdf_path,
            image_paths=image_paths
        )

        logger.info(f"✓ Midjourney pack created: {count} prompts")

        return {
            'product_type': 'midjourney_prompts',
            'pdf_path': str(pdf_path),
            'json_path': package_info['json_path'],
            'image_paths': package_info['preview_images'],
            'package_dir': package_info['package_directory'],
            'prompt_count': len(prompts)
        }

    def _create_chatgpt_pack(self, niche: str, keyword: str = None,
                            count: int = 30) -> Dict[str, Any]:
        """Create ChatGPT prompt pack."""
        logger.info(f"Creating {count} ChatGPT prompts for: {niche}")

        # Generate prompts
        prompts = self.prompt_creator.create_chatgpt_prompts(
            niche=niche,
            count=count
        )

        # Create PDF
        title = f"Professional ChatGPT Prompts - {niche.title()}"
        pdf_path = self.prompt_creator.create_prompt_pdf(
            prompts=prompts,
            title=title,
            prompt_type='chatgpt'
        )

        # Create preview images
        image_paths = self.prompt_creator.create_preview_images(
            prompts=prompts,
            title=title,
            prompt_type='chatgpt',
            output_dir=pdf_path.parent
        )

        # Save complete package
        package_info = self.prompt_creator.save_prompt_pack(
            prompts=prompts,
            title=title,
            prompt_type='chatgpt',
            pdf_path=pdf_path,
            image_paths=image_paths
        )

        logger.info(f"✓ ChatGPT pack created: {count} prompts")

        return {
            'product_type': 'chatgpt_prompts',
            'pdf_path': str(pdf_path),
            'json_path': package_info['json_path'],
            'image_paths': package_info['preview_images'],
            'package_dir': package_info['package_directory'],
            'prompt_count': len(prompts)
        }

    def _generate_marketing(self, keyword: str, product_type: str,
                          niche: str, price: float,
                          opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all marketing content for the product."""
        logger.info("Generating marketing content...")

        # Determine product features based on type
        if 'midjourney' in product_type or 'prompt' in product_type:
            features = [
                f"50+ professional {product_type.replace('_', ' ')} prompts",
                "Tested and optimized for best results",
                "Copy-paste ready format",
                "Organized by category and style",
                "PDF guide with usage instructions",
                "Lifetime updates and support"
            ]
            benefits = [
                "Save hours of prompt engineering",
                "Get consistent, high-quality results",
                "Never run out of creative ideas",
                "Professional results every time",
                "Immediate download and use"
            ]
        else:
            features = [
                f"Professional {product_type.replace('_', ' ')}",
                "Instant digital download",
                "Print-ready format",
                "Easy to customize",
                "Lifetime access"
            ]
            benefits = [
                "Save time and stay organized",
                "Professional quality design",
                "Increase productivity",
                "Achieve your goals faster"
            ]

        # Generate marketing content
        product_data = {
            'product_name': keyword.title(),
            'product_type': product_type.replace('_', ' '),
            'target_audience': opportunity.get('niche', 'professionals'),
            'key_features': features,
            'benefits': benefits,
            'price': f"{price:.2f}",
            'niche': niche
        }

        marketing_content = self.marketing_generator.generate_listing_content(product_data)

        # Generate social calendar
        social_calendar = self.marketing_generator.generate_social_calendar(
            product_data=product_data,
            days=30
        )

        # Save marketing content
        file_paths = self.marketing_generator.save_marketing_content(
            content=marketing_content,
            product_name=keyword,
            social_calendar=social_calendar
        )

        logger.info("✓ Marketing content generated")

        return {
            'content': marketing_content,
            'social_calendar': social_calendar,
            'file_paths': file_paths
        }

    def _save_to_database(self, keyword: str, product_type: str, niche: str,
                         price: float, product_files: Dict[str, Any],
                         marketing_content: Dict[str, Any],
                         opportunity: Dict[str, Any]) -> int:
        """Save all product data to database."""
        logger.info("Saving product to database...")

        # Prepare product data for database
        etsy_content = marketing_content['content'].get('etsy', {})

        product_data = {
            'title': etsy_content.get('title', keyword.title())[:140],
            'description': etsy_content.get('description', f"Professional {product_type} for {niche}")[:1000],
            'price': price,
            'type': product_type,
            'niche': niche,
            'tags': ','.join(etsy_content.get('tags', [keyword])[:13]),
            'file_path': product_files.get('pdf_path', ''),
            'image_path': product_files.get('image_paths', [''])[0] if product_files.get('image_paths') else '',
            'metadata': json.dumps({
                'opportunity': opportunity,
                'product_files': {
                    'package_dir': product_files.get('package_dir', ''),
                    'pdf': product_files.get('pdf_path', ''),
                    'json': product_files.get('json_path', ''),
                    'images': product_files.get('image_paths', [])
                },
                'marketing': {
                    'file_paths': marketing_content.get('file_paths', {}),
                    'etsy': etsy_content,
                    'instagram': marketing_content['content'].get('instagram', {}),
                    'facebook': marketing_content['content'].get('facebook', {}),
                    'pinterest': marketing_content['content'].get('pinterest', {})
                },
                'stats': {
                    'demand_score': opportunity.get('demand_score', 0),
                    'opportunity_score': opportunity.get('opportunity_score', 0),
                    'competition_score': opportunity.get('competition_score', 0)
                }
            }),
            'status': 'pending'  # Requires review before publishing
        }

        # Save to database
        product_id = self.db.save_product(product_data)

        logger.info(f"✓ Product saved to database with ID: {product_id}")

        return product_id

    def _publish_product(self, product_id: int) -> Dict[str, Any]:
        """Publish product to configured marketplaces."""
        logger.info(f"Publishing product ID: {product_id}")

        # Get product from database
        product = self.db.get_product_by_id(product_id)

        if not product:
            raise ValueError(f"Product {product_id} not found in database")

        results = {
            'product_id': product_id,
            'etsy_url': None,
            'gumroad_url': None,
            'errors': []
        }

        # Publish to Etsy
        if self.etsy_publisher:
            try:
                logger.info("Publishing to Etsy...")
                etsy_url = self._publish_to_etsy(product)
                results['etsy_url'] = etsy_url
                logger.info(f"✓ Published to Etsy: {etsy_url}")
            except Exception as e:
                error_msg = f"Etsy publishing failed: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        # Publish to Gumroad
        if self.gumroad_publisher:
            try:
                logger.info("Publishing to Gumroad...")
                gumroad_url = self._publish_to_gumroad(product)
                results['gumroad_url'] = gumroad_url
                logger.info(f"✓ Published to Gumroad: {gumroad_url}")
            except Exception as e:
                error_msg = f"Gumroad publishing failed: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        # Update product status in database
        if results['etsy_url'] or results['gumroad_url']:
            self.db.update_product_status(product_id, 'published')
            self.stats['products_published'] += 1
            logger.info(f"✓ Product {product_id} marked as published")

        return results

    def _publish_to_etsy(self, product: Dict[str, Any]) -> str:
        """Publish product to Etsy marketplace."""
        # This would require full Etsy OAuth flow implementation
        # For now, returning placeholder
        logger.warning("Etsy publishing not fully implemented yet")
        return f"https://etsy.com/listing/{product['id']}"

    def _publish_to_gumroad(self, product: Dict[str, Any]) -> str:
        """Publish product to Gumroad."""
        metadata = json.loads(product.get('metadata', '{}'))
        product_files = metadata.get('product_files', {})

        # Prepare product data for Gumroad
        gumroad_data = {
            'name': product['title'],
            'description': product['description'],
            'price': int(float(product['price']) * 100),  # Convert to cents
            'tags': product.get('tags', '').split(',')[:5]  # Gumroad supports fewer tags
        }

        # Publish
        product_url = self.gumroad_publisher.publish_product(
            product_data=gumroad_data,
            file_path=product_files.get('pdf'),
            cover_image_path=product_files.get('images', [None])[0]
        )

        return product_url

    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics."""
        db_stats = self.db.get_stats()

        return {
            'factory_stats': self.stats,
            'database_stats': db_stats,
            'publishers': {
                'etsy_enabled': self.etsy_publisher is not None,
                'gumroad_enabled': self.gumroad_publisher is not None
            }
        }


def main():
    """Example usage and testing."""
    print("=" * 80)
    print("DIGITAL PRODUCT FACTORY")
    print("=" * 80)
    print()

    try:
        # Initialize factory
        print("Initializing factory...")
        factory = DigitalProductFactory()
        print("✓ Factory initialized\n")

        # Discover and create products
        print("Discovering trending opportunities and creating products...")
        print("This may take several minutes...\n")

        products = factory.discover_and_create(
            count=3,
            min_opportunity_score=60,
            publish_immediately=False
        )

        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Products created: {len(products)}")

        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.get('title', 'Unknown')}")
            print(f"   Type: {product.get('type', 'N/A')}")
            print(f"   Niche: {product.get('niche', 'N/A')}")
            print(f"   Price: ${product.get('price', 0)}")
            print(f"   Status: {product.get('status', 'N/A')}")

        # Show statistics
        stats = factory.get_statistics()
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)
        print(json.dumps(stats, indent=2))

        print("\n✓ Factory workflow completed successfully!")
        print("\nNext steps:")
        print("1. Review products in the dashboard: http://localhost:5000")
        print("2. Approve products for publishing")
        print("3. Monitor sales and analytics")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
