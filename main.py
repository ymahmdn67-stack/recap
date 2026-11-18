import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox
from curl_cffi import requests as cffi_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("cfgate")

@dataclass
class GateResult:
    cleared: bool
    cookie: Optional[str] = None
    token: Optional[str] = None
    user_agent: Optional[str] = None
    cookies: dict = field(default_factory=dict)
    challenge_type: str = "unknown"
    error: Optional[str] = None

class CloudflareGate:
    """Solves Cloudflare Challenge (cookie) and Turnstile (token) with a real browser."""
    
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

    async def _detect_challenge(self, page) -> str:
        try:
            if page.is_closed():
                return "closed"
            html = (await page.content()) or ""
            
            if "challenges.cloudflare.com" in html or "cf-turnstile" in html:
                return "turnstile"
                
            for marker in self.CHALLENGE_MARKERS:
                if marker.lower() in html.lower():
                    return "challenge"
                    
            return "clear"
        except Exception as e:
            log.error(f"Error detecting challenge: {e}")
            return "error"

    async def _wait_turnstile_token(self, page) -> Optional[str]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000
        
        # انتظار ظهور الـ iframe
        try:
            await page.wait_for_selector(self.TURNSTILE_IFRAME, timeout=10000)
        except Exception:
            pass

        while loop.time() < deadline:
            if page.is_closed():
                return None
                
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
                    return token
            except Exception:
                pass

            # محاولة النقر على الـ Checkbox داخل الـ iframe
            try:
                iframe_element = page.frame_locator(self.TURNSTILE_IFRAME)
                checkbox = iframe_element.locator("input[type='checkbox']")
                if await checkbox.count() > 0:
                    await checkbox.first.click(force=True, timeout=2000)
                    log.info("Clicked Turnstile checkbox inside iframe")
                else:
                    iframe = page.locator(self.TURNSTILE_IFRAME).first
                    if await iframe.is_visible():
                        await iframe.click(force=True, timeout=2000)
                        log.info("Clicked Turnstile iframe directly")
            except Exception:
                pass

            await asyncio.sleep(self.poll_interval)
            
        return None

    async def _wait_clearance(self, page):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000
        
        while loop.time() < deadline:
            if page.is_closed():
                return None, {}
                
            cookies = await page.context.cookies()
            for c in cookies:
                if c["name"] == "cf_clearance" and c["value"]:
                    return c["value"], {ck["name"]: ck["value"] for ck in cookies}
                    
            await asyncio.sleep(self.poll_interval)
            
        return None, {}

    async def solve(self) -> GateResult:
        kind = "unknown"
        
        try:
            async with self._launch() as browser:
                page = await browser.new_page()
                
                log.info(f"Navigating to {self.url}...")
                try:
                    await page.goto(self.url, timeout=60000, wait_until="domcontentloaded")
                except Exception as nav_err:
                    return GateResult(cleared=False, error=f"Navigation failed: {nav_err}")
                    
                await asyncio.sleep(3)
                kind = await self._detect_challenge(page)
                log.info(f"Challenge detected: {kind}")

                if kind == "turnstile":
                    token = await self._wait_turnstile_token(page)
                    if token:
                        ua = await page.evaluate("navigator.userAgent")
                        cookies = await page.context.cookies()
                        jar = {c["name"]: c["value"] for c in cookies}
                        return GateResult(
                            cleared=True,
                            token=token,
                            user_agent=ua,
                            cookies=jar,
                            challenge_type="turnstile",
                        )
                    return GateResult(cleared=False, challenge_type="turnstile", error="turnstile token timeout")

                if kind == "challenge":
                    cookie, jar = await self._wait_clearance(page)
                    if cookie:
                        ua = await page.evaluate("navigator.userAgent")
                        return GateResult(
                            cleared=True,
                            cookie=cookie,
                            user_agent=ua,
                            cookies=jar,
                            challenge_type="challenge",
                        )
                    return GateResult(cleared=False, challenge_type="challenge", error="cf_clearance timeout")

                if kind == "closed":
                    return GateResult(cleared=False, error="Browser closed unexpectedly")

                # clear
                ua = await page.evaluate("navigator.userAgent")
                cookies = await page.context.cookies()
                return GateResult(
                    cleared=True,
                    user_agent=ua,
                    cookies={c["name"]: c["value"] for c in cookies},
                    challenge_type="clear",
                )
                
        except Exception as exc:
            log.exception("solve failed")
            return GateResult(cleared=False, error=str(exc))


class ClearanceSession:
    """Reuses cf_clearance or a Turnstile token over HTTP with a Chrome TLS fingerprint."""
    
    def __init__(self, gate: GateResult, proxy: Optional[str] = None):
        self.gate = gate
        self.proxy = proxy
        self.session = cffi_requests.Session(impersonate="chrome124")

    def _base_headers(self) -> dict:
        headers = {
            "User-Agent": self.gate.user_agent or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        return headers

    def get(self, url: str, **kwargs):
        headers = self._base_headers()
        headers.update(kwargs.pop("headers", {}) or {})
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        return self.session.get(url, headers=headers, proxies=proxies, timeout=30, **kwargs)

    def post_form(self, url: str, data: dict, **kwargs):
        headers = self._base_headers()
        headers.update(kwargs.pop("headers", {}) or {})
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        
        if self.gate.token:
            data = {**data, "cf-turnstile-response": self.gate.token}
            
        return self.session.post(url, data=data, headers=headers, proxies=proxies, timeout=30, **kwargs)


async def main(
    target: str,
    proxy: Optional[str] = None,
    headless: bool = True,
    output: Optional[str] = None,
):
    gate = CloudflareGate(target_url=target, proxy=proxy, headless=headless)
    result = await gate.solve()

    if not result.cleared:
        print(json.dumps({"success": False, "error": result.error, "type": result.challenge_type}))
        return

    session = ClearanceSession(result, proxy=proxy)
    
    # إضافة الكوكيز إلى الجلسة قبل الطلب
    for name, value in result.cookies.items():
        session.session.cookies.set(name, value)

    resp = session.get(target)
    
    print(json.dumps({
        "success": resp.status_code < 400,
        "status_code": resp.status_code,
        "challenge_type": result.challenge_type,
        "token": result.token,
        "cf_clearance": result.cookie,
        "user_agent": result.user_agent,
        "cookies": result.cookies,
    }, ensure_ascii=False, indent=2))
    
    if output:
        with open(output, "w", encoding="utf-8") as fh:
            json.dump({
                "token": result.token,
                "cf_clearance": result.cookie,
                "user_agent": result.user_agent,
                "cookies": result.cookies,
            }, fh, ensure_ascii=False, indent=2)
        log.info("result written to %s", output)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cloudflare Turnstile / Challenge solver")
    parser.add_argument("url", help="target URL")
    parser.add_argument("--proxy", default=os.environ.get("CF_PROXY"))
    parser.add_argument("--headed", action="store_true", help="run browser in headed mode")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    asyncio.run(main(args.url, args.proxy, headless=not args.headed, output=args.output))
