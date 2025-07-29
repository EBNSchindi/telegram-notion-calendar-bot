#!/bin/bash

# Comprehensive test runner for Telegram Notion Calendar Bot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_CMD=${PYTHON_CMD:-python3}
MIN_COVERAGE=${MIN_COVERAGE:-80}
PARALLEL=${PARALLEL:-auto}

# Print header
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Telegram Notion Calendar Bot Test Suite  ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
$PYTHON_CMD --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Install test-specific dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install factory-boy freezegun pyjwt pytest-benchmark || true

# Create test results directory
mkdir -p test-results
mkdir -p htmlcov

# Function to run tests
run_test_suite() {
    local test_name=$1
    local test_path=$2
    local test_marker=$3
    
    echo ""
    echo -e "${BLUE}Running $test_name...${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -z "$test_marker" ]; then
        pytest $test_path \
            -v \
            --tb=short \
            --cov=src \
            --cov-append \
            --junit-xml=test-results/${test_name// /-}-results.xml \
            -n $PARALLEL
    else
        pytest $test_path \
            -v \
            -m $test_marker \
            --tb=short \
            --cov=src \
            --cov-append \
            --junit-xml=test-results/${test_name// /-}-results.xml \
            -n $PARALLEL
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        FAILED_TESTS+=("$test_name")
    fi
}

# Initialize failed tests array
FAILED_TESTS=()

# Set Python path
export PYTHONPATH="$(pwd):$(pwd)/src"
export COVERAGE_CORE=sysmon

# Clear previous coverage data
coverage erase

# Run all test suites
echo ""
echo -e "${BLUE}Starting test execution...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Unit Tests
run_test_suite "Unit Tests" "tests/test_handlers tests/test_services tests/test_models tests/test_utils" "unit"

# 2. Integration Tests
run_test_suite "Integration Tests" "tests/test_integration" "integration"

# 3. End-to-End Tests
run_test_suite "E2E Tests" "tests/test_e2e" "e2e"

# 4. Performance Tests
run_test_suite "Performance Tests" "tests/test_performance" "performance"

# 5. Security Tests
run_test_suite "Security Tests" "tests/test_security" "security"

# 6. Error Handling Tests
echo ""
echo -e "${BLUE}Running Error Handling Tests...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pytest tests/ -k "error" -v --tb=short --junit-xml=test-results/error-handling-results.xml

# Generate coverage report
echo ""
echo -e "${BLUE}Generating coverage report...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

coverage report --skip-covered --show-missing
coverage html
coverage xml

# Check coverage threshold
COVERAGE_PERCENT=$(coverage report | grep TOTAL | awk '{print $NF}' | sed 's/%//')

if [ ! -z "$COVERAGE_PERCENT" ]; then
    if (( $(echo "$COVERAGE_PERCENT >= $MIN_COVERAGE" | bc -l) )); then
        echo -e "${GREEN}✓ Coverage check passed: ${COVERAGE_PERCENT}% (minimum: ${MIN_COVERAGE}%)${NC}"
    else
        echo -e "${RED}✗ Coverage check failed: ${COVERAGE_PERCENT}% (minimum: ${MIN_COVERAGE}%)${NC}"
        FAILED_TESTS+=("Coverage Check")
    fi
fi

# Run security scans
echo ""
echo -e "${BLUE}Running security scans...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Bandit security scan
echo -e "${YELLOW}Running Bandit...${NC}"
bandit -r src/ -f json -o test-results/bandit-report.json || true
bandit -r src/ -f txt

# Safety check
echo -e "${YELLOW}Running Safety check...${NC}"
safety check --json --output test-results/safety-report.json || true
safety check

# Type checking with mypy
echo ""
echo -e "${BLUE}Running type checking...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
mypy src/ --ignore-missing-imports --junit-xml test-results/mypy-results.xml || true

# Linting
echo ""
echo -e "${BLUE}Running linters...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Flake8
echo -e "${YELLOW}Running flake8...${NC}"
flake8 src/ tests/ --count --statistics --output-file=test-results/flake8-report.txt || true

# Black formatting check
echo -e "${YELLOW}Checking code formatting with black...${NC}"
black --check src/ tests/ || echo -e "${YELLOW}Some files need formatting${NC}"

# isort import sorting check
echo -e "${YELLOW}Checking import sorting with isort...${NC}"
isort --check-only src/ tests/ || echo -e "${YELLOW}Some imports need sorting${NC}"

# Summary
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}              Test Summary                  ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Count test results
TOTAL_TESTS=$(find test-results -name "*.xml" -exec grep -h "tests=" {} \; | grep -oP 'tests="\K[0-9]+' | awk '{s+=$1} END {print s}')
FAILED_COUNT=$(find test-results -name "*.xml" -exec grep -h "failures=" {} \; | grep -oP 'failures="\K[0-9]+' | awk '{s+=$1} END {print s}')
ERROR_COUNT=$(find test-results -name "*.xml" -exec grep -h "errors=" {} \; | grep -oP 'errors="\K[0-9]+' | awk '{s+=$1} END {print s}')

echo "Total tests run: ${TOTAL_TESTS:-0}"
echo "Failures: ${FAILED_COUNT:-0}"
echo "Errors: ${ERROR_COUNT:-0}"
echo "Coverage: ${COVERAGE_PERCENT:-N/A}%"
echo ""

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All test suites passed!${NC}"
    echo ""
    echo "Reports generated:"
    echo "- HTML Coverage Report: htmlcov/index.html"
    echo "- XML Coverage Report: coverage.xml"
    echo "- JUnit Test Results: test-results/*.xml"
    echo "- Security Reports: test-results/*-report.json"
    exit 0
else
    echo -e "${RED}✗ The following test suites failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  - $test${NC}"
    done
    exit 1
fi