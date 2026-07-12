import logging
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from playwright.sync_api import sync_playwright, Response as PlaywrightResponse, Page, BrowserContext
from playwright_stealth import Stealth
from faker import Faker

# --- إعداد نظام تسجيل الأحداث (Logger) الاحترافي ---
def setup_enterprise_logger() -> logging.Logger:
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

# --- الاستثناءات المخصصة للمشروع ---
class AutomationEngineException(Exception): pass
class BrowserAutomationError(AutomationEngineException): pass
class TokenExtractionError(AutomationEngineException): pass
class NetworkClientError(AutomationEngineException): pass

# --- الإعدادات العامة للنظام (Environment Configuration) ---
@dataclass(frozen=True)
class AppConfig:
    target_url: str = "https://greenmethods.com/my-account"
    billing_url: str = "https://greenmethods.com/my-account/edit-address/billing/"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    timeout_ms: int = 30000
    http_timeout_sec: float = 30.0
    max_retries: int = 4
    backoff_factor: float = 2.0
    headless_mode: bool = True  # اجعلها False إذا كنت تريد مراقبة المتصفح بصرياً

# --- مخزن بيانات الجلسة الحية (State Transfer Object) ---
@dataclass
class SessionContext:
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    session_storage: Dict[str, Any] = field(default_factory=dict)
    register_nonce: Optional[str] = None
    captcha_token: Optional[str] = None

# --- كلاس استخراج الرموز من هيكل الـ HTML ---
class TokenExtractor:
    @staticmethod
    def extract_register_nonce(html_content: str) -> Optional[str]:
        match = re.search(r'name="woocommerce-register-nonce" value="([^"]+)"', html_content)
        return match.group(1) if match else None

    @staticmethod
    def extract_billing_nonce(html_content: str) -> Optional[str]:
        match = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', html_content)
        return match.group(1) if match else None

# --- [تطوير جوهري] كلاس اعتراض الشبكة الذكي المبني على عدّاد الأحداث ---
class NetworkInterceptor:
    def __init__(self) -> None:
        # مصفوفة ديناميكية لتخزين التوكنات المتدفقة بالترتيب لمنع الاستعجال
        self._captured_tokens: list[str] = []

    def handle_response(self, response: PlaywrightResponse) -> None:
        if "recaptcha/api2/reload" in response.url or "recaptcha/api2/userverify" in response.url:
            try:
                response_text = response.text()
                match = re.search(r'rresp Trimmed","([^"]+)"', response_text) or re.search(r'rresp","([^"]+)"', response_text)
                if match:
                    token = match.group(1)
                    self._captured_tokens.append(token)
                    logger.info(f"NetworkInterceptor: Successfully captured Token #{len(self._captured_tokens)}")
            except Exception as e:
                logger.debug(f"NetworkInterceptor: Non-blocking error parsing frame: {e}")

    @property
    def captured_captcha_token(self) -> Optional[str]:
        # نأخذ دائماً التوكن الأحدث والأخير (التوكن الثاني الحاسم)
        if self._captured_tokens:
            return self._captured_tokens[-1]
        return None

    @property
    def token_count(self) -> int:
        return len(self._captured_tokens)

# --- إدارة الكوكيز والتخزين الداخلي للمتصفح ---
class CookieAndStorageManager:
    @staticmethod
    def extract_cookies(context: BrowserContext) -> Dict[str, str]:
        return {cookie['name']: cookie['value'] for cookie in context.cookies()}

    @staticmethod
    def extract_web_storage(page: Page) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        try:
            local_storage = page.evaluate("() => ({ ...localStorage })")
            session_storage = page.evaluate("() => ({ ...sessionStorage })")
            return local_storage, session_storage
        except Exception as e:
            logger.warning(f"CookieAndStorageManager: Failed to extract JS storage layers: {e}")
            return {}, {}

