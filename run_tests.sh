#!/bin/bash
# Test runner script for the Telegram Notion Calendar Bot

echo "🧪 Running tests for Telegram Notion Calendar Bot..."
echo "=================================================="

# Set environment variables for testing
export PYTHONPATH="$(pwd):$(pwd)/src"
export DEBUG=true
export LOG_LEVEL=DEBUG

# Set coverage environment variables
export COVERAGE_CORE=sysmon

# Create test environment file if it doesn't exist
if [ ! -f .env.test ]; then
    echo "Creating .env.test file..."
    cat > .env.test << EOF
# Test environment configuration
TELEGRAM_BOT_TOKEN=test_bot_token
OPENAI_API_KEY=test_openai_key
DEBUG=true
LOG_LEVEL=DEBUG
EOF
fi

# Load test environment
export $(cat .env.test | grep -v '^#' | xargs)

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "   Consider activating a virtual environment before running tests."
    echo ""
fi

# Install test dependencies if needed
echo "📦 Checking dependencies..."
pip install -q pytest pytest-asyncio pytest-mock pytest-cov

# Run different test suites based on argument
case "$1" in
    "unit")
        echo "🔍 Running unit tests only..."
        pytest tests/ -m "not integration" -v
        ;;
    "integration")
        echo "🔗 Running integration tests only..."
        pytest tests/ -m "integration" -v
        ;;
    "coverage")
        echo "📊 Running tests with coverage report..."
        pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
        echo ""
        echo "📄 Coverage report generated in htmlcov/index.html"
        ;;
    "quick")
        echo "⚡ Running quick tests (no coverage)..."
        pytest tests/ -x --tb=short
        ;;
    "memo")
        echo "📝 Running memo-related tests..."
        pytest tests/test_memo_*.py tests/test_ai_assistant_service.py -v
        ;;
    "sync")
        echo "🔄 Running sync-related tests..."
        pytest tests/test_partner_sync_service.py -v
        ;;
    "watch")
        echo "👀 Running tests in watch mode..."
        echo "   (Install pytest-watch: pip install pytest-watch)"
        ptw tests/ -- -x --tb=short --no-cov
        ;;
    *)
        echo "🧪 Running all tests..."
        pytest tests/ -v
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi