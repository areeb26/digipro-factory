"""
Marketing Content Generator Module

This module creates high-converting marketing content for digital products.
Generates SEO-optimized listings, social media content, and ad copy.

Features:
- Multi-provider AI support (Claude, Gemini, OpenAI) with automatic fallback
- SEO-optimized Etsy listings with tags
- Instagram, Facebook, Pinterest content
- 30-day social media calendar
- CSV export for bulk operations
- Strategic emoji placement

Author: Digital Product Factory
"""

import os
import json
import time
import logging
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Third-party imports
import anthropic
from anthropic import APIError, RateLimitError, APITimeoutError
from dotenv import load_dotenv
import yaml

# Try to import Gemini (optional)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Try to import OpenAI (optional)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


class MarketingContentGenerator:
    """
    Generates high-converting marketing content for digital products.

    This class uses AI to create SEO-optimized listings, social media content,
    ad copy, and posting schedules across multiple platforms.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the MarketingContentGenerator with multi-provider AI support.

        Args:
            config_path: Path to configuration YAML file
        """
        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize AI providers
        self.ai_providers = {}
        self._initialize_ai_providers()

        # Set up provider preference order from config
        content_gen_config = self.config.get('content_generation', {})
        self.preferred_provider = content_gen_config.get('preferred_model', 'anthropic')
        self.fallback_provider = content_gen_config.get('fallback_model', 'gemini')

        # Set up output directory
        self.output_dir = Path("output/marketing")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MarketingContentGenerator initialized with providers: {list(self.ai_providers.keys())}")
        logger.info(f"Provider preference: {self.preferred_provider} (fallback: {self.fallback_provider})")

    def _initialize_ai_providers(self):
        """Initialize all available AI providers."""
        # Initialize Anthropic (Claude)
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key and anthropic_key != 'your_anthropic_api_key_here':
            try:
                self.ai_providers['anthropic'] = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✓ Anthropic (Claude) provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")

        # Initialize Gemini
        if GEMINI_AVAILABLE:
            gemini_key = os.getenv('GEMINI_API_KEY')
            if gemini_key and gemini_key != 'your_gemini_api_key_here':
                try:
                    genai.configure(api_key=gemini_key)
                    self.ai_providers['gemini'] = genai.GenerativeModel('gemini-pro')
                    logger.info("✓ Gemini provider initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini provider: {e}")

        # Initialize OpenAI (optional)
        if OPENAI_AVAILABLE:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key and openai_key != 'your_openai_api_key_here':
                try:
                    openai.api_key = openai_key
                    self.ai_providers['openai'] = openai
                    logger.info("✓ OpenAI provider initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI provider: {e}")

        if not self.ai_providers:
            raise ValueError("No AI providers available. Please configure at least one API key.")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file {config_path} not found, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def generate_listing_content(self, product_data: Dict[str, Any],
                                 retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Generate comprehensive marketing content for a digital product.

        Args:
            product_data: Dictionary containing:
                - product_name: Name of the product
                - product_type: Type (e.g., "planner", "prompts")
                - target_audience: Who it's for
                - key_features: List of features
                - benefits: List of benefits
                - price: Product price
                - niche: Product niche
            retry_attempts: Number of retry attempts per provider

        Returns:
            Dictionary with all marketing content
        """
        logger.info(f"Generating marketing content for: {product_data.get('product_name', 'Unknown')}")

        # Build provider order
        provider_order = self._get_provider_order()
        logger.info(f"Provider order: {provider_order}")

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            logger.info(f"Attempting to use {provider_name} provider...")

            try:
                content = self._generate_content_with_provider(
                    provider_name, product_data, retry_attempts
                )

                logger.info(f"✓ Successfully generated marketing content using {provider_name}")
                return content

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _generate_content_with_provider(self, provider_name: str, product_data: Dict[str, Any],
                                       retry_attempts: int) -> Dict[str, Any]:
        """Generate marketing content using a specific AI provider."""
        prompt = self._build_content_generation_prompt(product_data)

        if provider_name == 'anthropic':
            return self._generate_content_anthropic(prompt, product_data, retry_attempts)
        elif provider_name == 'gemini':
            return self._generate_content_gemini(prompt, product_data, retry_attempts)
        elif provider_name == 'openai':
            return self._generate_content_openai(prompt, product_data, retry_attempts)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def _build_content_generation_prompt(self, product_data: Dict[str, Any]) -> str:
        """Build comprehensive prompt for generating marketing content."""
        product_name = product_data.get('product_name', 'Digital Product')
        product_type = product_data.get('product_type', 'digital product')
        target_audience = product_data.get('target_audience', 'professionals')
        key_features = product_data.get('key_features', [])
        benefits = product_data.get('benefits', [])
        price = product_data.get('price', '12.00')
        niche = product_data.get('niche', 'productivity')

        features_text = '\n'.join([f"- {f}" for f in key_features]) if key_features else "Professional quality digital product"
        benefits_text = '\n'.join([f"- {b}" for b in benefits]) if benefits else "Save time and increase productivity"

        return f"""Create comprehensive, high-converting marketing content for this digital product:

PRODUCT DETAILS:
- Name: {product_name}
- Type: {product_type}
- Target Audience: {target_audience}
- Niche: {niche}
- Price: ${price}

KEY FEATURES:
{features_text}

BENEFITS:
{benefits_text}

Generate the following marketing content in JSON format:

1. ETSY LISTING:
   - title: SEO-optimized title (max 140 characters, include main keywords)
   - description: Compelling description (800-1000 words) focusing on benefits, transformation, and results
   - tags: Array of 13 highly-researched Etsy tags (single words or short 2-word phrases, based on actual search volume)
   - materials: Array of 3-5 materials/what's included

2. INSTAGRAM CONTENT:
   - captions: Array of 5 different Instagram captions (150-200 words each), each with different angle:
     * Caption 1: Benefit-focused with pain points
     * Caption 2: Feature showcase with how-to
     * Caption 3: Transformation story
     * Caption 4: Social proof and testimonials style
     * Caption 5: Call-to-action focused
   - Each caption should include 5-10 strategic emojis and 10-15 relevant hashtags

3. FACEBOOK AD COPY:
   - variations: Array of 3 ad copy variations (125 words each):
     * Variation 1: Problem-solution focused
     * Variation 2: Benefits and features list
     * Variation 3: Urgency and scarcity angle
   - Each with attention-grabbing headline and clear CTA

4. PINTEREST:
   - pin_title: SEO-rich title (max 100 characters)
   - pin_description: Keyword-optimized description (300-400 words)
   - board_suggestions: Array of 5 board names where this pin should go

Return ONLY valid JSON with this exact structure:
{{
  "etsy": {{
    "title": "string (max 140 chars)",
    "description": "string (800-1000 words)",
    "tags": ["tag1", "tag2", ... 13 total],
    "materials": ["material1", "material2", "material3"]
  }},
  "instagram": {{
    "captions": [
      {{
        "angle": "benefit-focused",
        "text": "caption with emojis",
        "hashtags": ["#hashtag1", "#hashtag2", ...]
      }},
      ... 5 total captions
    ]
  }},
  "facebook": {{
    "variations": [
      {{
        "angle": "problem-solution",
        "headline": "attention-grabbing headline",
        "body": "ad copy text",
        "cta": "call to action"
      }},
      ... 3 total variations
    ]
  }},
  "pinterest": {{
    "pin_title": "SEO-rich title",
    "pin_description": "keyword-optimized description",
    "board_suggestions": ["board1", "board2", "board3", "board4", "board5"]
  }}
}}

IMPORTANT:
- Use strategic emoji placement (not overwhelming)
- Focus on benefits and transformation, not just features
- Include keywords naturally for SEO
- Write in conversational, engaging tone
- Use power words and emotional triggers
- All content must be ready to copy-paste and use immediately"""

    def _generate_content_anthropic(self, prompt: str, product_data: Dict[str, Any],
                                   retry_attempts: int) -> Dict[str, Any]:
        """Generate marketing content using Anthropic Claude."""
        client = self.ai_providers['anthropic']

        for attempt in range(retry_attempts):
            try:
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.7,  # Balanced for creative yet consistent copy
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text
                content = self._parse_content_response(response_text)

                # Add metadata
                content['metadata'] = {
                    'product_name': product_data.get('product_name', 'Unknown'),
                    'generated_by': 'anthropic',
                    'generated_at': datetime.now().isoformat(),
                    'model': message.model,
                    'tokens_used': message.usage.input_tokens + message.usage.output_tokens
                }

                return content

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Anthropic retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_content_gemini(self, prompt: str, product_data: Dict[str, Any],
                                retry_attempts: int) -> Dict[str, Any]:
        """Generate marketing content using Google Gemini."""
        model = self.ai_providers['gemini']

        for attempt in range(retry_attempts):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.7,
                        'max_output_tokens': 4000,
                    }
                )

                response_text = response.text
                content = self._parse_content_response(response_text)

                # Add metadata
                content['metadata'] = {
                    'product_name': product_data.get('product_name', 'Unknown'),
                    'generated_by': 'gemini',
                    'generated_at': datetime.now().isoformat(),
                    'model': 'gemini-pro'
                }

                return content

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Gemini retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_content_openai(self, prompt: str, product_data: Dict[str, Any],
                                retry_attempts: int) -> Dict[str, Any]:
        """Generate marketing content using OpenAI."""
        client = self.ai_providers['openai']

        for attempt in range(retry_attempts):
            try:
                response = client.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=4000
                )

                response_text = response.choices[0].message.content
                content = self._parse_content_response(response_text)

                # Add metadata
                content['metadata'] = {
                    'product_name': product_data.get('product_name', 'Unknown'),
                    'generated_by': 'openai',
                    'generated_at': datetime.now().isoformat(),
                    'model': response.model,
                    'tokens_used': response.usage.total_tokens
                }

                return content

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"OpenAI retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _parse_content_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured marketing content."""
        try:
            # Find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            content = json.loads(json_str)

            # Validate structure
            required_keys = ['etsy', 'instagram', 'facebook', 'pinterest']
            for key in required_keys:
                if key not in content:
                    logger.warning(f"Missing {key} in response, using placeholder")
                    content[key] = {}

            logger.info("Successfully parsed marketing content")
            return content

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise

    def optimize_seo(self, title: str, tags: List[str],
                    retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Analyze and optimize SEO for title and tags.

        Args:
            title: Current product title
            tags: List of current tags
            retry_attempts: Number of retry attempts

        Returns:
            Dictionary with SEO analysis and optimized versions
        """
        logger.info("Analyzing and optimizing SEO")

        # Build provider order
        provider_order = self._get_provider_order()

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            try:
                optimization = self._optimize_seo_with_provider(
                    provider_name, title, tags, retry_attempts
                )

                logger.info(f"✓ Successfully optimized SEO using {provider_name}")
                return optimization

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _optimize_seo_with_provider(self, provider_name: str, title: str,
                                   tags: List[str], retry_attempts: int) -> Dict[str, Any]:
        """Optimize SEO using a specific provider."""
        prompt = f"""Analyze and optimize this product listing for SEO:

CURRENT TITLE: {title}
CURRENT TAGS: {', '.join(tags)}

Provide detailed SEO analysis and optimization:

1. SEO STRENGTH ANALYSIS:
   - Title SEO Score (0-100)
   - Keyword density and placement
   - Character usage efficiency
   - Missing keywords or opportunities

2. TAG ANALYSIS:
   - Tag relevance score (0-100)
   - Search volume potential
   - Competition level for each tag
   - Missing high-value tags

3. OPTIMIZED VERSIONS:
   - 3 optimized title variations (with explanations)
   - 13 optimized tags (prioritized by search volume and relevance)
   - Recommended keywords to add

Return as JSON:
{{
  "analysis": {{
    "title_score": 0-100,
    "tag_score": 0-100,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "opportunities": ["opportunity1", "opportunity2"]
  }},
  "optimized_titles": [
    {{"title": "optimized title 1", "reason": "why this works"}},
    {{"title": "optimized title 2", "reason": "why this works"}},
    {{"title": "optimized title 3", "reason": "why this works"}}
  ],
  "optimized_tags": ["tag1", "tag2", ... 13 total],
  "keyword_recommendations": ["keyword1", "keyword2", "keyword3"]
}}"""

        if provider_name == 'anthropic':
            return self._optimize_seo_anthropic(prompt, retry_attempts)
        elif provider_name == 'gemini':
            return self._optimize_seo_gemini(prompt, retry_attempts)
        elif provider_name == 'openai':
            return self._optimize_seo_openai(prompt, retry_attempts)

    def _optimize_seo_anthropic(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Optimize SEO using Anthropic Claude."""
        client = self.ai_providers['anthropic']

        for attempt in range(retry_attempts):
            try:
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    temperature=0.5,  # Lower for analytical tasks
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text
                # Parse JSON from response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                optimization = json.loads(json_str)

                optimization['optimized_by'] = 'anthropic'
                optimization['optimized_at'] = datetime.now().isoformat()

                return optimization

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def _optimize_seo_gemini(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Optimize SEO using Google Gemini."""
        model = self.ai_providers['gemini']

        for attempt in range(retry_attempts):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={'temperature': 0.5, 'max_output_tokens': 2000}
                )

                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                optimization = json.loads(json_str)

                optimization['optimized_by'] = 'gemini'
                optimization['optimized_at'] = datetime.now().isoformat()

                return optimization

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def _optimize_seo_openai(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Optimize SEO using OpenAI."""
        client = self.ai_providers['openai']

        for attempt in range(retry_attempts):
            try:
                response = client.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=2000
                )

                response_text = response.choices[0].message.content
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                optimization = json.loads(json_str)

                optimization['optimized_by'] = 'openai'
                optimization['optimized_at'] = datetime.now().isoformat()

                return optimization

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def generate_social_calendar(self, product_data: Dict[str, Any],
                                 days: int = 30,
                                 retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Generate a social media content calendar.

        Args:
            product_data: Product information
            days: Number of days to plan (default 30)
            retry_attempts: Number of retry attempts

        Returns:
            Dictionary with 30-day posting schedule
        """
        logger.info(f"Generating {days}-day social media calendar")

        # Build provider order
        provider_order = self._get_provider_order()

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            try:
                calendar_data = self._generate_calendar_with_provider(
                    provider_name, product_data, days, retry_attempts
                )

                logger.info(f"✓ Successfully generated calendar using {provider_name}")
                return calendar_data

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _generate_calendar_with_provider(self, provider_name: str, product_data: Dict[str, Any],
                                        days: int, retry_attempts: int) -> Dict[str, Any]:
        """Generate social calendar using a specific provider."""
        product_name = product_data.get('product_name', 'Digital Product')

        prompt = f"""Create a {days}-day social media content calendar for: {product_name}

Generate diverse, engaging content for Instagram, Facebook, and Pinterest.

For each day, provide:
- Platform (Instagram, Facebook, or Pinterest)
- Post type (photo, carousel, video, story, reel, pin)
- Caption/description (platform-appropriate length)
- Best posting time
- Content theme
- Hashtags (for Instagram)
- Call-to-action

CONTENT MIX:
- Educational content (30%)
- Behind-the-scenes (20%)
- User-generated content/testimonials (15%)
- Promotional (20%)
- Engagement/Questions (15%)

Return as JSON:
{{
  "calendar": [
    {{
      "day": 1,
      "date": "2025-11-11",
      "platform": "Instagram",
      "post_type": "carousel",
      "theme": "Educational",
      "caption": "Full caption with emojis",
      "hashtags": ["#hashtag1", "#hashtag2", ...],
      "best_time": "10:00 AM",
      "cta": "Call to action",
      "notes": "Additional notes"
    }},
    ... {days} days total
  ],
  "overview": {{
    "total_posts": {days},
    "instagram_posts": 0,
    "facebook_posts": 0,
    "pinterest_posts": 0,
    "themes_covered": ["theme1", "theme2"]
  }}
}}"""

        if provider_name == 'anthropic':
            return self._generate_calendar_anthropic(prompt, retry_attempts)
        elif provider_name == 'gemini':
            return self._generate_calendar_gemini(prompt, retry_attempts)
        elif provider_name == 'openai':
            return self._generate_calendar_openai(prompt, retry_attempts)

    def _generate_calendar_anthropic(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate calendar using Anthropic Claude."""
        client = self.ai_providers['anthropic']

        for attempt in range(retry_attempts):
            try:
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.8,
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                calendar_data = json.loads(json_str)

                calendar_data['generated_by'] = 'anthropic'
                calendar_data['generated_at'] = datetime.now().isoformat()

                return calendar_data

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_calendar_gemini(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate calendar using Google Gemini."""
        model = self.ai_providers['gemini']

        for attempt in range(retry_attempts):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={'temperature': 0.8, 'max_output_tokens': 4000}
                )

                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                calendar_data = json.loads(json_str)

                calendar_data['generated_by'] = 'gemini'
                calendar_data['generated_at'] = datetime.now().isoformat()

                return calendar_data

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_calendar_openai(self, prompt: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate calendar using OpenAI."""
        client = self.ai_providers['openai']

        for attempt in range(retry_attempts):
            try:
                response = client.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=4000
                )

                response_text = response.choices[0].message.content
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                json_str = response_text[start_idx:end_idx]
                calendar_data = json.loads(json_str)

                calendar_data['generated_by'] = 'openai'
                calendar_data['generated_at'] = datetime.now().isoformat()

                return calendar_data

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

    def save_marketing_content(self, content: Dict[str, Any],
                              product_name: str,
                              social_calendar: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """
        Save marketing content to organized files and CSV.

        Args:
            content: Marketing content dictionary
            product_name: Product name for file naming
            social_calendar: Optional social media calendar

        Returns:
            Dictionary with file paths by category
        """
        logger.info(f"Saving marketing content for: {product_name}")

        # Create product directory
        safe_name = product_name.replace(' ', '_').lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_dir = self.output_dir / f"{safe_name}_{timestamp}"
        product_dir.mkdir(parents=True, exist_ok=True)

        file_paths = {
            'json': [],
            'text': [],
            'csv': []
        }

        # 1. Save complete JSON
        json_path = product_dir / 'marketing_content.json'
        with open(json_path, 'w') as f:
            json.dump(content, f, indent=2)
        file_paths['json'].append(str(json_path))

        # 2. Save Etsy listing as text file
        etsy_path = product_dir / 'etsy_listing.txt'
        etsy_data = content.get('etsy', {})
        with open(etsy_path, 'w') as f:
            f.write(f"TITLE:\n{etsy_data.get('title', '')}\n\n")
            f.write(f"DESCRIPTION:\n{etsy_data.get('description', '')}\n\n")
            f.write(f"TAGS:\n{', '.join(etsy_data.get('tags', []))}\n\n")
            f.write(f"MATERIALS:\n{', '.join(etsy_data.get('materials', []))}\n")
        file_paths['text'].append(str(etsy_path))

        # 3. Save Instagram captions
        instagram_path = product_dir / 'instagram_captions.txt'
        instagram_data = content.get('instagram', {})
        with open(instagram_path, 'w') as f:
            for i, caption_data in enumerate(instagram_data.get('captions', []), 1):
                f.write(f"=== CAPTION {i}: {caption_data.get('angle', 'N/A').upper()} ===\n\n")
                f.write(f"{caption_data.get('text', '')}\n\n")
                f.write(f"HASHTAGS:\n{' '.join(caption_data.get('hashtags', []))}\n\n")
                f.write("-" * 80 + "\n\n")
        file_paths['text'].append(str(instagram_path))

        # 4. Save Facebook ads
        facebook_path = product_dir / 'facebook_ads.txt'
        facebook_data = content.get('facebook', {})
        with open(facebook_path, 'w') as f:
            for i, var in enumerate(facebook_data.get('variations', []), 1):
                f.write(f"=== VARIATION {i}: {var.get('angle', 'N/A').upper()} ===\n\n")
                f.write(f"HEADLINE:\n{var.get('headline', '')}\n\n")
                f.write(f"BODY:\n{var.get('body', '')}\n\n")
                f.write(f"CTA:\n{var.get('cta', '')}\n\n")
                f.write("-" * 80 + "\n\n")
        file_paths['text'].append(str(facebook_path))

        # 5. Save Pinterest content
        pinterest_path = product_dir / 'pinterest_content.txt'
        pinterest_data = content.get('pinterest', {})
        with open(pinterest_path, 'w') as f:
            f.write(f"PIN TITLE:\n{pinterest_data.get('pin_title', '')}\n\n")
            f.write(f"PIN DESCRIPTION:\n{pinterest_data.get('pin_description', '')}\n\n")
            f.write(f"BOARD SUGGESTIONS:\n")
            for board in pinterest_data.get('board_suggestions', []):
                f.write(f"- {board}\n")
        file_paths['text'].append(str(pinterest_path))

        # 6. Save Etsy listing as CSV for bulk upload
        csv_path = product_dir / 'etsy_bulk_upload.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Description', 'Tags', 'Materials', 'Price'])
            writer.writerow([
                etsy_data.get('title', ''),
                etsy_data.get('description', ''),
                ','.join(etsy_data.get('tags', [])),
                ','.join(etsy_data.get('materials', [])),
                content.get('metadata', {}).get('product_name', '')
            ])
        file_paths['csv'].append(str(csv_path))

        # 7. Save social calendar if provided
        if social_calendar:
            calendar_json_path = product_dir / 'social_calendar.json'
            with open(calendar_json_path, 'w') as f:
                json.dump(social_calendar, f, indent=2)
            file_paths['json'].append(str(calendar_json_path))

            # Save calendar as CSV
            calendar_csv_path = product_dir / 'social_calendar.csv'
            with open(calendar_csv_path, 'w', newline='', encoding='utf-8') as f:
                if 'calendar' in social_calendar and social_calendar['calendar']:
                    writer = csv.DictWriter(f, fieldnames=social_calendar['calendar'][0].keys())
                    writer.writeheader()
                    writer.writerows(social_calendar['calendar'])
            file_paths['csv'].append(str(calendar_csv_path))

        # 8. Create README
        readme_path = product_dir / 'README.md'
        readme_content = self._generate_readme(product_name, content, social_calendar)
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        file_paths['text'].append(str(readme_path))

        logger.info(f"Marketing content saved to: {product_dir}")
        logger.info(f"Created {len(file_paths['json'])} JSON, {len(file_paths['text'])} text, {len(file_paths['csv'])} CSV files")

        return file_paths

    def _generate_readme(self, product_name: str, content: Dict[str, Any],
                        social_calendar: Optional[Dict[str, Any]]) -> str:
        """Generate README for marketing content package."""
        return f"""# Marketing Content for {product_name}

Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

## 📦 What's Included

### Etsy Listing Content
- **etsy_listing.txt**: Complete Etsy listing ready to copy-paste
- **etsy_bulk_upload.csv**: CSV format for Etsy bulk upload tool

### Social Media Content
- **instagram_captions.txt**: 5 different Instagram captions with hashtags
- **facebook_ads.txt**: 3 Facebook ad variations
- **pinterest_content.txt**: Pinterest pin title, description, and board suggestions

### Social Media Calendar
- **social_calendar.json**: 30-day content calendar in JSON format
- **social_calendar.csv**: Calendar in CSV for easy scheduling tools

### Complete Data
- **marketing_content.json**: All content in structured JSON format

## 🚀 How to Use

### Etsy Listing
1. Open `etsy_listing.txt`
2. Copy title (stays under 140 characters)
3. Copy description (optimized length for Etsy)
4. Add all 13 tags to your listing
5. List materials/what's included

### Instagram
1. Choose one of 5 caption styles based on your posting strategy
2. Copy caption with emojis already placed
3. Add hashtags at the end or in first comment
4. Post at recommended times from social calendar

### Facebook Ads
1. Create new ad campaign
2. Choose variation based on your target audience
3. Use headline as ad headline
4. Use body as primary text
5. Set CTA button to match the suggestion

### Pinterest
1. Create pin with your product image
2. Use pin title (SEO-optimized)
3. Add pin description (keyword-rich)
4. Save to suggested boards

### Social Calendar
1. Open `social_calendar.csv` in Excel or Google Sheets
2. Import into your scheduling tool (Buffer, Hootsuite, Later, etc.)
3. Schedule posts according to recommended times
4. Customize images/graphics for each post

## 💡 Tips for Best Results

1. **A/B Testing**: Try different Instagram captions to see what resonates
2. **Consistency**: Follow the social calendar for consistent engagement
3. **Adaptation**: Customize content to match your brand voice
4. **Tracking**: Monitor which content performs best and create more of it
5. **Freshness**: Refresh social calendar monthly for ongoing engagement

## 📊 Content Breakdown

- **Etsy Listing**: SEO-optimized for search
- **Instagram Captions**: 5 different angles/approaches
- **Facebook Ads**: 3 variations for different audiences
- **Pinterest**: Keyword-rich for discovery
- **Social Calendar**: 30 days of diverse content

## 🎯 Next Steps

1. Review all content
2. Customize any brand-specific details
3. Schedule social posts using the calendar
4. Launch Etsy listing
5. Run Facebook ad campaigns
6. Track performance and iterate

---

Generated by Digital Product Factory 🚀
"""

    def _get_provider_order(self) -> List[str]:
        """Get provider order based on config."""
        provider_order = []
        if self.preferred_provider in self.ai_providers:
            provider_order.append(self.preferred_provider)
        if self.fallback_provider in self.ai_providers and self.fallback_provider not in provider_order:
            provider_order.append(self.fallback_provider)
        # Add any other available providers
        for provider in self.ai_providers:
            if provider not in provider_order:
                provider_order.append(provider)
        return provider_order


def main():
    """Main function for testing and demonstration."""
    print("=" * 60)
    print("Digital Product Factory - Marketing Content Generator")
    print("=" * 60)
    print()

    try:
        # Initialize generator
        print("Initializing MarketingContentGenerator...")
        generator = MarketingContentGenerator()
        print("✓ MarketingContentGenerator initialized\n")

        # Example product data
        product_data = {
            'product_name': 'Ultimate Social Media Planner 2025',
            'product_type': 'digital planner',
            'target_audience': 'content creators and small business owners',
            'key_features': [
                '12-month planning system',
                'Content calendar templates',
                'Analytics tracking sheets',
                'Goal setting worksheets',
                'Platform-specific post templates'
            ],
            'benefits': [
                'Save 10+ hours per week on content planning',
                'Never run out of content ideas',
                'Increase engagement by 50%',
                'Organize all platforms in one place',
                'Professional-quality content consistently'
            ],
            'price': '15.00',
            'niche': 'social media marketing'
        }

        # Generate listing content
        print("Generating marketing content...")
        content = generator.generate_listing_content(product_data)
        print("✓ Marketing content generated\n")

        # Optimize SEO
        print("Optimizing SEO...")
        seo_optimization = generator.optimize_seo(
            title=content['etsy']['title'],
            tags=content['etsy']['tags']
        )
        print(f"✓ SEO optimized (Score: {seo_optimization['analysis']['title_score']}/100)\n")

        # Generate social calendar
        print("Generating 30-day social calendar...")
        social_calendar = generator.generate_social_calendar(product_data, days=30)
        print(f"✓ Social calendar created ({len(social_calendar['calendar'])} posts)\n")

        # Save everything
        print("Saving marketing content...")
        file_paths = generator.save_marketing_content(
            content=content,
            product_name=product_data['product_name'],
            social_calendar=social_calendar
        )
        print(f"✓ Saved {sum(len(v) for v in file_paths.values())} files\n")

        # Display summary
        print("=" * 60)
        print("MARKETING CONTENT CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"Product: {product_data['product_name']}")
        print(f"Etsy Title: {content['etsy']['title'][:60]}...")
        print(f"Instagram Captions: {len(content['instagram']['captions'])}")
        print(f"Facebook Ad Variations: {len(content['facebook']['variations'])}")
        print(f"Social Posts Planned: {len(social_calendar['calendar'])}")
        print(f"SEO Score: {seo_optimization['analysis']['title_score']}/100")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
