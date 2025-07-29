# Telegram Notion Calendar Bot - Test Suite

This directory contains a comprehensive test suite for the Telegram Notion Calendar Bot, following Test-Driven Development (TDD) principles with pytest.

## 📋 Test Coverage

The test suite includes:

- **Unit Tests**: Test individual functions and methods with edge cases
- **Integration Tests**: Test API endpoints and database operations
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Identify bottlenecks and measure response times
- **Security Tests**: Test authentication, authorization, and security vulnerabilities
- **Load Tests**: Test concurrent user scenarios using Locust

## 🚀 Quick Start

### Run All Tests
```bash
./run_all_tests.sh
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e

# Performance tests only
pytest -m performance

# Security tests only
pytest -m security
```

### Run Tests for Specific Modules
```bash
# Test handlers
pytest tests/test_handlers/

# Test services
pytest tests/test_services/

# Test a specific file
pytest tests/test_services/test_combined_appointment_service.py

# Run a specific test
pytest tests/test_handlers/test_enhanced_appointment_handler.py::TestEnhancedAppointmentHandler::test_create_appointment_success
```

## 📊 Test Coverage

The project maintains a minimum test coverage of **80%**.

### Generate Coverage Report
```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser

# XML report for CI/CD
pytest --cov=src --cov-report=xml
```

## 🏗️ Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── factories.py                # Test data factories using factory-boy
├── test_handlers/              # Handler unit tests
├── test_services/              # Service unit tests
├── test_models/                # Model unit tests
├── test_utils/                 # Utility unit tests
├── test_integration/           # Integration tests
├── test_e2e/                   # End-to-end workflow tests
├── test_performance/           # Performance benchmarks
├── test_security/              # Security tests
└── test_load/                  # Load testing with Locust
    ├── locustfile.py
    └── run_load_tests.sh
```

## 🧪 Test Fixtures

The test suite uses factory-boy for creating test data:

```python
# Create a test appointment
appointment = AppointmentFactory(
    title="Test Meeting",
    date=datetime.now() + timedelta(days=1)
)

# Create a test user update
update = TelegramUpdateFactory()

# Create a test Notion page
page = NotionPageFactory()
```

## 🔧 Running Load Tests

Load tests simulate concurrent users and help identify performance bottlenecks.

### Web UI Mode (Interactive)
```bash
cd tests/test_load
./run_load_tests.sh
# Access UI at http://localhost:8089
```

### Headless Mode
```bash
cd tests/test_load
TEST_TYPE=headless USERS=100 RUN_TIME=5m ./run_load_tests.sh
```

### Stress Test Mode
```bash
cd tests/test_load
TEST_TYPE=stress ./run_load_tests.sh
```

### Available Test Types:
- `web`: Interactive web UI
- `headless`: Automated test run
- `stress`: Gradually increase load until failure
- `spike`: Simulate traffic spikes
- `endurance`: Long-running stability test

## 🔒 Security Testing

Security tests check for common vulnerabilities:

- SQL injection prevention
- Command injection prevention
- XSS prevention
- Authentication/authorization
- Rate limiting
- Secure file handling
- API key protection

Run security scans:
```bash
# Bandit security scan
bandit -r src/

# Safety check for dependencies
safety check

# Run security test suite
pytest tests/test_security/
```

## ⚡ Performance Testing

Performance tests measure:

- Response times for API calls
- Database query performance
- Concurrent user handling
- Memory usage
- Caching effectiveness

Run performance benchmarks:
```bash
pytest tests/test_performance/ --benchmark-only
```

## 🤖 CI/CD Integration

The test suite is integrated with GitHub Actions:

1. **On Push/PR**: Run unit, integration, and E2E tests
2. **Daily**: Run full test suite including load tests
3. **Coverage Check**: Enforce 80% minimum coverage
4. **Security Scans**: Automated vulnerability scanning

## 🎯 Test Patterns

### AAA Pattern (Arrange-Act-Assert)
```python
@pytest.mark.asyncio
async def test_create_appointment(self, service):
    # Arrange
    user_id = 123456
    text = "Meeting tomorrow at 3pm"
    
    # Act
    result = await service.create_appointment_from_text(user_id, text)
    
    # Assert
    assert result.title == "Meeting"
    assert result.date.hour == 15
```

### Mocking External Services
```python
@pytest.mark.asyncio
async def test_with_mocked_notion(self, mock_notion_client):
    # Mock Notion API response
    mock_notion_client.pages.create = AsyncMock(
        return_value={"id": "page_123"}
    )
    
    # Test your code that uses Notion
    result = await service.create_page()
    assert result["id"] == "page_123"
```

### Time-based Testing
```python
from freezegun import freeze_time

@freeze_time("2024-01-15 10:00:00")
def test_time_sensitive_feature():
    # Test with fixed time
    appointment = create_appointment("Today at 2pm")
    assert appointment.date.hour == 14
```

## 📝 Writing New Tests

1. **Choose the appropriate test type**:
   - Unit test for isolated functions
   - Integration test for component interactions
   - E2E test for user workflows

2. **Use the appropriate marker**:
   ```python
   @pytest.mark.unit
   @pytest.mark.integration
   @pytest.mark.e2e
   @pytest.mark.performance
   @pytest.mark.security
   ```

3. **Use factories for test data**:
   ```python
   appointment = AppointmentFactory()
   user = UserConfigFactory()
   ```

4. **Mock external dependencies**:
   ```python
   with patch('module.external_service') as mock:
       mock.return_value = expected_response
       # Test your code
   ```

5. **Test edge cases**:
   - Empty inputs
   - Invalid data
   - Boundary conditions
   - Error scenarios
   - Concurrent access

## 🐛 Debugging Tests

### Run tests with verbose output
```bash
pytest -vv tests/

# With print statements
pytest -s tests/

# Stop on first failure
pytest -x tests/

# Run only failed tests
pytest --lf tests/

# Run tests matching pattern
pytest -k "appointment" tests/
```

### Debug with pdb
```python
def test_complex_logic():
    import pdb; pdb.set_trace()
    # Test code here
```

## 📈 Test Metrics

Monitor test health with:

- **Test execution time**: Keep tests fast (< 1s for unit tests)
- **Coverage percentage**: Maintain > 80%
- **Flaky test detection**: Fix intermittent failures
- **Test complexity**: Keep tests simple and focused

## 🔄 Continuous Improvement

1. **Add tests for new features** before implementation
2. **Update tests** when requirements change
3. **Refactor tests** to reduce duplication
4. **Monitor test performance** and optimize slow tests
5. **Review test coverage** reports regularly

## 🤝 Contributing

When contributing tests:

1. Follow the existing test structure
2. Use descriptive test names
3. Include docstrings for complex tests
4. Test both success and failure cases
5. Ensure tests are deterministic (not flaky)
6. Run the full test suite before submitting

## 📚 Resources

- [pytest documentation](https://docs.pytest.org/)
- [factory-boy documentation](https://factoryboy.readthedocs.io/)
- [Locust documentation](https://docs.locust.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)