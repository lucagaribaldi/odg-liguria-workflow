#!/bin/bash
# ODG Liguria Workflow - Environment Setup Script
# This script automates the complete setup of the ODG Liguria Workflow environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    print_status "Checking Python version..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $python_version is installed, but version $required_version or higher is required."
        exit 1
    fi
    
    print_success "Python $python_version is installed and meets requirements"
}

# Function to create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created successfully"
}

# Function to activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment activation script not found"
        exit 1
    fi
}

# Function to upgrade pip
upgrade_pip() {
    print_status "Upgrading pip..."
    pip install --upgrade pip
    print_success "Pip upgraded successfully"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies from requirements.txt..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    pip install -r requirements.txt
    print_success "Dependencies installed successfully"
}

# Function to create configuration files
create_config_files() {
    print_status "Creating configuration files..."
    
    # Create .env file
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
            print_warning "Please edit .env file with your actual configuration values"
        else
            print_error ".env.example not found"
            exit 1
        fi
    else
        print_warning ".env file already exists, skipping creation"
    fi
    
    # Create config.yaml file
    if [ ! -f "config.yaml" ]; then
        if [ -f "config.yaml.example" ]; then
            cp config.yaml.example config.yaml
            print_success "Created config.yaml file from config.yaml.example"
            print_warning "Please edit config.yaml file with your actual configuration values"
        else
            print_error "config.yaml.example not found"
            exit 1
        fi
    else
        print_warning "config.yaml file already exists, skipping creation"
    fi
}

# Function to create directory structure
create_directories() {
    print_status "Creating directory structure..."
    
    directories=(
        "data/input"
        "data/output"
        "data/backups"
        "logs"
        "cache"
        "temp"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        else
            print_warning "Directory already exists: $dir"
        fi
    done
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database..."
    
    if [ -f "src/database/init_db.py" ]; then
        python -m src.database.init_db
        print_success "Database initialized successfully"
    else
        print_warning "Database initialization script not found, skipping..."
    fi
}

# Function to install pre-commit hooks
install_pre_commit() {
    print_status "Installing pre-commit hooks..."
    
    if command_exists pre-commit; then
        pre-commit install
        print_success "Pre-commit hooks installed successfully"
    else
        print_warning "pre-commit not found, skipping hook installation"
    fi
}

# Function to run initial verification
run_verification() {
    print_status "Running initial verification..."
    
    # Check if Makefile exists and run basic verification
    if [ -f "Makefile" ]; then
        if command_exists make; then
            make check-deps || print_warning "Dependency check failed, but continuing..."
            print_success "Basic verification completed"
        else
            print_warning "make command not found, skipping verification"
        fi
    else
        print_warning "Makefile not found, skipping verification"
    fi
}

# Function to display setup summary
display_summary() {
    echo
    echo "=========================================="
    echo "  ODG Liguria Workflow Setup Complete!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo "1. Edit .env file with your email credentials and settings"
    echo "2. Edit config.yaml file with your specific configuration"
    echo "3. Run 'make verify' to ensure everything is working"
    echo "4. Run 'make run' to start the application"
    echo "5. Run 'make dashboard' to start the web dashboard"
    echo
    echo "Useful commands:"
    echo "- make help          : Show all available commands"
    echo "- make run           : Start the main application"
    echo "- make dashboard     : Start the web dashboard"
    echo "- make test          : Run all tests"
    echo "- make verify        : Run complete verification"
    echo "- make status        : Show system status"
    echo
    echo "Documentation:"
    echo "- README.md          : Complete setup and usage instructions"
    echo "- docs/              : Additional documentation"
    echo
    echo "Support:"
    echo "- Check logs in logs/odg_workflow.log"
    echo "- Run 'make status' to check system status"
    echo "- Run 'make verify' to diagnose issues"
    echo
    print_success "Setup completed successfully!"
}

# Function to handle errors
handle_error() {
    print_error "Setup failed at step: $1"
    print_error "Please check the error messages above and try again"
    exit 1
}

# Main setup function
main() {
    echo "=========================================="
    echo "  ODG Liguria Workflow Environment Setup"
    echo "=========================================="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Perform setup steps
    check_python_version || handle_error "Python version check"
    create_venv || handle_error "Virtual environment creation"
    activate_venv || handle_error "Virtual environment activation"
    upgrade_pip || handle_error "Pip upgrade"
    install_dependencies || handle_error "Dependencies installation"
    create_config_files || handle_error "Configuration files creation"
    create_directories || handle_error "Directory structure creation"
    initialize_database || handle_error "Database initialization"
    install_pre_commit || handle_error "Pre-commit hooks installation"
    run_verification || handle_error "Initial verification"
    
    display_summary
}

# Handle script interruption
trap 'print_error "Setup interrupted by user"; exit 1' INT

# Run main function
main "$@"