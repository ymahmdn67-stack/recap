import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from playwright.sync_api import sync_playwright, Response as PlaywrightResponse, Page, BrowserContext
from playwright_stealth import stealth_sync
from faker import Faker

# ==========================================
# 1. موديول التوثيق المركزي (Logger Module)
# ==========================================
def setup_enterprise_logger() -> logging.Logger:
    """إعداد نظام توثيق مركزي واحترافي لضمان إمكانية تتبع العمليات بدقة."""
    logger = logging.getLogger("CoreAutomationEngine")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger

logger = setup_enterprise_logger()


# ==========================================
# 2. موديول الاستثناءات المخصصة (Exceptions Module)
# ==========================================
class AutomationEngineException(Exception):
    """الاستثناء الأساسي لجميع أخطاء محرك الأتمتة."""
    pass

class BrowserAutomationError(AutomationEngineException):
    """يتم استدعاؤه عند فشل عمليات أتمتة المتصفح أو فشل تخطي الحماية."""
    pass

class TokenExtractionError(AutomationEngineException):
    """يتم استدعاؤه في حال العجز عن استخراج التوكنز الحيوية أو الـ Nonces."""
    pass

class NetworkClientError(AutomationEngineException):
    """يتم استدعاؤه عند حدوث انهيار في الاتصالات أو استجابات HTTP غير المتوقعة."""
    pass


# ==========================================
# 3. موديول الإعدادات (Config Module)
# ==========================================
@dataclass(frozen=True)
class AppConfig:
    """تخزين مركزي ثابت لجميع المتغيرات الحاكمة للمشروع لمنع تشتت البيانات."""
    target_url: str = "https://greenmethods.com/my-account"
    billing_url: str = "https://greenmethods.com/my-account/edit-address/billing/"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/124.0.0.0 Safari/537.36"
    timeout_ms: int = 45000
    http_timeout_sec: float = 30.0
    max_retries: int = 4
    backoff_factor: float = 2.0
    headless_mode: bool = True


# ==========================================
# 4. موديول إدارة حالة الجلسة (Session Storage & Context)
# ==========================================
@dataclass
class SessionContext:
    """كائن البيانات الموحد (DTO) لنقل سياق الجلسة المستخرج بالكامل من Playwright إلى Requests."""
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    session_storage: Dict[str, Any] = field(default_factory=dict)
    register_nonce: Optional[str] = None
    captcha_token: Optional[str] = None


# ==========================================
# 5. موديول استخراج التوكنز والقيم الديناميكية (TokenExtractor Module)
# ==========================================
class TokenExtractor:
    """مسؤولية حصرية عن معالجة النصوص و الـ DOM وقشط العناصر الحساسة."""
    
    @staticmethod
    def extract_register_nonce(html_content: str) -> Optional[str]:
        """استخراج توكن التسجيل الخاص بـ WooCommerce من الـ HTML المتولد."""
        match = re.search(r'name="woocommerce-register-nonce" value="([^"]+)"', html_content)
        return match.group(1) if match else None

    @staticmethod
    def extract_billing_nonce(html_content: str) -> Optional[str]:
        """استخراج توكن تعديل بيانات الفواتير بعد تسجيل الدخول بنجاح."""
        match = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', html_content)
        return match.group(1) if match else None


# ==========================================
# 6. موديول اعتراض حركة الشبكة (NetworkInterceptor Module)
# ==========================================
class NetworkInterceptor:
    """مسؤول عن مراقبة الطلبات الخلفية واقتناص استجابات Google reCAPTCHA العميقة."""
    
    def __init__(self) -> None:
        self._captured_captcha_token: Optional[str] = None

    def handle_response(self, response: PlaywrightResponse) -> None:
        """اعتراض وتحليل الاستجابات الشبكية بحثاً عن التوكن عالي الموثوقية."""
        if "recaptcha/api2/reload" in response.url or "recaptcha/api2/userverify" in response.url:
            try:
                response_text = response.text()
                # النمط المتقدم لاستخراج التوكن الصافي من مصفوفات استجابة جوجل
                match = re.search(r'rresp","([^"]+)"', response_text) or re.search(r'rresp Trimmed","([^"]+)"', response_text)
                if match:
                    self._captured_captcha_token = match.group(1)
                    logger.info("NetworkInterceptor: Successfully intercepted and decoded dynamic reCAPTCHA token.")
            except Exception as e:
                logger.debug(f"NetworkInterceptor: Non-blocking error reading network body: {e}")

    @property
    def captured_captcha_token(self) -> Optional[str]:
        return self._captured_captcha_token


