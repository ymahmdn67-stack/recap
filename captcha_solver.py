import re
import time
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
    def apply_stealth(page):
        Stealth().apply_stealth_sync(page)
except ImportError:
    def apply_stealth(page):
        pass

# قائمة لتخزين التوكنات الفريدة
CAPTCHA_TOKENS = []

def check_network_response(response):
    global CAPTCHA_TOKENS
    try:
        if "recaptcha/api2/reload" in response.url:
            try:
                body = response.text()
                match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
                if match:
                    token = match.group(1)
                    if token not in CAPTCHA_TOKENS:
                        CAPTCHA_TOKENS.append(token)
            except Exception:
                pass
    except Exception:
        pass

def main():
    global CAPTCHA_TOKENS
    cap = None  # تعريف متغير التوكن الثاني
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            apply_stealth(page)
            
            # ربط مستمع الشبكة
            page.on("response", check_network_response)
            
            try:
                page.goto("https://greenmethods.com/my-account/", wait_until="commit", timeout=30000)
            except Exception:
                pass
            
            # محاكاة تفاعل طبيعي
            page.mouse.move(100, 100)
            page.wait_for_timeout(600)
            page.mouse.move(250, 300)
            page.wait_for_timeout(400)
            
            # محاولة الكتابة في حقل البريد لتنشيط الكابتشا
            try:
                email_input = "input[type='email']"
                if page.is_visible(email_input):
                    page.type(email_input, "dawn.real.a688rcher99@gmail.com", delay=120)
            except Exception:
                pass
            
            # حلقة الانتظار لالتقاط التوكنات (بحد أقصى 30 ثانية)
            timeout_counter = 0
            max_timeout = 60  
            
            while len(CAPTCHA_TOKENS) < 2 and timeout_counter < max_timeout:
                page.wait_for_timeout(500)
                timeout_counter += 1
            
            # تحديد قيمة المتغير cap بناءً على التوكنات الملتَقطة
            if len(CAPTCHA_TOKENS) >= 2:
                cap = CAPTCHA_TOKENS[1]  # التوكن الثاني بالتمام
                print(f"✅ تم بنجاح اقتناص التوكن الثاني (cap): {cap[:50]}...")
            elif len(CAPTCHA_TOKENS) == 1:
                cap = CAPTCHA_TOKENS[0]
                print(f"⚠️ تم العثور على توكن واحد فقط: {cap[:50]}...")
            else:
                print("❌ لم يتم التقاط أي توكن.")
            
            browser.close()
            
            # (يمكنك الآن استخدام المتغير cap هنا مباشرة في بقية سكربتك)
            
    except Exception as e:
        print(f"❌ خطأ حرج: {str(e)}")

if __name__ == "__main__":
    main()
