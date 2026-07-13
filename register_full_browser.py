import re
import random
import logging
from dataclasses import dataclass
import requests
from playwright.sync_api import sync_playwright, BrowserContext, Page
from faker import Faker

try:
    from playwright_stealth import Stealth
    def apply_stealth(page: Page) -> None:
        Stealth().apply_stealth_sync(page)
except ImportError:
    def apply_stealth(page: Page) -> None:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FullBrowserEngine")

@dataclass(frozen=True)
class RegistrationPayload:
    email: str
    password: str

class FullBrowserWooCommerceEngine:
    """
    محرك المحاكاة الكاملة (Full Browser Automation):
    يقوم بكافة العمليات (تجاوز البوب اب، الكتابة، التسجيل، الانتقال، واستخراج النونس)
    داخل المتصفح مباشرة لضمان أعلى مستويات الأمان وتفادي قيود الـ HTTP.
    """
    
    def __init__(self) -> None:
        self.fake = Faker("en_UK")
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.address_nonce = None

    def _generate_payload(self) -> RegistrationPayload:
        f_name = self.fake.first_name()
        l_name = self.fake.last_name()
        email = f"{f_name.lower()}.{l_name.lower()}@greenmethods.com"
        password = f"SecurP@ss{random.randint(1000, 9999)}#2026"
        return RegistrationPayload(email=email, password=password)

    def execute(self) -> bool:
        payload = self._generate_payload()
        
        logger.info("⚡ بدء محرك المحاكاة الكاملة عبر Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, # اجعله True إذا كنت تشغله على سيرفر بدون واجهة مع Xvfb
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(user_agent=self.user_agent, viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            apply_stealth(page)

            try:
                # 1. الذهاب لصفحة التسجيل
                page.goto("https://greenmethods.com/my-account/", wait_until="networkidle", timeout=45000)
                
                # 2. تنظيف الواجهة من النوافذ المنبثقة (Popup)
                page.evaluate("""() => {
                    const selectors = ['[role="dialog"]', '.kl-private-reset-css-Xuajs1', '.modal', '.popup'];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                }""")
                page.wait_for_timeout(500)

                # 3. ملء البيانات بمحاكاة سلوكية (تأخير خفيف بين الحروف)
                logger.info(f"📝 كتابة البريد الإلكتروني: {payload.email}")
                email_locator = page.locator("input#reg_email")
                email_locator.focus()
                page.type("input#reg_email", payload.email, delay=random.randint(50, 100))
                
                logger.info("📝 كتابة كلمة المرور...")
                password_locator = page.locator("input#reg_password")
                password_locator.focus()
                page.type("input#reg_password", payload.password, delay=random.randint(50, 100))
                
                page.wait_for_timeout(1000) # انتظار قليل للتأكد من استقرار الكابتشا الخلفية

                # 4. الضغط على زر التسجيل داخل المتصفح مباشرة
                logger.info("🔘 الضغط على زر التسجيل (Register) داخل المتصفح...")
                register_button = page.locator("button[name='register']")
                
                # النقر مع تفعيل المتابعة حتى استقرار الشبكة بعد إعادة التوجيه
                with page.expect_navigation(wait_until="networkidle", timeout=45000):
                    register_button.click(force=True)

                # 5. الانتقال المباشر لصفحة العناوين داخل نفس المتصفح والموقع مسجل دخول
                logger.info("📬 الانتقال إلى صفحة تحرير العناوين لاستخراج الـ Nonce...")
                page.goto("https://greenmethods.com/my-account/edit-address/billing/", wait_until="networkidle", timeout=30000)
                
                # 6. استخراج الـ Address Nonce من محتوى المتصفح الحركي (DOM)
                html_content = page.content()
                match = re.search(r'name="woocommerce-edit-address-nonce"\s*value="([^"]+)"', html_content)
                
                if match:
                    self.address_nonce = match.group(1)
                    logger.info(f"🏆 [نجاح كامل ومضمون] تم استخراج Address Nonce: {self.address_nonce}")
                    browser.close()
                    return True
                else:
                    logger.error("❌ لم يتم العثور على Address Nonce. قد يكون الحساب لم يسجل بنجاح أو الكابتشا منعت الزر.")
                    
            except Exception as e:
                logger.error(f"❌ خطأ أثناء المحاكاة الكاملة: {e}")
            
            browser.close()
        return False

if __name__ == "__main__":
    engine = FullBrowserWooCommerceEngine()
    success = engine.execute()
    print(f"\n📈 النتيجة النهائية: {'✅ SUCCESS' if success else '❌ FAILED'}")
