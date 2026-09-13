from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from playwright.async_api import BrowserContext, Page, Response, async_playwright
except ImportError:
    print("Playwright is not installed. Run: python3 -m pip install playwright", file=sys.stderr)
    raise SystemExit(2)

USER_AGENT = "Authorized-Sources-Capture/1.0"
JS_TYPES = {"script", "text/javascript", "application/javascript", "application/x-javascript"}
MAX_DEFAULT = 50 * 1024 * 1024


def clean_url(url: str) -> str:
    p = urlparse(url)
    query = urlencode(sorted(parse_qsl(p.query, keep_blank_values=True)))
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path or "/", "", query, ""))


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value) or "unknown"


def local_path(url: str, root: Path) -> Path:
    p = urlparse(url)
    host = safe_name(p.netloc)
    segments = [safe_name(part) for part in p.path.split("/") if part not in {"", ".", ".."}]
    if not segments:
        segments = ["index"]
    if p.path.endswith("/"):
        segments.append("index")
    filename = segments[-1]
    if p.query:
        digest = hashlib.sha256(p.query.encode()).hexdigest()[:12]
        stem, dot, suffix = filename.rpartition(".")
        filename = f"{stem if dot else filename}__q_{digest}{('.' + suffix) if dot else ''}"
    segments[-1] = filename
    target = (root / host / Path(*segments)).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"Unsafe path: {url}")
    return target


def content_is_javascript(response: Response) -> bool:
    content_type = (response.headers.get("content-type") or "").split(";", 1)[0].lower()
    path = urlparse(response.url).path.lower()
    return response.request.resource_type in {"script", "worker"} or content_type in JS_TYPES or path.endswith((".js", ".mjs", ".cjs"))


class Capture:
    def __init__(self, root_url: str, output: Path, args: argparse.Namespace) -> None:
        self.root_url = root_url
        self.output = output
        self.args = args
        self.seen: set[str] = set()
        self.saved = 0
        self.skipped = 0
        self.errors = 0

    async def save_response(self, response: Response) -> None:
        url = clean_url(response.url)
        if url in self.seen or url.startswith(("data:", "blob:", "file:")):
            return
        self.seen.add(url)
        if not self.args.all_resources and not content_is_javascript(response):
            return
        try:
            body = await response.body()
            if len(body) > self.args.max_bytes:
                self.skipped += 1
                print(f"[SKIP: TOO LARGE] {url}")
                return
            target = local_path(url, self.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            self.saved += 1
            print(f"[+] {response.status} {url} -> {target.relative_to(self.output)} ({len(body):,} bytes)")
        except Exception as exc:
            self.errors += 1
            print(f"[ERROR] Could not save response body {url}: {exc}", file=sys.stderr)

    async def handle_page(self, page: Page) -> None:
        page.on("response", self.save_response)
        try:
            print(f"[*] Opening: {self.root_url}")
            await page.goto(self.root_url, wait_until="domcontentloaded", timeout=self.args.timeout * 1000)
            await page.wait_for_timeout(self.args.wait * 1000)
            for _ in range(self.args.scrolls):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(self.args.wait * 1000)
        except Exception as exc:
            print(f"[ERROR] Could not load page: {exc}", file=sys.stderr)

    async def crawl(self, context: BrowserContext) -> None:
        page = await context.new_page()
        await self.handle_page(page)
        if self.args.depth > 0:
            links = await page.locator("a[href]").evaluate_all("els => els.map(e => e.href)")
            root_host = (urlparse(self.root_url).hostname or "").lower()
            visited: set[str] = {clean_url(self.root_url)}
            for link in links[: self.args.max_pages]:
                parsed = urlparse(link)
                if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() != root_host:
                    continue
                normalized = clean_url(link)
                if normalized in visited:
                    continue
                visited.add(normalized)
                child = await context.new_page()
                old_url = self.root_url
                self.root_url = normalized
                await self.handle_page(child)
                self.root_url = old_url
                await child.close()
        await page.close()

    def make_zip(self) -> Path:
        script_dir = Path(__file__).resolve().parent
        host = safe_name(urlparse(self.root_url).netloc)
        archive = script_dir / f"{host}_sources_archive.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in sorted(self.output.rglob("*")):
                if file.is_file():
                    zf.write(file, file.relative_to(self.output))
        return archive


async def run(args: argparse.Namespace) -> int:
    root = clean_url(args.url)
    parsed = urlparse(root)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print("The URL must start with http:// or https://", file=sys.stderr)
        return 2
    script_dir = Path(__file__).resolve().parent
    host = safe_name(parsed.netloc)
    output = Path(args.output).expanduser().resolve() if args.output else script_dir / f"{host}_sources_files"
    if output.exists() and args.clean:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    capture = Capture(root, output, args)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not args.headed)
        context = await browser.new_context(ignore_https_errors=args.ignore_https_errors, user_agent=USER_AGENT)
        try:
            await capture.crawl(context)
        finally:
            await context.close()
            await browser.close()
    archive = capture.make_zip()
    mode = "all resources" if args.all_resources else "JavaScript resources only"
    print(f"\nCapture completed ({mode}).")
    print(f"Saved {capture.saved} files, skipped {capture.skipped} oversized files, and failed {capture.errors} files.")
    print(f"Output directory: {output}")
    print(f"ZIP archive: {archive}")
    if capture.saved == 0:
        print("[WARNING] No content was saved. The page may require login or block automated browsers.", file=sys.stderr)
    return 0


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture browser-loaded resource bodies and save them by domain and URL path")
    parser.add_argument("url", nargs="?", help="Site URL; if omitted, it will be requested interactively")
    parser.add_argument("--output", "-o", help="Output directory; defaults to a folder next to this Python file")
    parser.add_argument("--wait", type=float, default=5, help="Seconds to wait after loading (default: 5)")
    parser.add_argument("--scrolls", type=int, default=3, help="Scroll count to trigger lazy loading (default: 3)")
    parser.add_argument("--depth", type=int, default=0, help="Additional internal page depth (default: 0)")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum number of additional pages")
    parser.add_argument("--all-resources", action="store_true", help="Save every captured resource, not only JavaScript")
    parser.add_argument("--max-bytes", type=int, default=MAX_DEFAULT, help="Maximum size per resource")
    parser.add_argument("--timeout", type=int, default=45, help="Page load timeout in seconds")
    parser.add_argument("--clean", action="store_true", help="Delete the previous output directory first")
    parser.add_argument("--headed", action="store_true", help="Run Chromium with a visible window")
    parser.add_argument("--ignore-https-errors", action="store_true", help="Ignore HTTPS certificate errors")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if not args.url:
        args.url = input("Enter the URL of a site you own or are authorized to test: ").strip()
    if args.wait < 0 or args.scrolls < 0 or args.depth < 0 or args.max_pages < 0:
        print("Wait and crawl values cannot be negative.", file=sys.stderr)
        return 2
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
