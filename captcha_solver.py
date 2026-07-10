import re
from playwright.sync_api import sync_playwright

# متغير عالمي لحفظ التوكن فور التقاطه
CAPTCHA_TOKEN = None

def check_network_response(response):
    global CAPTCHA_TOKEN
    
    # الفحص الحصري لطلب الكابتشا الذي حددته فقط
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            # استخدام الـ Regex الخاص بك للاستخراج المباشر
            match = re.search(r'rresp","(.+?)"', body)
            if match:
                CAPTCHA_TOKEN = match.group(1)
        except Exception:
            pass

def main():
    with sync_playwright() as p:
        # 1. تشغيل المتصفح بوضع مرئي (headless=False) وهو السر الأساسي لرفع الموثوقية
        # 2. تمرير خيار disable-blink-features لإخفاء حقيقة أنه يُدار برمجياً
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 3. إعطاء المتصفح هوية (User-Agent) طبيعية ونظيفة تماماً
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        # ربط الاستماع بالاستجابات
        page.on("response", check_network_response)
        
        print("🚀 جاري فتح الصفحة والتقاط توكن عالي الموثوقية...")
        page.goto("https://greenmethods.com/my-account/", wait_until="commit")
        
        # 4. محاكاة حركة ماوس بسيطة جداً لإقناع جوجل بأننا لسنا روبوت صامت
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
        
        # حفظ التوكن في ملف نصي صغير لاستخدامه مباشرة
        with open("valid_token.txt", "w") as f:
            f.write(CAPTCHA_TOKEN)
            
        browser.close()

if __name__ == "__main__":
    main()
