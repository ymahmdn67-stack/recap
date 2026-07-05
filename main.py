from playwright.sync_api import sync_playwright
import re

TOKEN = None

def handle_response(response):
    global TOKEN
    # التحقق من أن الرابط يحتوي على نقطة النهاية المطلوبة
    if "recaptcha/enterprise/reload" in response.url:
        try:
            # Playwright يقوم بفك الضغط (gzip) وفك التشفير تلقائياً
            body = response.text()
            m = re.search(r'rresp","(.+?)"', body)
            if m:
                TOKEN = m.group(1)
        except Exception as e:
            # تجاهل الأخطاء في حال كانت الاستجابة غير قابلة للقراءة
            pass

def main():
    with sync_playwright() as p:
        # تشغيل المتصفح
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # توجيه المتصفح للاستماع إلى جميع الاستجابات وتمريرها للدالة
        page.on("response", handle_response)
        
        print("جاري فتح الصفحة والانتظار لالتقاط التوكن...")
        page.goto("https://recaptcha-demo.appspot.com/recaptcha-v2-invisible.php")
        
        # حلقة انتظار ذكية لا تجمد البرنامج
        while TOKEN is None:
            page.wait_for_timeout(1000) # الانتظار لمدة ثانية واحدة
            
        print("\nتم الالتقاط بنجاح!")
        print("TOKEN =", TOKEN)
        
        browser.close()

if __name__ == "__main__":
    main()
