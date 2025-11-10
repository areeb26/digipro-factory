"""
Notion Template Creator Module - Generates Notion templates for digital products

This module uses Claude API to generate comprehensive Notion template structures,
converts them to Notion-compatible markdown, creates preview images, and packages
everything for distribution.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import yaml
from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/notion_creator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NotionTemplateCreator:
    """
    Create comprehensive Notion templates using AI

    This class generates complete Notion template structures including page hierarchy,
    databases, views, formulas, and documentation using Claude API.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize NotionTemplateCreator

        Args:
            config_path: Path to config.yaml file (defaults to ../config.yaml)
        """
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        self.config = self._load_config(config_path)

        # Initialize Claude API
        self.anthropic_client = self._initialize_anthropic()

        # Output directories
        self.output_base = Path("output/notion_templates")
        self.output_base.mkdir(parents=True, exist_ok=True)

        logger.info("NotionTemplateCreator initialized successfully")

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

    def create_notion_template(self, product_type: str, niche: str,
                               retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Generate complete Notion template structure using Claude API

        Args:
            product_type: Type of template (e.g., "productivity", "business", "finance")
            niche: Target niche (e.g., "freelancers", "students", "entrepreneurs")
            retry_attempts: Number of retry attempts for API calls

        Returns:
            Dictionary containing complete template structure with:
            - page_hierarchy: Nested page structure
            - databases: Database schemas with properties
            - views: Different views for each database
            - formulas: Notion formulas for calculations
            - relations: Database relationships
        """
        logger.info(f"Creating Notion template for type: {product_type}, niche: {niche}")

        # Get template configuration
        notion_config = self.config.get('product_types', {}).get('notion_templates', {})

        prompt = self._create_template_generation_prompt(product_type, niche, notion_config)

        for attempt in range(retry_attempts):
            try:
                logger.info(f"Calling Claude API (attempt {attempt + 1}/{retry_attempts})")

                # Call Claude API
                message = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.8,
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
                template_structure = self._parse_claude_response(response_text)

                # Enrich with metadata
                template_structure['metadata'] = {
                    'product_type': product_type,
                    'niche': niche,
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0'
                }

                logger.info(f"Successfully created Notion template structure")
                return template_structure

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
                logger.error(f"Unexpected error creating template: {e}")
                raise

    def _create_template_generation_prompt(self, product_type: str, niche: str,
                                          config: Dict) -> str:
        """Create a detailed prompt for Claude to generate Notion template"""

        categories = config.get('categories', [])
        page_range = config.get('page_count_range', [5, 20])

        prompt = f"""Create a comprehensive Notion template structure for a {product_type} template targeting {niche}.

REQUIREMENTS:
- Target Audience: {niche}
- Template Type: {product_type}
- Page Count: {page_range[0]}-{page_range[1]} pages
- Include databases with properties, views, and formulas
- Create practical, actionable content

TEMPLATE STRUCTURE TO GENERATE:
Please create a complete Notion template structure as JSON with:

1. Page Hierarchy:
   - Main pages with subpages
   - Clear organization and navigation
   - Descriptive page titles and icons

2. Databases:
   - At least 2-4 databases with relevant properties
   - Property types: text, number, select, multi-select, date, checkbox, formula, relation
   - Meaningful default data examples

3. Views:
   - Multiple views per database (table, board, calendar, list, gallery)
   - Filters and sorts for each view
   - Grouping where appropriate

4. Formulas:
   - Useful calculations and automations
   - Progress tracking
   - Date calculations
   - Conditional formatting logic

5. Relations:
   - Link databases together logically
   - Rollups to aggregate data

Return a JSON structure like this:
{{
  "template_name": "Clear, descriptive name",
  "description": "What this template helps users accomplish",
  "target_audience": "{niche}",
  "pages": [
    {{
      "name": "Page Name",
      "icon": "📊",
      "description": "Purpose of this page",
      "content": "Brief content description",
      "subpages": [...]
    }}
  ],
  "databases": [
    {{
      "name": "Database Name",
      "icon": "📋",
      "description": "What this database tracks",
      "properties": [
        {{
          "name": "Property Name",
          "type": "text|number|select|date|checkbox|formula|relation",
          "config": {{}},
          "description": "What this property is for"
        }}
      ],
      "views": [
        {{
          "name": "View Name",
          "type": "table|board|calendar|list|gallery",
          "filters": [],
          "sorts": [],
          "groups": []
        }}
      ],
      "sample_data": [
        {{"property1": "value1", "property2": "value2"}}
      ]
    }}
  ],
  "formulas": [
    {{
      "name": "Formula Name",
      "database": "Database Name",
      "property": "Property Name",
      "formula": "Notion formula syntax",
      "description": "What this calculates"
    }}
  ],
  "relations": [
    {{
      "from_database": "Database A",
      "to_database": "Database B",
      "relation_name": "Relation Name",
      "description": "How these connect"
    }}
  ],
  "instructions": {{
    "setup_steps": ["Step 1", "Step 2", ...],
    "usage_tips": ["Tip 1", "Tip 2", ...],
    "customization_ideas": ["Idea 1", "Idea 2", ...]
  }}
}}

Make it practical, professional, and immediately useful for {niche}. Include specific examples and actionable content."""

        return prompt

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response and extract JSON template structure"""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                return parsed
            else:
                logger.error("No JSON found in Claude response")
                raise ValueError("Could not find JSON in response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            raise

    def generate_notion_markdown(self, template_structure: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert JSON structure to Notion-compatible markdown

        Args:
            template_structure: Dictionary containing template structure

        Returns:
            Dictionary with markdown files:
            - template.md: Main template markdown
            - setup_guide.md: Setup instructions
            - user_guide.md: Usage guide
        """
        logger.info("Generating Notion-compatible markdown")

        markdown_files = {}

        # 1. Generate main template markdown
        template_md = self._generate_template_markdown(template_structure)
        markdown_files['template.md'] = template_md

        # 2. Generate setup instructions
        setup_md = self._generate_setup_guide(template_structure)
        markdown_files['setup_guide.md'] = setup_md

        # 3. Generate user guide
        user_md = self._generate_user_guide(template_structure)
        markdown_files['user_guide.md'] = user_md

        logger.info(f"Generated {len(markdown_files)} markdown files")
        return markdown_files

    def _generate_template_markdown(self, template: Dict[str, Any]) -> str:
        """Generate main template markdown file"""
        md = []

        # Header
        md.append(f"# {template.get('template_name', 'Notion Template')}\n")
        md.append(f"> {template.get('description', '')}\n")
        md.append(f"**Target Audience:** {template.get('target_audience', 'General')}\n")
        md.append("---\n")

        # Table of Contents
        md.append("## 📑 Table of Contents\n")
        for i, page in enumerate(template.get('pages', []), 1):
            md.append(f"{i}. [{page.get('icon', '📄')} {page.get('name', 'Page')}](#{self._slugify(page.get('name', ''))})")
        md.append("\n---\n")

        # Pages
        for page in template.get('pages', []):
            md.append(f"\n## {page.get('icon', '📄')} {page.get('name', 'Page')}\n")
            md.append(f"*{page.get('description', '')}*\n")
            md.append(f"\n{page.get('content', '')}\n")

            # Subpages
            if page.get('subpages'):
                md.append("\n### Subpages:\n")
                for subpage in page['subpages']:
                    md.append(f"- **{subpage.get('icon', '📄')} {subpage.get('name', '')}**: {subpage.get('description', '')}")

        # Databases section
        md.append("\n---\n")
        md.append("## 🗄️ Databases\n")

        for db in template.get('databases', []):
            md.append(f"\n### {db.get('icon', '📋')} {db.get('name', 'Database')}\n")
            md.append(f"*{db.get('description', '')}*\n")

            # Properties
            md.append("\n**Properties:**\n")
            md.append("| Property | Type | Description |")
            md.append("|----------|------|-------------|")
            for prop in db.get('properties', []):
                md.append(f"| {prop.get('name', '')} | {prop.get('type', '')} | {prop.get('description', '')} |")

            # Views
            md.append(f"\n**Views:** {', '.join([v.get('name', '') for v in db.get('views', [])])}\n")

        # Formulas section
        if template.get('formulas'):
            md.append("\n---\n")
            md.append("## 🧮 Formulas\n")
            for formula in template['formulas']:
                md.append(f"\n### {formula.get('name', '')}")
                md.append(f"*{formula.get('description', '')}*\n")
                md.append(f"```")
                md.append(formula.get('formula', ''))
                md.append(f"```\n")

        return "\n".join(md)

    def _generate_setup_guide(self, template: Dict[str, Any]) -> str:
        """Generate setup instructions markdown"""
        md = []

        md.append(f"# 🚀 Setup Guide: {template.get('template_name', 'Template')}\n")
        md.append("## Quick Start\n")
        md.append("Follow these steps to set up your new Notion template:\n")

        instructions = template.get('instructions', {})
        setup_steps = instructions.get('setup_steps', [])

        if setup_steps:
            for i, step in enumerate(setup_steps, 1):
                md.append(f"{i}. {step}")
        else:
            # Default setup steps
            md.append("1. Duplicate this template to your Notion workspace")
            md.append("2. Customize the databases and properties to fit your needs")
            md.append("3. Add your own data to the databases")
            md.append("4. Adjust views and filters as needed")
            md.append("5. Share with your team if needed")

        md.append("\n## Database Setup\n")
        for db in template.get('databases', []):
            md.append(f"\n### {db.get('icon', '📋')} {db.get('name', '')}")
            md.append(f"{db.get('description', '')}\n")
            md.append("**Initial data to add:**")
            for item in db.get('sample_data', [])[:3]:
                md.append(f"- {', '.join([f'{k}: {v}' for k, v in item.items()])}")

        md.append("\n## Tips for Success\n")
        tips = instructions.get('usage_tips', [])
        for tip in tips:
            md.append(f"- ✅ {tip}")

        return "\n".join(md)

    def _generate_user_guide(self, template: Dict[str, Any]) -> str:
        """Generate user guide markdown"""
        md = []

        md.append(f"# 📖 User Guide: {template.get('template_name', 'Template')}\n")
        md.append("## Overview\n")
        md.append(f"{template.get('description', '')}\n")

        md.append("\n## How to Use This Template\n")

        # Pages guide
        md.append("\n### 📄 Pages\n")
        for page in template.get('pages', []):
            md.append(f"\n**{page.get('icon', '📄')} {page.get('name', '')}**")
            md.append(f"{page.get('description', '')}\n")

        # Databases guide
        md.append("\n### 🗄️ Working with Databases\n")
        for db in template.get('databases', []):
            md.append(f"\n**{db.get('icon', '📋')} {db.get('name', '')}**")
            md.append(f"{db.get('description', '')}\n")

            md.append("Available views:")
            for view in db.get('views', []):
                md.append(f"- **{view.get('name', '')}**: {view.get('type', '')} view")

        # Formulas explanation
        if template.get('formulas'):
            md.append("\n### 🧮 Understanding Formulas\n")
            md.append("This template includes automated calculations:\n")
            for formula in template['formulas']:
                md.append(f"- **{formula.get('name', '')}**: {formula.get('description', '')}")

        # Customization ideas
        md.append("\n## 💡 Customization Ideas\n")
        instructions = template.get('instructions', {})
        ideas = instructions.get('customization_ideas', [])

        if ideas:
            for idea in ideas:
                md.append(f"- {idea}")
        else:
            md.append("- Add custom properties to track additional information")
            md.append("- Create new views to see your data differently")
            md.append("- Link databases together for more powerful workflows")
            md.append("- Add formulas to automate calculations")

        md.append("\n## 🎯 Best Practices\n")
        md.append("- Keep your data updated regularly")
        md.append("- Use consistent naming conventions")
        md.append("- Leverage filters and sorts in views")
        md.append("- Share relevant pages with team members")
        md.append("- Archive completed items rather than deleting them")

        return "\n".join(md)

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        return text.lower().replace(' ', '-').replace('&', 'and')

    def create_preview_images(self, template_structure: Dict[str, Any],
                             output_dir: Path) -> List[str]:
        """
        Create mockup images of the template using Pillow

        Args:
            template_structure: Template structure dictionary
            output_dir: Directory to save images

        Returns:
            List of paths to generated images
        """
        logger.info("Creating preview images")

        image_paths = []

        try:
            # Create images directory
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            # 1. Cover image
            cover_path = self._create_cover_image(template_structure, images_dir)
            image_paths.append(str(cover_path))

            # 2. Database preview images
            for i, db in enumerate(template_structure.get('databases', [])[:3], 1):
                db_path = self._create_database_preview(db, images_dir, i)
                image_paths.append(str(db_path))

            # 3. Feature highlights image
            features_path = self._create_features_image(template_structure, images_dir)
            image_paths.append(str(features_path))

            logger.info(f"Created {len(image_paths)} preview images")
            return image_paths

        except Exception as e:
            logger.error(f"Error creating preview images: {e}")
            raise

    def _create_cover_image(self, template: Dict[str, Any], output_dir: Path) -> Path:
        """Create main cover image"""
        # Create image
        width, height = 1200, 630
        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)

        # Try to load a nice font, fallback to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        # Background gradient effect (simple top color)
        for y in range(height // 3):
            alpha = int(255 * (1 - y / (height // 3)))
            draw.rectangle([(0, y), (width, y + 1)], fill=(240, 240, 255))

        # Draw template name
        template_name = template.get('template_name', 'Notion Template')
        # Center text
        bbox = draw.textbbox((0, 0), template_name, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, 200), template_name, fill='#1a1a1a', font=title_font)

        # Draw description
        description = template.get('description', '')[:80]
        bbox = draw.textbbox((0, 0), description, font=subtitle_font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, 300), description, fill='#666666', font=subtitle_font)

        # Draw stats
        pages_count = len(template.get('pages', []))
        db_count = len(template.get('databases', []))
        stats_text = f"📄 {pages_count} Pages  •  🗄️ {db_count} Databases"
        bbox = draw.textbbox((0, 0), stats_text, font=subtitle_font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        draw.text((text_x, 400), stats_text, fill='#888888', font=subtitle_font)

        # Save
        output_path = output_dir / "cover.png"
        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Created cover image: {output_path}")

        return output_path

    def _create_database_preview(self, database: Dict[str, Any],
                                output_dir: Path, index: int) -> Path:
        """Create database preview image"""
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Header background
        draw.rectangle([(0, 0), (width, 100)], fill='#f7f7f7')

        # Database name
        db_name = f"{database.get('icon', '📋')} {database.get('name', 'Database')}"
        draw.text((30, 30), db_name, fill='#1a1a1a', font=title_font)

        # Properties list
        y_offset = 130
        draw.text((30, y_offset), "Properties:", fill='#666666', font=text_font)
        y_offset += 40

        for prop in database.get('properties', [])[:8]:
            prop_text = f"• {prop.get('name', '')} ({prop.get('type', '')})"
            draw.text((50, y_offset), prop_text, fill='#333333', font=small_font)
            y_offset += 30

        # Views
        y_offset += 20
        views_text = f"Views: {', '.join([v.get('name', '') for v in database.get('views', [])[:3]])}"
        draw.text((30, y_offset), views_text, fill='#666666', font=small_font)

        # Save
        output_path = output_dir / f"database_{index}.png"
        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Created database preview: {output_path}")

        return output_path

    def _create_features_image(self, template: Dict[str, Any], output_dir: Path) -> Path:
        """Create features highlight image"""
        width, height = 1000, 800
        img = Image.new('RGB', (width, height), color='#FFFFFF')
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Title
        draw.text((50, 50), "✨ Key Features", fill='#1a1a1a', font=title_font)

        # Features list
        features = [
            f"📄 {len(template.get('pages', []))} Organized Pages",
            f"🗄️ {len(template.get('databases', []))} Powerful Databases",
            f"🧮 {len(template.get('formulas', []))} Automated Formulas",
            f"👥 Perfect for {template.get('target_audience', 'Everyone')}",
            "⚡ Easy to Customize",
            "📱 Mobile Friendly"
        ]

        y_offset = 150
        for feature in features:
            draw.text((80, y_offset), feature, fill='#333333', font=text_font)
            y_offset += 60

        # Save
        output_path = output_dir / "features.png"
        img.save(output_path, 'PNG', quality=95)
        logger.info(f"Created features image: {output_path}")

        return output_path

    def save_template(self, template_structure: Dict[str, Any],
                     markdown_files: Dict[str, str],
                     image_paths: List[str]) -> Dict[str, Any]:
        """
        Save all template files and create product package

        Args:
            template_structure: Template JSON structure
            markdown_files: Dictionary of markdown files
            image_paths: List of image file paths

        Returns:
            Dictionary with:
            - package_dir: Path to package directory
            - files: List of all created files
            - metadata: Package metadata
        """
        logger.info("Saving template package")

        try:
            # Create output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            template_name = template_structure.get('template_name', 'template').replace(' ', '_')
            package_dir = self.output_base / f"{template_name}_{timestamp}"
            package_dir.mkdir(parents=True, exist_ok=True)

            created_files = []

            # 1. Save JSON structure
            json_path = package_dir / "template_structure.json"
            with open(json_path, 'w') as f:
                json.dump(template_structure, f, indent=2)
            created_files.append(str(json_path))
            logger.info(f"Saved JSON structure: {json_path}")

            # 2. Save markdown files
            docs_dir = package_dir / "docs"
            docs_dir.mkdir(exist_ok=True)

            for filename, content in markdown_files.items():
                file_path = docs_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                created_files.append(str(file_path))
                logger.info(f"Saved markdown: {file_path}")

            # 3. Copy/link images
            images_dir = package_dir / "images"
            images_dir.mkdir(exist_ok=True)

            for image_path in image_paths:
                # Images are already in the right place
                created_files.append(image_path)

            # 4. Create README
            readme_path = package_dir / "README.md"
            readme_content = self._generate_package_readme(template_structure, created_files)
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            created_files.append(str(readme_path))

            # 5. Create metadata file
            metadata = {
                'template_name': template_structure.get('template_name'),
                'version': template_structure.get('metadata', {}).get('version', '1.0'),
                'created_at': timestamp,
                'product_type': template_structure.get('metadata', {}).get('product_type'),
                'niche': template_structure.get('metadata', {}).get('niche'),
                'files': {
                    'json': str(json_path),
                    'markdown': [str(docs_dir / f) for f in markdown_files.keys()],
                    'images': image_paths
                },
                'stats': {
                    'pages': len(template_structure.get('pages', [])),
                    'databases': len(template_structure.get('databases', [])),
                    'formulas': len(template_structure.get('formulas', [])),
                    'relations': len(template_structure.get('relations', []))
                }
            }

            metadata_path = package_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            created_files.append(str(metadata_path))

            logger.info(f"Template package saved to: {package_dir}")
            logger.info(f"Total files created: {len(created_files)}")

            return {
                'package_dir': str(package_dir),
                'files': created_files,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Error saving template package: {e}")
            raise

    def _generate_package_readme(self, template: Dict[str, Any],
                                files: List[str]) -> str:
        """Generate README for the template package"""
        md = []

        md.append(f"# {template.get('template_name', 'Notion Template')}\n")
        md.append(f"> {template.get('description', '')}\n")
        md.append("---\n")

        md.append("## 📦 Package Contents\n")
        md.append("This package contains everything you need to use this Notion template:\n")
        md.append("- `template_structure.json` - Complete template structure")
        md.append("- `docs/template.md` - Template overview and documentation")
        md.append("- `docs/setup_guide.md` - Step-by-step setup instructions")
        md.append("- `docs/user_guide.md` - How to use the template")
        md.append("- `images/` - Preview images and mockups")
        md.append("- `metadata.json` - Package metadata\n")

        md.append("## 🚀 Quick Start\n")
        md.append("1. Read the `setup_guide.md` for installation instructions")
        md.append("2. Import the template into your Notion workspace")
        md.append("3. Customize to fit your needs")
        md.append("4. Refer to `user_guide.md` for usage tips\n")

        md.append("## 📊 Template Stats\n")
        md.append(f"- **Pages**: {len(template.get('pages', []))}")
        md.append(f"- **Databases**: {len(template.get('databases', []))}")
        md.append(f"- **Formulas**: {len(template.get('formulas', []))}")
        md.append(f"- **Target Audience**: {template.get('target_audience', 'General')}\n")

        md.append("## 💡 Support\n")
        md.append("For questions or customization help, please refer to the user guide or contact support.\n")

        md.append("---\n")
        md.append(f"*Created on {datetime.now().strftime('%Y-%m-%d')}*")

        return "\n".join(md)


def main():
    """Example usage of NotionTemplateCreator"""

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Initialize creator
    creator = NotionTemplateCreator()

    print("\n" + "="*60)
    print("NOTION TEMPLATE CREATOR - DEMONSTRATION")
    print("="*60 + "\n")

    try:
        # 1. Create template structure
        print("1. Creating Notion template structure with Claude AI...")
        template = creator.create_notion_template(
            product_type="productivity",
            niche="freelancers"
        )
        print(f"   ✓ Created template: {template.get('template_name')}")
        print(f"   - Pages: {len(template.get('pages', []))}")
        print(f"   - Databases: {len(template.get('databases', []))}")
        print(f"   - Formulas: {len(template.get('formulas', []))}\n")

        # 2. Generate markdown
        print("2. Converting to Notion-compatible markdown...")
        markdown_files = creator.generate_notion_markdown(template)
        print(f"   ✓ Generated {len(markdown_files)} markdown files\n")

        # 3. Create preview images
        print("3. Creating preview images...")
        output_dir = Path("output/notion_templates/temp")
        output_dir.mkdir(parents=True, exist_ok=True)
        image_paths = creator.create_preview_images(template, output_dir)
        print(f"   ✓ Created {len(image_paths)} preview images\n")

        # 4. Save complete package
        print("4. Packaging template files...")
        package_info = creator.save_template(template, markdown_files, image_paths)
        print(f"   ✓ Package saved to: {package_info['package_dir']}")
        print(f"   ✓ Total files: {len(package_info['files'])}\n")

        print("="*60)
        print("TEMPLATE CREATION COMPLETE")
        print("="*60)
        print(f"\nYour Notion template package is ready at:")
        print(f"{package_info['package_dir']}\n")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\nError: {e}")
        print("Make sure you have set up your .env file with ANTHROPIC_API_KEY")


if __name__ == "__main__":
    main()
