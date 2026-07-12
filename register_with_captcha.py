import re
from playwright.sync_api import sync_playwright

# استخدام مصفوفة (List) واضحة لتخزين كل التوكنات المتدفقة بالترتيب
CAPTCHA_TOKENS = []

def check_network_response(response):
    global CAPTCHA_TOKENS
    
    # الفحص الحصري لطلب إعادة تحميل الكابتشا
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            # الـ Regex المرن لالتقاط التوكن بغض النظر عن وجود مسافات أو فواصل ديناميكية
            match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
            if match:
                token = match.group(1)
                CAPTCHA_TOKENS.append(token)
                print(f"✨ [الشبكة] تم رصد توكن وإضافته للمصفوفة. الإجمالي الحالي: {len(CAPTCHA_TOKENS)}")
        except Exception:
            pass

def main():
    global CAPTCHA_TOKENS
    with sync_playwright() as p:
        # تشغيل المتصفح بوضع مرئي لإتمام التفاعل البشري بنجاح
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        # ربط مستمع الشبكة بالاستجابات قبل الانتقال للموقع
        page.on("response", check_network_response)
        
        print("🚀 جاري فتح الصفحة...")
        # تم إرجاعها إلى "commit" كما في كودك الأصلي لمنع تعليق المتصفح أو حدوث الـ Timeout
        page.goto("https://greenmethods.com/my-account/", wait_until="commit")
        
        # محاكاة حركة ماوس وتفاعل حقيقي داخل الصفحة لتحفيز جوجل على إطلاق التوكن الثاني
        page.mouse.move(100, 100)
        page.wait_for_timeout(600)
        page.mouse.move(250, 300)
        
        try:
            # الكتابة ببطء داخل حقل البريد لرفع تقييم الحساب البشري وتوليد التوكن الثاني
            if page.is_visible("input[type='email']"):
                page.type("input[type='email']", "dawn.real.a688rcher99@gmail.com", delay=120)
        except Exception:
            pass

        print("⏳ في انتظار تدفق التوكنات (نستهدف التقاط التوكن الثاني والأحدث)...")
        
        timeout_counter = 0
        # حلقة الانتظار الذكية: الكود لن يتحرك حتى يلتقط توكنين صراحة (أو تمر 15 ثانية كحد أقصى للأمان)
        while len(CAPTCHA_TOKENS) < 2 and timeout_counter < 30:
            page.wait_for_timeout(500)  # فحص حالة المصفوفة كل نصف ثانية
            timeout_counter += 1
            
        print("\n📊 انتهت فترة الفحص الحية. جاري معالجة البيانات المتوفرة:")
        print("-" * 50)
        
        final_token = None
        
        # اختيار التوكن بناءً على ما تم التقاطه في المصفوفة لمنع خطأ الاستعجال
        if len(CAPTCHA_TOKENS) >= 2:
            final_token = CAPTCHA_TOKENS[1]  # اعتماد التوكن الثاني والأحدث مباشرة
            print("🎉 نجاح باهر! تم اقتناص التوكن الثاني (High Score Token).")
        elif len(CAPTCHA_TOKENS) == 1:
            final_token = CAPTCHA_TOKENS[0]  # تراجع احتياطي للتوكن الأول في حال عدم صدور الثاني
            print("⚠️ تم التقاط توكن واحد فقط (التوكن المبدئي)، سيتم اعتماده كخيار احتياطي.")
        else:
            print("❌ فشل السكربت في التقاط أي توكن من الشبكة.")

        # حفظ التوكن المستهدف في الملف النصي لطبقة الـ POST
        if final_token:
            with open("valid_token.txt", "w") as f:
                f.write(final_token)
            print(f"💾 تم حفظ التوكن المعتمد بنجاح في ملف: valid_token.txt")
            print(f"بداية التوكن: {final_token[:40]}...")
        
        print("-" * 50)
        browser.close()

if __name__ == "__main__":
    main()
