---
skill_id: webapp-testing
type: skill
domain_tags: [testing, automation, web, e2e, playwright, development, qa]
scope: global
stack_context: [python, javascript, typescript, web]
created: 2026-02-22
last_used: 2026-02-22
reuse_count: 0
project_origin: anthropic-skills
status: active
verified_by: human
---

# Web Application Testing

## Key Insight

Test local web applications using native Python Playwright scripts. Use bundled helper scripts to manage server lifecycle and simplify automation workflows.

## Trigger

When you need to:
- Test local web applications programmatically
- Automate browser interactions for E2E testing
- Start and manage development servers during testing
- Inspect and interact with dynamic web applications
- Write automated tests for web UI components

## Decision Tree: Choosing Your Approach

```
User task → Is it static HTML?
    ├─ Yes → Read HTML file directly to identify selectors
    │         ├─ Success → Write Playwright script using selectors
    │         └─ Fails/Incomplete → Treat as dynamic (below)
    │
    └─ No (dynamic webapp) → Is the server already running?
        ├─ No → Run: python scripts/with_server.py --help
        │        Then use the helper + write simplified Playwright script
        │
        └─ Yes → Reconnaissance-then-action:
            1. Navigate and wait for networkidle
            2. Take screenshot or inspect DOM
            3. Identify selectors from rendered state
            4. Execute actions with discovered selectors
```

## Quick Start

### Using with_server.py (Server Management)

**Always run with --help first:**

```bash
python scripts/with_server.py --help
```

**Single server:**
```bash
python scripts/with_server.py \
  --server "npm run dev" \
  --port 5173 \
  -- python your_automation.py
```

**Multiple servers (backend + frontend):**
```bash
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

### Automation Script Template

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Always launch chromium in headless mode
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Server already running and ready (managed by with_server.py)
    page.goto('http://localhost:5173')
    
    # CRITICAL: Wait for JS to execute
    page.wait_for_load_state('networkidle')
    
    # ... your automation logic
    
    browser.close()
```

## Reconnaissance-Then-Action Pattern

### Step 1: Inspect rendered DOM

```python
# Take screenshot for visual inspection
page.screenshot(path='/tmp/inspect.png', full_page=True)

# Get page content
content = page.content()

# Find all buttons
buttons = page.locator('button').all()
```

### Step 2: Identify selectors from inspection

```python
# Using text selectors
page.locator('text=Submit').click()

# Using role selectors
page.locator('role=button[name="Submit form"]').click()

# Using CSS selectors
page.locator('.submit-button').click()

# Using IDs
page.locator('#submit-btn').click()
```

### Step 3: Execute actions

```python
# Fill form
page.locator('input[name="email"]').fill('test@example.com')

# Click button
page.locator('button[type="submit"]').click()

# Wait for navigation
page.wait_for_load_state('networkidle')

# Assert result
assert page.url == 'http://localhost:5173/success'
```

## Common Pitfall (AVOID THIS)

❌ **Don't inspect the DOM before waiting for networkidle on dynamic apps:**

```python
# WRONG - May get empty or incomplete DOM
page.goto('http://localhost:5173')
content = page.content()  # Too early!
```

✅ **Do wait for page.wait_for_load_state('networkidle') before inspection:**

```python
# CORRECT - Wait for JavaScript to execute
page.goto('http://localhost:5173')
page.wait_for_load_state('networkidle')  # Critical!
content = page.content()  # Now DOM is fully rendered
```

## Best Practices

### Use Bundled Scripts as Black Boxes

- Consider whether scripts in `scripts/` can help accomplish a task
- These handle common, complex workflows reliably
- Use `--help` to see usage, then invoke directly
- Don't read source unless absolutely necessary (scripts can be large)

### Playwright Patterns

**Use sync_playwright() for synchronous scripts:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # ... automation logic
    browser.close()
```

**Always close the browser when done:**
```python
browser.close()
```

**Use descriptive selectors:**
```python
# Good - clear intent
page.locator('text=Submit').click()
page.locator('role=button[name="Add to cart"]').click()
page.locator('#user-email').fill('test@example.com')

# Avoid - brittle selectors
page.locator('div > div:nth-child(3) > button').click()
```

**Add appropriate waits:**
```python
# Wait for element to appear
page.wait_for_selector('.loading-spinner', state='hidden')

# Wait for specific state
page.wait_for_load_state('networkidle')

