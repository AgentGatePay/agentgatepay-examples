#!/bin/bash
#
# AgentGatePay LangChain Integration - CI/CD Test Script
#
# This script runs all tests to validate the integration works BEFORE deployment.
# Run this after any code changes to ensure nothing breaks.
#
# Usage:
#   ./test_integration.sh              # Run all tests
#   ./test_integration.sh --quick      # Skip syntax checks (faster)
#   ./test_integration.sh --imports    # Only test imports
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Print functions
print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_skip() {
    echo -e "${YELLOW}⏭️  $1${NC}"
    ((TESTS_SKIPPED++))
}

# Parse arguments
QUICK_MODE=false
IMPORTS_ONLY=false

for arg in "$@"; do
    case $arg in
        --quick)
            QUICK_MODE=true
            ;;
        --imports)
            IMPORTS_ONLY=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./test_integration.sh [--quick] [--imports]"
            exit 1
            ;;
    esac
done

# Main test execution
print_header "AGENTGATEPAY LANGCHAIN INTEGRATION - CI/CD TESTS"

echo "Test mode: $([ "$QUICK_MODE" = true ] && echo "QUICK" || echo "FULL")"
echo "Working directory: $SCRIPT_DIR"
echo ""

# ========================================
# TEST 1: Check Python version
# ========================================

print_header "TEST 1: Python Version"

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Detected Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 12 ]); then
    print_error "Python 3.12+ required, found $PYTHON_VERSION"
    exit 1
else
    print_success "Python version check passed ($PYTHON_VERSION >= 3.12)"
fi

# ========================================
# TEST 2: Check required files exist
# ========================================

print_header "TEST 2: Required Files"

