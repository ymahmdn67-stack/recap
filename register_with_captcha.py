import re
import time
from faker import Faker
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# --- 1. إعداد البيانات العشوائية المتجددة تلقائياً ---
fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
email_address = f"{f.lower()}.{l.lower()}{fake.random_int(min=100, max=999)}@gmail.com"
password_string = "Willia5766ms#123CR7"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

print(f"[*] البيانات التخيلية للحساب الجديد:\n 📧 Email: {email_address}\n 🔑 Password: {password_string}\n" + "-"*30)

# --- 2. تشغيل محرك Playwright مدمجاً مع دروع التخفي التلقائية ---
with Stealth().use_sync(sync_playwright()) as p:
    print("[*] جاري تشغيل المتصفح المتخفي بالكامل (Headless)...")
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
    
    print("[*] جاري فتح صفحة الحساب الرئيسي...")
    page.goto(
        "https://greenmethods.com/my-account/", 
        wait_until="domcontentloaded", 
        timeout=60000
    )
    
    # 3. ملء بيانات نموذج التسجيل لـ WooCommerce
    print("[*] جاري محاكاة كتابة البيانات داخل النموذج آلياً...")
    
    email_input = page.locator("input#reg_email, input[name='email']").first
    email_input.fill(email_address)
    page.wait_for_timeout(600)
    
    password_input = page.locator("input#reg_password, input[name='password']").first
    password_input.fill(password_string)
    page.wait_for_timeout(1000)
    
    # 4. النقر على زر التسجيل بالقوة وتخطي الكابتشا غير المرئية
    print("[*] جاري الضغط على زر إنشاء الحساب وتخطي الحماية الحية الحاحبة...")
    register_button = page.locator("button[name='register'], input[name='register'], button:has-text('Register')").first
    
    # ✅ التعديل الجوهري: استخدام force=True لإجبار المتصفح على نقر الزر وتخطي نافذة Klaviyo المنبثقة
    register_button.click(force=True)
    
    print("[*] في انتظار استجابة السيرفر وتحديث الجلسة (انتظار 8 ثوانٍ)...")
    page.wait_for_timeout(8000)
    
    # 5. فحص محتوى الصفحة للتأكد من نجاح العملية واقتناص الـ Nonces
    html_content = page.content()
    
    if "logout" in html_content.lower() or "customer-logout" in html_content.lower():
        print("[🎉] مبروك! تم تخطي الحماية الحية والتسجيل في السيرفر بنجاح كامل عبر المتصفح المتخفي.")
        
        # 6. الانتقال مباشرة لصفحة الفواتير حاملاً نفس كوكيز الجلسة الناجحة لحصد الـ Nonce
        print("[*] جاري الانتقال الذاتي لصفحة الفواتير الحصرية لحصد الـ Nonce...")
        page.goto(
            "https://greenmethods.com/my-account/edit-address/billing/", 
            wait_until="domcontentloaded",
            timeout=60000
        )
        
        billing_html = page.content()
        address_nonce = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', billing_html)
        
        if address_nonce:
            print(f"[+] تم استخراج Nonce الفواتير بنجاح من داخل الجلسة: {address_nonce.group(1)}")
        else:
            print("[-] تعذر العثور على Nonce الفواتير، يرجى مراجعة تركيبة الصفحة.")
            
    else:
        print("[-] فشل السيرفر في قبول التسجيل. جاري فحص واجهة المستخدم لمعرفة السبب...")
        if page.locator(".woocommerce-error").count() > 0:
            error_messages = page.locator(".woocommerce-error").text_content()
            print(f" ⚠️ رسالة السيرفر: {error_messages.strip()}")
        else:
            print(" ⚠️ لا توجد رسالة خطأ واضحة في الواجهة، قد تكون الحماية الصارمة قد حظرت الطلب تماماً.")

    browser.close()
