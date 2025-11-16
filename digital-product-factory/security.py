"""
Digital Product Factory - Security Module

This module provides security features for the Digital Product Factory:
- Input sanitization (SQL injection, XSS prevention)
- Credential encryption
- File upload validation
- Rate limiting
- Security headers
- Environment validation

Usage:
    from security import sanitize_input, encrypt_credentials, validate_file_upload
    from security import setup_security_headers, RateLimiter

    # Sanitize user input
    clean_data = sanitize_input(user_input, input_type='text')

    # Encrypt API keys
    encrypted = encrypt_credentials({'api_key': 'secret'})

    # Validate file uploads
    is_safe, message = validate_file_upload('/path/to/file.pdf')

    # Rate limiting
    limiter = RateLimiter(max_requests=100, time_window=60)
    if limiter.is_allowed(client_id='user_123'):
        # Process request
        pass
"""

import os
import re
import sys
import html
import logging
import hashlib
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

# Cryptography imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.backends import default_backend
    import base64
except ImportError:
    print("Installing cryptography library...")
    os.system("pip install cryptography -q")
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.backends import default_backend
    import base64

# Load environment variables
load_dotenv()

# Setup logging
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'security.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
SECURITY_EVENTS_FILE = LOG_DIR / 'security_events.log'

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|DECLARE)\b)",
    r"(--|\#|\/\*|\*\/)",
    r"('|\")\s*(OR|AND)\s*('|\")?\s*=\s*('|\")?",
    r";\s*(DROP|DELETE|UPDATE|INSERT)",
    r"(xp_|sp_)\w+",
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
]

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'documents': {'.pdf', '.txt', '.md', '.docx'},
    'images': {'.jpg', '.jpeg', '.png', '.gif', '.webp'},
    'templates': {'.notion', '.json', '.csv'},
    'archives': {'.zip'},
}

# Maximum file sizes (in bytes)
MAX_FILE_SIZES = {
    'documents': 10 * 1024 * 1024,  # 10 MB
    'images': 5 * 1024 * 1024,       # 5 MB
    'templates': 2 * 1024 * 1024,    # 2 MB
    'archives': 20 * 1024 * 1024,    # 20 MB
}

# Malicious file signatures (magic bytes)
MALICIOUS_SIGNATURES = [
    b'MZ',  # DOS/Windows executable
    b'\x7fELF',  # Linux executable
    b'#!',  # Script shebang
]


class SecurityException(Exception):
    """Base exception for security-related errors."""
    pass


class InputValidationError(SecurityException):
    """Raised when input validation fails."""
    pass


class FileValidationError(SecurityException):
    """Raised when file validation fails."""
    pass


class RateLimitExceeded(SecurityException):
    """Raised when rate limit is exceeded."""
    pass


def log_security_event(event_type: str, message: str, severity: str = 'INFO', context: Optional[Dict] = None):
    """
    Log security events to dedicated security log.

    Args:
        event_type: Type of security event (e.g., 'input_validation', 'rate_limit')
        message: Event description
        severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        context: Additional context data
    """
    event_data = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'severity': severity,
        'message': message,
        'context': context or {}
    }

    # Log to security events file
    try:
        with open(SECURITY_EVENTS_FILE, 'a') as f:
            f.write(f"{event_data}\n")
    except Exception as e:
        logger.error(f"Failed to write security event: {str(e)}")

    # Also log to standard logger
    log_level = getattr(logging, severity, logging.INFO)
    logger.log(log_level, f"[SECURITY] {event_type}: {message}", extra={'context': context})


