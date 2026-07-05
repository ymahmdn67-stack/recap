import asyncio
import os
import logging
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Response

# تحميل المتغيرات البيئية من ملف .env
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RecaptchaInterceptor:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.token_future = asyncio.Future()

    async def handle_response(self, response: Response):
        if "recaptcha/enterprise/reload" in response.url:
            try:
                body = await response.text()
                import re
                m = re.search(r'rresp","([^"]+)"', body)
                if m and not self.token_future.done():
                    self.token_future.set_result(m.group(1))
            except Exception as e:
                logger.error(f"خطأ أثناء قراءة الاستجابة: {e}")

    async def capture_token(self, timeout: int = 30000) -> str:
        # قراءة إعدادات Headless من المتغيرات البيئية
        headless_env = os.getenv("HEADLESS", "false").lower()
        is_headless = headless_env in ("true", "1", "yes")

        async with async_playwright() as p:
            # إضافة إعدادات لتجنب الاكتشاف (Detection Avoidance)
            browser = await p.chromium.launch(
                headless=is_headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # إخفاء خاصية webdriver
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page.on("response", self.handle_response)
            
            logger.info(f"جاري فتح الصفحة {self.target_url} والانتظار لالتقاط التوكن...")
            await page.goto(self.target_url)
            
            try:
                token = await asyncio.wait_for(self.token_future, timeout=timeout / 1000.0)
                return token
            except asyncio.TimeoutError:
                logger.error("انتهى الوقت المحدد ولم يتم العثور على التوكن.")
                return None
            finally:
                await browser.close()

async def main():
    target_url = os.getenv("TARGET_URL", "https://recaptcha-demo.appspot.com/recaptcha-v2-invisible.php")
    timeout = int(os.getenv("TIMEOUT_MS", "15000"))
    
    interceptor = RecaptchaInterceptor(target_url)
    token = await interceptor.capture_token(timeout=timeout)
    
    if token:
        logger.info(f"تم الالتقاط بنجاح! TOKEN = {token[:40]}...")
        # يمكنك حفظ التوكن في ملف هنا إذا أردت
        with open("token.txt", "w") as f:
            f.write(token)
            logger.info("تم حفظ التوكن في ملف token.txt")
    else:
        logger.warning("فشلت عملية التقاط التوكن.")

if __name__ == "__main__":
    asyncio.run(main())
