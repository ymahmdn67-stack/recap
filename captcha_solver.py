import re
import time
from playwright.sync_api import sync_playwright

# --- الاستيراد الصحيح لمكتبة playwright-stealth (الإصدار الجديد) ---
# المشكلة: stealth هو module وليس دالة قابلة للاستدعاء
# الحل: استخدام Stealth() كـ class ثم استدعاء apply_stealth_sync(page)
try:
    from playwright_stealth import Stealth
    def apply_stealth(page):
        Stealth().apply_stealth_sync(page)
except ImportError:
    # في حالة عدم توفر المكتبة، نعرّف دالة وهمية
    def apply_stealth(page):
        print("⚠️ تحذير: مكتبة playwright_stealth غير مثبتة. قد يتم كشف الأتمتة.")

# استخدام قائمة لتخزين التوكنات المتدفقة بالترتيب
CAPTCHA_TOKENS = []

def check_network_response(response):
    """
    فحص استجابات الشبكة والبحث عن توكنات الكابتشا
    """
    global CAPTCHA_TOKENS
    
    try:
        # الفحص الحصري لطلب إعادة تحميل الكابتشا
        if "recaptcha/api2/reload" in response.url:
            try:
                # محاولة الحصول على نص الاستجابة بشكل آمن
                body = response.text()
                
                # البحث عن التوكن باستخدام regex مرن
                # يتعامل مع المسافات والفواصل الديناميكية
                match = re.search(r'rresp"\s*,\s*"([^"]+)"', body)
                
                if match:
                    token = match.group(1)
                    
                    # التحقق من عدم تكرار التوكن
                    if token not in CAPTCHA_TOKENS:
                        CAPTCHA_TOKENS.append(token)
                        print(f"✨ [الشبكة] تم رصد توكن جديد. الإجمالي الحالي: {len(CAPTCHA_TOKENS)}")
                        print(f"   بداية التوكن: {token[:30]}...")
                    else:
                        print(f"ℹ️ [الشبكة] تم رصد توكن مكرر (تم تجاهله)")
                        
            except Exception as e:
                print(f"⚠️ خطأ في معالجة استجابة الشبكة: {str(e)}")
                
    except Exception as e:
        print(f"❌ خطأ في فحص الاستجابة: {str(e)}")

def main():
    """
    الدالة الرئيسية لتشغيل السكربت
    """
    global CAPTCHA_TOKENS
    
    try:
        with sync_playwright() as p:
            print("🚀 جاري تهيئة المتصفح...")
            
            # تشغيل المتصفح بوضع مرئي
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'  # تحسين الأداء
                ]
            )
            
            # إنشاء سياق جديد مع user agent واقعي
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}  # دقة واقعية
            )
            
            page = context.new_page()
            
            # 🛡️ تفعيل نظام حماية المتصفح لتجاوز فحص الروبوتات
            print("🛡️ جاري تفعيل وضع الحماية ضد كشف الأتمتة...")
            apply_stealth(page)
            
            # ربط مستمع الشبكة بالاستجابات قبل الانتقال للموقع
            page.on("response", check_network_response)
            
            print("🌐 جاري فتح الصفحة...")
            try:
                page.goto("https://greenmethods.com/my-account/", wait_until="commit", timeout=30000)
            except Exception as e:
                print(f"⚠️ تحذير: حدث خطأ أثناء تحميل الصفحة: {str(e)}")
            
            # محاكاة حركة ماوس وتفاعل حقيقي
            print("🖱️ جاري محاكاة تفاعل المستخدم...")
            page.mouse.move(100, 100)
            page.wait_for_timeout(600)
            page.mouse.move(250, 300)
            page.wait_for_timeout(400)
            
            # محاولة الكتابة في حقل البريد
            try:
                email_input = "input[type='email']"
                if page.is_visible(email_input):
                    print("📧 جاري الكتابة في حقل البريد...")
                    page.type(email_input, "dawn.real.a688rcher99@gmail.com", delay=120)
                else:
                    print("⚠️ حقل البريد غير مرئي حالياً")
            except Exception as e:
                print(f"⚠️ تحذير: فشل الكتابة في حقل البريد: {str(e)}")
            
            print("⏳ جاري انتظار تدفق التوكنات...")
            print("   (نستهدف التقاط التوكن الثاني والأحدث)")
            print("-" * 60)
            
            # حلقة الانتظار الذكية
            timeout_counter = 0
            max_timeout = 30  # 15 ثانية كحد أقصى (30 × 500ms)
            
            while len(CAPTCHA_TOKENS) < 2 and timeout_counter < max_timeout:
                page.wait_for_timeout(500)
                timeout_counter += 1
                
                # طباعة تحديث كل 5 ثوان
                if timeout_counter % 10 == 0:
                    elapsed_seconds = (timeout_counter * 500) / 1000
                    print(f"   ⏱️ مرت {elapsed_seconds:.1f}s - تم التقاط {len(CAPTCHA_TOKENS)} توكن")
            
            print("-" * 60)
            print("\n📊 انتهت فترة الفحص الحية. جاري معالجة البيانات المتوفرة:")
            print("-" * 60)
            
            final_token = None
            
            # اختيار التوكن المناسب بناءً على ما تم التقاطه
            if len(CAPTCHA_TOKENS) >= 2:
                final_token = CAPTCHA_TOKENS[-1]  # آخر توكن (الأحدث)
                print(f"🎉 نجاح! تم اقتناص {len(CAPTCHA_TOKENS)} توكنات.")
                print(f"   تم اختيار: التوكن الأحدث (رقم {len(CAPTCHA_TOKENS)})")
                
            elif len(CAPTCHA_TOKENS) == 1:
                final_token = CAPTCHA_TOKENS[0]
                print("⚠️ تم التقاط توكن واحد فقط (التوكن المبدئي)")
                print("   سيتم اعتماده كخيار احتياطي")
                
            else:
                print("❌ فشل السكربت في التقاط أي توكن من الشبكة")
                print("   تحقق من:")
                print("   • اتصالك بالإنترنت")
                print("   • أن الموقع يحتوي على reCAPTCHA")
                print("   • أن المتصفح لم يتم إغلاقه مبكراً")
            
            # حفظ التوكن في ملف
            if final_token:
                try:
                    with open("valid_token.txt", "w", encoding="utf-8") as f:
                        f.write(final_token)
                    print(f"\n💾 تم حفظ التوكن بنجاح في: valid_token.txt")
                    print(f"   بداية التوكن: {final_token[:40]}...")
                    print(f"   طول التوكن: {len(final_token)} حرف")
                except Exception as e:
                    print(f"❌ خطأ في حفظ التوكن: {str(e)}")
            
            print("-" * 60)
            print("🔌 جاري إغلاق المتصفح...")
            browser.close()
            print("✅ انتهى السكربت بنجاح")
            
    except Exception as e:
        print(f"❌ خطأ حرج: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
