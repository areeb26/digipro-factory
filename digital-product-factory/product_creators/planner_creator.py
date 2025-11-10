"""
Planner Creator Module

This module creates professional digital planners using AI for design
and reportlab for PDF generation. Creates print-ready PDFs with preview images.

Features:
- Multi-provider AI support (Claude, Gemini, OpenAI) with automatic fallback
- Print-ready PDF generation (8.5x11 inch, 300 DPI)
- Professional formatting with graphics and styling
- Preview image generation for product listings
- Complete product packaging with metadata

Author: Digital Product Factory
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import calendar

# Third-party imports
import anthropic
from anthropic import APIError, RateLimitError, APITimeoutError
from dotenv import load_dotenv
import yaml
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Try to import Gemini (optional)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Gemini provider not available.")

# Try to import OpenAI (optional)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai not installed. OpenAI provider not available.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)


class PlannerCreator:
    """
    Creates digital planners with AI-generated designs and professional PDF output.

    This class uses Claude API to generate planner layouts and designs,
    then creates print-ready PDFs using reportlab. Includes preview image
    generation and product packaging.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the PlannerCreator with multi-provider AI support.

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
        self.output_dir = Path("output/planners")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"PlannerCreator initialized with providers: {list(self.ai_providers.keys())}")
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

    def create_planner(self, planner_type: str, aesthetic: str,
                       retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Generate planner design using AI with automatic provider fallback.

        Args:
            planner_type: Type of planner (e.g., "daily", "weekly", "budget")
            aesthetic: Visual aesthetic (e.g., "minimalist", "floral", "professional")
            retry_attempts: Number of retry attempts per provider

        Returns:
            Dictionary containing complete planner design specifications
        """
        logger.info(f"Creating {aesthetic} {planner_type} planner design")

        # Build provider order: preferred, fallback, then any remaining
        provider_order = []
        if self.preferred_provider in self.ai_providers:
            provider_order.append(self.preferred_provider)
        if self.fallback_provider in self.ai_providers and self.fallback_provider not in provider_order:
            provider_order.append(self.fallback_provider)
        # Add any other available providers
        for provider in self.ai_providers:
            if provider not in provider_order:
                provider_order.append(provider)

        logger.info(f"Provider order: {provider_order}")

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            logger.info(f"Attempting to use {provider_name} provider...")

            try:
                design_spec = self._generate_with_provider(
                    provider_name, planner_type, aesthetic, retry_attempts
                )

                logger.info(f"✓ Successfully created planner design using {provider_name}")
                return design_spec

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _generate_with_provider(self, provider_name: str, planner_type: str,
                                aesthetic: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate planner design using a specific AI provider."""
        # Build provider-specific prompt
        prompt = self._build_design_prompt(planner_type, aesthetic, provider_name)

        if provider_name == 'anthropic':
            return self._generate_with_anthropic(prompt, planner_type, aesthetic, retry_attempts)
        elif provider_name == 'gemini':
            return self._generate_with_gemini(prompt, planner_type, aesthetic, retry_attempts)
        elif provider_name == 'openai':
            return self._generate_with_openai(prompt, planner_type, aesthetic, retry_attempts)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def _generate_with_anthropic(self, prompt: str, planner_type: str,
                                 aesthetic: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate planner design using Anthropic Claude."""
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
                design_spec = self._parse_design_response(response_text)

                design_spec['metadata'] = {
                    'planner_type': planner_type,
                    'aesthetic': aesthetic,
                    'created_at': datetime.now().isoformat(),
                    'provider': 'anthropic',
                    'model': message.model,
                    'tokens_used': message.usage.input_tokens + message.usage.output_tokens
                }

                return design_spec

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Anthropic retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_with_gemini(self, prompt: str, planner_type: str,
                              aesthetic: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate planner design using Google Gemini."""
        model = self.ai_providers['gemini']

        for attempt in range(retry_attempts):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.8,
                        'max_output_tokens': 4000,
                    }
                )

                response_text = response.text
                design_spec = self._parse_design_response(response_text)

                design_spec['metadata'] = {
                    'planner_type': planner_type,
                    'aesthetic': aesthetic,
                    'created_at': datetime.now().isoformat(),
                    'provider': 'gemini',
                    'model': 'gemini-pro',
                    'tokens_used': 'N/A'  # Gemini doesn't always provide token counts
                }

                return design_spec

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Gemini retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_with_openai(self, prompt: str, planner_type: str,
                              aesthetic: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate planner design using OpenAI."""
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
                design_spec = self._parse_design_response(response_text)

                design_spec['metadata'] = {
                    'planner_type': planner_type,
                    'aesthetic': aesthetic,
                    'created_at': datetime.now().isoformat(),
                    'provider': 'openai',
                    'model': response.model,
                    'tokens_used': response.usage.total_tokens
                }

                return design_spec

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"OpenAI retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _build_design_prompt(self, planner_type: str, aesthetic: str, provider: str = 'anthropic') -> str:
        """Build provider-optimized prompt for planner design generation."""

        # Provider-specific prompt optimization
        if provider == 'gemini':
            # Gemini prefers more structured, step-by-step instructions
            instruction_style = "Follow these steps carefully to"
        elif provider == 'openai':
            # OpenAI GPT-4 works well with role-based prompts
            instruction_style = "As an expert planner designer, please"
        else:  # anthropic/claude
            # Claude prefers direct, task-oriented prompts
            instruction_style = "Please"

        return f"""{instruction_style} design a comprehensive {planner_type} planner with a {aesthetic} aesthetic.

Create a complete 12-month planner with the following specifications:

1. COVER PAGE DESIGN:
   - Title placement and typography
   - Subtitle and year
   - Visual elements and decorations
   - Color palette (provide hex codes)

2. PAGE STRUCTURE (for each month):
   - Monthly calendar view layout
   - Daily/weekly planning pages layout
   - Section headers and labels
   - Space allocation for different planning elements

3. CONTENT FOR EACH PAGE TYPE:
   - Cover page
   - Month overview pages (12 months)
   - Weekly planning pages
   - Notes pages
   - Goal tracking pages
   - Habit tracker pages

4. DESIGN ELEMENTS:
   - Primary color palette (3-5 hex colors)
   - Secondary accent colors
   - Typography recommendations (headings, body, labels)
   - Decorative elements (borders, icons, dividers)
   - Layout spacing and margins

5. SECTIONS TO INCLUDE:
   - Goals section
   - Habit tracker
   - Budget tracker (if applicable)
   - Notes pages
   - Contact information
   - Important dates

Return your response as a JSON object with this structure:
{{
    "planner_name": "creative name",
    "cover_design": {{
        "title": "main title",
        "subtitle": "subtitle text",
        "year": 2025,
        "color_palette": ["#hex1", "#hex2", "#hex3"],
        "decorative_elements": ["element1", "element2"]
    }},
    "color_scheme": {{
        "primary": "#hexcode",
        "secondary": "#hexcode",
        "accent": "#hexcode",
        "text_dark": "#hexcode",
        "text_light": "#hexcode",
        "background": "#hexcode"
    }},
    "typography": {{
        "heading_style": "style description",
        "body_style": "style description",
        "label_style": "style description"
    }},
    "page_layouts": {{
        "monthly_calendar": {{
            "layout_description": "description",
            "sections": ["section1", "section2"],
            "elements": ["element1", "element2"]
        }},
        "weekly_spread": {{
            "layout_description": "description",
            "sections": ["section1", "section2"],
            "elements": ["element1", "element2"]
        }},
        "daily_page": {{
            "layout_description": "description",
            "sections": ["section1", "section2"],
            "elements": ["element1", "element2"]
        }},
        "habit_tracker": {{
            "layout_description": "description",
            "tracking_method": "method description"
        }},
        "notes_page": {{
            "layout_description": "description",
            "line_style": "style description"
        }}
    }},
    "content_sections": [
        {{
            "name": "section name",
            "page_count": 2,
            "description": "what this section contains"
        }}
    ],
    "special_features": ["feature1", "feature2"],
    "target_audience": "who this planner is for",
    "key_benefits": ["benefit1", "benefit2"]
}}

Make the design cohesive, professional, and appealing to the target audience."""

    def _parse_design_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response into a structured design specification."""
        try:
            # Find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            design_spec = json.loads(json_str)

            return design_spec

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise

    def generate_pdf(self, design_spec: Dict[str, Any],
                     output_path: Optional[Path] = None) -> Path:
        """
        Generate print-ready PDF planner using reportlab.

        Args:
            design_spec: Design specifications from create_planner()
            output_path: Optional custom output path

        Returns:
            Path to generated PDF file
        """
        logger.info("Generating PDF planner")

        # Set up output path
        if output_path is None:
            planner_name = design_spec.get('planner_name', 'planner').replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"{planner_name}_{timestamp}.pdf"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create PDF with proper settings (8.5x11 inch, 300 DPI equivalent)
        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter  # 8.5 x 11 inches

        # Extract design elements
        colors_dict = design_spec.get('color_scheme', {})
        primary_color = HexColor(colors_dict.get('primary', '#4A5568'))
        secondary_color = HexColor(colors_dict.get('secondary', '#718096'))
        accent_color = HexColor(colors_dict.get('accent', '#ED8936'))

        # Page counter
        page_num = 0

        # 1. Create cover page
        page_num += 1
        self._create_cover_page(c, design_spec, width, height, primary_color, accent_color)
        c.showPage()

        # 2. Create year overview page
        page_num += 1
        self._create_year_overview(c, design_spec, width, height, primary_color, secondary_color)
        c.showPage()

        # 3. Create monthly pages (12 months)
        start_date = datetime(2025, 1, 1)
        for month_offset in range(12):
            current_date = start_date + timedelta(days=30 * month_offset)
            current_date = current_date.replace(day=1)

            # Month overview page
            page_num += 1
            self._create_month_page(c, design_spec, current_date, width, height,
                                   primary_color, secondary_color, accent_color)
            c.showPage()

            # Weekly pages for this month
            for week in range(4):
                page_num += 1
                week_start = current_date + timedelta(weeks=week)
                self._create_weekly_page(c, design_spec, week_start, width, height,
                                       primary_color, secondary_color, accent_color)
                c.showPage()

        # 4. Create habit tracker pages (quarterly)
        for quarter in range(4):
            page_num += 1
            self._create_habit_tracker(c, design_spec, quarter + 1, width, height,
                                      primary_color, accent_color)
            c.showPage()

        # 5. Create notes pages (10 pages)
        for notes_page in range(10):
            page_num += 1
            self._create_notes_page(c, design_spec, width, height, primary_color)
            c.showPage()

        # Save PDF
        c.save()

        logger.info(f"PDF generated successfully: {output_path} ({page_num} pages)")
        return output_path

    def _create_cover_page(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                          width: float, height: float,
                          primary_color: HexColor, accent_color: HexColor):
        """Create the cover page."""
        cover_design = design_spec.get('cover_design', {})

        # Background
        c.setFillColor(primary_color)
        c.rect(0, 0, width, height, fill=True, stroke=False)

        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 48)
        title = cover_design.get('title', design_spec.get('planner_name', '2025 Planner'))
        title_width = c.stringWidth(title, "Helvetica-Bold", 48)
        c.drawString((width - title_width) / 2, height - 2.5 * inch, title)

        # Subtitle
        c.setFont("Helvetica", 24)
        subtitle = cover_design.get('subtitle', 'Your Journey to Success')
        subtitle_width = c.stringWidth(subtitle, "Helvetica", 24)
        c.drawString((width - subtitle_width) / 2, height - 3.2 * inch, subtitle)

        # Year
        c.setFont("Helvetica-Bold", 72)
        year = str(cover_design.get('year', 2025))
        year_width = c.stringWidth(year, "Helvetica-Bold", 72)
        c.drawString((width - year_width) / 2, height - 5.5 * inch, year)

        # Decorative accent
        c.setFillColor(accent_color)
        c.rect(1.5 * inch, 2 * inch, width - 3 * inch, 0.5 * inch, fill=True, stroke=False)

    def _create_year_overview(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                             width: float, height: float,
                             primary_color: HexColor, secondary_color: HexColor):
        """Create year overview page with all 12 months."""
        # Header
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 32)
        c.drawString(1 * inch, height - 1.5 * inch, "2025 Year Overview")

        # Draw mini calendars for all 12 months (3x4 grid)
        months_per_row = 3
        calendar_width = (width - 2 * inch) / months_per_row - 0.3 * inch
        calendar_height = 1.2 * inch

        start_x = 1 * inch
        start_y = height - 2.5 * inch

        for month_num in range(1, 13):
            row = (month_num - 1) // months_per_row
            col = (month_num - 1) % months_per_row

            x = start_x + col * (calendar_width + 0.3 * inch)
            y = start_y - row * (calendar_height + 0.4 * inch)

            self._draw_mini_calendar(c, month_num, 2025, x, y, calendar_width,
                                    calendar_height, primary_color, secondary_color)

    def _draw_mini_calendar(self, c: canvas.Canvas, month: int, year: int,
                           x: float, y: float, width: float, height: float,
                           primary_color: HexColor, secondary_color: HexColor):
        """Draw a small calendar for a specific month."""
        # Month name
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 10)
        month_name = calendar.month_name[month]
        c.drawString(x, y, month_name)

        # Weekday headers
        c.setFont("Helvetica", 7)
        weekdays = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        cell_width = width / 7

        for i, day in enumerate(weekdays):
            c.drawString(x + i * cell_width, y - 0.15 * inch, day)

        # Calendar grid
        cal = calendar.monthcalendar(year, month)
        cell_height = (height - 0.3 * inch) / len(cal)

        c.setFont("Helvetica", 6)
        c.setFillColor(secondary_color)

        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day != 0:
                    day_x = x + day_num * cell_width + cell_width / 3
                    day_y = y - 0.3 * inch - (week_num + 1) * cell_height + cell_height / 3
                    c.drawString(day_x, day_y, str(day))

    def _create_month_page(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                          date: datetime, width: float, height: float,
                          primary_color: HexColor, secondary_color: HexColor,
                          accent_color: HexColor):
        """Create monthly overview page."""
        month_name = date.strftime('%B %Y')

        # Header with accent background
        c.setFillColor(primary_color)
        c.rect(0, height - 1.5 * inch, width, 1.5 * inch, fill=True, stroke=False)

        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 36)
        c.drawString(1 * inch, height - 1.2 * inch, month_name)

        # Large calendar
        cal_x = 1 * inch
        cal_y = height - 2 * inch
        cal_width = width - 2 * inch
        cal_height = 5 * inch

        self._draw_month_calendar(c, date.month, date.year, cal_x, cal_y,
                                 cal_width, cal_height, primary_color,
                                 secondary_color, accent_color)

        # Goals section
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1 * inch, 2.5 * inch, "Monthly Goals:")

        c.setFont("Helvetica", 11)
        c.setFillColor(secondary_color)
        for i in range(5):
            y_pos = 2.2 * inch - i * 0.25 * inch
            c.drawString(1.2 * inch, y_pos, f"☐ ____________________________________")

    def _draw_month_calendar(self, c: canvas.Canvas, month: int, year: int,
                            x: float, y: float, width: float, height: float,
                            primary_color: HexColor, secondary_color: HexColor,
                            accent_color: HexColor):
        """Draw a full month calendar with grid."""
        # Weekday headers
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(primary_color)
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        cell_width = width / 7

        for i, day in enumerate(weekdays):
            c.drawString(x + i * cell_width + 5, y, day[:3])

        # Draw grid
        cal = calendar.monthcalendar(year, month)
        cell_height = (height - 0.3 * inch) / len(cal)

        # Grid lines
        c.setStrokeColor(secondary_color)
        c.setLineWidth(0.5)

        # Vertical lines
        for i in range(8):
            c.line(x + i * cell_width, y - 0.2 * inch,
                  x + i * cell_width, y - 0.2 * inch - len(cal) * cell_height)

        # Horizontal lines
        for i in range(len(cal) + 1):
            c.line(x, y - 0.2 * inch - i * cell_height,
                  x + width, y - 0.2 * inch - i * cell_height)

        # Fill in dates
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(primary_color)

        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day != 0:
                    day_x = x + day_num * cell_width + 5
                    day_y = y - 0.35 * inch - week_num * cell_height
                    c.drawString(day_x, day_y, str(day))

    def _create_weekly_page(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                           week_start: datetime, width: float, height: float,
                           primary_color: HexColor, secondary_color: HexColor,
                           accent_color: HexColor):
        """Create weekly planning page."""
        # Header
        week_end = week_start + timedelta(days=6)
        header_text = f"Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}"

        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1 * inch, height - 1 * inch, header_text)

        # Draw 7 day boxes
        box_height = (height - 2.5 * inch) / 7
        box_width = width - 2 * inch

        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i in range(7):
            current_day = week_start + timedelta(days=i)
            y_pos = height - 1.5 * inch - i * box_height

            # Day header background
            c.setFillColor(accent_color if i < 5 else secondary_color)
            c.rect(1 * inch, y_pos - 0.3 * inch, box_width, 0.3 * inch, fill=True, stroke=False)

            # Day name and date
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 11)
            day_label = f"{weekdays[i]}, {current_day.strftime('%B %d')}"
            c.drawString(1.1 * inch, y_pos - 0.22 * inch, day_label)

            # Planning box
            c.setStrokeColor(secondary_color)
            c.setLineWidth(1)
            c.rect(1 * inch, y_pos - box_height, box_width, box_height - 0.35 * inch,
                  fill=False, stroke=True)

    def _create_habit_tracker(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                             quarter: int, width: float, height: float,
                             primary_color: HexColor, accent_color: HexColor):
        """Create quarterly habit tracker page."""
        # Header
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(1 * inch, height - 1 * inch, f"Habit Tracker - Q{quarter} 2025")

        # Instructions
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.grey)
        c.drawString(1 * inch, height - 1.3 * inch, "Track your daily habits. Mark each day you complete the habit.")

        # Create habit tracking grid
        habits = [
            "Morning Exercise",
            "Drink 8 Glasses of Water",
            "Read for 30 Minutes",
            "Meditate",
            "Healthy Eating",
            "Sleep 8 Hours",
            "Journal",
            "Learn Something New"
        ]

        grid_start_y = height - 2 * inch
        row_height = 0.4 * inch
        col_width = 0.25 * inch

        # Draw habit names
        c.setFont("Helvetica", 9)
        c.setFillColor(primary_color)
        for i, habit in enumerate(habits):
            y_pos = grid_start_y - i * row_height
            c.drawString(1 * inch, y_pos, habit)

        # Draw grid for 31 days
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)

        grid_x_start = 3.5 * inch
        for day in range(31):
            col = day % 15
            row_offset = 0 if day < 15 else len(habits) + 1

            x_pos = grid_x_start + col * col_width

            # Day number header
            if row_offset == 0:
                c.setFont("Helvetica", 7)
                c.setFillColor(accent_color)
                c.drawString(x_pos + 0.05 * inch, grid_start_y + 0.2 * inch, str(day + 1))

            # Draw checkboxes for each habit
            for i in range(len(habits)):
                y_pos = grid_start_y - (i + row_offset) * row_height
                c.rect(x_pos, y_pos - 0.15 * inch, 0.2 * inch, 0.2 * inch,
                      fill=False, stroke=True)

    def _create_notes_page(self, c: canvas.Canvas, design_spec: Dict[str, Any],
                          width: float, height: float, primary_color: HexColor):
        """Create lined notes page."""
        # Header
        c.setFillColor(primary_color)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1 * inch, height - 1 * inch, "Notes")

        # Draw horizontal lines
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)

        line_spacing = 0.3 * inch
        start_y = height - 1.5 * inch

        for i in range(int((start_y - 0.5 * inch) / line_spacing)):
            y_pos = start_y - i * line_spacing
            c.line(1 * inch, y_pos, width - 1 * inch, y_pos)

    def create_preview_images(self, design_spec: Dict[str, Any],
                             pdf_path: Path) -> List[Path]:
        """
        Create preview images of planner pages for marketing.

        Args:
            design_spec: Design specifications
            pdf_path: Path to generated PDF

        Returns:
            List of paths to preview images
        """
        logger.info("Creating preview images")

        # Create images directory
        images_dir = pdf_path.parent / 'images'
        images_dir.mkdir(exist_ok=True)

        preview_images = []

        # Extract colors
        colors_dict = design_spec.get('color_scheme', {})
        primary_hex = colors_dict.get('primary', '#4A5568')
        accent_hex = colors_dict.get('accent', '#ED8936')

        # 1. Cover preview (1200x1600 - product listing)
        cover_path = images_dir / 'cover_preview.png'
        self._create_cover_preview(design_spec, cover_path, primary_hex, accent_hex)
        preview_images.append(cover_path)

        # 2. Sample spread preview (1600x1200 - two-page spread)
        spread_path = images_dir / 'sample_spread.png'
        self._create_spread_preview(design_spec, spread_path, primary_hex, accent_hex)
        preview_images.append(spread_path)

        # 3. Full overview (1200x1200 - features showcase)
        overview_path = images_dir / 'full_overview.png'
        self._create_overview_image(design_spec, overview_path, primary_hex, accent_hex)
        preview_images.append(overview_path)

        logger.info(f"Created {len(preview_images)} preview images")
        return preview_images

    def _create_cover_preview(self, design_spec: Dict[str, Any],
                             output_path: Path, primary_hex: str, accent_hex: str):
        """Create cover page preview image."""
        # Create image
        img = Image.new('RGB', (1200, 1600), color=primary_hex)
        draw = ImageDraw.Draw(img)

        # Try to use a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            year_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            year_font = ImageFont.load_default()

        cover_design = design_spec.get('cover_design', {})

        # Title
        title = cover_design.get('title', design_spec.get('planner_name', '2025 Planner'))
        bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = bbox[2] - bbox[0]
        draw.text((600 - title_width/2, 300), title, fill='white', font=title_font)

        # Subtitle
        subtitle = cover_design.get('subtitle', 'Your Journey to Success')
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = bbox[2] - bbox[0]
        draw.text((600 - subtitle_width/2, 420), subtitle, fill='white', font=subtitle_font)

        # Year
        year = str(cover_design.get('year', 2025))
        bbox = draw.textbbox((0, 0), year, font=year_font)
        year_width = bbox[2] - bbox[0]
        draw.text((600 - year_width/2, 700), year, fill='white', font=year_font)

        # Decorative accent rectangle
        draw.rectangle([200, 950, 1000, 1000], fill=accent_hex)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Cover preview saved: {output_path}")

    def _create_spread_preview(self, design_spec: Dict[str, Any],
                              output_path: Path, primary_hex: str, accent_hex: str):
        """Create two-page spread preview."""
        # Create wide image for spread
        img = Image.new('RGB', (1600, 1200), color='white')
        draw = ImageDraw.Draw(img)

        try:
            header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        # Left page - Monthly calendar
        draw.text((50, 50), "January 2025", fill=primary_hex, font=header_font)

        # Draw mini calendar grid
        grid_x, grid_y = 50, 120
        cell_size = 90

        weekdays = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        for i, day in enumerate(weekdays):
            draw.text((grid_x + i * cell_size + 20, grid_y), day, fill=primary_hex, font=body_font)

        # Sample calendar dates
        for row in range(5):
            for col in range(7):
                x = grid_x + col * cell_size
                y = grid_y + 50 + row * cell_size
                draw.rectangle([x, y, x + cell_size - 5, y + cell_size - 5],
                             outline=accent_hex, width=2)
                day_num = row * 7 + col + 1
                if day_num <= 31:
                    draw.text((x + 30, y + 25), str(day_num), fill=primary_hex, font=body_font)

        # Right page - Weekly view
        draw.text((850, 50), "Week 1", fill=primary_hex, font=header_font)

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for i, day in enumerate(days):
            y = 150 + i * 180
            draw.rectangle([850, y, 1550, y + 150], outline=accent_hex, width=2)
            draw.text((870, y + 10), day, fill=primary_hex, font=body_font)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Spread preview saved: {output_path}")

    def _create_overview_image(self, design_spec: Dict[str, Any],
                              output_path: Path, primary_hex: str, accent_hex: str):
        """Create overview image showcasing features."""
        img = Image.new('RGB', (1200, 1200), color='white')
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            feature_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            feature_font = ImageFont.load_default()

        # Title
        planner_name = design_spec.get('planner_name', '2025 Planner')
        draw.text((100, 50), f"{planner_name} - Features", fill=primary_hex, font=title_font)

        # List key features
        features = design_spec.get('key_benefits', [
            "12-Month Planning System",
            "Weekly & Monthly Views",
            "Habit Tracking Pages",
            "Goal Setting Sections",
            "Notes & Reflection Space",
            "Print-Ready PDF Format"
        ])

        y_offset = 180
        for i, feature in enumerate(features[:8]):  # Max 8 features
            # Draw bullet point
            draw.ellipse([100, y_offset + 5, 120, y_offset + 25], fill=accent_hex)
            # Draw feature text
            draw.text((150, y_offset), f"{feature}", fill=primary_hex, font=feature_font)
            y_offset += 100

        # Add decorative border
        draw.rectangle([50, 50, 1150, 1150], outline=accent_hex, width=5)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Overview image saved: {output_path}")

    def save_planner(self, design_spec: Dict[str, Any],
                     pdf_path: Path, image_paths: List[Path]) -> Dict[str, Any]:
        """
        Save complete planner package with all files and metadata.

        Args:
            design_spec: Design specifications
            pdf_path: Path to generated PDF
            image_paths: List of preview image paths

        Returns:
            Dictionary with package information and file paths
        """
        logger.info("Saving planner package")

        # Create package directory
        package_dir = pdf_path.parent

        # Save design specifications as JSON
        spec_path = package_dir / 'design_specifications.json'
        with open(spec_path, 'w') as f:
            json.dump(design_spec, f, indent=2)

        # Create README
        readme_path = package_dir / 'README.md'
        readme_content = self._generate_readme(design_spec, pdf_path, image_paths)
        with open(readme_path, 'w') as f:
            f.write(readme_content)

        # Create metadata
        metadata = {
            'planner_name': design_spec.get('planner_name', 'Planner'),
            'planner_type': design_spec['metadata']['planner_type'],
            'aesthetic': design_spec['metadata']['aesthetic'],
            'created_at': datetime.now().isoformat(),
            'files': {
                'pdf': str(pdf_path.name),
                'design_spec': str(spec_path.name),
                'readme': str(readme_path.name),
                'preview_images': [str(p.name) for p in image_paths]
            },
            'specifications': {
                'page_size': '8.5 x 11 inches (Letter)',
                'format': 'PDF',
                'print_ready': True,
                'dpi_equivalent': '300 DPI',
                'color_mode': 'RGB'
            },
            'target_audience': design_spec.get('target_audience', 'General audience'),
            'key_benefits': design_spec.get('key_benefits', [])
        }

        metadata_path = package_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Create package info
        package_info = {
            'package_directory': str(package_dir),
            'pdf_path': str(pdf_path),
            'preview_images': [str(p) for p in image_paths],
            'design_spec_path': str(spec_path),
            'readme_path': str(readme_path),
            'metadata_path': str(metadata_path),
            'metadata': metadata
        }

        logger.info(f"Planner package saved: {package_dir}")
        return package_info

    def _generate_readme(self, design_spec: Dict[str, Any],
                        pdf_path: Path, image_paths: List[Path]) -> str:
        """Generate README content for planner package."""
        planner_name = design_spec.get('planner_name', 'Planner')

        readme = f"""# {planner_name}

## Overview

{design_spec.get('target_audience', 'A comprehensive digital planner designed to help you stay organized and productive.')}

## Features

"""

        # Add key benefits
        benefits = design_spec.get('key_benefits', [])
        for benefit in benefits:
            readme += f"- {benefit}\n"

        readme += f"""
## Contents

This planner includes:

"""

        # Add content sections
        sections = design_spec.get('content_sections', [])
        for section in sections:
            readme += f"- **{section['name']}**: {section['description']}\n"

        readme += f"""
## File Structure

- `{pdf_path.name}` - Print-ready PDF planner
- `design_specifications.json` - Complete design specifications
- `images/` - Preview images for product listings
- `metadata.json` - Product metadata and specifications

## Specifications

- **Format**: PDF
- **Page Size**: 8.5 x 11 inches (US Letter)
- **Print Ready**: Yes (300 DPI equivalent)
- **Pages**: 60+ pages
- **Year**: 2025

## Color Scheme

"""

        colors = design_spec.get('color_scheme', {})
        for color_name, color_hex in colors.items():
            readme += f"- **{color_name.replace('_', ' ').title()}**: {color_hex}\n"

        readme += f"""
## Usage Instructions

1. Open the PDF file in your preferred PDF reader
2. Print the pages you need, or use digitally on your tablet
3. For best results, print on high-quality paper
4. Consider binding for a professional finish

## Special Features

"""

        special_features = design_spec.get('special_features', [])
        for feature in special_features:
            readme += f"- {feature}\n"

        readme += f"""
## License

This planner is for personal use. Commercial use and redistribution require explicit permission.

## Created

Generated on {datetime.now().strftime('%B %d, %Y')} using Digital Product Factory.

---

Enjoy your planning journey! 📅✨
"""

        return readme