def sanitize_input(user_input: Any, input_type: str = 'text', max_length: Optional[int] = None) -> str:
    """
    Sanitize user input to prevent SQL injection and XSS attacks.

    Args:
        user_input: The input to sanitize
        input_type: Type of input ('text', 'html', 'number', 'email', 'url')
        max_length: Maximum allowed length

    Returns:
        Sanitized input string

    Raises:
        InputValidationError: If input contains malicious patterns

    Usage:
        clean_text = sanitize_input(user_input, input_type='text')
        clean_email = sanitize_input(email, input_type='email')
    """
    # Convert to string
    if user_input is None:
        return ''

    input_str = str(user_input).strip()

    # Check length
    if max_length and len(input_str) > max_length:
        log_security_event(
            'input_validation',
            f'Input exceeds max length: {len(input_str)} > {max_length}',
            'WARNING'
        )
        input_str = input_str[:max_length]

    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            log_security_event(
                'sql_injection_attempt',
                f'SQL injection pattern detected: {pattern}',
                'ERROR',
                {'input': input_str[:100]}
            )
            raise InputValidationError(f"Invalid input detected: potential SQL injection")

    # Type-specific sanitization
    if input_type == 'text':
        # Remove HTML tags and escape special characters
        input_str = html.escape(input_str)

        # Check for XSS patterns
        for pattern in XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                log_security_event(
                    'xss_attempt',
                    f'XSS pattern detected: {pattern}',
                    'ERROR',
                    {'input': input_str[:100]}
                )
                raise InputValidationError(f"Invalid input detected: potential XSS attack")

    elif input_type == 'html':
        # Escape HTML but preserve structure (use with caution)
        input_str = html.escape(input_str, quote=False)

    elif input_type == 'number':
        # Validate and convert to number
        if not re.match(r'^-?\d+\.?\d*$', input_str):
            raise InputValidationError(f"Invalid number format: {input_str}")

    elif input_type == 'email':
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, input_str):
            raise InputValidationError(f"Invalid email format: {input_str}")
        input_str = input_str.lower()

    elif input_type == 'url':
        # Validate URL format
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, input_str):
            raise InputValidationError(f"Invalid URL format: {input_str}")

        # Block javascript: and data: URLs
        if input_str.lower().startswith(('javascript:', 'data:')):
            raise InputValidationError(f"Prohibited URL scheme detected")

    logger.debug(f"Input sanitized successfully (type: {input_type})")
    return input_str


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key for credential storage.

    Returns:
        Encryption key as bytes

    Note:
        In production, store this key securely (e.g., AWS KMS, HashiCorp Vault)
    """
    key_file = Path(__file__).parent.parent / '.encryption_key'

    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Generate new key
        password = os.getenv('ENCRYPTION_PASSWORD', 'default-password-change-me').encode()
        salt = os.getenv('ENCRYPTION_SALT', 'default-salt').encode()

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(kdf.derive(password))

        # Save key
        with open(key_file, 'wb') as f:
            f.write(key)

        # Restrict permissions (Unix-like systems)
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass

        logger.info("New encryption key generated")
        return key


def encrypt_credentials(credentials: Union[str, Dict[str, Any]]) -> str:
    """
    Encrypt API keys and credentials for secure storage.

    Args:
        credentials: Credentials to encrypt (string or dict)

    Returns:
        Encrypted credentials as base64 string

    Usage:
        encrypted = encrypt_credentials({'api_key': 'sk-123', 'secret': 'abc'})
        # Store encrypted in database
    """
    try:
        # Convert to JSON string if dict
        if isinstance(credentials, dict):
            import json
            credentials_str = json.dumps(credentials)
        else:
            credentials_str = str(credentials)

        # Get encryption key
        key = get_encryption_key()
        fernet = Fernet(key)

        # Encrypt
        encrypted = fernet.encrypt(credentials_str.encode())

        logger.debug("Credentials encrypted successfully")
        return encrypted.decode()

    except Exception as e:
        logger.error(f"Failed to encrypt credentials: {str(e)}")
        raise SecurityException(f"Encryption failed: {str(e)}")


def decrypt_credentials(encrypted_credentials: str) -> Union[str, Dict[str, Any]]:
    """
    Decrypt encrypted credentials.

    Args:
        encrypted_credentials: Encrypted credentials string

    Returns:
        Decrypted credentials (string or dict)

    Usage:
        credentials = decrypt_credentials(encrypted_data)
    """
    try:
        # Get encryption key
        key = get_encryption_key()
        fernet = Fernet(key)

        # Decrypt
        decrypted = fernet.decrypt(encrypted_credentials.encode())
        decrypted_str = decrypted.decode()

        # Try to parse as JSON
        try:
            import json
            return json.loads(decrypted_str)
        except json.JSONDecodeError:
            return decrypted_str

    except Exception as e:
        logger.error(f"Failed to decrypt credentials: {str(e)}")
        raise SecurityException(f"Decryption failed: {str(e)}")


def validate_file_upload(file_path: Union[str, Path]) -> Tuple[bool, str]:
    """
    Validate uploaded files for security.

    Checks:
    - File type (extension and MIME)
    - File size
    - Malicious content (magic bytes)
    - File exists and readable

    Args:
        file_path: Path to file to validate

    Returns:
        Tuple of (is_safe, message)

    Usage:
        is_safe, message = validate_file_upload('/path/to/file.pdf')
        if not is_safe:
            raise FileValidationError(message)
    """
    file_path = Path(file_path)

    # Check file exists
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"

    if not file_path.is_file():
        return False, f"Path is not a file: {file_path}"

    # Check file extension
    extension = file_path.suffix.lower()
    file_category = None

    for category, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            file_category = category
            break

    if not file_category:
        log_security_event(
            'file_validation',
            f'Unauthorized file type: {extension}',
            'WARNING',
            {'file': str(file_path)}
        )
        return False, f"File type not allowed: {extension}"

    # Check file size
    file_size = file_path.stat().st_size
    max_size = MAX_FILE_SIZES.get(file_category, 10 * 1024 * 1024)

    if file_size > max_size:
        log_security_event(
            'file_validation',
            f'File too large: {file_size} bytes (max: {max_size})',
            'WARNING',
            {'file': str(file_path)}
        )
        return False, f"File too large: {file_size / 1024 / 1024:.1f} MB (max: {max_size / 1024 / 1024:.1f} MB)"

    # Check MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        # Verify MIME matches extension
        expected_mimes = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
        }

        expected = expected_mimes.get(extension)
        if expected and mime_type != expected:
            log_security_event(
                'file_validation',
                f'MIME type mismatch: expected {expected}, got {mime_type}',
                'WARNING',
                {'file': str(file_path)}
            )
            return False, f"File type mismatch (MIME: {mime_type})"

    # Scan for malicious signatures (magic bytes)
    try:
        with open(file_path, 'rb') as f:
            header = f.read(256)  # Read first 256 bytes

            for signature in MALICIOUS_SIGNATURES:
                if header.startswith(signature):
                    log_security_event(
                        'malicious_file',
                        f'Malicious signature detected: {signature}',
                        'ERROR',
                        {'file': str(file_path)}
                    )
                    return False, f"Potentially malicious file detected"

    except Exception as e:
        logger.error(f"Failed to scan file: {str(e)}")
        return False, f"File scan failed: {str(e)}"

    logger.info(f"File validated successfully: {file_path.name}")
    return True, "File is safe"


class RateLimiter:
    """
    Rate limiter for API endpoints and operations.

    Implements token bucket algorithm for rate limiting.

    Usage:
        limiter = RateLimiter(max_requests=100, time_window=60)

        if limiter.is_allowed(client_id='user_123'):
            # Process request
            pass
        else:
            raise RateLimitExceeded("Too many requests")
    """

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[datetime]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for client.

        Args:
            client_id: Unique identifier for client (IP, user ID, etc.)

        Returns:
            True if request allowed, False if rate limit exceeded
        """
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.time_window)

        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff_time
        ]

        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.max_requests:
            log_security_event(
                'rate_limit_exceeded',
                f'Rate limit exceeded for client: {client_id}',
                'WARNING',
                {'client_id': client_id, 'requests': len(self.requests[client_id])}
            )
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.time_window)

        # Count valid requests
        valid_requests = sum(
            1 for req_time in self.requests.get(client_id, [])
            if req_time > cutoff_time
        )

        return max(0, self.max_requests - valid_requests)


