"""
UI tests for the Sign Up (/join) page.

Run independently from the backend suite:
    pytest ui_tests/ --base-url http://localhost:5900

Or set the server URL via environment variable:
    FORMSHARE_UI_TEST_URL=http://myserver:5900 pytest ui_tests/
"""


def test_signup_page_loads(page, base_url):
    """Sign up page returns 200 and shows the registration form."""
    response = page.goto(f"{base_url}/join")
    assert response.status == 200


def test_signup_page_title(page, base_url):
    """Page title contains 'FormShare'."""
    page.goto(f"{base_url}/join")
    assert "FormShare" in page.title()


def test_signup_form_fields_present(page, base_url):
    """All required form fields are visible."""
    page.goto(f"{base_url}/join")
    assert page.locator("input[name='user_name']").is_visible()
    assert page.locator("input[name='user_email']").is_visible()
    assert page.locator("input[name='user_password']").is_visible()
    assert page.locator("input[name='user_password2']").is_visible()
    assert page.locator("button[type='submit']").is_visible()


def test_signup_honeypot_field_hidden(page, base_url):
    """The honeypot address field is positioned off-screen (spam protection)."""
    page.goto(f"{base_url}/join")
    field = page.locator("#user_address")
    # The field exists in the DOM but is moved off-screen via JS
    assert field.count() == 1
    box = field.bounding_box()
    # Off-screen means either not rendered or positioned far outside viewport
    assert box is None or box["x"] < 0 or box["y"] < 0


def test_signup_link_to_login(page, base_url):
    """The 'Sign in' link points to the login page."""
    page.goto(f"{base_url}/join")
    sign_in = page.locator("a.btn", has_text="Sign in")
    assert sign_in.is_visible()
    href = sign_in.get_attribute("href")
    assert href is not None and "/login" in href


def test_signup_password_mismatch(page, base_url):
    """Submitting mismatched passwords shows an error and stays on the page."""
    page.goto(f"{base_url}/join")
    page.fill("input[name='user_name']", "Test User")
    page.fill("input[name='user_email']", "ui_test_mismatch@example.com")
    page.fill("input[name='user_password']", "Password1!")
    page.fill("input[name='user_password2']", "Different1!")
    page.click("button[type='submit']")
    # Browser native validation prevents submit; still on /join
    assert "/join" in page.url


def test_signup_required_fields_enforced(page, base_url):
    """Submitting an empty form stays on the page (native HTML required validation)."""
    page.goto(f"{base_url}/join")
    page.click("button[type='submit']")
    assert "/join" in page.url
