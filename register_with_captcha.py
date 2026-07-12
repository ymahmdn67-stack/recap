import re
import time
import random
import json
import base64
import requests
from playwright.sync_api import sync_playwright
from faker import Faker

# محاولة استيراد مكتبة التخفي
try:
    from playwright_stealth import Stealth
    def apply_stealth(page):
        Stealth().apply_stealth_sync(page)
except ImportError:
    def apply_stealth(page):
        pass

# قائمة لتخزين التوكنات الفريدة
CAPTCHA_TOKENS = []

def check_network_response(response):
    global CAPTCHA_TOKENS
    try:
        if "recaptcha/api2/reload" in response.url:
            try:
                body = response.text()
                match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
                if match:
                    token = match.group(1)
                    if token not in CAPTCHA_TOKENS:
                        CAPTCHA_TOKENS.append(token)
            except Exception:
                pass
    except Exception:
        pass

def get_captcha_token():
    """المرحلة الأولى: تشغيل Playwright واقتناص التوكن"""
    global CAPTCHA_TOKENS
    cap = None  
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            apply_stealth(page)
            
            # ربط مستمع الشبكة
            page.on("response", check_network_response)
            
            try:
                page.goto("https://greenmethods.com/my-account/", wait_until="commit", timeout=30000)
            except Exception:
                pass
            
            # محاكاة تفاعل طبيعي
            page.mouse.move(100, 100)
            page.wait_for_timeout(600)
            page.mouse.move(250, 300)
            page.wait_for_timeout(400)
            
            # محاولة الكتابة لتنشيط الحقول
            try:
                email_input = "input[type='email']"
                if page.is_visible(email_input):
                    page.type(email_input, "test.user@greenmethods.com", delay=120)
            except Exception:
                pass
            
            # حلقة الانتظار لالتقاط التوكنات
            timeout_counter = 0
            max_timeout = 60  
            
            while len(CAPTCHA_TOKENS) < 2 and timeout_counter < max_timeout:
                page.wait_for_timeout(500)
                timeout_counter += 1
            
            # تحديد قيمة المتغير cap بناءً على التوكنات الملتَقطة
            if len(CAPTCHA_TOKENS) >= 2:
                cap = CAPTCHA_TOKENS[1]
                print(f"✅ تم بنجاح اقتناص التوكن الثاني (cap): {cap[:50]}...")
            elif len(CAPTCHA_TOKENS) == 1:
                cap = CAPTCHA_TOKENS[0]
                print(f"⚠️ تم العثور على توكن واحد فقط: {cap[:50]}...")
            else:
                print("❌ لم يتم التقاط أي توكن.")
            
            browser.close()
            return cap  # إرجاع التوكن لاستخدامه لاحقاً
            
    except Exception as e:
        print(f"❌ خطأ حرج في مرحلة المتصفح: {str(e)}")
        return None

def execute_requests_session(cap_token):
    """المرحلة الثانية: معالجة الطلبات وإرسال التوكن المستخرج"""
    if not cap_token:
        print("❌ إلغاء العملية: لم يتم توفير توكن CAPTCHA valid.")
        return

    r = requests.Session()
    fake = Faker("en_UK")

    f = fake.first_name()
    l = fake.last_name()
    e = f"{f.lower()}.{l.lower()}@greenmethods.com"

    headers = {
        'authority': 'greenmethods.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    try:
        # 1. طلب الصفحة لاستخراج الـ Nonce الأول
        response = r.get('https://greenmethods.com/my-account/', headers=headers)
        non = re.search(r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"', response.text)

        if non:
            nonce_value = non.group(1)
            print(f"🟢 Nonce المستخرج: {nonce_value}")
        else:
            print("❌ Nonce not found")
            return

        # 2. إرسال طلب التسجيل بالتوكن والـ Nonce
        post_headers = headers.copy()
        post_headers.update({
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://greenmethods.com',
            'referer': 'https://greenmethods.com/my-account/'
        })

        data = {
            'email': e,
            'password': 'Password123#Example',
            'g-recaptcha-response': cap_token,  # استخدام التوكن الممرر هنا
            'woocommerce-register-nonce': nonce_value,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }

        r.post('https://greenmethods.com/my-account/', headers=post_headers, data=data)

        # 3. طلب صفحة تعديل العنوان لاستخراج الـ Nonce الثاني
        response = r.get('https://greenmethods.com/my-account/edit-address/billing/', headers=headers)
        non_address = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', response.text)

        if non_address:
            print(f"🟢 Address Nonce المستخرج: {non_address.group(1)}")
        else:
            print("❌ Address Nonce not found")

    except Exception as e:
        print(f"❌ خطأ أثناء تنفيذ طلبات الـ HTTP: {str(e)}")

if __name__ == "__main__":
    # خطوة 1: استخراج التوكن عبر المتصفح
    captured_token = get_captcha_token()
    
    # خطوة 2: تمرير التوكن مباشرة للجلسة والمتابعة
    execute_requests_session(captured_token)