REQUIRED_FILES=(
    "requirements.txt"
    ".env.example"
    ".gitignore"
    "README.md"
    "examples/1_api_basic_payment.py"
    "examples/2a_api_buyer_agent.py"
    "examples/2b_api_seller_agent.py"
    "examples/3_api_with_audit.py"
    "examples/4_mcp_basic_payment.py"
    "docs/API_VS_MCP.md"
    "tests/test_imports.py"
    "tests/test_configuration.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "File exists: $file"
    else
        print_error "File missing: $file"
    fi
done

# ========================================
# TEST 3: Python syntax check
# ========================================

if [ "$QUICK_MODE" = false ]; then
    print_header "TEST 3: Python Syntax Check"

    for py_file in examples/*.py tests/*.py; do
        if python3 -m py_compile "$py_file" 2>/dev/null; then
            print_success "Syntax valid: $py_file"
        else
            print_error "Syntax error: $py_file"
        fi
    done
else
    print_skip "Skipping syntax check (--quick mode)"
fi

# ========================================
# TEST 4: Check for hardcoded secrets
# ========================================

if [ "$QUICK_MODE" = false ]; then
    print_header "TEST 4: Hardcoded Secrets Check"

    SECRETS_FOUND=false

    # Check for patterns that might be secrets
    for py_file in examples/*.py; do
        # Check for pk_live_ followed by actual characters (not placeholders)
        if grep -E "pk_live_[a-f0-9]{32}" "$py_file" | grep -v "YOUR_" | grep -v ".env" > /dev/null 2>&1; then
            print_error "Possible hardcoded API key in $py_file"
            SECRETS_FOUND=true
        fi

        # Check for 0x followed by 64 hex chars (private keys)
        if grep -E "0x[a-f0-9]{64}" "$py_file" | grep -v "YOUR_" | grep -v ".env" | grep -v "# " > /dev/null 2>&1; then
            print_warning "Possible hardcoded private key in $py_file (verify manually)"
        fi
    done

    if [ "$SECRETS_FOUND" = false ]; then
        print_success "No hardcoded secrets detected"
    fi
else
    print_skip "Skipping secrets check (--quick mode)"
fi

# ========================================
# TEST 5: Dependencies check
# ========================================

print_header "TEST 5: Dependencies"

# Check if virtual environment is recommended
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Not running in virtual environment (recommended: python3 -m venv venv)"
fi

# Try to import key dependencies
if python3 -c "import agentgatepay_sdk" 2>/dev/null; then
    SDK_VERSION=$(python3 -c "import agentgatepay_sdk; print(agentgatepay_sdk.__version__)" 2>/dev/null || echo "unknown")
    print_success "agentgatepay-sdk installed (version: $SDK_VERSION)"

    # Check version is >= 1.1.3
    if [ "$SDK_VERSION" != "unknown" ]; then
        MAJOR=$(echo $SDK_VERSION | cut -d. -f1)
        MINOR=$(echo $SDK_VERSION | cut -d. -f2)
        PATCH=$(echo $SDK_VERSION | cut -d. -f3)

        if [ "$MAJOR" -ge 1 ] && [ "$MINOR" -ge 1 ] && [ "$PATCH" -ge 3 ]; then
            print_success "SDK version check passed ($SDK_VERSION >= 1.1.3)"
        else
            print_error "SDK version too old: $SDK_VERSION (requires >= 1.1.3)"
        fi
    fi
else
    print_warning "agentgatepay-sdk not installed (run: pip install -r requirements.txt)"
fi

if [ "$IMPORTS_ONLY" = true ]; then
    print_header "IMPORTS-ONLY MODE: Skipping remaining tests"
    # Skip to summary
else
    # ========================================
    # TEST 6: Pytest unit tests
    # ========================================

    print_header "TEST 6: Unit Tests (pytest)"

    if command -v pytest &> /dev/null; then
        echo "Running pytest..."
        if pytest tests/ -v --tb=short 2>&1 | tee /tmp/pytest_output.txt; then
            print_success "All pytest tests passed"
        else
            print_error "Some pytest tests failed (see output above)"
            cat /tmp/pytest_output.txt
        fi
    else
        print_warning "pytest not installed (run: pip install pytest)"
    fi

    # ========================================
    # TEST 7: Configuration validation
    # ========================================

    print_header "TEST 7: Configuration Validation"

    # Check .env.example has all required vars
    REQUIRED_VARS=(
        "AGENTPAY_API_URL"
        "BUYER_API_KEY"
        "SELLER_API_KEY"
        "BASE_RPC_URL"
        "BUYER_PRIVATE_KEY"
        "BUYER_WALLET"
        "SELLER_WALLET"
        "OPENAI_API_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" .env.example; then
            print_success "Variable in .env.example: $var"
        else
            print_error "Missing variable in .env.example: $var"
        fi
    done

    # ========================================
    # TEST 8: README documentation check
    # ========================================

    print_header "TEST 8: Documentation Check"

    # Check README has key sections
    README_SECTIONS=(
        "Quick Start"
        "Installation"
        "Configuration"
        "Examples"
        "REST API vs MCP"
    )

    for section in "${README_SECTIONS[@]}"; do
        if grep -qi "$section" README.md; then
            print_success "README section exists: $section"
        else
            print_warning "README section missing: $section"
        fi
    done

    # ========================================
    # TEST 9: Example script validation
    # ========================================

    print_header "TEST 9: Example Scripts Validation"

    # Check each example has proper structure
    for py_file in examples/*.py; do
        FILENAME=$(basename "$py_file")

        # Check for shebang
        if head -1 "$py_file" | grep -q "#!/usr/bin/env python3"; then
            print_success "Shebang present: $FILENAME"
        else
            print_error "Missing shebang: $FILENAME"
        fi

        # Check for docstring
        if head -20 "$py_file" | grep -q '"""'; then
            print_success "Docstring present: $FILENAME"
        else
            print_warning "Missing docstring: $FILENAME"
        fi

        # Check uses load_dotenv()
        if grep -q "load_dotenv()" "$py_file"; then
            print_success "Uses load_dotenv(): $FILENAME"
        else
            print_warning "Missing load_dotenv(): $FILENAME"
        fi
    done
fi

# ========================================
# SUMMARY
# ========================================

print_header "TEST SUMMARY"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))

echo "Total tests:   $TOTAL_TESTS"
echo -e "${GREEN}Passed:        $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed:        $TESTS_FAILED${NC}"
fi
if [ $TESTS_SKIPPED -gt 0 ]; then
    echo -e "${YELLOW}Skipped:       $TESTS_SKIPPED${NC}"
fi

echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}✅ ALL TESTS PASSED - Ready to deploy!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    exit 0
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ TESTS FAILED - Fix errors before deploying!${NC}"
    echo -e "${RED}============================================================${NC}"
    exit 1
fi
