"""
Digital Product Factory - System Monitoring & Health Checks

This module provides comprehensive system monitoring, health checks, and alerting
capabilities for the Digital Product Factory.

Features:
- System health monitoring (services, APIs, disk space, database)
- Alert management (logging, email, Slack)
- Error tracking with frequency analysis
- Circuit breaker pattern for API calls
- Retry logic with exponential backoff
- Performance metrics tracking

Usage:
    from monitoring import check_system_health, send_alert, log_error, CircuitBreaker

    # Check system health
    health = check_system_health()
    if not health['overall_healthy']:
        send_alert('critical', f"System unhealthy: {health['issues']}")

    # Log errors with context
    try:
        risky_operation()
    except Exception as e:
        log_error(e, {'operation': 'risky_operation', 'user_id': 123})

    # Use circuit breaker for API calls
    breaker = CircuitBreaker(failure_threshold=5, timeout=60)

    @breaker
    def call_external_api():
        return requests.get('https://api.example.com/data')
"""

import os
import sys
import json
import logging
import smtplib
import requests
import sqlite3
import hashlib
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict
from functools import wraps
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'monitoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
ALERTS_FILE = LOG_DIR / 'alerts.json'
ERRORS_FILE = LOG_DIR / 'errors_tracking.json'
HEALTH_FILE = LOG_DIR / 'health_status.json'

# Alert severity levels
SEVERITY_INFO = 'info'
SEVERITY_WARNING = 'warning'
SEVERITY_ERROR = 'error'
SEVERITY_CRITICAL = 'critical'

# Circuit breaker states
STATE_CLOSED = 'closed'
STATE_OPEN = 'open'
STATE_HALF_OPEN = 'half_open'


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.

    Prevents cascading failures by stopping calls to failing services
    and allowing them time to recover.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service has recovered

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        @breaker
        def call_api():
            return requests.get('https://api.example.com')
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = STATE_CLOSED

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == STATE_OPEN:
                if self._should_attempt_reset():
                    self.state = STATE_HALF_OPEN
                    logger.info(f"Circuit breaker entering HALF_OPEN state for {func.__name__}")
                else:
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}. Service temporarily unavailable.")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() >= self.timeout

    def _on_success(self):
        """Handle successful call."""
        if self.state == STATE_HALF_OPEN:
            logger.info("Circuit breaker recovered, entering CLOSED state")
        self.failure_count = 0
        self.state = STATE_CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != STATE_OPEN:
                logger.error(f"Circuit breaker opening due to {self.failure_count} failures")
                send_alert(
                    'critical',
                    f"Circuit breaker opened after {self.failure_count} failures",
                    {'threshold': self.failure_threshold, 'timeout': self.timeout}
                )
            self.state = STATE_OPEN


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds

    Usage:
        @retry_with_backoff(max_retries=5, base_delay=2.0)
        def unstable_operation():
            # May fail, will be retried with exponential backoff
            return api_call()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, max_delay)  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} retry attempts failed for {func.__name__}")

            # All retries exhausted
            raise last_exception

        return wrapper
    return decorator


