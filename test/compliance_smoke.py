from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto('http://127.0.0.1:3000/compliance')
    page.wait_for_load_state('networkidle')
    assert page.get_by_role('heading', name='设计方案合规体检').is_visible()
    assert page.get_by_text('证据优先的判定边界').is_visible()
    assert page.get_by_text('01 · 项目条件').is_visible()
    assert page.get_by_text('02 · 可审计体检报告').is_visible()
    page.screenshot(path='compliance-smoke.png', full_page=True)
    browser.close()
