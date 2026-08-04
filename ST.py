import asyncio
import re
import base64
from curl_cffi.requests import AsyncSession

async def fetch_donation_tokens():
    url = 'https://bukjeh.org/donations/donation-2023-2-3/'
    
    headers = {
        'authority': 'bukjeh.org',
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
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    # استخدام AsyncSession مع محاكاة متصفح Chrome لتجاوز التشفير والحظر
    async with AsyncSession(impersonate="chrome120") as session:
        response = await session.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"[!] فشل الطلب، رمز الاستجابة: {response.status_code}")
            return

        html_text = response.text

        # دالة لاستخراج القيم من Regex بأمان دون توقف الكود
        def extract(pattern, text):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1) if match else None

        # أنماط مرنة للـ Form Parameters (تتعامل مع اختلاف ترتيب العناصر والأقواس)
        form_hash = (
            extract(r'name=["\']give-form-hash["\']\s+value=["\'](.*?)["\']', html_text) or
            extract(r'value=["\'](.*?)["\']\s+name=["\']give-form-hash["\']', html_text)
        )
        
        form_prefix = (
            extract(r'name=["\']give-form-id-prefix["\']\s+value=["\'](.*?)["\']', html_text) or
            extract(r'value=["\'](.*?)["\']\s+name=["\']give-form-id-prefix["\']', html_text)
        )
        
        form_id = (
            extract(r'name=["\']give-form-id["\']\s+value=["\'](.*?)["\']', html_text) or
            extract(r'value=["\'](.*?)["\']\s+name=["\']give-form-id["\']', html_text)
        )

        # استخراج Token البوابة (Braintree/PayPal)
        client_token = (
            extract(r'["\']data-client-token["\']\s*:\s*["\'](.*?)["\']', html_text) or
            extract(r'data-client-token=["\'](.*?)["\']', html_text)
        )

        access_token = None
        if client_token:
            try:
                decoded_token = base64.b64decode(client_token).decode("utf-8")
                access_token = extract(r'["\']accessToken["\']\s*:\s*["\'](.*?)["\']', decoded_token)
            except Exception as e:
                print(f"[!] خطأ أثناء فك تشفير client-token: {e}")

        # الطباعة والتحقق
        print("=== البيانات المستخرجة ===")
        print("give-form-hash:", form_hash)
        print("give-form-id-prefix:", form_prefix)
        print("give-form-id:", form_id)
        print("accessToken:", access_token)

        # تحذير في حال فقدان أي عنصر
        missing = [k for k, v in {"hash": form_hash, "prefix": form_prefix, "id": form_id}.items() if not v]
        if missing:
            print(f"\n[⚠️] تنبيه: لم يتم استخراج القيم التالية: {', '.join(missing)}")

# تشغيل الدالة غير المتزامنة
if __name__ == '__main__':
    asyncio.run(fetch_donation_tokens())
