import requests
import re
import json
import base64
import random
import time
from faker import Faker
from playwright.sync_api import sync_playwright

# متغير عالمي لحفظ التوكن فور التقاطه
CAPTCHA_TOKEN = None

def check_network_response(response):
    global CAPTCHA_TOKEN
    
    # الفحص الحصري لطلب الكابتشا
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            # الاستخراج المباشر للتوكن
            match = re.search(r'rresp","(.+?)"', body)
            if match:
                CAPTCHA_TOKEN = match.group(1)
        except Exception:
            pass

def get_captcha_token():
    global CAPTCHA_TOKEN
    CAPTCHA_TOKEN = None
    
    with sync_playwright() as p:
        # تشغيل المتصفح بوضع مرئي
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # إعطاء المتصفح هوية طبيعية
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        # ربط الاستماع بالاستجابات
        page.on("response", check_network_response)
        
        print("🚀 جاري فتح الصفحة والتقاط توكن عالي الموثوقية...")
        page.goto("https://greenmethods.com/my-account/", wait_until="commit")
        
        # محاكاة حركة ماوس بسيطة جداً
        page.mouse.move(100, 100)
        page.wait_for_timeout(500)
        page.mouse.move(250, 300)
        
        # حلقة الانتظار الذكية - تتوقف فوراً عند العثور على التوكن
        while CAPTCHA_TOKEN is None:
            page.wait_for_timeout(500)
            
        print("\n🎉 تم التقاط التوكن بنجاح وبأعلى موثوقية!")
        print("-" * 50)
        print("TOKEN =", CAPTCHA_TOKEN)
        print("-" * 50)
        
        browser.close()
        return CAPTCHA_TOKEN

def register_account():
    # الحصول على التوكن أولاً وتعيينه للمتغير cap
    cap = get_captcha_token()
    
    if not cap:
        print("فشل في الحصول على التوكن. إيقاف العملية.")
        return
        
    print("\nبدء عملية التسجيل...")
    r = requests.Session()
    fake = Faker("en_UK")
    
    f = fake.first_name()
    l = fake.last_name()
    k = f"{f} {l}"
    e = f"{f.lower()}.{l.lower()}@gmail.com"
    print(f"الايميل المستخدم: {e}")
    
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
    
    # الحصول على صفحة التسجيل
    response = r.get('https://greenmethods.com/my-account/', headers=headers)
    
    # استخراج النونس
    non_match = re.search(
        r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"',
        response.text
    )
    
    if non_match:
        non_value = non_match.group(1)
        print(f"تم العثور على النونس للتسجيل: {non_value}")
    else:
        print("لم يتم العثور على النونس للتسجيل")
        return
        
    # تجهيز طلب التسجيل
    post_headers = {
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
        'woocommerce-register-nonce': non_value,
        '_wp_http_referer': '/my-account/',
        'register': 'Register',
    }
    
    # إرسال طلب التسجيل
    print("إرسال طلب التسجيل...")
    post_response = r.post('https://greenmethods.com/my-account/', headers=post_headers, data=data)
    
    if "my-account" in post_response.url or "dashboard" in post_response.text.lower():
        print("✅ تم التسجيل بنجاح أو توجيهك لحسابك!")
    else:
        print("⚠️ قد يكون هناك مشكلة في التسجيل، تحقق من الاستجابة.")
        
    # الخطوة التالية: تحرير العنوان
    edit_headers = {
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
    
    print("جلب صفحة تحرير العنوان...")
    edit_response = r.get('https://greenmethods.com/my-account/edit-address/billing/', headers=edit_headers)
    
    edit_non_match = re.search(
        r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
        edit_response.text
    )
    
    if edit_non_match:
        print(f"تم العثور على النونس لتحرير العنوان: {edit_non_match.group(1)}")
    else:
        print("لم يتم العثور على النونس لتحرير العنوان")

if __name__ == "__main__":
    register_account()
