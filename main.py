import sys
import subprocess

# --- 1. قسم الفحص والتثبيت التلقائي ---
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


# --- 2. الكود الأساسي بعد التعديل ---
from playwright.sync_api import sync_playwright
import re

TOKEN = None

def handle_response(response):
    global TOKEN
    # التعديل الأول: البحث عن api2 بدلاً من enterprise
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            m = re.search(r'rresp","(.+?)"', body)
            if m:
                TOKEN = m.group(1)
        except Exception:
            pass

def main():
    with sync_playwright() as p:
        # ملاحظة: تم ترك headless=True ليعمل في الخلفية، يمكنك تغييرها لـ False إذا أردت رؤية المتصفح
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        page.on("response", handle_response)
        
        print("\nجاري فتح الصفحة والانتظار لالتقاط التوكن...")
        # التعديل الثاني: تغيير الرابط إلى الموقع المطلوب
        page.goto("https://greenmethods.com/my-account/")
        
        # حلقة الانتظار حتى التقاط التوكن
        while TOKEN is None:
            page.wait_for_timeout(1000)
            
        print("\n🎉 تم التقاط التوكن بنجاح من الموقع الجديد!")
        print("TOKEN =", TOKEN)
        
        browser.close()

if __name__ == "__main__":
    main()
