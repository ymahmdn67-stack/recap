import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from camoufox.async_api import AsyncCamoufox


TARGET_URL = "https://example.com/"


@dataclass
class GateResult:
    cleared: bool
    cookie: Optional[str] = None
    token: Optional[str] = None
    cookies: dict = field(default_factory=dict)
    challenge_type: str = "unknown"
    error: Optional[str] = None


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
            options["proxy"] = {"server": self.proxy}
        return AsyncCamoufox(**options)

    async def _detect_challenge(self, page) -> str:
        html = (await page.content()) or ""
        if "challenges.cloudflare.com" in html or "cf-turnstile" in html:
            return "turnstile"

        for marker in self.CHALLENGE_MARKERS:
            if marker.lower() in html.lower():
                return "challenge"

        return "clear"

    async def _wait_turnstile_token(self, page) -> Optional[str]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000

        while loop.time() < deadline:
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

            try:
                clicked = await page.evaluate(
                    f"""
                    (() => {{
                        const iframe = document.querySelector("{self.TURNSTILE_IFRAME}");
                        if (!iframe) return false;
                        const rect = iframe.getBoundingClientRect();
                        return {{x: rect.x + rect.width / 2, y: rect.y + rect.height / 2}};
                    }})()
                    """
                )
                if clicked and isinstance(clicked, dict):
                    await page.mouse.click(clicked["x"], clicked["y"])
            except Exception:
                pass

            await asyncio.sleep(self.poll_interval)

        return None

    async def _wait_clearance(self, page):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout / 1000

        while loop.time() < deadline:
            cookies = await page.context.cookies()

            for cookie in cookies:
                if cookie["name"] == "cf_clearance" and cookie["value"]:
                    return cookie["value"], {
                        item["name"]: item["value"] for item in cookies
                    }

            await asyncio.sleep(self.poll_interval)

        return None, {}

    async def solve(self) -> GateResult:
        kind = "unknown"

        try:
            async with self._launch() as browser:
                page = await browser.new_page()
                await page.goto(self.url)
                await asyncio.sleep(2)

                kind = await self._detect_challenge(page)

                if kind == "turnstile":
                    token = await self._wait_turnstile_token(page)

                    if token:
                        cookies = await page.context.cookies()
                        return GateResult(
                            cleared=True,
                            token=token,
                            cookies={
                                cookie["name"]: cookie["value"]
                                for cookie in cookies
                            },
                            challenge_type="turnstile",
                        )

                    return GateResult(
                        cleared=False,
                        challenge_type="turnstile",
                        error="turnstile token timeout",
                    )

                if kind == "challenge":
                    cookie, jar = await self._wait_clearance(page)

                    if cookie:
                        return GateResult(
                            cleared=True,
                            cookie=cookie,
                            cookies=jar,
                            challenge_type="challenge",
                        )

                    return GateResult(
                        cleared=False,
                        challenge_type="challenge",
                        error="cf_clearance timeout",
                    )

                cookies = await page.context.cookies()
                return GateResult(
                    cleared=True,
                    cookies={
                        cookie["name"]: cookie["value"]
                        for cookie in cookies
                    },
                    challenge_type="clear",
                )

        except Exception as exc:
            return GateResult(
                cleared=False,
                challenge_type=kind,
                error=str(exc),
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

    result = asyncio.run(main(proxy=args.proxy, headless=not args.headed))

    print("Cleared:", result.cleared)
    print("Challenge type:", result.challenge_type)
    print("Token present:", bool(result.token))
    print("cf_clearance present:", bool(result.cookies.get("cf_clearance")))
    print("Cookie count:", len(result.cookies))
    print("Error:", result.error)