# ==========================================
# 7. موديول إدارة الكوكيز والتخزين المحامي (Cookie & Storage Manager)
# ==========================================
class CookieAndStorageManager:
    """مسؤول عن استخلاص جميع أنواع الكوكيز والتخزين المحلي من سياق المتصفح بصيغة متوافقة."""
    
    @staticmethod
    def extract_cookies(context: BrowserContext) -> Dict[str, str]:
        """تحويل مصفوفة كوكيز Playwright المعقدة إلى قاموس Flat Dictionary مناسب لـ Requests."""
        return {cookie['name']: cookie['value'] for cookie in context.cookies()}

    @staticmethod
    def extract_web_storage(page: Page) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """قراءة الـ Local Storage والـ Session Storage من سياق الـ JavaScript الآمن."""
        try:
            local_storage = page.evaluate("() => ({ ...localStorage })")
            session_storage = page.evaluate("() => ({ ...sessionStorage })")
            return local_storage, session_storage
        except Exception as e:
            logger.warning(f"CookieAndStorageManager: Failed to extract JS storage layers: {e}")
            return {}, {}


# ==========================================
# 8. موديول إدارة وتنظيم المتصفح (BrowserManager Module)
# ==========================================
class BrowserManager:
    """المتحكم الحصري بدورة حياة المتصفح (Chromium)، وإعداد بيئة متخفية بالكامل (Stealth)."""
    
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.interceptor = NetworkInterceptor()

    def build_authenticated_context(self) -> SessionContext:
        """تشغيل المتصفح، تحميل الصفحة بالكامل، محاكاة السلوك البشري، ثم استخلاص البيانات وإغلاق الموارد."""
        session_context = SessionContext()
        
        with sync_playwright() as playwright_launcher:
            logger.info("BrowserManager: Launching Chromium core instance under stealth parameters...")
            browser = playwright_launcher.chromium.launch(
                headless=self.config.headless_mode,
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars'
                ]
            )
            
            # إنشاء سياق متصفح منعزل تماماً مع حقن الـ User-Agent
            context = browser.new_context(
                user_agent=self.config.user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            stealth_sync(page)  # تطبيق نظام الحماية المتقدم لإخفاء هويتنا البرمجية عن جدران الحماية

            # ربط موديول اعتراض الشبكة بأحداث الصفحة الحية
            page.on("response", self.interceptor.handle_response)

            try:
                logger.info(f"BrowserManager: Navigation triggered to target: {self.config.target_url}")
                page.goto(self.config.target_url, wait_until="networkidle", timeout=self.config.timeout_ms)
                
                # ميكانيكية انتظار ذكية مضافة لضمان استقرار تحميل نصوص جافاسكريبت الخلفية وعناصر AJAX
                page.wait_for_timeout(6000)
                
                # محاكاة حركة بشرية متناهية الصغر لتنشيط طلبات كابتشا جوجل غير المرئية (v3 / Enterprise Reload)
                page.mouse.move(150, 150)
                page.wait_for_timeout(500)
                page.mouse.move(400, 350)
                page.wait_for_timeout(1000)

                # قراءة الـ DOM المكتمل لاستخراج الـ Nonce الخاص بالتسجيل
                html_dom = page.content()
                session_context.register_nonce = TokenExtractor.extract_register_nonce(html_dom)
                
                if session_context.register_nonce:
                    logger.info(f"BrowserManager: Core registration nonce found: {session_context.register_nonce}")
                else:
                    logger.warning("BrowserManager: Registration nonce was not detected in initial DOM sweep.")

                # تجميع كافة الكوكيز والـ Storage الطبقية
                session_context.cookies = CookieAndStorageManager.extract_cookies(context)
                session_context.local_storage, session_context.session_storage = CookieAndStorageManager.extract_web_storage(page)
                
                # بناء ترويسات (Headers) قياسية مطابقة تماماً للمتصفح لمنع تجميد الاتصال لاحقاً
                session_context.headers = {
                    'User-Agent': self.config.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Origin': self.config.target_url.split('/my-account')[0],
                    'Referer': self.config.target_url + '/',
                    'Connection': 'keep-alive'
                }
                
                session_context.captcha_token = self.interceptor.captured_captcha_token

            except Exception as exception:
                logger.error(f"BrowserManager: Critical structural error during automation: {exception}")
                raise BrowserAutomationError("Failed to successfully orchestrate cold browser context initialization.") from exception
            finally:
                logger.info("BrowserManager: Closing browser architecture and releasing system resources to memory.")
                context.close()
                browser.close()
                
        return session_context


# ==========================================
# 9. موديول مدير اتصالات الشبكة الصامتة (RequestClient Module)
# ==========================================
class RequestClient:
    """عميل HTTP ذكي ومتقدم مبني فوق Requests Session، يدعم تجميع الاتصالات وإعادة المحاولة التلقائية."""
    
    def __init__(self, config: AppConfig, session_context: SessionContext) -> None:
        self.config = config
        self.context = session_context
        self.session = requests.Session()
        self._hydrate_and_configure_session()

    def _hydrate_and_configure_session(self) -> None:
        """حقن بيانات الجلسة المنقولة بالكامل وتهيئة الـ Connection Pooling وإستراتيجيات التراجع الأسّي."""
        self.session.cookies.update(self.context.cookies)
        self.session.headers.update(self.context.headers)

        # إعداد ميكانيكية التراجع الأسّي المتطورة لإعادة المحاولة عند مواجهة تقطعات شبكية أو أخطاء السيرفرات المؤقتة
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        
        # ربط الـ Adapter لضمان تجميع قنوات الاتصال (Connection Pooling) بحد أقصى 15 اتصالاً متوازياً
        http_adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=15, pool_maxsize=15)
        self.session.mount("http://", http_adapter)
        self.session.mount("https://", http_adapter)
        logger.info("RequestClient: Network session fully hydrated with cookies, headers, and pooling configurations.")

    def execute_post(self, url: str, payload: Dict[str, Any]) -> requests.Response:
        """تنفيذ طلب POST آمن تحت حماية مهلات الاتصال الصارمة."""
        try:
            response = self.session.post(url, data=payload, timeout=self.config.http_timeout_sec)
            return response
        except requests.RequestException as e:
            logger.error(f"RequestClient: Core POST operation failed on endpoint: {url}. Details: {e}")
            raise NetworkClientError(f"HTTP POST operation fundamentally collapsed: {e}") from e

    def execute_get(self, url: str) -> requests.Response:
        """تنفيذ طلب GET معزول وآمن لاستدعاء البيانات والـ Nonces اللاحقة."""
        try:
            response = self.session.get(url, timeout=self.config.http_timeout_sec)
            return response
        except requests.RequestException as e:
            logger.error(f"RequestClient: Core GET operation failed on endpoint: {url}. Details: {e}")
            raise NetworkClientError(f"HTTP GET operation fundamentally collapsed: {e}") from e


