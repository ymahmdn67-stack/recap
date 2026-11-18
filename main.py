import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox

TARGET_URL = "https://pureprescriptions.com/"

@dataclass
class GateResult:
    cleared: bool
    cookie: Optional[str] = None
    token: Optional[str] = None
    cookies: list = field(default_factory=list)
    challenge_type: str = "unknown"
    error: Optional[str] = None
    page_url: Optional[str] = None
    page_title: Optional[str] = None

class CloudflareGate:
    TURNSTILE_IFRAME = "iframe[src*='challenges.cloudflare.com']"
    CHALLENGE_MARKERS = (
        "Just a moment",
        "Checking your browser",
        "cf-browser-verification",
        "challenge-platform",
    )
    TURNSTILE_INPUT = "input[name='cf-turnstile-response']"
    TURNSTILE_TEXTAREA = "textarea[name='cf-turnstile-response']"

    def __init__(
        self,
        target_url: str,
        proxy: Optional[str] = None,
        headless: bool = True,
        timeout: int = 60000,
        poll_interval: float = 1.0,
    ):
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"invalid target url: {target_url}")

        self.url = target_url
        self.proxy = proxy
        self.headless = headless
        self.timeout = timeout
        self.poll_interval = poll_interval

    def _launch(self):
        options = {"headless": self.headless}
        if self.proxy:
            parsed_proxy = urlparse(self.proxy)
            proxy_config = {
                "server": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}"
            }
            if parsed_proxy.username and parsed_proxy.password:
                proxy_config["username"] = parsed_proxy.username
                proxy_config["password"] = parsed_proxy.password
            options["proxy"] = proxy_config
        return AsyncCamoufox(**options)

    async def _detect_challenge(self, page) -> tuple[str, Optional[str]]:
        try:
            html = await page.content()
        except Exception as e:
            return "error", str(e)

        if "cf-turnstile-response" in html or "cf-turnstile" in html:
            return "turnstile", None

        for marker in self.CHALLENGE_MARKERS:
            if marker.lower() in html.lower():
                return "challenge", None

        return "clear", None

    async def _wait_turnstile_token(self, page) -> tuple[Optional[str], list, Optional[str]]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000
        last_cookies = []
        cookie_error = None

        while loop.time() < deadline:
            if page.is_closed():
                return None, last_cookies, "Page closed during wait"
            try:
                last_cookies = await page.context.cookies()
            except Exception as e:
                cookie_error = f"Failed to read cookies: {e}"

            try:
                token = await page.evaluate(
                    f"""
                    (() => {{
                        const el = document.querySelector("{self.TURNSTILE_INPUT}")
                                 || document.querySelector("{self.TURNSTILE_TEXTAREA}");
                        return el ? el.value : null;
                    }})()
                    """
                )
                if token and len(token) > 20:
                    return token, last_cookies, cookie_error
            except Exception:
                pass

            try:
                iframe_element = page.frame_locator(self.TURNSTILE_IFRAME)
                checkbox = iframe_element.locator("input[type='checkbox']")
                if await checkbox.count() > 0:
                    await checkbox.first.click(force=True, timeout=2000)
                else:
                    iframe = page.locator(self.TURNSTILE_IFRAME).first
                    if await iframe.is_visible():
                        await iframe.click(force=True, timeout=2000)
            except Exception:
                pass

            await asyncio.sleep(self.poll_interval)

        return None, last_cookies, "turnstile token timeout"

    async def _wait_clearance(self, page) -> tuple[Optional[str], list, Optional[str]]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000
        last_cookies = []
        cookie_error = None

        while loop.time() < deadline:
            if page.is_closed():
                return None, last_cookies, "Page closed during wait"
            try:
                last_cookies = await page.context.cookies()
            except Exception as e:
                cookie_error = f"Failed to read cookies: {e}"

            for c in last_cookies:
                if c.get("name") == "cf_clearance" and c.get("value"):
                    return c["value"], last_cookies, cookie_error

            await asyncio.sleep(self.poll_interval)

        return None, last_cookies, "cf_clearance timeout"

    async def solve(self) -> GateResult:
        kind = "unknown"
        cleared = False
        token = None
        cookie = None
        final_cookies = []
        error_msg = None
        page_url = None
        page_title = None

        try:
            async with self._launch() as browser:
                page = await browser.new_page()
                try:
                    await page.goto(self.url, timeout=self.timeout)
                    await asyncio.sleep(2)

                    kind, detect_err = await self._detect_challenge(page)

                    if kind == "error":
                        error_msg = f"Detection failed: {detect_err}"
                    elif kind == "turnstile":
                        token, final_cookies, wait_err = await self._wait_turnstile_token(page)
                        if token:
                            cleared = True
                            if wait_err:
                                error_msg = wait_err
                        else:
                            error_msg = wait_err
                    elif kind == "challenge":
                        cookie, final_cookies, wait_err = await self._wait_clearance(page)
                        if cookie:
                            cleared = True
                            if wait_err:
                                error_msg = wait_err
                        else:
                            error_msg = wait_err
                    else:
                        try:
                            final_cookies = await page.context.cookies()
                            cleared = True
                        except Exception as e:
                            error_msg = f"Failed to read cookies: {e}"

                except Exception as exc:
                    error_msg = str(exc) if not error_msg else f"{error_msg}; {exc}"
                finally:
                    if not page.is_closed():
                        try:
                            latest = await page.context.cookies()
                            if latest:
                                final_cookies = latest
                        except Exception as e:
                            if not error_msg:
                                error_msg = f"Failed final cookie read: {e}"

                        page_url = page.url
                        try:
                            page_title = await page.title()
                        except Exception:
                            pass
                    elif not error_msg:
                        error_msg = "Page or browser closed unexpectedly before completion"

        except Exception as exc:
            if not error_msg:
                error_msg = str(exc)

        return GateResult(
            cleared=cleared,
            cookie=cookie,
            token=token,
            cookies=final_cookies,
            challenge_type=kind,
            error=error_msg,
            page_url=page_url,
            page_title=page_title
        )

