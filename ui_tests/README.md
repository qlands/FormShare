# FormShare UI Tests

Browser-based UI tests using [Playwright for Python](https://playwright.dev/python/).
These are **separate** from the backend pytest suite and must be run manually.

## Setup (one time)

```bash
pip install pytest-playwright
playwright install chromium
```

## Running

Start the FormShare development server first, then:

```bash
# Default — assumes server is at http://localhost:5900
pytest ui_tests/

# Custom server URL
pytest ui_tests/ --base-url http://192.168.0.12:5900

# Or via environment variable
FORMSHARE_UI_TEST_URL=http://192.168.0.12:5900 pytest ui_tests/

# Headed mode (watch the browser)
pytest ui_tests/ --headed

# Slow motion (useful for demos/debugging)
pytest ui_tests/ --headed --slowmo 500

# Save a trace for failures
pytest ui_tests/ --tracing on
```

## Test files

| File | Coverage |
|---|---|
| `test_signup.py` | `/join` sign-up page |

## Adding new tests

Create a new `test_<feature>.py` file in this directory.
The `page` fixture (Playwright browser page) and `base_url` fixture are available to all tests automatically.