def setup_security_headers(app):
    """
    Setup security headers for Flask application.

    Args:
        app: Flask application instance

    Usage:
        from flask import Flask
        app = Flask(__name__)
        setup_security_headers(app)
    """
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Enforce HTTPS in production
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:;"
        )

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    logger.info("Security headers configured for Flask app")


def validate_environment():
    """
    Validate environment variables and configuration.

    Checks:
    - Required variables are set
    - API keys have correct format
    - Paths are valid
    - Secure configuration in production

    Raises:
        SecurityException: If validation fails
    """
    logger.info("Validating environment configuration...")

    errors = []

    # Check required variables
    required_vars = ['ANTHROPIC_API_KEY']

    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")

    # Validate API key formats
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
    if anthropic_key and not anthropic_key.startswith('sk-ant-'):
        errors.append("Invalid Anthropic API key format (should start with 'sk-ant-')")

    # Check Flask environment
    flask_env = os.getenv('FLASK_ENV', 'development')

    if flask_env == 'production':
        # Production-specific checks
        if not os.getenv('FLASK_SECRET_KEY'):
            errors.append("FLASK_SECRET_KEY must be set in production")

        flask_secret = os.getenv('FLASK_SECRET_KEY', '')
        if len(flask_secret) < 32:
            errors.append("FLASK_SECRET_KEY must be at least 32 characters in production")

        # Check HTTPS requirement
        if not os.getenv('FORCE_HTTPS', 'false').lower() == 'true':
            log_security_event(
                'configuration',
                'HTTPS not enforced in production',
                'WARNING'
            )

    # Validate paths
    database_path = os.getenv('DATABASE_PATH', 'data/products.db')
    db_dir = Path(database_path).parent

    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create database directory: {str(e)}")

    # Report errors
    if errors:
        error_message = "Environment validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        log_security_event('environment_validation', error_message, 'ERROR')
        raise SecurityException(error_message)

    logger.info("Environment validation passed")


