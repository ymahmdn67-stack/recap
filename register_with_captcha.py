import re
import json
import base64
import random
import time
import requests
from faker import Faker
from playwright.sync_api import sync_playwright

BASE_URL = "https://greenmethods.com"
DOMAIN = "greenmethods.com"

# إنشاء بيانات وهمية للتسجيل
fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
k = f"{f} {l}"
e = f"{f.lower()}.{l.lower()}@gmail.com"

cap = None

def check_network_response(response):
    global cap
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            match = re.search(r'rresp","(.+?)"', body)
            if match:
                cap = match.group(1)
                print(f"   [✔] تم التقاط توكن الكابتشا من الشبكة بنجاح! الطول: {len(cap)} حرف.")
        except Exception as err:
            print(f"   [❌] خطأ أثناء استخراج التوكن من الاستجابة: {err}")

def fetch_captcha_token():
    global cap
    print("\n[*] جاري تشغيل متصفح Playwright للحصول على التوكن...")
    with sync_playwright() as p:
        # إضافة خيارات السيرفر لضمان عمل xvfb-run بدون مشاكل
        browser = p.chromium.launch(
            headless=False, 
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.on("response", check_network_response)
        
        print(f"[*] جاري فتح صفحة الحساب: {BASE_URL}/my-account/")
        page.goto(f"{BASE_URL}/my-account/", wait_until="commit")
        
        print("[*] جاري محاكاة حركة الماوس لرفع موثوقية التوكن (Score)...")
        page.mouse.move(100, 100)
        page.wait_for_timeout(500)
        page.mouse.move(250, 300)
        
        print("[⏳] في انتظار استجابة الكابتشا...")
        start_time = time.time()
        while cap is None:
            page.wait_for_timeout(500)
            # تجنب الانتظار اللانهائي (مهلة دقيقة واحدة)
            if time.time() - start_time > 60:
                print("[❌] تجاوز المهلة الزمنية (60 ثانية) ولم يتم التقاط التوكن.")
                break
            
        browser.close()
    return cap

def main():
    global cap
    
    print("="*60)
    print(f"🚀 بدء عملية أتمتة التسجيل للمستخدم: {k}")
    print(f"📧 البريد الإلكتروني المستخدم: {e}")
    print("="*60)
    
    # 1. الحصول على التوكن
    cap = fetch_captcha_token()
    if not cap:
        print("[❌] توقف البرنامج لعدم توفر توكن كابتشا موثوق.")
        return

    r = requests.Session()
    
    headers_get = {
        'authority': DOMAIN,
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
    
    # 2. طلب الصفحة للحصول على Nonce التسجيل
    print("\n[+] جاري إرسال طلب GET للموقع لجلب الـ nonce المخصص للتسجيل...")
    response = r.get(f'{BASE_URL}/my-account/', headers=headers_get)
    print(f"    [-] حالة استجابة الـ GET: {response.status_code}")
    
    non_register = re.search(
        r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"',
        response.text
    )
    
    register_nonce_val = ""
    if non_register:
        register_nonce_val = non_register.group(1)
        print(f"    [✔] تم استخراج woocommerce-register-nonce بنجاح: {register_nonce_val}")
    else:
        print("    [❌] فشل استخراج الـ nonce الخاص بالتسجيل! قد لا تكتمل العملية.")
    
    # 3. إرسال طلب الـ POST لإتمام التسجيل
    headers_post = {
        'authority': DOMAIN,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': BASE_URL,
        'referer': f'{BASE_URL}/my-account/',
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
        'wc_order_attribution_session_entry': f'{BASE_URL}/my-account/',
        'wc_order_attribution_session_start_time': '2026-07-09 22:38:43',
        'wc_order_attribution_session_pages': '2',
        'wc_order_attribution_session_count': '1',
        'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'woocommerce-register-nonce': register_nonce_val,
        '_wp_http_referer': '/my-account/',
        'register': 'Register',
    }
    
    print("\n[+] جاري إرسال طلب POST لإنشاء الحساب وتمرير الكابتشا والمحددات...")
    response = r.post(f'{BASE_URL}/my-account/', headers=headers_post, data=data)
    print(f"    [-] حالة استجابة الـ POST: {response.status_code}")
    
    # فحص أولي لمعرفة نجاح التسجيل
    if "reCAPTCHA verification failed" in response.text:
        print("    [❌] خطأ بالسيرفر: فشل التحقق من الكابتشا (reCAPTCHA verification failed).")
    elif "Registration Form" not in response.text or "logout" in response.text.lower():
         print("    [✔] مؤشر أولي: يبدو أن عملية التسجيل نجحت وتم إنشاء الحساب والولوج!")
    else:
         print("    [⚠️] تم إرسال الطلب، لكن لم يتم تأكيد نجاح التسجيل أو فشله من محتوى الصفحة.")

if __name__ == "__main__":
    main()