def main():
    """Main function for testing and demonstration."""
    print("=" * 60)
    print("Digital Product Factory - Planner Creator")
    print("=" * 60)
    print()

    try:
        # Initialize creator
        print("Initializing PlannerCreator...")
        creator = PlannerCreator()
        print("✓ PlannerCreator initialized\n")

        # Example 1: Create a minimalist daily planner
        print("Creating minimalist daily planner...")
        design_spec = creator.create_planner(
            planner_type="daily",
            aesthetic="minimalist"
        )
        print(f"✓ Design created: {design_spec.get('planner_name', 'Planner')}\n")

        # Generate PDF
        print("Generating PDF planner...")
        pdf_path = creator.generate_pdf(design_spec)
        print(f"✓ PDF generated: {pdf_path}\n")

        # Create preview images
        print("Creating preview images...")
        image_paths = creator.create_preview_images(design_spec, pdf_path)
        print(f"✓ Created {len(image_paths)} preview images\n")

        # Save complete package
        print("Saving planner package...")
        package_info = creator.save_planner(design_spec, pdf_path, image_paths)
        print(f"✓ Package saved: {package_info['package_directory']}\n")

        # Display summary
        print("=" * 60)
        print("PLANNER CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"Planner Name: {design_spec.get('planner_name', 'Planner')}")
        print(f"Type: {design_spec['metadata']['planner_type']}")
        print(f"Aesthetic: {design_spec['metadata']['aesthetic']}")
        print(f"PDF Path: {pdf_path}")
        print(f"Preview Images: {len(image_paths)}")
        print(f"Package Directory: {package_info['package_directory']}")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
