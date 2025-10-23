#!/usr/bin/env python3
"""
Improved authentication script for Microsoft 365 admin center.
This version gives you more control and time to sign in.


  1. Run: python3 authenticate_microsoft_v2.py
  2. Sign in again
  3. Copy the new session: docker cp microsoft_auth_state.json 
  status-dashboard-backend:/app/

  
"""
import asyncio
from playwright.async_api import async_playwright
import json
import os

STORAGE_FILE = "microsoft_auth_state.json"

async def authenticate():
    """Open browser for user to authenticate, then save session."""
    async with async_playwright() as p:
        print("=" * 70)
        print("Microsoft 365 Authentication - Interactive Setup")
        print("=" * 70)
        print()
        print("🌐 A browser window will open")
        print("📝 Steps to follow:")
        print("   1. Sign in to your Microsoft 365 admin account")
        print("   2. Complete any MFA/2FA verification")
        print("   3. Navigate to Service Health (or I'll do it automatically)")
        print("   4. Come back here and press Enter when ready")
        print()

        # Launch browser in non-headless mode
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )

        # Create context
        context = await browser.new_context(
            viewport=None  # Use full window
        )
        page = await context.new_page()

        # Start at the main admin center (easier to authenticate)
        print("📍 Opening: https://admin.microsoft.com")
        print()

        try:
            await page.goto('https://admin.microsoft.com', timeout=60000)
        except Exception as e:
            print(f"⚠️  Initial navigation: {e}")
            print("   This is normal - the page might redirect for authentication")

        print("⏳ Waiting for you to sign in...")
        print("   Take your time - complete all authentication steps")
        print()

        # Wait for user to complete authentication
        input("👉 Press Enter AFTER you've signed in and can see the admin center: ")

        # Check current state
        current_url = page.url
        print(f"\n📍 Current URL: {current_url}")

        # Try to navigate to service health
        print("\n🔄 Navigating to Service Health page...")
        try:
            await page.goto(
                'https://admin.microsoft.com/Adminportal/Home#/servicehealth/overview',
                timeout=30000,
                wait_until='load'
            )
            await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️  Navigation note: {e}")

        # Final check
        final_url = page.url
        page_title = await page.title()

        print(f"\n📄 Page title: {page_title}")
        print(f"🔗 Final URL: {final_url}")

        # Check if authenticated
        if 'login' in final_url.lower() or 'oauth2' in final_url.lower():
            print("\n❌ ERROR: Still on authentication page")
            print("   Please try running the script again and complete the sign-in")
            await browser.close()
            return False

        if 'admin.microsoft.com' not in final_url.lower():
            print("\n⚠️  WARNING: Not on admin.microsoft.com")
            print(f"   Current URL: {final_url}")

            retry = input("\n   Continue anyway? (y/n): ")
            if retry.lower() != 'y':
                await browser.close()
                return False

        # Save the authentication state
        print("\n💾 Saving authentication session...")
        storage_state = await context.storage_state()

        with open(STORAGE_FILE, 'w') as f:
            json.dump(storage_state, f, indent=2)

        print(f"✅ Session saved to: {os.path.abspath(STORAGE_FILE)}")
        print()
        print("=" * 70)
        print("SUCCESS! Authentication complete")
        print("=" * 70)
        print()
        print("📋 Next step:")
        print(f"   docker cp {STORAGE_FILE} status-dashboard-backend:/app/")
        print()

        # Keep browser open for a moment so user can verify
        print("The browser will close in 5 seconds...")
        await asyncio.sleep(5)
        await browser.close()

        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(authenticate())
        if not result:
            print("\n⚠️  Authentication was not successful. Please try again.")
            exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Playwright is installed:")
        print("  pip install playwright")
        print("  playwright install chromium")
        exit(1)
