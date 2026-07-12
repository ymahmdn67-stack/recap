import re
from playwright.sync_api import sync_playwright
# استيراد أداة التخفي الاحترافية المثبتة في بيئتك لمنع كشف الـ Bot Traffic
from playwright_stealth import stealth_sync

# مصفوفة لحفظ التوكنات المتعاقبة
CAPTCHA_TOKENS = []

def check_network_response(response):
    global CAPTCHA_TOKENS
    
    # مراقبة الرابط المخصص لإعادة تحميل الكابتشا
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            # الـ Regex المطور للتعامل مع الفواصل والمسافات الديناميكية ["rresp"\s*,\s*"TOKEN"]
            match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
            if match:
                token = match.group(1)
                CAPTCHA_TOKENS.append(token)
                print(f"✨ [الشبكة] تم التقاط التوكن رقم #{len(CAPTCHA_TOKENS)} بنجاح.")
        except Exception:
            pass

def main():
    with sync_playwright() as p:
        # تشغيل المتصفح بوضع مرئي مع تعطيل سمات التحكم الآلي القياسية
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.new_page()
        
        # 🛡️ تفعيل نظام التخفي لتجاوز خوارزمية فحص الروبوتات الحساسة لجوجل
        stealth_sync(page)
        
        # ربط الاستماع بالاستجابات
        page.on("response", check_network_response)
        
        print("🚀 جاري فتح الصفحة وتوليد تفاعلات بشرية لمحاكاة حركة طبيعية...")
        page.goto("https://greenmethods.com/my-account/", wait_until="networkidle")
        
        # 1. محاكاة حركة ماوس طبيعية أفقياً وعمودياً
        page.mouse.move(200, 200)
        page.wait_for_timeout(1000)
        page.mouse.move(400, 500)
        
        # 2. تحفيز حماية جوجل لإصدار التوكن الثاني عبر الكتابة داخل الحقول بصورة طبيعية
        try:
            # البحث عن حقل البريد والكتابة فيه بتأخير زمني يحاكي البشر (delay)
            if page.is_visible("input[type='email']"):
                page.type("input[type='email']", "dawn.real.a688rcher99@gmail.com", delay=120)
                page.wait_for_timeout(800)
                page.type("input[type='password']", "Williams#123CR7", delay=150)
                print("⌨️ تم ملء الحقول لمحاكاة التفاعل وتحفيز التوكن الثاني...")
        except Exception as e:
            print("⚠️ لم يتم العثور على حقول الإدخال مباشرة، الاعتماد على حركة المتصفح العامة.")
            
        page.mouse.move(100, 300)
        
        # حلقة الانتظار الذكية - تتوقف فوراً عند التقاط التوكن الثاني (أو بعد 20 ثانية كحد أقصى)
        timeout_counter = 0
        while len(CAPTCHA_TOKENS) < 2 and timeout_counter < 40:
            page.wait_for_timeout(500)
            timeout_counter += 1
            
        # فحص النتائج وحفظ التوكن الثاني عالي الموثوقية
        if len(CAPTCHA_TOKENS) >= 2:
            second_token = CAPTCHA_TOKENS[1]
            print("\n🎉 نجاح باهر! تم اقتناص التوكن الثاني (High Score Token)")
            print("-" * 60)
            print("SECOND_TOKEN =", second_token[:50] + "...")
            print("-" * 60)
            
            # حفظ التوكن الثاني في ملفك النصي لاعتماده في طلب الـ POST
            with open("valid_token.txt", "w") as f:
                f.write(second_token)
            print("💾 تم حفظ التوكن الثاني بنجاح في ملف valid_token.txt")
        else:
            print("\n⚠️ تنبيه: لم يتم التقاط التوكن الثاني.")
            if len(CAPTCHA_TOKENS) == 1:
                print("تم حفظ التوكن الأول كخيار احتياطي.")
                with open("valid_token.txt", "w") as f:
                    f.write(CAPTCHA_TOKENS[0])
            
        browser.close()

if __name__ == "__main__":
    main()
