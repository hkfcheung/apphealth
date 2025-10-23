#!/usr/bin/env python3
"""
One-time authentication script for Microsoft 365 admin center.
Run this locally (not in Docker) to authenticate and save session cookies.
"""
import asyncio
from playwright.async_api import async_playwright
import json
import os

STORAGE_FILE = "microsoft_auth_state.json"

async def authenticate():
    """Open browser for user to authenticate, then save session."""
    async with async_playwright() as p:
        print("🌐 Launching browser for authentication...")
        print("   You'll need to sign in with your Microsoft 365 admin account\n")

        # Launch browser in non-headless mode so user can see and interact
        browser = await p.chromium.launch(headless=False)

        # Create context - this will store cookies/session
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to Microsoft 365 admin service health
        print("📍 Opening: https://admin.microsoft.com/Adminportal/Home#/servicehealth/overview")
        await page.goto('https://admin.microsoft.com/Adminportal/Home#/servicehealth/overview',
                       timeout=60000)

        print("\n⏳ Please sign in to your Microsoft 365 admin account in the browser window...")
        print("   After signing in and seeing the Service Health page, press Enter here to continue.\n")

        # Wait for user to authenticate manually
        input("Press Enter after you've successfully signed in and can see the Service Health page: ")

        # Check if we're authenticated
        current_url = page.url
        page_title = await page.title()

        print(f"\n📄 Current page: {page_title}")
        print(f"🔗 URL: {current_url}")

        if 'login' in current_url.lower() or 'signin' in current_url.lower() or 'oauth2' in current_url.lower():
            print("\n❌ Still on login/OAuth page. Authentication did not complete.")
            print("   Possible reasons:")
            print("   - The sign-in process was not completed")
            print("   - MFA/2FA may have timed out")
            print("   - The page didn't finish loading")
            print("\n   Please try again.")
            await browser.close()
            return False

        # Save the authentication state (cookies, local storage, etc.)
        storage_state = await context.storage_state()

        # Save to file
        with open(STORAGE_FILE, 'w') as f:
            json.dump(storage_state, f, indent=2)

        print(f"\n✅ Authentication successful!")
        print(f"   Session saved to: {os.path.abspath(STORAGE_FILE)}")
        print(f"\n📋 Next steps:")
        print(f"   1. Copy {STORAGE_FILE} into the Docker container:")
        print(f"      docker cp {STORAGE_FILE} status-dashboard-backend:/app/")
        print(f"   2. The backend will use this session for authenticated scraping")

        await browser.close()
        return True

if __name__ == "__main__":
    print("=" * 70)
    print("Microsoft 365 Admin Center - Authentication Setup")
    print("=" * 70)
    print()

    # Check if playwright is installed
    try:
        asyncio.run(authenticate())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Playwright is installed:")
        print("  pip install playwright")
        print("  playwright install chromium")