# --- مدير أتمتة المتصفح المتطور (Browser Handoff Core) ---
class BrowserManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.interceptor = NetworkInterceptor()

    def build_authenticated_context(self, mock_email: str) -> SessionContext:
        session_context = SessionContext()
        
        with Stealth().use_sync(sync_playwright()) as playwright_launcher:
            logger.info("BrowserManager: Launching Chromium instance under stealth layer...")
            browser = playwright_launcher.chromium.launch(
                headless=self.config.headless_mode,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent=self.config.user_agent,
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # ربط مستمع الشبكة
            page.on("response", self.interceptor.handle_response)
            
            try:
                logger.info(f"BrowserManager: Navigating to target via DomContentLoaded strategy.")
                page.goto(self.config.target_url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                
                # --- [تحديث] محاكاة السلوك البشري المرن لتوليد بيانات التلغيم (Telemetry) ---
                try:
                    target_selector = '#reg_email' if page.query_selector('#reg_email') else 'input[type="email"]'
                    if page.query_selector(target_selector):
                        page.wait_for_selector(target_selector, timeout=3000)
                        page.focus(target_selector)
                        page.type(target_selector, mock_email, delay=120)  # كتابة ببطء بشري محايد
                        logger.info("BrowserManager: Generated typing telemetry on input field.")
                    else:
                        logger.info("BrowserManager: Form fields not immediately found. Executing movement fallbacks...")
                        page.mouse.move(500, 300)
                        page.mouse.click(500, 300)
                        page.evaluate("window.scrollTo(0, 300);")
                        page.wait_for_timeout(500)
                        page.evaluate("window.scrollTo(0, 0);")
                except Exception as telemetry_err:
                    logger.warning(f"BrowserManager: Handled non-blocking telemetry delay notice: {telemetry_err}")

                # --- [تحديث جوهري] بوابة العبور المشروطة لمنع استعجال الكود ---
                logger.info("BrowserManager: Holding execution gate. Waiting specifically for Token #2 from network stream...")
                start_gate_time = time.time()
                while self.interceptor.token_count < 2:
                    page.wait_for_timeout(200)  # فحص دوري كل 200 ملي ثانية
                    # حد أقصى للأمان لمنع التعليق اللانهائي في حال بطء الشبكة
                    if time.time() - start_gate_time > 8:
                        logger.warning("BrowserManager: Safety gate timeout reached. Moving forward with latest state.")
                        break

                # قراءة الهيكل النهائي لاستخراج الـ Nonce
                html_dom = page.content()
                session_context.register_nonce = TokenExtractor.extract_register_nonce(html_dom)
                
                # [مزامنة حرجة]: سحب الكوكيز الآن بعد أن قام الطلب الثاني بتحديث كوكيز الحماية الديناميكية
                session_context.cookies = CookieAndStorageManager.extract_cookies(context)
                session_context.local_storage, session_context.session_storage = CookieAndStorageManager.extract_web_storage(page)
                
                # إعداد الهيدرز المقترنة بالمتصفح
                session_context.headers = {
                    'User-Agent': self.config.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Origin': self.config.target_url.split('/my-account')[0],
                    'Referer': self.config.target_url + '/',
                    'Connection': 'keep-alive'
                }
                session_context.captcha_token = self.interceptor.captured_captcha_token
                
            except Exception as exception:
                logger.error(f"BrowserManager: Operational crash during page processing: {exception}")
                raise BrowserAutomationError("Failed to orchestrate context handoff layers.") from exception
            finally:
                logger.info("BrowserManager: Releasing browser resources cleanly.")
                context.close()
                browser.close()
                
        return session_context

# --- عميل إرسال الطلبات السريعة عبر طبقة الـ HTTP الخلفية الصامتة ---
class RequestClient:
    def __init__(self, config: AppConfig, session_context: SessionContext) -> None:
        self.config = config
        self.context = session_context
        self.session = requests.Session()
        self._hydrate_session()

    def _hydrate_session(self) -> None:
        self.session.cookies.update(self.context.cookies)
        self.session.headers.update(self.context.headers)
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        logger.info("RequestClient: Internal HTTP Session fully hydrated with synchronized tokens and cookies.")

    def execute_post(self, url: str, payload: Dict[str, Any]) -> requests.Response:
        return self.session.post(url, data=payload, timeout=self.config.http_timeout_sec)

    def execute_get(self, url: str) -> requests.Response:
        return self.session.get(url, timeout=self.config.http_timeout_sec)

# --- منشئ الهويات العشوائية المطابقة للمواصفات الحقيقية ---
class IdentityGenerator:
    def __init__(self) -> None:
        self.faker = Faker("en_US")

    def create_mock_profile(self) -> Dict[str, str]:
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        unique_email = f"{first_name.lower()}.{last_name.lower()}{self.faker.random_int(min=10, max=999)}@gmail.com"
        return {
            "email": unique_email,
            "password": f"StrongSecurePass!{self.faker.random_int(min=100, max=999)}"
        }

# --- المايسترو والمنظم العام لسير العمل (Pipeline Orchestrator) ---
class RegistrationWorkflowOrchestrator:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.identity_provider = IdentityGenerator()

    def run_pipeline(self) -> Optional[str]:
        logger.info("=== STARTING WORKFLOW PIPELINE WITH DATA LIFE-CYCLE HANDOFF ===")
        
        # توليد بيانات مستخدم جديدة مسبقاً لاستخدامها في محاكاة حركة الكيبورد
        account_profile = self.identity_provider.create_mock_profile()
        
        # الخطوة 1: تشغيل أتمتة المتصفح الموجهة بالأحداث لاقتناص التوكن الثاني والكوكيز المتسلسلة
        browser_manager = BrowserManager(self.config)
        session_context = browser_manager.build_authenticated_context(mock_email=account_profile['email'])
        
        # فحص جودة وصحة البيانات الملتقطة قبل الانتقال للشبكة الخلفية
        if not session_context.captcha_token:
            logger.error("Orchestrator: Pipeline aborted. Token #2 was not caught by interceptor.")
            return None
        if not session_context.register_nonce:
            logger.error("Orchestrator: Pipeline aborted. Baseline registration nonce was missing from DOM.")
            return None
            
        logger.info("Orchestrator: Handoff validation passed. Initiating silent back-end HTTP session.")
        
        # الخطوة 2: إنشاء الحساب صامتاً عبر طبقة الـ HTTP فورا وبأعلى درجة وثوقية
        client = RequestClient(self.config, session_context)
        
        post_payload = {
            'email': account_profile['email'],
            'password': account_profile['password'],
            'woocommerce-register-nonce': session_context.register_nonce,
            '_wp_http_referer': '/my-account/',
            'g-recaptcha-response': session_context.captcha_token,
            'register': 'Register'
        }
        
        logger.info(f"Orchestrator: Dispatching silent transaction for: {account_profile['email']}")
        http_response = client.execute_post(self.config.target_url, payload=post_payload)
        response_html = http_response.text
        
        # الخطوة 3: التحقق من نجاح العملية واقتناص رمز الـ Billing Nonce
        if "logout" in response_html.lower() or "customer-logout" in response_html.lower():
            logger.info("Orchestrator: Success! Session successfully established at HTTP layer.")
            
            billing_nonce = TokenExtractor.extract_billing_nonce(response_html)
            if billing_nonce:
                return billing_nonce
                
            logger.info("Orchestrator: Fetching secondary billing endpoint to extract nonce value...")
            billing_page = client.execute_get(self.config.billing_url)
            return TokenExtractor.extract_billing_nonce(billing_page.text)
        else:
            if "verification failed" in response_html.lower():
                logger.error("Orchestrator: Rejected. Google flagged the session scoring as bot traffic.")
            else:
                logger.error("Orchestrator: Handshake failed. The form fields or structure might be out of sync.")
            return None

# --- نقطة الانطلاق الرئيسية للمشروع ---
if __name__ == "__main__":
    system_config = AppConfig(headless_mode=True)
    orchestrator = RegistrationWorkflowOrchestrator(system_config)
    final_token = orchestrator.run_pipeline()
    
    print("\n" + "="*60)
    if final_token:
        print(f"🏆 SUCCESSFUL PIPELINE CONCLUSION (Billing Nonce): {final_token}")
    else:
        print("❌ PIPELINE CONCLUDED: Unable to retrieve valid target session.")
    print("="*60 + "\n")
