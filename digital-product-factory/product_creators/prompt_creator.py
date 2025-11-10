"""
AI Prompt Creator Module

This module creates professional AI prompt packs for Midjourney and ChatGPT.
Generates high-quality, tested prompts with multi-provider AI support.

Features:
- Multi-provider AI support (Claude, Gemini, OpenAI) with automatic fallback
- Midjourney prompt generation (40-60 words, proper parameters)
- ChatGPT prompt collections with use cases and examples
- Professional PDF generation with table of contents
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
from datetime import datetime
from io import BytesIO

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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors

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


class AIPromptCreator:
    """
    Creates professional AI prompt packs with multi-provider support.

    This class generates high-quality prompts for Midjourney and ChatGPT,
    creates professional PDFs with table of contents, and packages everything
    for digital product sales.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the AIPromptCreator with multi-provider AI support.

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
        self.output_dir = Path("output/prompts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AIPromptCreator initialized with providers: {list(self.ai_providers.keys())}")
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

    def create_midjourney_prompts(self, category: str, count: int = 50,
                                  retry_attempts: int = 3) -> List[Dict[str, Any]]:
        """
        Generate high-quality Midjourney prompts using AI with automatic fallback.

        Args:
            category: Category/theme (e.g., "fantasy art", "product photography")
            count: Number of prompts to generate
            retry_attempts: Number of retry attempts per provider

        Returns:
            List of prompt dictionaries with text, parameters, and metadata
        """
        logger.info(f"Creating {count} Midjourney prompts for category: {category}")

        # Build provider order
        provider_order = self._get_provider_order()
        logger.info(f"Provider order: {provider_order}")

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            logger.info(f"Attempting to use {provider_name} provider...")

            try:
                prompts = self._generate_midjourney_with_provider(
                    provider_name, category, count, retry_attempts
                )

                logger.info(f"✓ Successfully created {len(prompts)} Midjourney prompts using {provider_name}")
                return prompts

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _generate_midjourney_with_provider(self, provider_name: str, category: str,
                                          count: int, retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate Midjourney prompts using a specific AI provider."""
        prompt = self._build_midjourney_generation_prompt(category, count)

        if provider_name == 'anthropic':
            return self._generate_midjourney_anthropic(prompt, category, retry_attempts)
        elif provider_name == 'gemini':
            return self._generate_midjourney_gemini(prompt, category, retry_attempts)
        elif provider_name == 'openai':
            return self._generate_midjourney_openai(prompt, category, retry_attempts)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def _build_midjourney_generation_prompt(self, category: str, count: int) -> str:
        """Build prompt for AI to generate Midjourney prompts."""
        return f"""Generate {count} high-quality Midjourney prompts for the category: {category}

Each prompt MUST follow these Midjourney best practices:

1. LENGTH: 40-60 words (critical for quality)
2. STRUCTURE: Subject + Style + Composition + Lighting + Parameters
3. DESCRIPTIVE: Use specific, vivid adjectives
4. PARAMETERS: Include appropriate parameters:
   - Aspect ratios: --ar 16:9, --ar 3:2, --ar 1:1, --ar 2:3, etc.
   - Version: --v 6 (latest version)
   - Stylize: --stylize 50-1000 (higher = more artistic)
   - Quality: --quality 2 (for highest quality)
   - Style: --style raw (for photorealistic)

5. AVOID: Generic descriptions, overused words, multiple subjects

EXAMPLE FORMAT:
{{
  "prompt_text": "Professional product photography of a luxury watch on black velvet, studio lighting with dramatic rim light, macro lens capturing intricate details of the mechanism, reflective surfaces, commercial advertising style, ultra-sharp focus",
  "parameters": "--ar 16:9 --v 6 --style raw --quality 2",
  "category": "{category}",
  "use_case": "Product photography, e-commerce, advertising",
  "style_focus": "Photorealistic, commercial",
  "word_count": 42
}}

Return your response as a JSON array of {count} prompts following this exact structure.
Make each prompt unique, creative, and production-ready for Midjourney V6.
"""

    def _generate_midjourney_anthropic(self, prompt: str, category: str,
                                       retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate Midjourney prompts using Anthropic Claude."""
        client = self.ai_providers['anthropic']

        for attempt in range(retry_attempts):
            try:
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.9,  # Higher for more creative prompts
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = message.content[0].text
                prompts = self._parse_prompt_array(response_text, category, 'midjourney')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'anthropic'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Anthropic retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_midjourney_gemini(self, prompt: str, category: str,
                                    retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate Midjourney prompts using Google Gemini."""
        model = self.ai_providers['gemini']

        for attempt in range(retry_attempts):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.9,
                        'max_output_tokens': 4000,
                    }
                )

                response_text = response.text
                prompts = self._parse_prompt_array(response_text, category, 'midjourney')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'gemini'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Gemini retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_midjourney_openai(self, prompt: str, category: str,
                                    retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate Midjourney prompts using OpenAI."""
        client = self.ai_providers['openai']

        for attempt in range(retry_attempts):
            try:
                response = client.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.9,
                    max_tokens=4000
                )

                response_text = response.choices[0].message.content
                prompts = self._parse_prompt_array(response_text, category, 'midjourney')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'openai'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"OpenAI retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def create_chatgpt_prompts(self, niche: str, count: int = 30,
                              retry_attempts: int = 3) -> List[Dict[str, Any]]:
        """
        Generate ChatGPT prompt collections for a specific niche.

        Args:
            niche: Target niche (e.g., "social media marketing", "coding")
            count: Number of prompts to generate
            retry_attempts: Number of retry attempts per provider

        Returns:
            List of prompt dictionaries with text, use_case, and example_output
        """
        logger.info(f"Creating {count} ChatGPT prompts for niche: {niche}")

        # Build provider order
        provider_order = self._get_provider_order()
        logger.info(f"Provider order: {provider_order}")

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            logger.info(f"Attempting to use {provider_name} provider...")

            try:
                prompts = self._generate_chatgpt_with_provider(
                    provider_name, niche, count, retry_attempts
                )

                logger.info(f"✓ Successfully created {len(prompts)} ChatGPT prompts using {provider_name}")
                return prompts

            except Exception as e:
                logger.warning(f"✗ {provider_name} provider failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _generate_chatgpt_with_provider(self, provider_name: str, niche: str,
                                       count: int, retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate ChatGPT prompts using a specific AI provider."""
        prompt = self._build_chatgpt_generation_prompt(niche, count)

        if provider_name == 'anthropic':
            return self._generate_chatgpt_anthropic(prompt, niche, retry_attempts)
        elif provider_name == 'gemini':
            return self._generate_chatgpt_gemini(prompt, niche, retry_attempts)
        elif provider_name == 'openai':
            return self._generate_chatgpt_openai(prompt, niche, retry_attempts)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def _build_chatgpt_generation_prompt(self, niche: str, count: int) -> str:
        """Build prompt for AI to generate ChatGPT prompts."""
        return f"""Generate {count} high-quality ChatGPT prompts for the niche: {niche}

Each prompt MUST follow these ChatGPT best practices:

1. CLARITY: Clear, specific instructions
2. CONTEXT: Include relevant background information
3. ROLE: Assign an expert role when appropriate
4. FORMAT: Specify desired output format
5. CONSTRAINTS: Include any limitations or requirements
6. EXAMPLES: Provide example inputs/outputs when helpful

STRUCTURE:
- Title: Clear, descriptive title
- Prompt text: The actual prompt to use
- Use case: When to use this prompt
- Example output: What to expect as result
- Tips: Best practices for using this prompt

EXAMPLE FORMAT:
{{
  "title": "Social Media Caption Generator",
  "prompt_text": "Act as a social media marketing expert. Create 5 engaging Instagram captions for [PRODUCT/SERVICE]. Each caption should: 1) Include relevant emojis, 2) Be under 150 characters, 3) Include a call-to-action, 4) Use trending hashtags. Target audience: [AUDIENCE]. Tone: [TONE].",
  "use_case": "Creating social media content quickly for businesses and influencers",
  "example_output": "Example caption with emojis and hashtags...",
  "tips": ["Fill in brackets with specific details", "Adjust tone based on brand voice", "Test multiple versions"],
  "category": "{niche}",
  "difficulty": "Beginner",
  "variables": ["PRODUCT/SERVICE", "AUDIENCE", "TONE"]
}}

Return your response as a JSON array of {count} prompts following this exact structure.
Make each prompt practical, tested, and immediately useful for {niche} professionals.
"""

    def _generate_chatgpt_anthropic(self, prompt: str, niche: str,
                                   retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate ChatGPT prompts using Anthropic Claude."""
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
                prompts = self._parse_prompt_array(response_text, niche, 'chatgpt')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'anthropic'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except (APIError, RateLimitError, APITimeoutError) as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Anthropic retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_chatgpt_gemini(self, prompt: str, niche: str,
                                retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate ChatGPT prompts using Google Gemini."""
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
                prompts = self._parse_prompt_array(response_text, niche, 'chatgpt')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'gemini'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Gemini retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _generate_chatgpt_openai(self, prompt: str, niche: str,
                                retry_attempts: int) -> List[Dict[str, Any]]:
        """Generate ChatGPT prompts using OpenAI."""
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
                prompts = self._parse_prompt_array(response_text, niche, 'chatgpt')

                # Add metadata
                for p in prompts:
                    p['generated_by'] = 'openai'
                    p['generated_at'] = datetime.now().isoformat()

                return prompts

            except Exception as e:
                if attempt < retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"OpenAI retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

    def _parse_prompt_array(self, response_text: str, category: str,
                           prompt_type: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured prompt array."""
        try:
            # Find JSON array in response
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")

            json_str = response_text[start_idx:end_idx]
            prompts = json.loads(json_str)

            # Validate and enhance prompts
            validated_prompts = []
            for i, prompt in enumerate(prompts, 1):
                prompt['id'] = i
                prompt['prompt_type'] = prompt_type

                # Validate required fields based on type
                if prompt_type == 'midjourney':
                    if 'prompt_text' not in prompt or 'parameters' not in prompt:
                        logger.warning(f"Skipping invalid Midjourney prompt #{i}")
                        continue
                elif prompt_type == 'chatgpt':
                    if 'prompt_text' not in prompt or 'use_case' not in prompt:
                        logger.warning(f"Skipping invalid ChatGPT prompt #{i}")
                        continue

                validated_prompts.append(prompt)

            logger.info(f"Validated {len(validated_prompts)} prompts")
            return validated_prompts

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise

    def create_prompt_pdf(self, prompts: List[Dict[str, Any]],
                         title: str, prompt_type: str,
                         output_path: Optional[Path] = None) -> Path:
        """
        Create professional PDF with prompts, table of contents, and usage guide.

        Args:
            prompts: List of prompt dictionaries
            title: PDF title
            prompt_type: 'midjourney' or 'chatgpt'
            output_path: Optional custom output path

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Creating PDF for {len(prompts)} {prompt_type} prompts")

        # Set up output path
        if output_path is None:
            safe_title = title.replace(' ', '_').lower()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"{safe_title}_{timestamp}.pdf"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Container for PDF elements
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )

        prompt_title_style = ParagraphStyle(
            'PromptTitle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=HexColor('#2980B9'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )

        # Cover page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"{len(prompts)} Professional {prompt_type.title()} Prompts", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(PageBreak())

        # Table of Contents
        story.append(Paragraph("Table of Contents", heading_style))
        story.append(Spacer(1, 0.2*inch))

        toc_data = [["#", "Title", "Page"]]
        for i, prompt in enumerate(prompts, 1):
            prompt_title = prompt.get('title', f"Prompt #{i}")
            page_num = i + 2  # Rough estimate
            toc_data.append([str(i), prompt_title[:50], str(page_num)])

        toc_table = Table(toc_data, colWidths=[0.5*inch, 5*inch, 0.75*inch])
        toc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(toc_table)
        story.append(PageBreak())

        # Usage Guide
        story.append(Paragraph("How to Use These Prompts", heading_style))
        story.append(Spacer(1, 0.2*inch))

        if prompt_type == 'midjourney':
            usage_text = """
            <b>Using Midjourney Prompts:</b><br/>
            1. Copy the prompt text<br/>
            2. Open Midjourney Discord or web interface<br/>
            3. Type /imagine followed by the prompt<br/>
            4. Add the parameters exactly as shown<br/>
            5. Press Enter and wait for results<br/>
            <br/>
            <b>Tips:</b><br/>
            • Experiment with different parameters<br/>
            • Try variations of successful prompts<br/>
            • Use --seed for consistent results<br/>
            • Adjust --stylize for more/less artistic output<br/>
            """
        else:  # chatgpt
            usage_text = """
            <b>Using ChatGPT Prompts:</b><br/>
            1. Copy the prompt text<br/>
            2. Replace [VARIABLES] with your specific information<br/>
            3. Paste into ChatGPT<br/>
            4. Review and refine the output<br/>
            5. Save successful prompts for reuse<br/>
            <br/>
            <b>Tips:</b><br/>
            • Be specific with variables<br/>
            • Add context when needed<br/>
            • Iterate on responses<br/>
            • Combine prompts for complex tasks<br/>
            """

        story.append(Paragraph(usage_text, body_style))
        story.append(PageBreak())

        # Individual prompts
        for i, prompt in enumerate(prompts, 1):
            # Prompt header
            prompt_title = prompt.get('title', f"Prompt #{i}")
            story.append(Paragraph(f"{i}. {prompt_title}", prompt_title_style))

            if prompt_type == 'midjourney':
                # Midjourney prompt format
                prompt_text = prompt.get('prompt_text', '')
                parameters = prompt.get('parameters', '')
                use_case = prompt.get('use_case', 'N/A')
                style_focus = prompt.get('style_focus', 'N/A')

                story.append(Paragraph(f"<b>Prompt:</b>", body_style))
                story.append(Paragraph(prompt_text, body_style))
                story.append(Paragraph(f"<b>Parameters:</b> {parameters}", body_style))
                story.append(Paragraph(f"<b>Use Case:</b> {use_case}", body_style))
                story.append(Paragraph(f"<b>Style:</b> {style_focus}", body_style))

            else:  # chatgpt
                # ChatGPT prompt format
                prompt_text = prompt.get('prompt_text', '')
                use_case = prompt.get('use_case', 'N/A')
                example = prompt.get('example_output', 'N/A')
                tips = prompt.get('tips', [])
                difficulty = prompt.get('difficulty', 'N/A')

                story.append(Paragraph(f"<b>Difficulty:</b> {difficulty}", body_style))
                story.append(Paragraph(f"<b>Use Case:</b> {use_case}", body_style))
                story.append(Paragraph(f"<b>Prompt:</b>", body_style))
                story.append(Paragraph(prompt_text, body_style))

                if example != 'N/A':
                    story.append(Paragraph(f"<b>Example Output:</b>", body_style))
                    story.append(Paragraph(example, body_style))

                if tips:
                    story.append(Paragraph(f"<b>Tips:</b>", body_style))
                    for tip in tips:
                        story.append(Paragraph(f"• {tip}", body_style))

            story.append(Spacer(1, 0.3*inch))

            # Page break every 2 prompts for readability
            if i % 2 == 0 and i < len(prompts):
                story.append(PageBreak())

        # Build PDF
        doc.build(story)

        logger.info(f"PDF created successfully: {output_path}")
        return output_path

    def create_preview_images(self, prompts: List[Dict[str, Any]],
                            title: str, prompt_type: str,
                            output_dir: Path) -> List[Path]:
        """
        Create preview images for product listings.

        Args:
            prompts: List of prompt dictionaries
            title: Product title
            prompt_type: 'midjourney' or 'chatgpt'
            output_dir: Directory to save images

        Returns:
            List of paths to preview images
        """
        logger.info("Creating preview images")

        images_dir = output_dir / 'images'
        images_dir.mkdir(exist_ok=True)

        preview_images = []

        # Color scheme
        primary_color = '#2C3E50'
        accent_color = '#3498DB'
        bg_color = '#ECF0F1'

        # 1. Cover image (1200x1600)
        cover_path = images_dir / 'cover.png'
        self._create_cover_image(title, len(prompts), prompt_type, cover_path,
                                primary_color, accent_color)
        preview_images.append(cover_path)

        # 2. Sample prompts preview (1600x1200)
        samples_path = images_dir / 'samples.png'
        self._create_samples_image(prompts[:3], prompt_type, samples_path,
                                   primary_color, accent_color)
        preview_images.append(samples_path)

        # 3. Features overview (1200x1200)
        features_path = images_dir / 'features.png'
        self._create_features_image(title, len(prompts), prompt_type, features_path,
                                   primary_color, accent_color)
        preview_images.append(features_path)

        logger.info(f"Created {len(preview_images)} preview images")
        return preview_images

    def _create_cover_image(self, title: str, count: int, prompt_type: str,
                           output_path: Path, primary_color: str, accent_color: str):
        """Create cover image for product listing."""
        img = Image.new('RGB', (1200, 1600), color=primary_color)
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            count_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            count_font = ImageFont.load_default()

        # Title
        lines = self._wrap_text(title, title_font, 1100)
        y_offset = 300
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            width = bbox[2] - bbox[0]
            draw.text((600 - width/2, y_offset), line, fill='white', font=title_font)
            y_offset += 80

        # Count
        count_text = str(count)
        bbox = draw.textbbox((0, 0), count_text, font=count_font)
        count_width = bbox[2] - bbox[0]
        draw.text((600 - count_width/2, 650), count_text, fill=accent_color, font=count_font)

        # Subtitle
        subtitle = f"Professional {prompt_type.title()} Prompts"
        bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = bbox[2] - bbox[0]
        draw.text((600 - subtitle_width/2, 780), subtitle, fill='white', font=subtitle_font)

        # Decorative line
        draw.rectangle([300, 900, 900, 920], fill=accent_color)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Cover image saved: {output_path}")

    def _create_samples_image(self, prompts: List[Dict[str, Any]], prompt_type: str,
                             output_path: Path, primary_color: str, accent_color: str):
        """Create samples preview image."""
        img = Image.new('RGB', (1600, 1200), color='white')
        draw = ImageDraw.Draw(img)

        try:
            header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        # Header
        draw.text((50, 50), "Sample Prompts", fill=primary_color, font=header_font)

        # Draw sample prompts
        y_offset = 150
        for i, prompt in enumerate(prompts[:3], 1):
            # Prompt number and title
            title = prompt.get('title', f"Prompt #{i}")
            draw.text((50, y_offset), f"{i}. {title[:60]}", fill=primary_color, font=body_font)

            # Prompt preview (truncated)
            prompt_text = prompt.get('prompt_text', '')[:150] + "..."
            lines = self._wrap_text(prompt_text, body_font, 1500)

            y_offset += 40
            for line in lines[:3]:  # Max 3 lines
                draw.text((70, y_offset), line, fill='gray', font=body_font)
                y_offset += 30

            # Separator
            draw.rectangle([50, y_offset + 20, 1550, y_offset + 23], fill=accent_color)
            y_offset += 80

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Samples image saved: {output_path}")

    def _create_features_image(self, title: str, count: int, prompt_type: str,
                              output_path: Path, primary_color: str, accent_color: str):
        """Create features overview image."""
        img = Image.new('RGB', (1200, 1200), color='white')
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            feature_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            feature_font = ImageFont.load_default()

        # Title
        draw.text((100, 80), "What's Included", fill=primary_color, font=title_font)

        # Features
        features = [
            f"{count} Professional Prompts",
            "Tested & Production-Ready",
            "Organized by Category",
            "Copy-Paste Ready Format",
            "Usage Tips & Examples",
            "PDF + JSON Formats",
            "Lifetime Updates"
        ]

        y_offset = 200
        for feature in features:
            # Bullet point
            draw.ellipse([100, y_offset + 5, 120, y_offset + 25], fill=accent_color)
            # Feature text
            draw.text((150, y_offset), feature, fill=primary_color, font=feature_font)
            y_offset += 100

        # Border
        draw.rectangle([50, 50, 1150, 1150], outline=accent_color, width=5)

        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Features image saved: {output_path}")

    def _wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line = ' '.join(current_line)

            # Use a temporary draw to measure
            temp_img = Image.new('RGB', (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]

            if width > max_width:
                if len(current_line) == 1:
                    lines.append(current_line.pop())
                else:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def save_prompt_pack(self, prompts: List[Dict[str, Any]],
                        title: str, prompt_type: str,
                        pdf_path: Path, image_paths: List[Path]) -> Dict[str, Any]:
        """
        Save complete prompt pack with all files and metadata.

        Args:
            prompts: List of prompt dictionaries
            title: Pack title
            prompt_type: 'midjourney' or 'chatgpt'
            pdf_path: Path to generated PDF
            image_paths: List of preview image paths

        Returns:
            Dictionary with package information and file paths
        """
        logger.info("Saving prompt pack")

        # Create package directory
        package_dir = pdf_path.parent

        # Save prompts as JSON
        json_path = package_dir / f"{pdf_path.stem}.json"
        with open(json_path, 'w') as f:
            json.dump(prompts, f, indent=2)

        # Create README
        readme_path = package_dir / 'README.md'
        readme_content = self._generate_readme(prompts, title, prompt_type, pdf_path)
        with open(readme_path, 'w') as f:
            f.write(readme_content)

        # Create metadata
        metadata = {
            'title': title,
            'prompt_type': prompt_type,
            'prompt_count': len(prompts),
            'created_at': datetime.now().isoformat(),
            'files': {
                'pdf': str(pdf_path.name),
                'json': str(json_path.name),
                'readme': str(readme_path.name),
                'preview_images': [str(p.name) for p in image_paths]
            },
            'categories': list(set(p.get('category', 'General') for p in prompts)),
            'generated_by': prompts[0].get('generated_by', 'unknown') if prompts else 'unknown'
        }

        metadata_path = package_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Create package info
        package_info = {
            'package_directory': str(package_dir),
            'pdf_path': str(pdf_path),
            'json_path': str(json_path),
            'preview_images': [str(p) for p in image_paths],
            'readme_path': str(readme_path),
            'metadata_path': str(metadata_path),
            'metadata': metadata
        }

        logger.info(f"Prompt pack saved: {package_dir}")
        return package_info

    def _generate_readme(self, prompts: List[Dict[str, Any]],
                        title: str, prompt_type: str, pdf_path: Path) -> str:
        """Generate README content for prompt pack."""
        return f"""# {title}

## Overview

This pack contains {len(prompts)} professional {prompt_type.title()} prompts, carefully crafted and tested for optimal results.

## What's Included

- **{len(prompts)} Prompts**: Production-ready, tested prompts
- **PDF Guide**: Professional format with table of contents
- **JSON Data**: Machine-readable format for automation
- **Preview Images**: Marketing materials for showcasing
- **Usage Guide**: Tips and best practices

## File Structure

- `{pdf_path.name}` - Professional PDF with all prompts
- `{pdf_path.stem}.json` - JSON format for developers
- `images/` - Preview images for marketing
- `README.md` - This file
- `metadata.json` - Pack metadata

## How to Use

### {prompt_type.title()} Prompts

"""

        if prompt_type == 'midjourney':
            readme = readme + """
1. Open Midjourney (Discord or web interface)
2. Type `/imagine` followed by the prompt text
3. Add the parameters exactly as shown (--ar, --v, etc.)
4. Press Enter and wait for results

**Tips:**
- Experiment with different aspect ratios (--ar)
- Adjust stylize value for more/less artistic output
- Use --seed for reproducible results
- Try variations with /remix mode

"""
        else:  # chatgpt
            readme = readme + """
1. Open ChatGPT (web, app, or API)
2. Copy the prompt text
3. Replace [VARIABLES] with your specific information
4. Paste into ChatGPT and submit
5. Refine based on the output

**Tips:**
- Be specific when filling in variables
- Add context when needed
- Iterate on responses for better results
- Save successful variations

"""

        readme += f"""
## Categories

"""

        # Add categories
        categories = set(p.get('category', 'General') for p in prompts)
        for category in sorted(categories):
            count = sum(1 for p in prompts if p.get('category') == category)
            readme += f"- **{category}**: {count} prompts\n"

        readme += f"""
## License

This prompt pack is for personal and commercial use. You may:
- Use prompts to generate content for personal projects
- Use prompts to generate content for client work
- Modify prompts to suit your needs

You may NOT:
- Resell or redistribute the prompt pack
- Claim authorship of the prompts
- Use for training AI models

## Support

For questions, updates, or support, contact the Digital Product Factory team.

## Created

Generated on {datetime.now().strftime('%B %d, %Y')} using Digital Product Factory AI.

---

Happy Prompting! 🚀✨
"""

        return readme

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
    print("Digital Product Factory - AI Prompt Creator")
    print("=" * 60)
    print()

    try:
        # Initialize creator
        print("Initializing AIPromptCreator...")
        creator = AIPromptCreator()
        print("✓ AIPromptCreator initialized\n")

        # Example 1: Create Midjourney prompts
        print("Creating Midjourney prompts...")
        mj_prompts = creator.create_midjourney_prompts(
            category="product photography",
            count=10
        )
        print(f"✓ Created {len(mj_prompts)} Midjourney prompts\n")

        # Create PDF
        print("Generating PDF...")
        pdf_path = creator.create_prompt_pdf(
            prompts=mj_prompts,
            title="Product Photography Prompts",
            prompt_type="midjourney"
        )
        print(f"✓ PDF generated: {pdf_path}\n")

        # Create preview images
        print("Creating preview images...")
        image_paths = creator.create_preview_images(
            prompts=mj_prompts,
            title="Product Photography Prompts",
            prompt_type="midjourney",
            output_dir=pdf_path.parent
        )
        print(f"✓ Created {len(image_paths)} preview images\n")

        # Save complete package
        print("Saving prompt pack...")
        package_info = creator.save_prompt_pack(
            prompts=mj_prompts,
            title="Product Photography Prompts",
            prompt_type="midjourney",
            pdf_path=pdf_path,
            image_paths=image_paths
        )
        print(f"✓ Package saved: {package_info['package_directory']}\n")

        # Example 2: Create ChatGPT prompts
        print("Creating ChatGPT prompts...")
        gpt_prompts = creator.create_chatgpt_prompts(
            niche="social media marketing",
            count=10
        )
        print(f"✓ Created {len(gpt_prompts)} ChatGPT prompts\n")

        # Display summary
        print("=" * 60)
        print("PROMPT PACKS CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"Midjourney Prompts: {len(mj_prompts)}")
        print(f"ChatGPT Prompts: {len(gpt_prompts)}")
        print(f"Package Directory: {package_info['package_directory']}")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
