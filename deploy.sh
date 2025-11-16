#!/bin/bash
#
# Digital Product Factory - Deployment Script (Linux/Mac)
#
# This script automates the complete setup and deployment process:
# - Checks system requirements
# - Creates virtual environment
# - Installs dependencies
# - Runs setup wizard
# - Initializes database
# - Runs validation tests
# - Starts the system
#
# Usage:
#   ./deploy.sh                 # Full deployment
#   ./deploy.sh --skip-wizard   # Skip interactive wizard
#   ./deploy.sh --dev           # Development mode
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PYTHON_MIN_VERSION="3.10"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/deploy_$(date +%Y%m%d_%H%M%S).log"

# Parse arguments
SKIP_WIZARD=false
DEV_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-wizard)
            SKIP_WIZARD=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-wizard] [--dev]"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "${CYAN}"
    echo "================================================================================"
    echo "$1" | awk '{printf "%" int((80+length)/2) "s\n", $0}'
    echo "================================================================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Create log directory
mkdir -p "$PROJECT_DIR/logs"

# Start logging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

print_header "DIGITAL PRODUCT FACTORY - DEPLOYMENT"

echo "Started: $(date)"
echo "Project Directory: $PROJECT_DIR"
echo "Log File: $LOG_FILE"
echo ""

# Step 1: Check Python version
print_step "Step 1/10: Checking Python version..."

if ! check_command python3; then
    print_error "Python 3 not found. Please install Python $PYTHON_MIN_VERSION or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_VERSION_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_VERSION_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

MIN_MAJOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f1)
MIN_MINOR=$(echo $PYTHON_MIN_VERSION | cut -d. -f2)

if [ $PYTHON_VERSION_MAJOR -lt $MIN_MAJOR ] || ([ $PYTHON_VERSION_MAJOR -eq $MIN_MAJOR ] && [ $PYTHON_VERSION_MINOR -lt $MIN_MINOR ]); then
    print_error "Python $PYTHON_VERSION found, but $PYTHON_MIN_VERSION or higher is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Step 2: Check system requirements
print_step "Step 2/10: Checking system requirements..."

# Check disk space (need at least 500MB)
DISK_SPACE=$(df -BM "$PROJECT_DIR" | awk 'NR==2 {print $4}' | sed 's/M//')
if [ "$DISK_SPACE" -lt 500 ]; then
    print_warning "Low disk space: ${DISK_SPACE}MB available (500MB+ recommended)"
else
    print_success "Disk space: ${DISK_SPACE}MB available"
fi

# Check memory
if check_command free; then
    MEMORY=$(free -m | awk 'NR==2 {print $2}')
    print_success "Memory: ${MEMORY}MB total"
fi

# Step 3: Create virtual environment
print_step "Step 3/10: Creating virtual environment..."

if [ -d "$VENV_DIR" ]; then
    print_warning "Virtual environment already exists at $VENV_DIR"
    read -p "Remove and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        print_success "Removed existing virtual environment"
    else
        print_success "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created"
else
    print_success "Virtual environment ready"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
print_success "Virtual environment activated"

# Step 4: Upgrade pip
print_step "Step 4/10: Upgrading pip..."

pip install --upgrade pip -q
print_success "pip upgraded to $(pip --version | awk '{print $2}')"

# Step 5: Install dependencies
print_step "Step 5/10: Installing dependencies..."

if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    print_error "requirements.txt not found"
    exit 1
fi

echo "Installing from requirements.txt..."
pip install -r "$PROJECT_DIR/requirements.txt" -q

# Verify critical packages
CRITICAL_PACKAGES=("anthropic" "flask" "requests" "pandas" "matplotlib" "click" "schedule" "cryptography")
MISSING_PACKAGES=()

for package in "${CRITICAL_PACKAGES[@]}"; do
    if ! pip show "$package" &> /dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    print_error "Missing critical packages: ${MISSING_PACKAGES[*]}"
    exit 1
fi

print_success "All dependencies installed"

# Step 6: Create directory structure
print_step "Step 6/10: Creating directory structure..."

DIRS=("data" "logs" "output" "output/products" "output/marketing" "output/reports" "backups")

for dir in "${DIRS[@]}"; do
    mkdir -p "$PROJECT_DIR/$dir"
done

print_success "Directory structure created"

# Step 7: Run setup wizard
print_step "Step 7/10: Running setup wizard..."

if [ "$SKIP_WIZARD" = true ]; then
    print_warning "Skipping setup wizard (--skip-wizard flag)"

    # Check if .env exists
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_error ".env file not found and wizard skipped"
        print_error "Either run without --skip-wizard or create .env manually"
        exit 1
    fi
else
    if [ -f "$PROJECT_DIR/.env" ]; then
        print_warning ".env file already exists"
        read -p "Run setup wizard anyway? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python "$PROJECT_DIR/setup_wizard.py"
        else
            print_success "Using existing .env configuration"
        fi
    else
        python "$PROJECT_DIR/setup_wizard.py"
    fi
fi

print_success "Configuration complete"

# Step 8: Initialize database
print_step "Step 8/10: Initializing database..."

cd "$PROJECT_DIR/digital-product-factory"

python -c "
from database import ProductDB
db = ProductDB()
print('Database initialized successfully')
"

print_success "Database ready"

# Step 9: Run validation tests
print_step "Step 9/10: Running validation tests..."

cd "$PROJECT_DIR"

if [ "$DEV_MODE" = true ]; then
    print_warning "Development mode: Skipping tests"
else
    # Run quick integration tests
    if python integration_test.py --quick; then
        print_success "Validation tests passed"
    else
        print_error "Some validation tests failed"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Step 10: Final setup
print_step "Step 10/10: Final setup..."

# Create systemd service file (optional)
SERVICE_FILE="/etc/systemd/system/digipro-factory.service"

if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
    read -p "Create systemd service for automatic startup? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Digital Product Factory
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable digipro-factory.service
        print_success "Systemd service created and enabled"
        echo "Start service with: sudo systemctl start digipro-factory"
    fi
fi

print_success "Setup complete"

# Display summary
print_header "DEPLOYMENT COMPLETE!"

echo -e "${GREEN}✓ Digital Product Factory is ready to use!${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo ""
echo "  1. Activate virtual environment:"
echo "     source $VENV_DIR/bin/activate"
echo ""
echo "  2. Create your first product:"
echo "     python cli.py create-product --type=notion --niche=productivity"
echo ""
echo "  3. Check trending opportunities:"
echo "     python cli.py check-trends"
echo ""
echo "  4. Start review dashboard:"
echo "     python cli.py review-dashboard"
echo ""
echo "  5. Run automated mode:"
echo "     python main.py"
echo ""
echo -e "${CYAN}Documentation:${NC}"
echo "  • CLI Guide: CLI_GUIDE.md"
echo "  • Automation Guide: AUTOMATION.md"
echo "  • Log files: logs/"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  • Environment: .env"
echo "  • Database: data/products.db"
echo "  • Backups: backups/"
echo ""

if [ "$DEV_MODE" = true ]; then
    echo -e "${YELLOW}Development Mode:${NC}"
    echo "  Tests skipped - run manually with: python integration_test.py"
    echo ""
fi

echo "Deployment log saved to: $LOG_FILE"
echo ""
echo -e "${GREEN}Happy product creating! 🚀${NC}"
echo ""

exit 0