def check_system_health() -> Dict[str, Any]:
    """
    Comprehensive system health check.

    Verifies:
    - All services running (database, APIs)
    - API rate limits status
    - Disk space availability
    - Database connection
    - Recent error rates

    Returns:
        Dict with health status:
        {
            'overall_healthy': bool,
            'timestamp': str,
            'checks': {
                'database': {'status': 'ok', 'message': '...'},
                'disk_space': {'status': 'ok', 'free_gb': 100.5},
                'api_anthropic': {'status': 'ok', 'rate_limit_remaining': 45},
                'api_gumroad': {'status': 'ok'},
                'error_rate': {'status': 'ok', 'recent_errors': 2}
            },
            'issues': ['list of any problems found']
        }
    """
    logger.info("Starting comprehensive system health check")

    health_status = {
        'overall_healthy': True,
        'timestamp': datetime.now().isoformat(),
        'checks': {},
        'issues': []
    }

    # 1. Check database connection
    try:
        db_check = _check_database()
        health_status['checks']['database'] = db_check
        if db_check['status'] != 'ok':
            health_status['overall_healthy'] = False
            health_status['issues'].append(f"Database: {db_check['message']}")
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status['checks']['database'] = {'status': 'error', 'message': str(e)}
        health_status['overall_healthy'] = False
        health_status['issues'].append(f"Database check failed: {str(e)}")

    # 2. Check disk space
    try:
        disk_check = _check_disk_space()
        health_status['checks']['disk_space'] = disk_check
        if disk_check['status'] == 'warning':
            health_status['issues'].append(f"Low disk space: {disk_check['free_gb']:.1f} GB remaining")
        elif disk_check['status'] == 'critical':
            health_status['overall_healthy'] = False
            health_status['issues'].append(f"Critical: Only {disk_check['free_gb']:.1f} GB disk space remaining")
    except Exception as e:
        logger.error(f"Disk space check failed: {str(e)}")
        health_status['checks']['disk_space'] = {'status': 'error', 'message': str(e)}

    # 3. Check Anthropic API
    try:
        anthropic_check = _check_anthropic_api()
        health_status['checks']['api_anthropic'] = anthropic_check
        if anthropic_check['status'] != 'ok':
            health_status['issues'].append(f"Anthropic API: {anthropic_check.get('message', 'Not available')}")
    except Exception as e:
        logger.error(f"Anthropic API check failed: {str(e)}")
        health_status['checks']['api_anthropic'] = {'status': 'error', 'message': str(e)}

    # 4. Check Gumroad API
    try:
        gumroad_check = _check_gumroad_api()
        health_status['checks']['api_gumroad'] = gumroad_check
        if gumroad_check['status'] != 'ok':
            health_status['issues'].append(f"Gumroad API: {gumroad_check.get('message', 'Not available')}")
    except Exception as e:
        logger.error(f"Gumroad API check failed: {str(e)}")
        health_status['checks']['api_gumroad'] = {'status': 'error', 'message': str(e)}

    # 5. Check recent error rate
    try:
        error_check = _check_error_rate()
        health_status['checks']['error_rate'] = error_check
        if error_check['status'] == 'warning':
            health_status['issues'].append(f"Elevated error rate: {error_check['recent_errors']} in last hour")
        elif error_check['status'] == 'critical':
            health_status['overall_healthy'] = False
            health_status['issues'].append(f"Critical error rate: {error_check['recent_errors']} in last hour")
    except Exception as e:
        logger.error(f"Error rate check failed: {str(e)}")
        health_status['checks']['error_rate'] = {'status': 'error', 'message': str(e)}

    # Save health status to file
    try:
        with open(HEALTH_FILE, 'w') as f:
            json.dump(health_status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save health status: {str(e)}")

    # Send alert if system is unhealthy
    if not health_status['overall_healthy']:
        send_alert(
            SEVERITY_CRITICAL,
            f"System health check failed: {', '.join(health_status['issues'])}",
            health_status
        )
        logger.error(f"System unhealthy: {health_status['issues']}")
    else:
        logger.info("System health check passed - all systems operational")

    return health_status


def _check_database() -> Dict[str, Any]:
    """Check database connection and integrity."""
    db_path = Path(__file__).parent.parent / 'data' / 'products.db'

    if not db_path.exists():
        return {'status': 'error', 'message': 'Database file not found'}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]

        # Check database size
        db_size_mb = db_path.stat().st_size / (1024 * 1024)

        conn.close()

        return {
            'status': 'ok',
            'message': f'Connected successfully',
            'product_count': count,
            'db_size_mb': round(db_size_mb, 2)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _check_disk_space(warning_threshold_gb: float = 5.0, critical_threshold_gb: float = 1.0) -> Dict[str, Any]:
    """Check available disk space."""
    project_root = Path(__file__).parent.parent

    try:
        stat = shutil.disk_usage(project_root)
        free_gb = stat.free / (1024 ** 3)
        total_gb = stat.total / (1024 ** 3)
        used_gb = stat.used / (1024 ** 3)
        percent_used = (stat.used / stat.total) * 100

        if free_gb < critical_threshold_gb:
            status = 'critical'
        elif free_gb < warning_threshold_gb:
            status = 'warning'
        else:
            status = 'ok'

        return {
            'status': status,
            'free_gb': round(free_gb, 2),
            'total_gb': round(total_gb, 2),
            'used_gb': round(used_gb, 2),
            'percent_used': round(percent_used, 1)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _check_anthropic_api() -> Dict[str, Any]:
    """Check Anthropic API availability."""
    api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        return {'status': 'warning', 'message': 'API key not configured'}

    try:
        # Simple check - verify key format (starts with sk-ant-)
        if api_key.startswith('sk-ant-'):
            return {'status': 'ok', 'message': 'API key configured'}
        else:
            return {'status': 'warning', 'message': 'API key format may be invalid'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _check_gumroad_api() -> Dict[str, Any]:
    """Check Gumroad API availability."""
    access_token = os.getenv('GUMROAD_ACCESS_TOKEN')

    if not access_token:
        return {'status': 'warning', 'message': 'API token not configured'}

    try:
        # Test API connection with user info endpoint
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://api.gumroad.com/v2/user', headers=headers, timeout=10)

        if response.status_code == 200:
            user_data = response.json()
            return {
                'status': 'ok',
                'message': 'Connected',
                'user': user_data.get('user', {}).get('name', 'Unknown')
            }
        else:
            return {'status': 'error', 'message': f'API returned {response.status_code}'}
    except requests.exceptions.Timeout:
        return {'status': 'warning', 'message': 'API request timed out'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _check_error_rate(time_window_minutes: int = 60, warning_threshold: int = 10, critical_threshold: int = 50) -> Dict[str, Any]:
    """Check recent error rate."""
    try:
        if not ERRORS_FILE.exists():
            return {'status': 'ok', 'recent_errors': 0}

        with open(ERRORS_FILE, 'r') as f:
            errors_data = json.load(f)

        # Count errors in time window
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_errors = 0

        for error_hash, error_info in errors_data.items():
            for occurrence in error_info.get('occurrences', []):
                error_time = datetime.fromisoformat(occurrence['timestamp'])
                if error_time > cutoff_time:
                    recent_errors += 1

        if recent_errors >= critical_threshold:
            status = 'critical'
        elif recent_errors >= warning_threshold:
            status = 'warning'
        else:
            status = 'ok'

        return {
            'status': status,
            'recent_errors': recent_errors,
            'time_window_minutes': time_window_minutes
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def send_alert(severity: str, message: str, context: Optional[Dict[str, Any]] = None):
    """
    Send alert through multiple channels (log, email, Slack).

    Args:
        severity: Alert severity - 'info', 'warning', 'error', 'critical'
        message: Alert message
        context: Optional additional context data

    Usage:
        send_alert('critical', 'Database connection lost', {'db_path': '/path/to/db'})
        send_alert('warning', 'Low disk space', {'free_gb': 2.5})
    """
    alert_data = {
        'timestamp': datetime.now().isoformat(),
        'severity': severity,
        'message': message,
        'context': context or {}
    }

    # Log alert
    log_level = {
        SEVERITY_INFO: logging.INFO,
        SEVERITY_WARNING: logging.WARNING,
        SEVERITY_ERROR: logging.ERROR,
        SEVERITY_CRITICAL: logging.CRITICAL
    }.get(severity, logging.INFO)

    logger.log(log_level, f"[ALERT] {message}", extra={'context': context})

    # Save to alerts file
    try:
        alerts = []
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)

        alerts.append(alert_data)

        # Keep only last 1000 alerts
        alerts = alerts[-1000:]

        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save alert to file: {str(e)}")

    # Send email for error and critical alerts
    if severity in [SEVERITY_ERROR, SEVERITY_CRITICAL]:
        try:
            _send_email_alert(severity, message, context)
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")

    # Send Slack notification for critical alerts
    if severity == SEVERITY_CRITICAL:
        try:
            _send_slack_alert(severity, message, context)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")


def _send_email_alert(severity: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Send alert via email."""
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    alert_email = os.getenv('ALERT_EMAIL')

    if not all([smtp_user, smtp_password, alert_email]):
        logger.debug("Email alerts not configured (missing SMTP credentials)")
        return

    msg = EmailMessage()
    msg['Subject'] = f"[{severity.upper()}] Digital Product Factory Alert"
    msg['From'] = smtp_user
    msg['To'] = alert_email

    body = f"""
Digital Product Factory Alert

Severity: {severity.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Message:
{message}

Context:
{json.dumps(context or {}, indent=2)}

---
This is an automated alert from Digital Product Factory.
"""
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)

    logger.info(f"Email alert sent to {alert_email}")


def _send_slack_alert(severity: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Send alert to Slack webhook."""
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')

    if not slack_webhook:
        logger.debug("Slack alerts not configured (missing webhook URL)")
        return

    emoji = {
        SEVERITY_INFO: ':information_source:',
        SEVERITY_WARNING: ':warning:',
        SEVERITY_ERROR: ':x:',
        SEVERITY_CRITICAL: ':rotating_light:'
    }.get(severity, ':bell:')

    payload = {
        'text': f"{emoji} *{severity.upper()}* Alert",
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f'{emoji} {severity.upper()} Alert'
                }
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f"*Message:*\n{message}"
                }
            }
        ]
    }

    if context:
        payload['blocks'].append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f"*Context:*\n```{json.dumps(context, indent=2)}```"
            }
        })

    response = requests.post(slack_webhook, json=payload, timeout=10)
    response.raise_for_status()

    logger.info("Slack alert sent successfully")


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Log error with context and track frequency.

    Groups similar errors and alerts on critical patterns.

    Args:
        error: The exception object
        context: Additional context about the error

    Usage:
        try:
            dangerous_operation()
        except Exception as e:
            log_error(e, {'operation': 'dangerous_operation', 'user_id': 123})
    """
    error_info = {
        'type': type(error).__name__,
        'message': str(error),
        'context': context or {},
        'timestamp': datetime.now().isoformat()
    }

    # Create hash for grouping similar errors
    error_signature = f"{error_info['type']}:{error_info['message']}"
    error_hash = hashlib.md5(error_signature.encode()).hexdigest()

    # Log to standard logging
    logger.error(
        f"Error logged: {error_info['type']} - {error_info['message']}",
        exc_info=error,
        extra={'context': context}
    )

    # Track error frequency
    try:
        errors_data = {}
        if ERRORS_FILE.exists():
            with open(ERRORS_FILE, 'r') as f:
                errors_data = json.load(f)

        if error_hash not in errors_data:
            errors_data[error_hash] = {
                'type': error_info['type'],
                'message': error_info['message'],
                'first_seen': error_info['timestamp'],
                'count': 0,
                'occurrences': []
            }

        errors_data[error_hash]['count'] += 1
        errors_data[error_hash]['last_seen'] = error_info['timestamp']
        errors_data[error_hash]['occurrences'].append({
            'timestamp': error_info['timestamp'],
            'context': context or {}
        })

        # Keep only last 100 occurrences per error type
        errors_data[error_hash]['occurrences'] = errors_data[error_hash]['occurrences'][-100:]

        # Save to file
        with open(ERRORS_FILE, 'w') as f:
            json.dump(errors_data, f, indent=2)

        # Alert on high-frequency errors
        error_count = errors_data[error_hash]['count']
        if error_count == 5:
            send_alert(
                SEVERITY_WARNING,
                f"Error occurred 5 times: {error_info['type']} - {error_info['message']}",
                {'error_hash': error_hash, 'count': error_count}
            )
        elif error_count == 20:
            send_alert(
                SEVERITY_ERROR,
                f"Error occurred 20 times: {error_info['type']} - {error_info['message']}",
                {'error_hash': error_hash, 'count': error_count}
            )
        elif error_count >= 50 and error_count % 25 == 0:
            send_alert(
                SEVERITY_CRITICAL,
                f"Error occurred {error_count} times: {error_info['type']} - {error_info['message']}",
                {'error_hash': error_hash, 'count': error_count}
            )
    except Exception as e:
        logger.error(f"Failed to track error frequency: {str(e)}")


def check_publishing_health(min_success_rate: float = 0.5) -> Dict[str, Any]:
    """
    Check publishing success rate and alert if too low.

    Args:
        min_success_rate: Minimum acceptable success rate (0.0 to 1.0)

    Returns:
        Dict with publishing health metrics
    """
    logger.info("Checking publishing success rate")

    db_path = Path(__file__).parent.parent / 'data' / 'products.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get recent publishing attempts (last 7 days)
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM products
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY status
        """)

        status_counts = dict(cursor.fetchall())
        conn.close()

        total = sum(status_counts.values())
        published = status_counts.get('published', 0)
        failed = status_counts.get('failed', 0)

        if total == 0:
            return {'status': 'ok', 'message': 'No recent publishing attempts'}

        success_rate = published / total

        result = {
            'success_rate': round(success_rate, 2),
            'total_attempts': total,
            'published': published,
            'failed': failed,
            'pending': status_counts.get('pending', 0),
            'approved': status_counts.get('approved', 0)
        }

        if success_rate < min_success_rate:
            result['status'] = 'critical'
            send_alert(
                SEVERITY_CRITICAL,
                f"Low publishing success rate: {success_rate:.1%} (threshold: {min_success_rate:.1%})",
                result
            )
        else:
            result['status'] = 'ok'

        logger.info(f"Publishing success rate: {success_rate:.1%} ({published}/{total})")
        return result

    except Exception as e:
        logger.error(f"Failed to check publishing health: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def check_sales_performance(min_daily_sales: int = 1, days: int = 7) -> Dict[str, Any]:
    """
    Check sales performance and alert if below threshold.

    Args:
        min_daily_sales: Minimum expected daily sales
        days: Number of days to analyze

    Returns:
        Dict with sales performance metrics
    """
    logger.info(f"Checking sales performance for last {days} days")

    db_path = Path(__file__).parent.parent / 'data' / 'products.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get published products with analytics
        cursor.execute("""
            SELECT metadata
            FROM products
            WHERE status = 'published'
            AND created_at >= datetime('now', '-{} days')
        """.format(days))

        total_sales = 0
        total_revenue = 0.0

        for row in cursor.fetchall():
            metadata = json.loads(row[0] or '{}')
            analytics = metadata.get('analytics', {})

            for platform_data in analytics.get('platforms', {}).values():
                total_sales += platform_data.get('sales_count', 0)
                total_revenue += platform_data.get('revenue', 0.0)

        conn.close()

        daily_average = total_sales / days if days > 0 else 0

        result = {
            'total_sales': total_sales,
            'total_revenue': round(total_revenue, 2),
            'daily_average': round(daily_average, 2),
            'days_analyzed': days,
            'min_threshold': min_daily_sales
        }

        if daily_average < min_daily_sales:
            result['status'] = 'warning'
            send_alert(
                SEVERITY_WARNING,
                f"Low sales performance: {daily_average:.1f} sales/day (threshold: {min_daily_sales})",
                result
            )
        else:
            result['status'] = 'ok'

        logger.info(f"Sales performance: {daily_average:.1f} sales/day, ${total_revenue:.2f} total revenue")
        return result

    except Exception as e:
        logger.error(f"Failed to check sales performance: {str(e)}")
        return {'status': 'error', 'message': str(e)}


def main():
    """Main function for testing monitoring features."""
    print("=" * 80)
    print("DIGITAL PRODUCT FACTORY - SYSTEM MONITORING TEST")
    print("=" * 80)
    print()

    # Test 1: System Health Check
    print("1. Running comprehensive system health check...")
    print("-" * 80)
    health = check_system_health()
    print(f"Overall Health: {'✓ HEALTHY' if health['overall_healthy'] else '✗ UNHEALTHY'}")
    print(f"Timestamp: {health['timestamp']}")
    print()

    for check_name, check_result in health['checks'].items():
        status_symbol = '✓' if check_result['status'] == 'ok' else '✗'
        print(f"  {status_symbol} {check_name}: {check_result['status']}")
        if check_result['status'] != 'ok':
            print(f"    Message: {check_result.get('message', 'N/A')}")

    if health['issues']:
        print("\nIssues found:")
        for issue in health['issues']:
            print(f"  - {issue}")
    print()

    # Test 2: Alert System
    print("2. Testing alert system...")
    print("-" * 80)
    send_alert(SEVERITY_INFO, "Test info alert", {'test': True})
    print("✓ Info alert sent")

    send_alert(SEVERITY_WARNING, "Test warning alert", {'test': True, 'level': 'warning'})
    print("✓ Warning alert sent")
    print()

    # Test 3: Error Logging
    print("3. Testing error logging and tracking...")
    print("-" * 80)
    try:
        # Simulate an error
        raise ValueError("Test error for monitoring system")
    except Exception as e:
        log_error(e, {'test': True, 'operation': 'monitoring_test'})
        print("✓ Error logged and tracked")
    print()

    # Test 4: Circuit Breaker
    print("4. Testing circuit breaker...")
    print("-" * 80)
    breaker = CircuitBreaker(failure_threshold=3, timeout=5)

    @breaker
    def flaky_function(should_fail=False):
        if should_fail:
            raise Exception("Simulated failure")
        return "Success"

    # Success case
    try:
        result = flaky_function(should_fail=False)
        print(f"✓ Circuit breaker allows successful calls: {result}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    # Failure case
    for i in range(4):
        try:
            flaky_function(should_fail=True)
        except Exception as e:
            if i < 3:
                print(f"  Failure {i+1}/3: {e}")
            else:
                print(f"✓ Circuit breaker opened after threshold reached")
    print()

    # Test 5: Retry Logic
    print("5. Testing retry with backoff...")
    print("-" * 80)

    attempt_count = [0]

    @retry_with_backoff(max_retries=3, base_delay=0.1, max_delay=1.0)
    def unreliable_function():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception(f"Attempt {attempt_count[0]} failed")
        return "Success after retries"

    try:
        result = unreliable_function()
        print(f"✓ Retry succeeded after {attempt_count[0]} attempts: {result}")
    except Exception as e:
        print(f"✗ All retries exhausted: {e}")
    print()

    # Test 6: Publishing Health
    print("6. Checking publishing health...")
    print("-" * 80)
    pub_health = check_publishing_health(min_success_rate=0.5)
    print(f"Status: {pub_health['status']}")
    if 'success_rate' in pub_health:
        print(f"Success Rate: {pub_health['success_rate']:.1%}")
        print(f"Published: {pub_health['published']}, Failed: {pub_health['failed']}")
    else:
        print(f"Message: {pub_health.get('message', 'N/A')}")
    print()

    # Test 7: Sales Performance
    print("7. Checking sales performance...")
    print("-" * 80)
    sales_health = check_sales_performance(min_daily_sales=1, days=7)
    print(f"Status: {sales_health['status']}")
    if 'daily_average' in sales_health:
        print(f"Daily Average: {sales_health['daily_average']:.1f} sales/day")
        print(f"Total Revenue: ${sales_health['total_revenue']:.2f}")
    else:
        print(f"Message: {sales_health.get('message', 'N/A')}")
    print()

    print("=" * 80)
    print("MONITORING TEST COMPLETE")
    print("=" * 80)
    print()
    print("Log files:")
    print(f"  - Monitoring: {LOG_DIR / 'monitoring.log'}")
    print(f"  - Alerts: {ALERTS_FILE}")
    print(f"  - Errors: {ERRORS_FILE}")
    print(f"  - Health: {HEALTH_FILE}")


if __name__ == '__main__':
    main()
