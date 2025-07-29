# Test Coverage Fix Documentation

## Problem
The test coverage was showing 0% in some cases, despite having tests in the project.

## Root Causes Identified

1. **Missing Test Dependencies**
   - `factory-boy` - Required by tests/factories.py
   - `freezegun` - Required for time-based test fixtures
   - `pyjwt` - Required by security tests
   - `pytest-benchmark` - Required by performance tests

2. **Configuration Issues**
   - Missing `.coveragerc` file for proper coverage configuration
   - Conflicting coverage settings in `pytest.ini`

3. **Python Path Issues**
   - PYTHONPATH not properly set in test scripts

## Solution Implemented

### 1. Installed Missing Dependencies
```bash
pip install factory-boy freezegun pyjwt pytest-benchmark
```

### 2. Created `.coveragerc` Configuration
```ini
[run]
source = src
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */env/*
    */.venv/*

[report]
precision = 2
skip_covered = False
show_missing = True
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__.:
    raise AssertionError
    raise NotImplementedError
    if 0:
    if False:
    if TYPE_CHECKING:

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

### 3. Updated `pytest.ini`
Removed conflicting coverage options from addopts to prevent double configuration:
```ini
# Coverage options
addopts = 
    --verbose
    --strict-markers
    --tb=short
```

### 4. Updated Test Scripts
- Fixed PYTHONPATH in `run_tests.sh`
- Added COVERAGE_CORE=sysmon for better coverage tracking
- Updated coverage report commands to include XML output

## Current Coverage Status

After fixes, the coverage correctly reports:
- **Total Coverage**: ~18% (3749 statements, 3075 missing)
- Coverage is working correctly but low due to limited test coverage
- Key areas with coverage:
  - `src/models/appointment.py`: 25%
  - `src/models/memo.py`: 26.37%
  - `src/utils/error_handler.py`: 34.65%
  - `src/utils/log_sanitizer.py`: 96.77%

## Running Tests with Coverage

### Basic Coverage Run
```bash
source venv/bin/activate
pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
```

### Using Test Scripts
```bash
# Run with coverage report
./run_tests.sh coverage

# Run all test suites with coverage
./run_all_tests.sh
```

### Viewing Coverage Reports
- **Terminal**: Shows immediately after test run
- **HTML Report**: Open `htmlcov/index.html` in browser
- **XML Report**: `coverage.xml` for CI/CD integration

## Next Steps

To improve coverage from 18% to 80%+:
1. Write unit tests for all service classes (currently 0% coverage)
2. Add tests for handlers (currently 0-16% coverage)
3. Complete tests for utility modules
4. Add integration tests for main bot functionality
5. Implement E2E tests for complete workflows

## Troubleshooting

If coverage shows 0% again:
1. Check all dependencies are installed: `pip install -r requirements.txt`
2. Ensure virtual environment is activated
3. Verify `.coveragerc` exists and is properly configured
4. Run with explicit coverage config: `pytest --cov=src --cov-config=.coveragerc`
5. Check for pytest/pytest-asyncio version conflicts