# ==========================================
# 10. موديول المساعدات العامة (Utils Module)
# ==========================================
class IdentityGenerator:
    """مسؤول عن توليد هويات عشوائية نظيفة للاستخدام في التسجيل لمنع تكرار البيانات الصامتة."""
    
    def __init__(self) -> None:
        self.faker = Faker("en_UK")

    def create_mock_profile(self) -> Dict[str, str]:
        """إنشاء بروفايل مستخدم وهمي متوافق مع شروط التسجيل."""
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        # إضافة قيمة رقمية ديناميكية لضمان عدم حدوث خطأ "المستخدم مسجل مسبقاً" في السيرفر
        unique_email = f"{first_name.lower()}.{last_name.lower()}{self.faker.random_int(min=1000, max=9999)}@gmail.com"
        return {
            "email": unique_email,
            "password": "ComplexSecurePassword!2026#$"
        }


# ==========================================
# 11. المنسق العام لسير العمل (Orchestrator Module)
# ==========================================
class RegistrationWorkflowOrchestrator:
    """المايسترو المسؤول عن تجميع كافة الموديولات السابقة وإدارة تدفق البيانات من البداية للنهاية."""
    
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.identity_provider = IdentityGenerator()

    def run_pipeline(self) -> Optional[str]:
        """تنفيذ خط الإنتاج بالكامل والوصول للنتيجة النهائية."""
        logger.info("=== STARTING ARCHITECTURAL STATE HANDOFF WORKFLOW ===")
        
        # المرحلة الأولى: تشغيل طبقة الأتمتة واستخراج بذور الجلسة الحية
        browser_manager = BrowserManager(self.config)
        session_context = browser_manager.build_authenticated_context()

        # التحقق من توفر العناصر الحاكمة قبل المخاطرة بإرسال طلب الـ HTTP Layer
        if not session_context.captcha_token:
            logger.error("Orchestrator: Aborting execution. Critical 'g-recaptcha-response' token was not intercepted.")
            return None
        
        if not session_context.register_nonce:
            logger.error("Orchestrator: Aborting execution. Critical Woocommerce Registration Nonce is missing.")
            return None

        logger.info("Orchestrator: Session context verification passed. Transitioning execution completely to HTTP Layer.")

        # المرحلة الثانية: تهيئة عميل الـ HTTP وحقن الحالة المعزولة بالكامل
        client = RequestClient(self.config, session_context)
        account_profile = self.identity_provider.create_mock_profile()

        # بناء الـ Payload المطابق تماماً لنمط إرسال المتصفح الأصلي
        post_payload = {
            'email': account_profile['email'],
            'password': account_profile['password'],
            'woocommerce-register-nonce': session_context.register_nonce,
            '_wp_http_referer': '/my-account/',
            'g-recaptcha-response': session_context.captcha_token,
            'register': 'Register'
        }

        # المرحلة الثالثة: تنفيذ عملية التسجيل الصامتة عبر الـ Backend مباشرة وبسرعة هائلة
        logger.info(f"Orchestrator: Submitting silent registration for entity: {account_profile['email']}")
        http_response = client.execute_post(self.config.target_url, payload=post_payload)
        response_html = http_response.text

        # المرحلة الرابعة: تحليل الاستجابة والتحقق من انتقال حالة الجلسة بنجاح
        if "logout" in response_html.lower() or "customer-logout" in response_html.lower():
            logger.info("🎉 Orchestrator: Registration completed successfully via HTTP Session Handoff!")
            
            # محاولة قشط الـ Billing Nonce من صفحة الرد الفورية في حال توفرها
            billing_nonce = TokenExtractor.extract_billing_nonce(response_html)
            if billing_nonce:
                logger.info("Orchestrator: Billing nonce extracted directly from initial authentication payload.")
                return billing_nonce
            
            # إذا لم تكن موجودة، نتوجه لصفحة تعديل عنوان الفواتير مباشرة معتمدين على نفس الجلسة المستمرة
            logger.info("Orchestrator: Navigating to billing sub-domain endpoint to fetch secondary nonces...")
            billing_page_response = client.execute_get(self.config.billing_url)
            billing_nonce = TokenExtractor.extract_billing_nonce(billing_page_response.text)
            
            if billing_nonce:
                return billing_nonce
            else:
                logger.warning("Orchestrator: Registration succeeded, but the billing nonce structure has changed in the DOM.")
                return None
        else:
            if "recaptcha verification failed" in response_html.lower():
                logger.error("Orchestrator: Registration rejected by target security layer due to poor reCAPTCHA score (IP reputation low).")
            else:
                logger.error("Orchestrator: Registration request failed to authenticate. Check structure variables or proxy constraints.")
            return None


# ==========================================
# 12. نقطة الانطلاق الرسمية (Application Entrypoint)
# ==========================================
if __name__ == "__main__":
    # تهيئة الإعدادات المركزية (يمكنك تمرير headless_mode=False إذا كنت ترغب في رؤية المتصفح أثناء الفحص والمراجعة البصرية)
    system_config = AppConfig(headless_mode=True)
    
    # بناء وتشغيل خط الإنتاج المنسق
    pipeline_orchestrator = RegistrationWorkflowOrchestrator(system_config)
    final_billing_token = pipeline_orchestrator.run_pipeline()
    
    print("\n" + "="*50)
    if final_billing_token:
        print(f"[🏆] ULTIMATE PRODUCTION RESULT (Billing Nonce): {final_billing_token}")
    else:
        print("[-] System automation workflow concluded without capturing the final Billing Nonce.")
    print("="*50 + "\n")

