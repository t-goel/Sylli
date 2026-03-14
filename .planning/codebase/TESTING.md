# Testing Patterns

**Analysis Date:** 2026-03-13

## Test Framework

**Runner:**
- pytest (specified in `/Users/tanmaygoel/CS/Sylli/tests/requirements.txt`)
- Version: Not pinned; latest version installed
- Config: No pytest.ini or pyproject.toml configuration file found; uses defaults

**Assertion Library:**
- Built-in pytest assertions: `assert response.status_code == 200`

**Run Commands:**
```bash
pytest tests/unit/                    # Run unit tests
pytest tests/integration/             # Run integration tests
pytest tests/                         # Run all tests
pytest -v                             # Run with verbose output
pytest --tb=short                     # Run with short traceback
```

## Test File Organization

**Location:**
- Co-located in separate `tests/` directory, not alongside source code
- Directory structure mirrors source: `tests/unit/`, `tests/integration/`
- Test files not in same directory as source files (`backend/`, `hello_world/`)

**Naming:**
- Pattern: `test_*.py` for test files: `test_handler.py`, `test_api_gateway.py`
- Pattern follows pytest conventions

**Structure:**
```
tests/
├── __init__.py              # Empty init file
├── unit/                    # Unit test directory
│   ├── __init__.py         # Empty init file
│   └── test_handler.py     # Lambda handler tests
├── integration/             # Integration test directory
│   ├── __init__.py         # Empty init file
│   └── test_api_gateway.py # End-to-end API tests
└── requirements.txt        # Test dependencies
```

## Test Structure

**Suite Organization:**
```python
# From tests/unit/test_handler.py
@pytest.fixture()
def apigw_event():
    """Generates API GW Event"""
    return {
        "body": '{ "test": "body"}',
        # ... event structure
    }

def test_lambda_handler(apigw_event):
    ret = app.lambda_handler(apigw_event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
    assert data["message"] == "hello world"
```

**Patterns:**
- Setup using pytest fixtures: `@pytest.fixture()` decorator
- Fixture injected as function parameter: `def test_lambda_handler(apigw_event):`
- Fixtures return complex test data structures (API Gateway events)
- Assertions use simple `assert` statements with direct equality checks

## Mocking

**Framework:** Not explicitly used in current tests; boto3 clients not mocked

**Patterns:**
```python
# Current pattern: No mocking
# Integration test makes real AWS calls via boto3
class TestApiGateway:
    @pytest.fixture()
    def api_gateway_url(self):
        client = boto3.client("cloudformation")
        response = client.describe_stacks(StackName=stack_name)
        # ... extract URL from CloudFormation outputs
```

**What to Mock:**
- AWS service calls (boto3 clients): bedrock, dynamodb, s3
- External HTTP requests: Bedrock API calls should be mocked in unit tests
- File operations: Mock file uploads in unit tests

**What NOT to Mock:**
- FastAPI request/response handling
- Internal service layer logic
- Business logic transformations

## Fixtures and Factories

**Test Data:**
```python
# From tests/unit/test_handler.py - fixture for API Gateway event
@pytest.fixture()
def apigw_event():
    """Generates API GW Event"""
    return {
        "body": '{ "test": "body"}',
        "resource": "/{proxy+}",
        "requestContext": { ... },
        "queryStringParameters": {"foo": "bar"},
        "headers": { ... },
        "pathParameters": {"proxy": "/examplepath"},
        "httpMethod": "POST",
        "stageVariables": {"baz": "qux"},
        "path": "/examplepath",
    }
```

**Location:**
- Fixtures defined in same test file: `tests/unit/test_handler.py` and `tests/integration/test_api_gateway.py`
- No conftest.py; fixtures are file-scoped, not shared across test modules

## Coverage

**Requirements:** No coverage requirements found; not enforced in codebase

**View Coverage:**
```bash
pytest --cov=backend --cov=hello_world --cov-report=html
```

## Test Types

**Unit Tests:**
- Location: `tests/unit/test_handler.py`
- Scope: Lambda handler function testing
- Approach: Direct function call with fixture-provided AWS Lambda Proxy Input event
- Tests response structure and message content
- Scope limited to single handler function; service layer not currently tested

**Integration Tests:**
- Location: `tests/integration/test_api_gateway.py`
- Scope: Full API Gateway + Lambda integration
- Approach: Real AWS CloudFormation stack queries and HTTP requests to deployed API
- Requires `AWS_SAM_STACK_NAME` environment variable to locate deployed stack
- Makes actual HTTP requests: `requests.get(api_gateway_url)`
- Requires deployed infrastructure; not suitable for local CI/CD without SAM deployment

**E2E Tests:**
- Framework: Not explicitly separated
- Integration tests function as E2E tests for Lambda/API Gateway layer

## Common Patterns

**Async Testing:**
- Current tests don't test async functions directly
- FastAPI async routes tested via HTTP requests in integration tests
- No pytest-asyncio configuration found; async testing not yet implemented for service layer

**Error Testing:**
```python
# From tests/integration/test_api_gateway.py
# Error handling through environment variable validation
if stack_name is None:
    raise ValueError('Please set the AWS_SAM_STACK_NAME environment variable...')

# Error handling for CloudFormation stack lookup
try:
    response = client.describe_stacks(StackName=stack_name)
except Exception as e:
    raise Exception(f"Cannot find stack {stack_name}...") from e
```

## Test Dependencies

**Installed:**
- pytest: Test runner
- boto3: AWS service client testing
- requests: HTTP testing for API Gateway integration tests

**Missing:**
- pytest-asyncio: For testing async functions (services layer)
- moto: For mocking AWS services locally
- httpx or TestClient: For testing FastAPI without actual deployment

## Coverage Gaps

**Not Tested:**
- Service layer functions: `upload_syllabus_to_s3()`, `fetch_syllabus()`, `parse_syllabus_with_bedrock()`, `store_syllabus()`, `get_syllabus()`
- Router layer validation: File extension checking, error handling in syllabus router
- Bedrock API integration: Mocking Claude responses
- DynamoDB operations: Mock table operations
- S3 operations: Mock file upload and storage
- Health check endpoint

**Recommendation:**
- Add unit tests for service layer with mocked AWS services
- Add tests for router-level validation logic
- Use moto for local AWS service mocking in development
- Add async test support with pytest-asyncio

---

*Testing analysis: 2026-03-13*
