import requests
import re
import json
import base64
import user_agent
import random
import time
import sys
import subprocess
from faker import Faker

# --- 1. قسم الفحص والتثبيت التلقائي (من الكود الثاني كما هو) ---
def ensure_playwright_ready():
    try:
        import playwright
    except ImportError:
        print("📦 مكتبة Playwright غير مثبتة. جاري التثبيت الآن...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        print("✅ تم تثبيت مكتبة بايثون بنجاح.")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception:
        print("⚙️ المتصفحات أو ملفات النظام ناقصة. جاري تحميلها وتثبيتها تلقائياً...")
        print("(قد تستغرق هذه العملية دقيقة أو دقيقتين، يرجى الانتظار...)")
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps"])
            print("✅ تم تجهيز المتصفحات وملفات النظام بنجاح!")
        except Exception as install_error:
            print(f"❌ فشل التثبيت التلقائي بسبب: {install_error}")
            sys.exit(1)

# تشغيل الفحص الذكي قبل بدء الكود الأساسي
ensure_playwright_ready()


# --- 2. كود جلب التوكن عبر Playwright ---
from playwright.sync_api import sync_playwright

TOKEN = None

def handle_response(response):
    global TOKEN
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            m = re.search(r'rresp","(.+?)"', body)
            if m:
                TOKEN = m.group(1)
        except Exception:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) 
    page = browser.new_page()
    
    page.on("response", handle_response)
    
    print("\nجاري فتح الصفحة والانتظار لالتقاط التوكن...")
    page.goto("https://greenmethods.com/my-account/")
    
    while TOKEN is None:
        page.wait_for_timeout(1000)
        
    print("\n🎉 تم التقاط التوكن بنجاح من الموقع الجديد!")
    print("TOKEN =", TOKEN)
    
    browser.close()

# تعيين التوكن المجلوب للمتغير cap لاستخدامه في البيانات أدناه
cap = TOKEN


# --- 3. كود الـ Requests والهيدرز الأصلية دون أي تعديل ---
fake = Faker("en_UK")

f = fake.first_name()
l = fake.last_name()
k = f"{f} {l}"
e = f"{f.lower()}.{l.lower()}@gmail.com"

r = requests.Session()

headers = {
    'authority': 'greenmethods.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

response = r.get('https://greenmethods.com/my-account/', headers=headers)

non_search = re.search(
    r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"',
    response.text
)

if non_search:
    print(non_search.group(1))
    non = non_search.group(1) # استخراج النص لتمريره بشكل صحيح في الداتا
else:
    print("Nonce not found")
    non = ""

headers = {
    'authority': 'greenmethods.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://greenmethods.com',
    'referer': 'https://greenmethods.com/my-account/',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

data = {
    'email': e,
    'password': 'Willia5766ms#123CR7',
    'g-recaptcha-response': cap,
    'wc_order_attribution_source_type': 'typein',
    'wc_order_attribution_referrer': '(none)',
    'wc_order_attribution_utm_campaign': '(none)',
    'wc_order_attribution_utm_source': '(direct)',
    'wc_order_attribution_utm_medium': '(none)',
    'wc_order_attribution_utm_content': '(none)',
    'wc_order_attribution_utm_id': '(none)',
    'wc_order_attribution_utm_term': '(none)',
    'wc_order_attribution_utm_source_platform': '(none)',
    'wc_order_attribution_utm_creative_format': '(none)',
    'wc_order_attribution_utm_marketing_tactic': '(none)',
    'wc_order_attribution_session_entry': 'https://greenmethods.com/my-account/',
    'wc_order_attribution_session_start_time': '2026-07-09 22:38:43',
    'wc_order_attribution_session_pages': '2',
    'wc_order_attribution_session_count': '1',
    'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    'woocommerce-register-nonce': non,
    '_wp_http_referer': '/my-account/',
    'register': 'Register',
}

response = r.post('https://greenmethods.com/my-account/', headers=headers, data=data)


headers = {
    'authority': 'greenmethods.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'referer': 'https://greenmethods.com/my-account/edit-address/',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

response = r.get('https://greenmethods.com/my-account/edit-address/billing/', headers=headers)

non_billing = re.search(
    r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
    response.text
)

if non_billing:
    print(non_billing.group(1))
else:
    print("Nonce not found")