def main():
    """Main function for testing security features."""
    print("=" * 80)
    print("DIGITAL PRODUCT FACTORY - SECURITY MODULE TEST")
    print("=" * 80)
    print()

    # Test 1: Input Sanitization
    print("1. Testing input sanitization...")
    print("-" * 80)

    test_inputs = [
        ("Hello World", "text"),
        ("user@example.com", "email"),
        ("https://example.com", "url"),
        ("123.45", "number"),
        ("<script>alert('xss')</script>", "text"),  # Should fail
    ]

    for test_input, input_type in test_inputs:
        try:
            result = sanitize_input(test_input, input_type)
            print(f"✓ {input_type}: {test_input[:50]} → {result[:50]}")
        except InputValidationError as e:
            print(f"✗ {input_type}: {test_input[:50]} → BLOCKED ({str(e)})")

    print()

    # Test 2: Credential Encryption
    print("2. Testing credential encryption...")
    print("-" * 80)

    credentials = {
        'api_key': 'sk-test-123456789',
        'secret': 'my-secret-token'
    }

    encrypted = encrypt_credentials(credentials)
    print(f"✓ Encrypted: {encrypted[:50]}...")

    decrypted = decrypt_credentials(encrypted)
    print(f"✓ Decrypted: {decrypted}")

    assert credentials == decrypted, "Encryption/decryption mismatch!"
    print("✓ Encryption test passed")
    print()

    # Test 3: Rate Limiting
    print("3. Testing rate limiter...")
    print("-" * 80)

    limiter = RateLimiter(max_requests=5, time_window=10)
    client_id = "test_client"

    for i in range(7):
        allowed = limiter.is_allowed(client_id)
        remaining = limiter.get_remaining(client_id)
        status = "✓ Allowed" if allowed else "✗ Blocked"
        print(f"Request {i+1}: {status} (remaining: {remaining})")

    print()

    # Test 4: Environment Validation
    print("4. Testing environment validation...")
    print("-" * 80)

    try:
        validate_environment()
        print("✓ Environment validation passed")
    except SecurityException as e:
        print(f"✗ Environment validation failed:\n{str(e)}")

    print()

    print("=" * 80)
    print("SECURITY TEST COMPLETE")
    print("=" * 80)
    print()
    print(f"Security events log: {SECURITY_EVENTS_FILE}")


if __name__ == '__main__':
    main()
