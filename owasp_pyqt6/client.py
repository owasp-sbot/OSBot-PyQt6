#!/usr/bin/env python3
import asyncio
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def capture_content(page_url, debug_port=9222, capture_dir=None):
    """Capture content from a webpage using Playwright"""
    # Set up capture directory
    if capture_dir is None:
        capture_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")

    os.makedirs(capture_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_name = f"capture_{timestamp}"

    print(f"Starting content capture for: {page_url}")
    print(f"Using Chrome debugging port: {debug_port}")

    async with async_playwright() as p:
        try:
            # Connect to the browser (either our PyQt browser or a running Chrome instance)
            try:
                # First try connecting to our PyQt browser via CDP
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
                print("Connected to existing browser via CDP")
            except Exception as e:
                print(f"Could not connect to existing browser: {e}")
                print("Launching new browser instance")
                # If connection fails, launch a new browser instance
                browser = await p.chromium.launch(headless=False)

            # Create a new page
            page = await browser.new_page()

            # Navigate to the target URL
            print(f"Navigating to {page_url}")
            await page.goto(page_url, wait_until="networkidle")

            # Capture the page content
            html_content = await page.content()

            # Save HTML content
            html_path = os.path.join(capture_dir, f"{capture_name}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"HTML content saved to: {html_path}")

            # Take a screenshot
            screenshot_path = os.path.join(capture_dir, f"{capture_name}.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved to: {screenshot_path}")

            # Collect all resources (scripts, stylesheets, etc.)
            resource_info = []

            # This is a placeholder for more sophisticated resource capturing
            # In a full implementation, we would:
            # 1. Use page.route() to intercept network requests
            # 2. Store all resources (JS, CSS, images, XHR responses)
            # 3. Create a manifest of all captured resources

            # For now, we'll just get a list of scripts as a demonstration
            scripts = await page.evaluate("""
                Array.from(document.querySelectorAll('script[src]')).map(s => s.src)
            """)

            styles = await page.evaluate("""
                Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(s => s.href)
            """)

            resource_info.extend([{"type": "script", "url": url} for url in scripts])
            resource_info.extend([{"type": "stylesheet", "url": url} for url in styles])

            # Save resource info
            resource_path = os.path.join(capture_dir, f"{capture_name}_resources.txt")
            with open(resource_path, "w", encoding="utf-8") as f:
                for res in resource_info:
                    f.write(f"{res['type']}: {res['url']}\n")

            print(f"Resource info saved to: {resource_path}")
            print(f"Captured {len(resource_info)} resources")

            # In a production version, we would store full resources and compute hashes

            # Close the page (but not the browser if we connected to an existing one)
            await page.close()

            return {
                "status": "success",
                "url": page_url,
                "timestamp": timestamp,
                "html_path": html_path,
                "screenshot_path": screenshot_path,
                "resource_count": len(resource_info)
            }

        except Exception as e:
            print(f"Error capturing content: {e}")
            return {
                "status": "error",
                "url": page_url,
                "error": str(e)
            }
        finally:
            # Make sure to disconnect if we connected to an existing browser
            if 'browser' in locals():
                await browser.close()


async def main():
    # Get arguments from command line
    debug_port = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
    target_url = sys.argv[2] if len(sys.argv) > 2 else "https://docs.diniscruz.ai"

    # Run the capture
    result = await capture_content(target_url, debug_port)

    # Print the result status
    if result["status"] == "success":
        print(f"Successfully captured content from {result['url']}")
        print(f"HTML: {result['html_path']}")
        print(f"Screenshot: {result['screenshot_path']}")
        print(f"Resources captured: {result['resource_count']}")
    else:
        print(f"Failed to capture content: {result['error']}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))