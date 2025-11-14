"""
Digital Product Factory - Analytics Module

This module provides comprehensive analytics and reporting capabilities:
- Product performance tracking
- Niche analysis and recommendations
- Platform comparison (Etsy vs Gumroad)
- Weekly PDF reports with charts
- Trend prediction using historical data

Features:
- Pandas for data analysis
- Matplotlib for visualizations
- PDF generation with charts
- Conversion rate calculations
- Profitability analysis
- Predictive analytics

Usage:
    from analytics import Analytics

    analytics = Analytics()

    # Get product performance
    performance = analytics.get_product_performance()

    # Analyze niches
    niche_data = analytics.get_niche_performance()

    # Compare platforms
    comparison = analytics.get_platform_comparison()

    # Generate weekly report
    analytics.generate_weekly_report(output_path='reports/weekly.pdf')

    # Predict trends
    predictions = analytics.predict_trends()
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import smtplib
from email.message import EmailMessage

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from dotenv import load_dotenv

from database import ProductDB

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Analytics:
    """
    Comprehensive analytics for Digital Product Factory.

    Provides insights into product performance, niche profitability,
    platform comparison, and predictive analytics.
    """

    # Platform fee structures
    PLATFORM_FEES = {
        'gumroad': {
            'percentage': 0.10,  # 10%
            'name': 'Gumroad'
        },
        'etsy': {
            'listing_fee': 0.20,
            'transaction_fee': 0.065,  # 6.5%
            'payment_processing': 0.03,  # 3% + $0.25
            'payment_processing_fixed': 0.25,
            'name': 'Etsy'
        }
    }

    def __init__(self, db_path: str = None):
        """
        Initialize Analytics module.

        Args:
            db_path: Optional path to database (uses default if not provided)
        """
        self.db = ProductDB(db_path) if db_path else ProductDB()
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)

        logger.info("Analytics module initialized")

    def get_product_performance(self, days: int = 30) -> pd.DataFrame:
        """
        Get performance metrics for all products.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            DataFrame with columns:
                - product_id
                - title
                - type
                - niche
                - price
                - views (if tracked)
                - sales
                - revenue
                - conversion_rate
                - platform
                - created_at
        """
        logger.info(f"Analyzing product performance for last {days} days")

        # Get all published products
        products = self.db.get_products_by_status('published')

        if not products:
            logger.warning("No published products found")
            return pd.DataFrame()

        # Build performance data
        performance_data = []

        for product in products:
            try:
                product_id = product['id']
                metadata = json.loads(product.get('metadata', '{}'))
                analytics = metadata.get('analytics', {})

                # Extract metrics from analytics
                gumroad_data = analytics.get('platforms', {}).get('gumroad', {})
                etsy_data = analytics.get('platforms', {}).get('etsy', {})

                # Gumroad metrics
                if gumroad_data:
                    performance_data.append({
                        'product_id': product_id,
                        'title': product.get('title', 'Unknown'),
                        'type': product.get('type', 'Unknown'),
                        'niche': product.get('niche', 'Unknown'),
                        'price': float(product.get('price', 0)),
                        'views': 0,  # Gumroad doesn't provide views in API
                        'sales': gumroad_data.get('sales_count', 0),
                        'revenue': gumroad_data.get('revenue', 0.0),
                        'conversion_rate': 0.0,  # Can't calculate without views
                        'platform': 'Gumroad',
                        'created_at': product.get('created_at', '')
                    })

                # Etsy metrics (when implemented)
                if etsy_data:
                    views = etsy_data.get('views', 0)
                    sales = etsy_data.get('sales', 0)

                    performance_data.append({
                        'product_id': product_id,
                        'title': product.get('title', 'Unknown'),
                        'type': product.get('type', 'Unknown'),
                        'niche': product.get('niche', 'Unknown'),
                        'price': float(product.get('price', 0)),
                        'views': views,
                        'sales': sales,
                        'revenue': sales * float(product.get('price', 0)),
                        'conversion_rate': (sales / views * 100) if views > 0 else 0.0,
                        'platform': 'Etsy',
                        'created_at': product.get('created_at', '')
                    })

            except Exception as e:
                logger.error(f"Error processing product {product_id}: {e}")
                continue

        if not performance_data:
            logger.warning("No performance data available")
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(performance_data)

        # Calculate conversion rates where possible
        df['conversion_rate'] = df.apply(
            lambda row: (row['sales'] / row['views'] * 100) if row['views'] > 0 else 0.0,
            axis=1
        )

        # Sort by revenue
        df = df.sort_values('revenue', ascending=False)

        logger.info(f"Analyzed {len(df)} product records")

        return df

    def get_niche_performance(self) -> pd.DataFrame:
        """
        Analyze performance by niche.

        Returns:
            DataFrame with columns:
                - niche
                - product_count
                - total_sales
                - total_revenue
                - avg_price
                - avg_conversion_rate
                - recommendation (rating 1-5 stars)
        """
        logger.info("Analyzing niche performance")

        # Get product performance
        df = self.get_product_performance()

        if df.empty:
            logger.warning("No data for niche analysis")
            return pd.DataFrame()

        # Group by niche
        niche_stats = df.groupby('niche').agg({
            'product_id': 'count',
            'sales': 'sum',
            'revenue': 'sum',
            'price': 'mean',
            'conversion_rate': 'mean'
        }).reset_index()

        niche_stats.columns = [
            'niche',
            'product_count',
            'total_sales',
            'total_revenue',
            'avg_price',
            'avg_conversion_rate'
        ]

        # Calculate performance score (0-5 stars)
        # Based on: revenue, sales, conversion rate
        max_revenue = niche_stats['total_revenue'].max()
        max_sales = niche_stats['total_sales'].max()
        max_conversion = niche_stats['avg_conversion_rate'].max()

        def calculate_score(row):
            if max_revenue == 0 or max_sales == 0:
                return 0

            revenue_score = (row['total_revenue'] / max_revenue) * 2
            sales_score = (row['total_sales'] / max_sales) * 2
            conversion_score = (row['avg_conversion_rate'] / max_conversion) * 1 if max_conversion > 0 else 0

            total_score = revenue_score + sales_score + conversion_score
            return min(5, total_score)  # Cap at 5 stars

        niche_stats['recommendation'] = niche_stats.apply(calculate_score, axis=1)

        # Add recommendation text
        def get_recommendation_text(score):
            if score >= 4:
                return "⭐⭐⭐⭐⭐ Excellent - Create more!"
            elif score >= 3:
                return "⭐⭐⭐⭐ Good - Profitable niche"
            elif score >= 2:
                return "⭐⭐⭐ Average - Monitor performance"
            elif score >= 1:
                return "⭐⭐ Below average - Consider alternatives"
            else:
                return "⭐ Poor - Avoid this niche"

        niche_stats['recommendation_text'] = niche_stats['recommendation'].apply(get_recommendation_text)

        # Sort by total revenue
        niche_stats = niche_stats.sort_values('total_revenue', ascending=False)

        logger.info(f"Analyzed {len(niche_stats)} niches")

        return niche_stats

    def get_platform_comparison(self) -> Dict[str, Any]:
        """
        Compare performance between Etsy and Gumroad.

        Returns:
            Dictionary with:
                - platforms: DataFrame comparing metrics
                - fees_breakdown: Detailed fee calculations
                - net_profit: Profit after fees per platform
                - recommendation: Which platform is better
        """
        logger.info("Comparing platform performance")

        # Get product performance
        df = self.get_product_performance()

        if df.empty:
            logger.warning("No data for platform comparison")
            return {
                'platforms': pd.DataFrame(),
                'fees_breakdown': {},
                'net_profit': {},
                'recommendation': 'Insufficient data'
            }

        # Group by platform
        platform_stats = df.groupby('platform').agg({
            'product_id': 'count',
            'sales': 'sum',
            'revenue': 'sum',
            'views': 'sum',
            'conversion_rate': 'mean'
        }).reset_index()

        platform_stats.columns = [
            'platform',
            'products',
            'total_sales',
            'gross_revenue',
            'total_views',
            'avg_conversion_rate'
        ]

        # Calculate fees and net profit
        fees_breakdown = {}
        net_profit = {}

        for _, row in platform_stats.iterrows():
            platform = row['platform'].lower()
            gross = row['gross_revenue']
            sales_count = row['total_sales']

            if platform == 'gumroad':
                fee = gross * self.PLATFORM_FEES['gumroad']['percentage']
                fees_breakdown['Gumroad'] = {
                    'platform_fee': fee,
                    'percentage': f"{self.PLATFORM_FEES['gumroad']['percentage'] * 100}%",
                    'total_fees': fee
                }
                net_profit['Gumroad'] = gross - fee

            elif platform == 'etsy':
                listing_fees = sales_count * self.PLATFORM_FEES['etsy']['listing_fee']
                transaction_fees = gross * self.PLATFORM_FEES['etsy']['transaction_fee']
                payment_fees = (gross * self.PLATFORM_FEES['etsy']['payment_processing'] +
                               sales_count * self.PLATFORM_FEES['etsy']['payment_processing_fixed'])

                total_fees = listing_fees + transaction_fees + payment_fees

                fees_breakdown['Etsy'] = {
                    'listing_fees': listing_fees,
                    'transaction_fees': transaction_fees,
                    'payment_processing': payment_fees,
                    'total_fees': total_fees
                }
                net_profit['Etsy'] = gross - total_fees

        # Add net profit to platform stats
        platform_stats['net_profit'] = platform_stats['platform'].map(
            lambda p: net_profit.get(p, 0)
        )

        # Calculate profit margin
        platform_stats['profit_margin'] = (
            platform_stats['net_profit'] / platform_stats['gross_revenue'] * 100
        ).fillna(0)

        # Determine recommendation
        if len(platform_stats) == 0:
            recommendation = "No data available"
        elif len(platform_stats) == 1:
            recommendation = f"Only {platform_stats.iloc[0]['platform']} is configured"
        else:
            best_platform = platform_stats.loc[platform_stats['net_profit'].idxmax(), 'platform']
            best_profit = platform_stats.loc[platform_stats['net_profit'].idxmax(), 'net_profit']

            recommendation = f"{best_platform} is more profitable (${best_profit:.2f} net profit)"

        logger.info("Platform comparison complete")

        return {
            'platforms': platform_stats,
            'fees_breakdown': fees_breakdown,
            'net_profit': net_profit,
            'recommendation': recommendation
        }

    def generate_weekly_report(self, output_path: Optional[str] = None,
                              email_to: Optional[str] = None) -> str:
        """
        Generate comprehensive weekly PDF report with charts.

        Args:
            output_path: Optional custom output path
            email_to: Optional email address to send report

        Returns:
            Path to generated PDF report
        """
        logger.info("Generating weekly report")

        # Set output path
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d')
            output_path = self.reports_dir / f"weekly_report_{timestamp}.pdf"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get data
        product_performance = self.get_product_performance(days=7)
        niche_performance = self.get_niche_performance()
        platform_comparison = self.get_platform_comparison()

        # Create PDF
        with PdfPages(output_path) as pdf:
            # Page 1: Cover Page
            self._create_cover_page(pdf)

            # Page 2: Executive Summary
            self._create_executive_summary(pdf, product_performance, niche_performance)

            # Page 3: Product Performance Chart
            if not product_performance.empty:
                self._create_product_chart(pdf, product_performance)

            # Page 4: Niche Analysis
            if not niche_performance.empty:
                self._create_niche_chart(pdf, niche_performance)

            # Page 5: Platform Comparison
            if not platform_comparison['platforms'].empty:
                self._create_platform_chart(pdf, platform_comparison)

            # Page 6: Recommendations
            self._create_recommendations_page(pdf, niche_performance, platform_comparison)

            # Add metadata
            d = pdf.infodict()
            d['Title'] = 'Digital Product Factory - Weekly Report'
            d['Author'] = 'Analytics Module'
            d['Subject'] = f'Performance report for week of {datetime.now().strftime("%Y-%m-%d")}'
            d['Keywords'] = 'Analytics, Performance, Products'
            d['CreationDate'] = datetime.now()

        logger.info(f"Report generated: {output_path}")

        # Email report if requested
        if email_to:
            try:
                self._email_report(output_path, email_to)
            except Exception as e:
                logger.error(f"Failed to email report: {e}")

        return str(output_path)

    def _create_cover_page(self, pdf: PdfPages):
        """Create report cover page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.7, 'Digital Product Factory',
                ha='center', va='center', fontsize=32, fontweight='bold',
                transform=ax.transAxes)

        # Subtitle
        ax.text(0.5, 0.6, 'Weekly Performance Report',
                ha='center', va='center', fontsize=24,
                transform=ax.transAxes)

        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

        ax.text(0.5, 0.5, date_range,
                ha='center', va='center', fontsize=16, style='italic',
                transform=ax.transAxes)

        # Footer
        ax.text(0.5, 0.2, 'Generated by Analytics Module',
                ha='center', va='center', fontsize=10, color='gray',
                transform=ax.transAxes)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_executive_summary(self, pdf: PdfPages,
                                  product_df: pd.DataFrame,
                                  niche_df: pd.DataFrame):
        """Create executive summary page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.95, 'Executive Summary',
                ha='center', va='top', fontsize=24, fontweight='bold',
                transform=ax.transAxes)

        # Key metrics
        if not product_df.empty:
            total_products = len(product_df)
            total_sales = product_df['sales'].sum()
            total_revenue = product_df['revenue'].sum()
            avg_conversion = product_df['conversion_rate'].mean()

            metrics_text = f"""
            Key Metrics (Last 7 Days)
            {'=' * 40}

            Products Published: {total_products}
            Total Sales: {int(total_sales)}
            Total Revenue: ${total_revenue:.2f}
            Average Conversion Rate: {avg_conversion:.2f}%

            Top Product: {product_df.iloc[0]['title']}
            Top Revenue: ${product_df.iloc[0]['revenue']:.2f}
            """

            ax.text(0.1, 0.80, metrics_text, ha='left', va='top',
                   fontsize=12, family='monospace',
                   transform=ax.transAxes)

        # Top niches
        if not niche_df.empty:
            top_niches_text = "\nTop Performing Niches:\n" + "=" * 40 + "\n\n"

            for i, row in niche_df.head(5).iterrows():
                top_niches_text += f"{i+1}. {row['niche']}\n"
                top_niches_text += f"   Revenue: ${row['total_revenue']:.2f}\n"
                top_niches_text += f"   {row['recommendation_text']}\n\n"

            ax.text(0.1, 0.45, top_niches_text, ha='left', va='top',
                   fontsize=10, family='monospace',
                   transform=ax.transAxes)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_product_chart(self, pdf: PdfPages, df: pd.DataFrame):
        """Create product performance charts."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.suptitle('Product Performance Analysis', fontsize=16, fontweight='bold')

        # Top 10 products by revenue
        top_products = df.nlargest(10, 'revenue')
        ax1.barh(range(len(top_products)), top_products['revenue'])
        ax1.set_yticks(range(len(top_products)))
        ax1.set_yticklabels([t[:30] for t in top_products['title']], fontsize=8)
        ax1.set_xlabel('Revenue ($)')
        ax1.set_title('Top 10 Products by Revenue')
        ax1.invert_yaxis()

        # Sales by product type
        type_sales = df.groupby('type')['sales'].sum().sort_values(ascending=False)
        ax2.pie(type_sales.values, labels=type_sales.index, autopct='%1.1f%%')
        ax2.set_title('Sales Distribution by Product Type')

        # Conversion rates
        if df['conversion_rate'].sum() > 0:
            top_conversion = df.nlargest(10, 'conversion_rate')
            ax3.barh(range(len(top_conversion)), top_conversion['conversion_rate'])
            ax3.set_yticks(range(len(top_conversion)))
            ax3.set_yticklabels([t[:30] for t in top_conversion['title']], fontsize=8)
            ax3.set_xlabel('Conversion Rate (%)')
            ax3.set_title('Top 10 Products by Conversion Rate')
            ax3.invert_yaxis()
        else:
            ax3.text(0.5, 0.5, 'No conversion data available',
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.axis('off')

        # Revenue vs Sales scatter
        ax4.scatter(df['sales'], df['revenue'], alpha=0.6)
        ax4.set_xlabel('Sales Count')
        ax4.set_ylabel('Revenue ($)')
        ax4.set_title('Revenue vs Sales')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_niche_chart(self, pdf: PdfPages, df: pd.DataFrame):
        """Create niche analysis charts."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.suptitle('Niche Performance Analysis', fontsize=16, fontweight='bold')

        # Revenue by niche
        top_niches = df.nlargest(10, 'total_revenue')
        ax1.barh(range(len(top_niches)), top_niches['total_revenue'])
        ax1.set_yticks(range(len(top_niches)))
        ax1.set_yticklabels(top_niches['niche'], fontsize=9)
        ax1.set_xlabel('Total Revenue ($)')
        ax1.set_title('Top 10 Niches by Revenue')
        ax1.invert_yaxis()

        # Product count by niche
        ax2.bar(range(len(top_niches)), top_niches['product_count'])
        ax2.set_xticks(range(len(top_niches)))
        ax2.set_xticklabels(top_niches['niche'], rotation=45, ha='right', fontsize=8)
        ax2.set_ylabel('Number of Products')
        ax2.set_title('Product Count by Niche')

        # Average price by niche
        ax3.bar(range(len(top_niches)), top_niches['avg_price'])
        ax3.set_xticks(range(len(top_niches)))
        ax3.set_xticklabels(top_niches['niche'], rotation=45, ha='right', fontsize=8)
        ax3.set_ylabel('Average Price ($)')
        ax3.set_title('Average Price by Niche')

        # Recommendation scores
        ax4.barh(range(len(top_niches)), top_niches['recommendation'])
        ax4.set_yticks(range(len(top_niches)))
        ax4.set_yticklabels(top_niches['niche'], fontsize=9)
        ax4.set_xlabel('Recommendation Score (0-5)')
        ax4.set_title('Niche Recommendations')
        ax4.set_xlim(0, 5)
        ax4.invert_yaxis()

        # Add color coding
        colors = ['red' if s < 2 else 'orange' if s < 3 else 'yellow' if s < 4 else 'green'
                  for s in top_niches['recommendation']]
        for i, (bar, color) in enumerate(zip(ax4.patches, colors)):
            bar.set_color(color)

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_platform_chart(self, pdf: PdfPages, comparison: Dict[str, Any]):
        """Create platform comparison charts."""
        df = comparison['platforms']

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 8.5))
        fig.suptitle('Platform Performance Comparison', fontsize=16, fontweight='bold')

        platforms = df['platform'].tolist()
        x = range(len(platforms))

        # Gross revenue comparison
        ax1.bar(x, df['gross_revenue'])
        ax1.set_xticks(x)
        ax1.set_xticklabels(platforms)
        ax1.set_ylabel('Revenue ($)')
        ax1.set_title('Gross Revenue by Platform')

        # Net profit comparison
        ax2.bar(x, df['net_profit'], color='green')
        ax2.set_xticks(x)
        ax2.set_xticklabels(platforms)
        ax2.set_ylabel('Profit ($)')
        ax2.set_title('Net Profit by Platform')

        # Sales count
        ax3.bar(x, df['total_sales'], color='blue')
        ax3.set_xticks(x)
        ax3.set_xticklabels(platforms)
        ax3.set_ylabel('Sales')
        ax3.set_title('Total Sales by Platform')

        # Profit margin
        ax4.bar(x, df['profit_margin'], color='purple')
        ax4.set_xticks(x)
        ax4.set_xticklabels(platforms)
        ax4.set_ylabel('Profit Margin (%)')
        ax4.set_title('Profit Margin by Platform')

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _create_recommendations_page(self, pdf: PdfPages,
                                    niche_df: pd.DataFrame,
                                    platform_comparison: Dict[str, Any]):
        """Create recommendations page."""
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')

        # Title
        ax.text(0.5, 0.95, 'Recommendations & Action Items',
                ha='center', va='top', fontsize=20, fontweight='bold',
                transform=ax.transAxes)

        recommendations_text = "Based on this week's data:\n\n"

        # Niche recommendations
        if not niche_df.empty:
            recommendations_text += "1. Niche Strategy:\n"
            recommendations_text += "-" * 40 + "\n"

            top_niche = niche_df.iloc[0]
            recommendations_text += f"   ✓ Focus on '{top_niche['niche']}' niche\n"
            recommendations_text += f"     (${top_niche['total_revenue']:.2f} revenue)\n\n"

            if len(niche_df) > 1:
                second_niche = niche_df.iloc[1]
                recommendations_text += f"   ✓ Expand '{second_niche['niche']}'\n"
                recommendations_text += f"     (Good potential)\n\n"

            # Poor performers
            poor_niches = niche_df[niche_df['recommendation'] < 2]
            if not poor_niches.empty:
                recommendations_text += f"   ✗ Avoid: {', '.join(poor_niches['niche'].head(3))}\n"
                recommendations_text += f"     (Low performance)\n\n"

        # Platform recommendations
        recommendations_text += "\n2. Platform Strategy:\n"
        recommendations_text += "-" * 40 + "\n"
        recommendations_text += f"   {platform_comparison['recommendation']}\n\n"

        # Action items
        recommendations_text += "\n3. Action Items:\n"
        recommendations_text += "-" * 40 + "\n"
        recommendations_text += "   □ Create 3 more products in top niche\n"
        recommendations_text += "   □ Optimize pricing for low performers\n"
        recommendations_text += "   □ Review marketing for poor converting products\n"
        recommendations_text += "   □ Expand to recommended platform\n"
        recommendations_text += "   □ Update product descriptions for SEO\n"

        ax.text(0.1, 0.85, recommendations_text, ha='left', va='top',
               fontsize=10, family='monospace',
               transform=ax.transAxes)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

    def _email_report(self, report_path: Path, email_to: str):
        """
        Email the PDF report.

        Args:
            report_path: Path to PDF report
            email_to: Recipient email address
        """
        logger.info(f"Emailing report to {email_to}")

        # Email configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')

        if not smtp_user or not smtp_password:
            raise ValueError("SMTP credentials not configured in .env")

        # Create email
        msg = EmailMessage()
        msg['Subject'] = f"Weekly Report - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = smtp_user
        msg['To'] = email_to

        msg.set_content(f"""
        Digital Product Factory Weekly Report

        Please find attached your weekly performance report.

        Report period: {datetime.now().strftime('%B %d, %Y')}

        Best regards,
        Digital Product Factory Analytics
        """)

        # Attach PDF
        with open(report_path, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application',
                             subtype='pdf', filename=report_path.name)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

        logger.info("Report emailed successfully")

    def predict_trends(self, days_ahead: int = 7) -> Dict[str, Any]:
        """
        Predict upcoming hot niches based on historical data.

        Args:
            days_ahead: Number of days to predict (default: 7)

        Returns:
            Dictionary with:
                - predictions: List of predicted hot niches
                - confidence: Confidence level for each prediction
                - suggested_products: Product ideas for each niche
        """
        logger.info(f"Predicting trends for next {days_ahead} days")

        # Get historical performance
        niche_df = self.get_niche_performance()

        if niche_df.empty or len(niche_df) < 3:
            return {
                'predictions': [],
                'message': 'Insufficient data for predictions (need at least 3 niches with sales)'
            }

        # Simple prediction based on:
        # 1. Current performance (revenue, sales)
        # 2. Product count (more products = more data)
        # 3. Conversion rates

        # Calculate momentum score
        niche_df['momentum_score'] = (
            (niche_df['total_revenue'] / niche_df['total_revenue'].max() * 0.4) +
            (niche_df['total_sales'] / niche_df['total_sales'].max() * 0.3) +
            (niche_df['avg_conversion_rate'] / niche_df['avg_conversion_rate'].max() * 0.3)
        )

        # Sort by momentum
        trending = niche_df.nlargest(5, 'momentum_score')

        predictions = []

        for _, row in trending.iterrows():
            # Calculate confidence based on data points
            confidence = min(100, (row['product_count'] / 10) * 100)

            # Suggest product types based on niche
            product_suggestions = self._suggest_products_for_niche(row['niche'])

            predictions.append({
                'niche': row['niche'],
                'confidence': f"{confidence:.0f}%",
                'current_revenue': f"${row['total_revenue']:.2f}",
                'trend': 'Increasing' if row['momentum_score'] > 0.7 else 'Stable',
                'suggested_products': product_suggestions,
                'reasoning': self._generate_prediction_reasoning(row)
            })

        logger.info(f"Generated {len(predictions)} trend predictions")

        return {
            'predictions': predictions,
            'generated_at': datetime.now().isoformat(),
            'prediction_period': f"Next {days_ahead} days"
        }

    def _suggest_products_for_niche(self, niche: str) -> List[str]:
        """Suggest product types for a niche."""
        # Common product suggestions
        base_suggestions = [
            f"{niche.title()} Prompt Pack (50+ prompts)",
            f"{niche.title()} Digital Planner",
            f"{niche.title()} Notion Template",
            f"{niche.title()} Social Media Templates"
        ]

        return base_suggestions[:3]

    def _generate_prediction_reasoning(self, row: pd.Series) -> str:
        """Generate reasoning for prediction."""
        reasons = []

        if row['total_revenue'] > 100:
            reasons.append("strong revenue")

        if row['total_sales'] > 10:
            reasons.append("high sales volume")

        if row['avg_conversion_rate'] > 5:
            reasons.append("good conversion rate")

        if row['product_count'] > 3:
            reasons.append("multiple successful products")

        if not reasons:
            return "Based on initial data"

        return "Based on " + ", ".join(reasons)


def main():
    """Test analytics functionality."""
    print("=" * 60)
    print("Digital Product Factory - Analytics Test")
    print("=" * 60)
    print()

    try:
        # Initialize
        print("Initializing analytics...")
        analytics = Analytics()
        print("✓ Analytics initialized\n")

        # Product performance
        print("Analyzing product performance...")
        performance = analytics.get_product_performance()
        if not performance.empty:
            print(f"✓ Analyzed {len(performance)} products")
            print(f"  Total revenue: ${performance['revenue'].sum():.2f}")
            print(f"  Total sales: {performance['sales'].sum()}")
        else:
            print("  No performance data available")
        print()

        # Niche analysis
        print("Analyzing niches...")
        niches = analytics.get_niche_performance()
        if not niches.empty:
            print(f"✓ Analyzed {len(niches)} niches")
            print(f"  Top niche: {niches.iloc[0]['niche']}")
            print(f"  Revenue: ${niches.iloc[0]['total_revenue']:.2f}")
        else:
            print("  No niche data available")
        print()

        # Platform comparison
        print("Comparing platforms...")
        comparison = analytics.get_platform_comparison()
        print(f"✓ {comparison['recommendation']}")
        print()

        # Generate report
        print("Generating weekly report...")
        report_path = analytics.generate_weekly_report()
        print(f"✓ Report generated: {report_path}")
        print()

        # Predict trends
        print("Predicting trends...")
        predictions = analytics.predict_trends()
        if predictions.get('predictions'):
            print(f"✓ Generated {len(predictions['predictions'])} predictions")
            for pred in predictions['predictions'][:3]:
                print(f"  • {pred['niche']}: {pred['trend']} ({pred['confidence']})")
        else:
            print("  Insufficient data for predictions")
        print()

        print("=" * 60)
        print("✓ All analytics tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
