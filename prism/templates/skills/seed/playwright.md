---
skill_id: playwright
type: skill
domain_tags: [testing, automation, frontend, browser, e2e, debugging, web]
scope: global
stack_context: [python, javascript, typescript, web]
created: 2026-02-22
last_used: 2026-02-22
reuse_count: 0
project_origin: claude-code-skills
status: active
verified_by: human
---

# Playwright

## Key Insight

Browser automation tool for programmatically inspecting, testing, and interacting with web pages. Essential for debugging frontend issues, testing accessibility, capturing screenshots, and analyzing DOM structure.

## Trigger

Use when you need to:
- Inspect DOM structure and element layout
- Capture screenshots of web pages
- Test page accessibility programmatically
- Automate browser interactions
- Debug frontend rendering issues
- Analyze page styles and positioning
- Run automated tests on web applications
- Check element visibility and positioning

## Installation

```bash
pip install playwright
playwright install chromium
```

## Quick Start

### Inspect Page DOM and Layout

```bash
python scripts/inspect_page.py http://localhost:3000
python scripts/inspect_page.py http://localhost:3000 ".navbar"
```

Returns JSON with:
- Element tag, text, className, id
- Position (x, y, width, height)
- Computed styles (display, position, z-index, margin, padding, colors)

### Capture Screenshots

```bash
python scripts/screenshot.py http://localhost:3000 screenshot.png
python scripts/screenshot.py http://localhost:3000 screenshot.png 1280x720
```

### Test Accessibility

```bash
python scripts/accessibility.py http://localhost:3000
```

Returns JSON with accessibility violations (missing labels, alt text, etc.)

## Common Patterns

### Inspect Element Position and Styles

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto(url)
    
    # Get bounding box
    box = page.query_selector(selector).bounding_box()
    # Returns: {'x': 0, 'y': 0, 'width': 100, 'height': 50}
    
    # Get computed styles
    styles = page.query_selector(selector).evaluate('el => window.getComputedStyle(el)')
    # Returns: CSSStyleDeclaration object
    
    browser.close()
```

### Extract DOM Structure

```python
# Get all interactive elements
elements = page.query_selector_all('button, a, input, [role="button"]')

# For each element
for el in elements:
    text = el.text_content()
    class_name = el.get_attribute('class')
    id = el.get_attribute('id')
    box = el.bounding_box()
```

### Test Element Visibility

```python
# Check if element is visible
is_visible = page.is_visible(selector)

# Check if element is in viewport
is_in_viewport = page.evaluate('''el => { 
    const rect = el.getBoundingClientRect(); 
    return rect.top >= 0 && rect.left >= 0; 
}''', element)
```

### Get Page State

```python
# Page title
title = page.title()

# Page URL
url = page.url

# Get console errors
errors = []
page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
```

## Debugging Layout Issues

### Check Overlapping Elements

```python
# Find elements that overlap with target
target = page.query_selector('.target').bounding_box()

others = page.query_selector_all('*')
overlaps = []

for el in others:
    box = el.bounding_box()
    if box and target:
        # Check overlap
        if (box['x'] < target['x'] + target['width'] and
            box['x'] + box['width'] > target['x'] and
            box['y'] < target['y'] + target['height'] and
            box['y'] + box['height'] > target['y']):
            overlaps.append(el)
```

### Check Z-Index Stacking

```python
def get_z_index(element):
    styles = element.evaluate('el => window.getComputedStyle(el)')
    return int(styles['z-index']) if styles['z-index'] != 'auto' else 0

# Get z-index order of overlapping elements
elements_with_z = [(el, get_z_index(el)) for el in overlapping_elements]
elements_with_z.sort(key=lambda x: x[1], reverse=True)
```

## Best Practices

- **Headless Mode**: Use headless mode by default for efficiency
- **Custom Viewport**: Customize viewport size for responsive testing
- **Wait for Network Idle**: Scripts wait for network idle before capturing data
- **Standalone Scripts**: Scripts are standalone and can be executed directly

## Script Examples

### inspect_page.py
```python
#!/usr/bin/env python3
"""Inspect page DOM and layout."""
import sys
import json
from playwright.sync_api import sync_playwright

def inspect_page(url, selector=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle')
        
        if selector:
            elements = page.query_selector_all(selector)
        else:
            elements = page.query_selector_all('body *')
        
        results = []
        for el in elements[:100]:  # Limit to first 100
            box = el.bounding_box()
            if box:
                results.append({
                    'tag': el.evaluate('el => el.tagName.toLowerCase()'),
                    'text': el.text_content()[:50],
                    'id': el.get_attribute('id'),
                    'class': el.get_attribute('class'),
                    'position': box,
                })
        
        browser.close()
        return results

if __name__ == '__main__':
    url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(inspect_page(url, selector), indent=2))
```

### screenshot.py
```python
#!/usr/bin/env python3
"""Capture page screenshot."""
import sys
from playwright.sync_api import sync_playwright

def capture_screenshot(url, output_path, viewport=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        if viewport:
            width, height = map(int, viewport.split('x'))
            page = browser.new_page(viewport={'width': width, 'height': height})
        else:
            page = browser.new_page()
        
        page.goto(url, wait_until='networkidle')
        page.screenshot(path=output_path, full_page=True)
        browser.close()
        print(f"Screenshot saved to {output_path}")

if __name__ == '__main__':
    url = sys.argv[1]
    output = sys.argv[2]
    viewport = sys.argv[3] if len(sys.argv) > 3 else None
    capture_screenshot(url, output, viewport)
```

### accessibility.py
```python
#!/usr/bin/env python3
"""Test page accessibility."""
import sys
import json
from playwright.sync_api import sync_playwright

def check_accessibility(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until='networkidle')
        
        # Basic accessibility checks
        violations = []
        
        # Check images without alt
        images = page.query_selector_all('img')
        for img in images:
            if not img.get_attribute('alt'):
                violations.append({
                    'type': 'missing-alt',
                    'element': 'img',
                    'src': img.get_attribute('src')[:50]
                })
        
        # Check form inputs without labels
        inputs = page.query_selector_all('input, select, textarea')
        for inp in inputs:
            id_attr = inp.get_attribute('id')
            aria_label = inp.get_attribute('aria-label')
            aria_labelled_by = inp.get_attribute('aria-labelledby')
            
            has_label = False
            if id_attr:
                label = page.query_selector(f'label[for="{id_attr}"]')
                if label:
                    has_label = True
            
            if not has_label and not aria_label and not aria_labelled_by:
                violations.append({
                    'type': 'missing-label',
                    'element': inp.evaluate('el => el.tagName.toLowerCase()'),
                    'id': id_attr
                })
        
        browser.close()
        return violations

if __name__ == '__main__':
    url = sys.argv[1]
    result = check_accessibility(url)
    print(json.dumps(result, indent=2))
```

## Use Cases

### Frontend Debugging
- Inspect element positions and styles
- Debug z-index stacking issues
- Check for overlapping elements
- Verify responsive layout behavior

### E2E Testing
- Automate user flows
- Test form submissions
- Verify navigation works
- Check state transitions

### Visual Regression
- Capture screenshots for comparison
- Test across different viewports
- Verify styling consistency

### Accessibility Testing
- Check for missing alt text
- Verify form labels
- Test keyboard navigation
- Validate ARIA attributes

## Source

Originally from [Claude Code Skills](https://github.com/anthropics/claude-skills)
Skill location: ~/.claude/skills/playwright
