import os
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=os.environ.get("FORMSHARE_UI_TEST_URL", "http://localhost:5900"),
        help="Base URL of the running FormShare server (default: http://localhost:5900 "
        "or FORMSHARE_UI_TEST_URL env var)",
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    return pytestconfig.getoption("--base-url").rstrip("/")