async def main(
    proxy: Optional[str] = None,
    headless: bool = True,
) -> GateResult:
    gate = CloudflareGate(
        target_url=TARGET_URL,
        proxy=proxy,
        headless=headless,
    )
    result = await gate.solve()
    return result

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", default=os.environ.get("CF_PROXY"))
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    # ✅ تم إرجاع البروكسي هنا في هذه النسخة
    MY_PROXY = args.proxy or "http://krake73891:kraken@proxies.toolz.ovh:8443"

    # ⏱️ بداية العداد
    start_time = time.time()

    result = asyncio.run(main(proxy=MY_PROXY, headless=not args.headed))

    # ⏱️ نهاية العداد وحساب الفارق
    end_time = time.time()
    elapsed_time = end_time - start_time

    print("\n" + "="*40)
    print("📊 [FINAL DIAGNOSTIC SUMMARY]")
    print("="*40)
    print("Page URL:", result.page_url)
    print("Page title:", result.page_title)
    print("Cleared:", result.cleared)
    print("Challenge type:", result.challenge_type)
    print("Token present:", bool(result.token))
    print(
        "cf_clearance present:",
        any(
            c.get("name") == "cf_clearance" and bool(c.get("value"))
            for c in result.cookies
        ),
    )
    print("Cookie count:", len(result.cookies))
    print("Error:", result.error)
    print(f"⏱️ Execution Time: {elapsed_time:.2f} seconds")
    
    print("\n" + "="*40)
    print("🔑 [RAW DATA - TOKEN & COOKIES]")
    print("="*40)
    
    print("Token:")
    print(result.token if result.token else "None (No token found)")
    
    print("\nCookies (Name & Value):")
    if result.cookies:
        for c in result.cookies:
            print(f"- {c.get('name')}: {c.get('value')}")
    else:
        print("None (No cookies found)")
        
    print("\ncf_clearance:")
    print(result.cookie if result.cookie else "None")
    print("="*40 + "\n")