# Wait with timeout
page.wait_for_selector('.result', timeout=10000)
```

## Example Patterns

### Testing Form Submission

```python
from playwright.sync_api import sync_playwright

def test_form_submission():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto('http://localhost:5173/contact')
        page.wait_for_load_state('networkidle')
        
        # Fill form
        page.locator('input[name="name"]').fill('John Doe')
        page.locator('input[name="email"]').fill('john@example.com')
        page.locator('textarea[name="message"]').fill('Test message')
        
        # Submit
        page.locator('button[type="submit"]').click()
        
        # Wait for success
        page.wait_for_selector('.success-message')
        
        browser.close()

if __name__ == '__main__':
    test_form_submission()
```

### Testing User Flow

```python
def test_checkout_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to shop
        page.goto('http://localhost:5173/shop')
        page.wait_for_load_state('networkidle')
        
        # Add item to cart
        page.locator('text=Add to Cart').first.click()
        page.wait_for_selector('.cart-count', text='1')
        
        # Go to checkout
        page.locator('text=Checkout').click()
        page.wait_for_load_state('networkidle')
        
        # Fill payment info
        page.locator('input[name="card-number"]').fill('4242424242424242')
        page.locator('input[name="expiry"]').fill('12/25')
        page.locator('input[name="cvc"]').fill('123')
        
        # Complete purchase
        page.locator('text=Complete Purchase').click()
        page.wait_for_selector('.order-confirmation')
        
        browser.close()
```

### Capturing Console Logs

```python
def test_with_console_logging():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Capture console logs
        logs = []
        page.on('console', lambda msg: logs.append(msg.text))
        
        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')
        
        # Check for errors
        errors = [log for log in logs if 'error' in log.lower()]
        assert len(errors) == 0, f"Console errors found: {errors}"
        
        browser.close()
```

## Testing Checklist

### Before Writing Tests

- [ ] Identify if app is static HTML or dynamic JavaScript
- [ ] Check if server needs to be started
- [ ] Determine test scope (single feature vs full flow)
- [ ] Identify critical user paths to test

### Test Implementation

- [ ] Use `with_server.py` for automatic server management
- [ ] Wait for `networkidle` before inspecting dynamic content
- [ ] Use clear, descriptive selectors
- [ ] Add appropriate waits for async operations
- [ ] Always close browser in cleanup

### Assertions

- [ ] Verify page URL after navigation
- [ ] Check element visibility and text content
- [ ] Validate form submissions succeed
- [ ] Confirm error states handled correctly
- [ ] Test responsive behavior if applicable

## Troubleshooting

### Server Won't Start

```bash
# Check port availability
lsof -i :5173

# Use different port
python scripts/with_server.py \
  --server "npm run dev -- --port 5174" \
  --port 5174 \
  -- python test.py
```

### Elements Not Found

```python
# Add debug screenshot
page.screenshot(path='/tmp/debug.png', full_page=True)

# Log page content
print(page.content())

# Try different wait strategies
page.wait_for_load_state('domcontentloaded')  # Basic DOM ready
page.wait_for_load_state('networkidle')       # All network requests done
page.wait_for_timeout(1000)                   # Explicit wait (last resort)
```

### Flaky Tests

```python
# Use auto-retry for flaky elements
page.locator('.dynamic-element').click(timeout=10000)

# Wait for element to be stable
page.wait_for_selector('.element', state='visible')
page.wait_for_selector('.element', state='stable')

# Retry pattern
for attempt in range(3):
    try:
        page.locator('.element').click()
        break
    except TimeoutError:
        if attempt == 2:
            raise
        page.wait_for_timeout(1000)
```

## Reference Files

**Examples available in `examples/` directory:**

- `element_discovery.py` - Discovering buttons, links, and inputs on a page
- `static_html_automation.py` - Using file:// URLs for local HTML
- `console_logging.py` - Capturing console logs during automation

## Integration with CI/CD

```yaml
# .github/workflows/test.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Playwright
        run: |
          pip install playwright
          playwright install chromium
      
      - name: Run E2E Tests
        run: |
          python scripts/with_server.py \
            --server "npm run dev" \
            --port 5173 \
            -- pytest e2e/
```

## Source

Originally from [Anthropic Skills](https://skills.sh/anthropics/skills/webapp-testing)
Weekly Installs: 12.9K
