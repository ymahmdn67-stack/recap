import re
import random
import logging
from dataclasses import dataclass
from typing import Optional, List
import requests
from playwright.sync_api import sync_playwright, BrowserContext, Page
from faker import Faker

# محاولة استيراد مكتبة التخفي ديناميكياً
try:
    from playwright_stealth import Stealth
    def apply_stealth(page: Page) -> None:
        Stealth().apply_stealth_sync(page)
except ImportError:
    def apply_stealth(page: Page) -> None:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MultiTokenHybridEngine")

@dataclass(frozen=True)
class RegistrationPayload:
    """كيان بيانات التسجيل النقي لضمان سلامة البيانات ونقاء الأنواع."""
    email: str
    password: str

class OptimizedHybridWooCommerceEngine:
    """
    المحرك الهجين المتقدم:
    - يراقب الشبكة لاقتناص توكنات reCAPTCHA المتعددة ويعزل التوكن الثاني (Action Token).
    - ينقل الجلسة والكوكيز والتوكن الثاني إلى Requests لإتمام التسجيل وجلب البيانات بسرعة فائقة.
    """
    
    def __init__(self) -> None:
        self.fake = Faker("en_UK")
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.session = requests.Session()
        self.captcha_tokens: List[str] = []
        self.register_nonce: Optional[str] = None
        self.address_nonce: Optional[str] = None

    def _generate_payload(self) -> RegistrationPayload:
        f_name = self.fake.first_name()
        l_name = self.fake.last_name()
        email = f"{f_name.lower()}.{l_name.lower()}@greenmethods.com"
        password = f"SecurP@ss{random.randint(1000, 9999)}#2026"
        return RegistrationPayload(email=email, password=password)

    def _check_network_response(self, response) -> None:
        """مستمع الشبكة: عزل التوكنات الفريدة من استجابات reload الخاصة بجوجل."""
        try:
            if "recaptcha/api2/reload" in response.url:
                body = response.text()
                match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
                if match:
                    token = match.group(1)
                    if token not in self.captcha_tokens:
                        self.captcha_tokens.append(token)
                        logger.info(f"🎯 [رصد توكن] تم التقاط توكن رقم ({len(self.captcha_tokens)}): {token[:30]}...")
        except Exception:
            pass

    def _handover_cookies(self, context: BrowserContext) -> None:
        """حقن الكوكيز الحية للمتصفح داخل جلسة requests لتوحيد بيئة العمل."""
        for cookie in context.cookies():
            self.session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie['domain'],
                path=cookie['path']
            )
        logger.info(f"🔄 تم نقل ملفات تعريف الارتباط بالكامل إلى جلسة Requests.")

    def execute(self) -> bool:
        payload = self._generate_payload()
        target_captcha_token: Optional[str] = None
        
        # --- المرحلة الأولى: تشغيل Playwright لاقتناص التوكن الثاني وتجهيز الجلسة ---
        logger.info("⚡ [المرحلة 1] بدء أتمتة المتصفح لبناء الجلسة واقتناص التوكن الثاني...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(user_agent=self.user_agent, viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            apply_stealth(page)
            page.on("response", self._check_network_response)

            try:
                # الانتقال للموقع لبدء توليد التوكن الأول
                page.goto("https://greenmethods.com/my-account/", wait_until="networkidle", timeout=45000)
                
                # استخراج الـ Register Nonce الأصلي المتزامن مع هذه الجلسة
                html = page.content()
                nonce_match = re.search(r'name="woocommerce-register-nonce"\s*value="([^"]+)"', html)
                if nonce_match:
                    self.register_nonce = nonce_match.group(1)
                    logger.info(f"🟢 الـ Register Nonce المستخرج: {self.register_nonce}")

                # محاكاة سلوك تفاعلي طبيعي
                page.mouse.move(100, 100)
                page.wait_for_timeout(400)
                
                # الكتابة داخل الحقل بقيمة وهمية لتحفيز توليد التوكن الثاني (Action Token)
                logger.info("📝 الكتابة في حقل البريد الإلكتروني لتحفيز التوكن الثاني...")
                page.click("input#reg_email")
                page.type("input#reg_email", payload.email, delay=random.randint(60, 120))
                
                # حلقة انتظار ذكية حتى يتم التقاط توكنين بالتمام أو انتهاء المهلة (30 ثانية)
                timeout_counter = 0
                while len(self.captcha_tokens) < 2 and timeout_counter < 60:
                    page.wait_for_timeout(500)
                    timeout_counter += 1

                # استراتيجية اختيار التوكن الصحيح
                if len(self.captcha_tokens) >= 2:
                    target_captcha_token = self.captcha_tokens[1] # عزل التوكن الثاني المطلـوب
                    logger.info(f"🏆 [نجاح الاقتناص] تم اعتماد التوكن الثاني بنجاح: {target_captcha_token[:40]}...")
                elif len(self.captcha_tokens) == 1:
                    target_captcha_token = self.captcha_tokens[0]
                    logger.warning(f"⚠️ تم العثور على توكن واحد فقط، سيتم استخدامه كخيار بديل.")
                else:
                    logger.error("❌ لم يتم التقاط أي توكن كابتشا من الشبكة. إجهاض العملية.")
                    browser.close()
                    return False
                
                # نسخ هوية الجلسة قبل إغلاق المتصفح
                self._handover_cookies(context)
                
            except Exception as e:
                logger.error(f"❌ خطأ غير متوقع في بيئة المتصفح: {e}")
                browser.close()
                return False
            
            browser.close()
            logger.info("🛑 تم إغلاق المتصفح بنجاح وتوفير كافة موارد النظام.")

        # --- المرحلة الثانية: تنفيذ طلب الـ POST والتسجيل الفعلي عبر Requests السريعة ---
        logger.info("🚀 [المرحلة 2] المتابعة السريعة عبرRequests HTTP Client...")
        
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': 'https://greenmethods.com',
            'Referer': 'https://greenmethods.com/my-account/',
            'Content-Type': 'application/x-www-form-urlencoded'
        })

        # دمج التوكن الثاني بدقة داخل حزمة البيانات المرسلة للـ POST
        post_data = {
            'email': payload.email,
            'password': payload.password,
            'g-recaptcha-response': target_captcha_token, # حقن التوكن الثاني هنا
            'woocommerce-register-nonce': self.register_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }

        try:
            # 1. إرسال طلب إنشاء الحساب مباشرة عبر البروتوكول
            logger.info("📡 إرسال طلب الـ POST الفعلي للتسجيل...")
            self.session.post("https://greenmethods.com/my-account/", data=post_data, timeout=20)
            
            # 2. الانتقال الفوري لصفحة العناوين للتأكد من نجاح التوثيق واستخراج النونس الثاني
            logger.info("📬 طلب صفحة تحرير العناوين لاستخراج الـ Address Nonce...")
            addr_response = self.session.get("https://greenmethods.com/my-account/edit-address/billing/", timeout=15)
            
            if addr_response.status_code == 200:
                match = re.search(r'name="woocommerce-edit-address-nonce"\s*value="([^"]+)"', addr_response.text)
                if match:
                    self.address_nonce = match.group(1)
                    logger.info(f"🏆 [نجاح بروتوكولي باهر] تم التسجيل واستخراج Address Nonce بنجاح: {self.address_nonce}")
                    return True
                else:
                    logger.error("❌ لم يتم العثور على Address Nonce. يبدو أن الخادم رفض التوكن الثاني أو هناك حظر IP.")
            else:
                logger.error(f"❌ فشل في جلب الصفحة، كود الاستجابة: {addr_response.status_code}")

        except Exception as e:
            logger.critical(f"💥 خطأ بروتوكولي أثناء معالجة الطلبات: {e}")

        return False

if __name__ == "__main__":
    engine = OptimizedHybridWooCommerceEngine()
    success = engine.execute()
    print(f"\n📈 الحالة الهندسية النهائية: {'✅ SUCCESS' if success else '❌ FAILED'}")
