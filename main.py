import sys
import subprocess
import asyncio
import re
from faker import Faker
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright

# --- 1. قسم الفحص والتثبيت الصامت لـ Playwright ---
def ensure_playwright_ready():
    try:
        import playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception:
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps"])
        except Exception:
            sys.exit(1)

ensure_playwright_ready()


# --- 2. دالة استخراج توكن الكابتشا ---
async def get_captcha_token():
    cap_container = {"value": None}

    async def handle_response(response):
        if "recaptcha/api2/reload" in response.url:
            try:
                body = await response.text()
                m = re.search(r'rresp","(.+?)"', body)
                if m:
                    cap_container["value"] = m.group(1)
            except Exception:
                pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        page = await browser.new_page()
        page.on("response", handle_response)
        await page.goto("https://greenmethods.com/my-account/")
        
        while cap_container["value"] is None:
            await page.wait_for_timeout(1000)
            
        cap = cap_container["value"]
        await browser.close()
        return cap


# --- 3. الدالة الأساسية للربط والطلبات المتتالية ---
async def main():
    # استخراج توكن الكابتشا وحفظه في متغير cap
    cap = await get_captcha_token()
    
    if not cap:
        print("Fails to get token.")
        return

    # إعداد البيانات الوهمية للمستخدم الجديد
    fake = Faker("en_UK")
    f = fake.first_name()
    l = fake.last_name()
    e = f"{f.lower()}.{l.lower()}@gmail.com"
    
    # تعيين User-Agent حقيقي لمتصفح Chrome (Android) متوافق مع بنية الـ headers الحالية
    REAL_USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'

    # بدء جلسة curl_cffi الموحدة للحفاظ على الكوكيز والاتصال تلقائياً
    async with AsyncSession(impersonate="chrome120") as r:
        
        # --- الطلب الأول (GET): لصفحة الحساب لاستخراج الـ register nonce ---
        headers_get = {
            'authority': 'greenmethods.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': REAL_USER_AGENT,
        }

        response = await r.get('https://greenmethods.com/my-account/', headers=headers_get)

        register_nonce = ""
        non = re.search(r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"', response.text)
        if non:
            register_nonce = non.group(1)

        # --- الطلب الثاني (POST): إرسال بيانات التسجيل مع توكن الكابتشا cap ---
        headers_post = {
            'authority': 'greenmethods.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://greenmethods.com',
            'referer': 'https://greenmethods.com/my-account/',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': REAL_USER_AGENT,
        }

        data = {
            'email': e,
            'password': 'Williams#123CR7',
            'g-recaptcha-response': cap,
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
            'wc_order_attribution_user_agent': REAL_USER_AGENT,
            'woocommerce-register-nonce': register_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }

        await r.post('https://greenmethods.com/my-account/', headers=headers_post, data=data)

        # --- الطلب الثالث (GET): الانتقال لصفحة تعديل العنوان لاستخراج التوكن المطلوبة ---
        headers_billing = {
            'authority': 'greenmethods.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://greenmethods.com/my-account/edit-address/',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': REAL_USER_AGENT,
        }

        response_billing = await r.get('https://greenmethods.com/my-account/edit-address/billing/', headers=headers_billing)

        # استخراج woocommerce-edit-address-nonce وطباعته
        non_edit = re.search(r'name="woocommerce-edit-address-nonce" value="([^"]+)"', response_billing.text)
        if non_edit:
            print(f"Success! Edit Address Nonce: {non_edit.group(1)}")
        else:
            print("Failed to get edit address nonce.")

if __name__ == "__main__":
    asyncio.run(main())
