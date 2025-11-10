"""
Trend Monitor Module - Tracks and analyzes trending topics for digital product opportunities

This module uses Google Trends (pytrends) to monitor keyword trends and Claude API
to analyze which trends present profitable opportunities for digital products.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from pytrends.request import TrendReq
from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/trend_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter to prevent API abuse"""

    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < self.time_window]

        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.requests = []

        self.requests.append(now)


class TrendMonitor:
    """
    Monitor and analyze trends for digital product opportunities

    This class integrates Google Trends data with Claude AI analysis to identify
    profitable digital product opportunities.
    """

    # Default keywords to monitor
    DEFAULT_KEYWORDS = [
        "notion template 2025",
        "digital planner aesthetic",
        "midjourney prompts",
        "printable planner",
        "budget tracker"
    ]

    def __init__(self, config_path: str = None):
        """
        Initialize TrendMonitor

        Args:
            config_path: Path to config.yaml file (defaults to ../config.yaml)
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        self.config = self._load_config(config_path)

        # Initialize APIs
        self.anthropic_client = self._initialize_anthropic()
        self.pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))

        # Setup rate limiters
        self._setup_rate_limiters()

        # Cache for trend data
        self.trend_cache = {}
        self.cache_duration = timedelta(
            hours=self.config.get('api_rate_limits', {}).get('general', {}).get('cache_duration_hours', 24)
        )

        logger.info("TrendMonitor initialized successfully")

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _initialize_anthropic(self) -> Anthropic:
        """Initialize Anthropic Claude API client"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your_anthropic_api_key_here':
            logger.error("ANTHROPIC_API_KEY not set in environment variables")
            raise ValueError("ANTHROPIC_API_KEY must be set in .env file")

        return Anthropic(api_key=api_key)

    def _setup_rate_limiters(self):
        """Setup rate limiters for different APIs"""
        anthropic_config = self.config.get('api_rate_limits', {}).get('anthropic', {})
        trends_config = self.config.get('api_rate_limits', {}).get('google_trends', {})

        self.anthropic_limiter = RateLimiter(
            max_requests=anthropic_config.get('requests_per_minute', 50),
            time_window=60
        )

        self.trends_limiter = RateLimiter(
            max_requests=trends_config.get('requests_per_hour', 100),
            time_window=3600
        )

    def fetch_google_trends(self, keywords: List[str] = None,
                           timeframe: str = 'today 3-m',
                           geo: str = 'US') -> Dict[str, Any]:
        """
        Fetch Google Trends data for given keywords

        Args:
            keywords: List of keywords to track (defaults to DEFAULT_KEYWORDS)
            timeframe: Timeframe for trends (e.g., 'today 3-m', 'today 12-m')
            geo: Geographic region (e.g., 'US', 'UK', 'CA')

        Returns:
            Dictionary containing trend data for each keyword
        """
        if keywords is None:
            keywords = self.DEFAULT_KEYWORDS

        # Check cache
        cache_key = f"{'-'.join(keywords)}_{timeframe}_{geo}"
        if cache_key in self.trend_cache:
            cache_time, cache_data = self.trend_cache[cache_key]
            if datetime.now() - cache_time < self.cache_duration:
                logger.info(f"Returning cached trend data for {keywords}")
                return cache_data

        logger.info(f"Fetching Google Trends for keywords: {keywords}")

        try:
            self.trends_limiter.wait_if_needed()

            # Build payload
            self.pytrends.build_payload(
                kw_list=keywords,
                timeframe=timeframe,
                geo=geo
            )

            # Get interest over time
            interest_over_time = self.pytrends.interest_over_time()

            # Get related queries
            related_queries = self.pytrends.related_queries()

            # Get regional interest
            regional_interest = self.pytrends.interest_by_region(resolution='COUNTRY')

            # Process and structure the data
            trend_data = {
                'timestamp': datetime.now().isoformat(),
                'keywords': keywords,
                'timeframe': timeframe,
                'geo': geo,
                'trends': {}
            }

            for keyword in keywords:
                if not interest_over_time.empty and keyword in interest_over_time.columns:
                    # Get recent trend values
                    recent_values = interest_over_time[keyword].tail(30).tolist()
                    current_value = interest_over_time[keyword].iloc[-1] if len(interest_over_time) > 0 else 0
                    avg_value = interest_over_time[keyword].mean()

                    # Calculate trend momentum (recent average vs overall average)
                    recent_avg = sum(recent_values[-7:]) / min(7, len(recent_values)) if recent_values else 0
                    momentum = ((recent_avg - avg_value) / avg_value * 100) if avg_value > 0 else 0

                    trend_data['trends'][keyword] = {
                        'current_interest': int(current_value),
                        'average_interest': float(avg_value),
                        'momentum': float(momentum),
                        'recent_values': recent_values,
                        'related_queries': {
                            'top': related_queries[keyword]['top'].to_dict('records') if related_queries[keyword]['top'] is not None else [],
                            'rising': related_queries[keyword]['rising'].to_dict('records') if related_queries[keyword]['rising'] is not None else []
                        }
                    }
                else:
                    trend_data['trends'][keyword] = {
                        'current_interest': 0,
                        'average_interest': 0,
                        'momentum': 0,
                        'recent_values': [],
                        'related_queries': {'top': [], 'rising': []}
                    }

            # Cache the results
            self.trend_cache[cache_key] = (datetime.now(), trend_data)

            logger.info(f"Successfully fetched trend data for {len(keywords)} keywords")
            return trend_data

        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            raise

    def analyze_with_claude(self, trend_data: Dict[str, Any],
                           retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Analyze trend data using Claude API to determine profitability

        Args:
            trend_data: Dictionary containing Google Trends data
            retry_attempts: Number of retry attempts for API calls

        Returns:
            Dictionary with analysis results including:
            - product_type: Recommended product type
            - niche: Target niche
            - demand_score: Score from 0-100
            - competition_score: Score from 0-100
            - recommended_price: Suggested price range
            - reasoning: Explanation of the analysis
        """
        logger.info("Analyzing trends with Claude API")

        # Prepare the prompt for Claude
        prompt = self._create_analysis_prompt(trend_data)

        for attempt in range(retry_attempts):
            try:
                self.anthropic_limiter.wait_if_needed()

                # Call Claude API
                message = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                # Parse the response
                response_text = message.content[0].text

                # Extract JSON from response
                analysis = self._parse_claude_response(response_text)

                logger.info("Successfully analyzed trends with Claude")
                return analysis

            except RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{retry_attempts})")
                if attempt < retry_attempts - 1:
                    sleep_time = 2 ** attempt  # Exponential backoff
                    time.sleep(sleep_time)
                else:
                    raise

            except (APIError, APITimeoutError) as e:
                logger.error(f"API error on attempt {attempt + 1}/{retry_attempts}: {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(2)
                else:
                    raise

            except Exception as e:
                logger.error(f"Unexpected error analyzing with Claude: {e}")
                raise

    def _create_analysis_prompt(self, trend_data: Dict[str, Any]) -> str:
        """Create a detailed prompt for Claude to analyze trends"""

        # Get pricing ranges from config
        pricing = self.config.get('pricing', {})

        prompt = f"""Analyze the following Google Trends data for digital product opportunities.

TREND DATA:
{json.dumps(trend_data, indent=2)}

CONTEXT:
- We create digital products: Notion templates, digital planners, printables, prompt packs
- Target platforms: Etsy, Gumroad
- Price ranges:
  * Notion templates: ${pricing.get('notion_templates', {}).get('min', 5)}-${pricing.get('notion_templates', {}).get('max', 25)}
  * Digital planners: ${pricing.get('digital_planners', {}).get('min', 8)}-${pricing.get('digital_planners', {}).get('max', 35)}
  * Printables: ${pricing.get('printables', {}).get('min', 3)}-${pricing.get('printables', {}).get('max', 15)}
  * Prompt packs: ${pricing.get('prompt_packs', {}).get('min', 10)}-${pricing.get('prompt_packs', {}).get('max', 30)}

TASK:
For each keyword, analyze:
1. Demand score (0-100): Based on search volume and momentum
2. Competition score (0-100): Based on market saturation (lower is better)
3. Recommended product type: Which digital product fits best
4. Target niche: Specific audience segment
5. Recommended price: Suggested price point
6. Reasoning: Why this is or isn't a good opportunity

Return your analysis as a JSON array with this structure:
[
  {{
    "keyword": "keyword name",
    "product_type": "notion_template|digital_planner|printable|prompt_pack",
    "niche": "specific target audience",
    "demand_score": 0-100,
    "competition_score": 0-100,
    "opportunity_score": 0-100,
    "recommended_price": "numeric value",
    "reasoning": "detailed explanation",
    "suggested_variations": ["variation 1", "variation 2"]
  }},
  ...
]

Focus on actionable insights and be specific about product recommendations."""

        return prompt

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response and extract JSON analysis"""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1

            if start_idx == -1 or end_idx == 0:
                # No JSON array found, try object
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)

                return {
                    'timestamp': datetime.now().isoformat(),
                    'analysis': parsed if isinstance(parsed, list) else [parsed],
                    'raw_response': response_text
                }
            else:
                logger.warning("No JSON found in Claude response, returning raw text")
                return {
                    'timestamp': datetime.now().isoformat(),
                    'analysis': [],
                    'raw_response': response_text
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis': [],
                'raw_response': response_text,
                'error': str(e)
            }

    def get_top_trends(self, limit: int = 5,
                      keywords: List[str] = None,
                      min_opportunity_score: int = 60) -> List[Dict[str, Any]]:
        """
        Get top trending opportunities by combining Google Trends with Claude analysis

        Args:
            limit: Number of top trends to return (default: 5)
            keywords: List of keywords to analyze (defaults to DEFAULT_KEYWORDS)
            min_opportunity_score: Minimum opportunity score to include (0-100)

        Returns:
            List of top trending opportunities with full analysis
        """
        logger.info(f"Getting top {limit} trends")

        if keywords is None:
            # Get keywords from config or use defaults
            keywords = self.config.get('trend_monitoring', {}).get('keywords', self.DEFAULT_KEYWORDS)
            # Limit to first 5 keywords per request (Google Trends limitation)
            keywords = keywords[:5]

        try:
            # Fetch Google Trends data
            trend_data = self.fetch_google_trends(keywords)

            # Analyze with Claude
            analysis = self.analyze_with_claude(trend_data)

            # Extract and sort opportunities
            opportunities = analysis.get('analysis', [])

            # Filter by minimum opportunity score
            opportunities = [
                opp for opp in opportunities
                if opp.get('opportunity_score', 0) >= min_opportunity_score
            ]

            # Sort by opportunity score (descending)
            opportunities.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)

            # Limit results
            top_opportunities = opportunities[:limit]

            # Enrich with additional metadata
            for opp in top_opportunities:
                keyword = opp.get('keyword', '')
                if keyword in trend_data.get('trends', {}):
                    opp['trend_metrics'] = {
                        'current_interest': trend_data['trends'][keyword]['current_interest'],
                        'momentum': trend_data['trends'][keyword]['momentum'],
                        'related_queries': trend_data['trends'][keyword]['related_queries']
                    }

            logger.info(f"Found {len(top_opportunities)} opportunities above score {min_opportunity_score}")

            return top_opportunities

        except Exception as e:
            logger.error(f"Error getting top trends: {e}")
            raise

    def save_analysis(self, analysis: Dict[str, Any], output_dir: str = "data/analyses"):
        """
        Save trend analysis to a JSON file

        Args:
            analysis: Analysis results to save
            output_dir: Directory to save analysis files
        """
        try:
            # Create output directory if it doesn't exist
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trend_analysis_{timestamp}.json"
            filepath = Path(output_dir) / filename

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2)

            logger.info(f"Analysis saved to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
            raise


def main():
    """Example usage of TrendMonitor"""

    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Initialize monitor
    monitor = TrendMonitor()

    # Get top trends
    print("\n" + "="*60)
    print("FETCHING TOP TRENDING OPPORTUNITIES")
    print("="*60 + "\n")

    try:
        top_trends = monitor.get_top_trends(limit=5)

        print(f"\nFound {len(top_trends)} opportunities:\n")

        for i, trend in enumerate(top_trends, 1):
            print(f"{i}. {trend.get('keyword', 'Unknown')}")
            print(f"   Product Type: {trend.get('product_type', 'N/A')}")
            print(f"   Niche: {trend.get('niche', 'N/A')}")
            print(f"   Opportunity Score: {trend.get('opportunity_score', 0)}/100")
            print(f"   Demand Score: {trend.get('demand_score', 0)}/100")
            print(f"   Competition Score: {trend.get('competition_score', 0)}/100")
            print(f"   Recommended Price: ${trend.get('recommended_price', 0)}")
            print(f"   Reasoning: {trend.get('reasoning', 'N/A')[:200]}...")
            print()

        # Save analysis
        analysis_result = {
            'top_trends': top_trends,
            'timestamp': datetime.now().isoformat()
        }
        filepath = monitor.save_analysis(analysis_result)
        print(f"\nFull analysis saved to: {filepath}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\nError: {e}")
        print("Make sure you have set up your .env file with ANTHROPIC_API_KEY")


if __name__ == "__main__":
    main()
