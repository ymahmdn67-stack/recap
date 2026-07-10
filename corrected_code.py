import asyncio
import re
import os
import time
import logging
import random
from typing import Optional
from dotenv import load_dotenv
from faker import Faker
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright

# --- إعداد Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تحميل متغيرات البيئة
load_dotenv()

# --- قائمة User-Agents واقعية ---
USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
]


# --- 1. دالة استخراج التوكن مع معالجة صحيحة ---
async def get_captcha_token(timeout_seconds: int = 30) -> Optional[str]:
    """
    استخراج توكن reCAPTCHA من الموقع
    
    Args:
        timeout_seconds: المدة القصوى لانتظار التوكن (بالثواني)
    
    Returns:
        التوكن إذا تم استخراجه، وإلا None
    """
    cap_container = {"value": None}
    
    async def handle_response(response):
        """معالج الاستجابات - يبحث عن توكن reCAPTCHA"""
        try:
            if "recaptcha/api2/reload" in response.url:
                try:
                    body = await response.text()
                    # تحسين النمط للبحث عن التوكن
                    m = re.search(r'"rresp"\s*:\s*"([^"]+)"', body)
                    if m:
                        cap_container["value"] = m.group(1)
                        logger.info("Successfully extracted captcha token")
                except Exception as e:
                    logger.debug(f"Error processing response: {e}")
        except Exception as e:
            logger.debug(f"Error in handle_response: {e}")
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("response", handle_response)
            
            logger.info("Navigating to the target page...")
            await page.goto("https://greenmethods.com/my-account/", timeout=15000)
            
            # انتظار التوكن مع timeout
            start_time = time.time()
            while cap_container["value"] is None:
                elapsed = time.time() - start_time
                
                # التحقق من timeout
                if elapsed > timeout_seconds:
                    logger.warning(f"Timeout: Failed to extract captcha token after {timeout_seconds} seconds")
                    return None
                
                # انتظار قصير قبل المحاولة التالية
                await page.wait_for_timeout(500)
            
            cap = cap_container["value"]
            logger.info("Captcha token extracted successfully")
            return cap
            
    except asyncio.TimeoutError:
        logger.error("Timeout while loading the page")
        return None
    except Exception as e:
        logger.error(f"Error in get_captcha_token: {e}")
        return None
    finally:
        if browser:
            try:
                await browser.close()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")


# --- 2. دالة توليد بريد إلكتروني صحيح ---
def generate_valid_email() -> str:
    """توليد بريد إلكتروني صحيح من الناحية الفنية"""
    fake = Faker("en_UK")
    
    # إزالة الأحرف الخاصة والمسافات
    first_name = re.sub(r'[^a-z0-9]', '', fake.first_name().lower())
    last_name = re.sub(r'[^a-z0-9]', '', fake.last_name().lower())
    
    # التأكد من أن الأسماء ليست فارغة
    if not first_name:
        first_name = "user"
    if not last_name:
        last_name = "account"
    
    email = f"{first_name}.{last_name}@gmail.com"
    logger.info(f"Generated email: {email}")
    return email


# --- 3. دالة الحصول على كلمة المرور من متغيرات البيئة ---
def get_password() -> Optional[str]:
    """الحصول على كلمة المرور من متغيرات البيئة"""
    password = os.getenv('ACCOUNT_PASSWORD')
    
    if not password:
        logger.error("Error: ACCOUNT_PASSWORD not found in environment variables")
        logger.info("Please set ACCOUNT_PASSWORD in your .env file")
        return None
    
    return password


# --- 4. دالة الحصول على User-Agent عشوائي ---
def get_random_user_agent() -> str:
    """اختيار user-agent عشوائي من قائمة موثوقة"""
    return random.choice(USER_AGENTS)


# --- 5. دالة استخراج Nonce مع التحقق ---
def extract_nonce(html_content: str, nonce_name: str) -> Optional[str]:
    """
    استخراج nonce من محتوى HTML
    
    Args:
        html_content: محتوى الصفحة HTML
        nonce_name: اسم الـ nonce المراد البحث عنه
    
    Returns:
        قيمة الـ nonce أو None
    """
    pattern = f'name="{nonce_name}"[^>]*value="([^"]+)"'
    match = re.search(pattern, html_content)
    
    if match:
        nonce = match.group(1)
        logger.info(f"Successfully extracted {nonce_name}")
        return nonce
    else:
        logger.warning(f"Could not extract {nonce_name}")
        return None


# --- 6. الدالة الأساسية للربط والتسجيل ---
async def main():
    """الدالة الرئيسية لتنفيذ عملية التسجيل"""
    try:
        # الخطوة 1: استخراج التوكن
        logger.info("Step 1: Extracting captcha token...")
        cap = await get_captcha_token(timeout_seconds=30)
        
        if not cap:
            logger.error("Failed to extract captcha token")
            return False
        
        logger.info(f"Captcha token obtained: {cap[:20]}...")
        
        # الخطوة 2: الحصول على كلمة المرور
        logger.info("Step 2: Getting password from environment...")
        password = get_password()
        
        if not password:
            logger.error("Failed to get password")
            return False
        
        # الخطوة 3: توليد البيانات الوهمية
        logger.info("Step 3: Generating fake data...")
        email = generate_valid_email()
        user_agent = get_random_user_agent()
        
        logger.info(f"Generated data - Email: {email}, User-Agent: {user_agent[:50]}...")
        
        # الخطوة 4: إعداد جلسة curl_cffi
        logger.info("Step 4: Setting up HTTP session...")
        async with AsyncSession(impersonate="chrome120") as session:
            
            # --- الطلب الأول: GET ---
            logger.info("Step 5: Sending GET request...")
            headers_get = {
                'authority': 'greenmethods.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': user_agent,
            }
            
            try:
                response = await session.get(
                    'https://greenmethods.com/my-account/',
                    headers=headers_get,
                    timeout=15
                )
                
                # التحقق من حالة الاستجابة
                if response.status_code != 200:
                    logger.error(f"GET request failed with status {response.status_code}")
                    return False
                
                logger.info(f"GET request successful (Status: {response.status_code})")
                
            except asyncio.TimeoutError:
                logger.error("GET request timed out")
                return False
            except Exception as e:
                logger.error(f"Error in GET request: {e}")
                return False
            
            # استخراج register nonce
            logger.info("Step 6: Extracting register nonce...")
            register_nonce = extract_nonce(response.text, "woocommerce-register-nonce")
            
            if not register_nonce:
                logger.error("Failed to extract register nonce - registration may fail")
                return False
            
            # --- الطلب الثاني: POST ---
            logger.info("Step 7: Sending POST request...")
            headers_post = {
                'authority': 'greenmethods.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'max-age=0',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://greenmethods.com',
                'referer': 'https://greenmethods.com/my-account/',
                'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': user_agent,
            }
            
            data = {
                'email': email,
                'password': password,
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
                'wc_order_attribution_session_start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'wc_order_attribution_session_pages': '2',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': user_agent,
                'woocommerce-register-nonce': register_nonce,
                '_wp_http_referer': '/my-account/',
                'register': 'Register',
            }
            
            try:
                response = await session.post(
                    'https://greenmethods.com/my-account/',
                    headers=headers_post,
                    data=data,
                    timeout=15
                )
                
                # التحقق من حالة الاستجابة
                if response.status_code not in [200, 302]:
                    logger.error(f"POST request failed with status {response.status_code}")
                    logger.debug(f"Response text: {response.text[:500]}")
                    return False
                
                logger.info(f"POST request successful (Status: {response.status_code})")
                
            except asyncio.TimeoutError:
                logger.error("POST request timed out")
                return False
            except Exception as e:
                logger.error(f"Error in POST request: {e}")
                return False
            
            # التحقق الأولي من نجاح التسجيل
            logger.info("Step 8: Verifying registration success...")
            non_edit_check = extract_nonce(response.text, "woocommerce-edit-address-nonce")

            if not non_edit_check:
                logger.warning("Registration may have failed - proceeding to billing page check...")

            # --- الطلب الثالث: GET صفحة billing ---
            logger.info("Step 9: Fetching billing address page...")
            headers_billing = {
                'authority': 'greenmethods.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
                'referer': 'https://greenmethods.com/my-account/edit-address/',
                'sec-ch-ua': '"Chromium";v="120", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': user_agent,
            }

            try:
                response_billing = await session.get(
                    'https://greenmethods.com/my-account/edit-address/billing/',
                    headers=headers_billing,
                    timeout=15
                )

                if response_billing.status_code != 200:
                    logger.error(f"Billing GET request failed with status {response_billing.status_code}")
                    return False

                logger.info(f"Billing GET request successful (Status: {response_billing.status_code})")

            except asyncio.TimeoutError:
                logger.error("Billing GET request timed out")
                return False
            except Exception as e:
                logger.error(f"Error in Billing GET request: {e}")
                return False

            # استخراج woocommerce-edit-address-nonce من صفحة billing
            logger.info("Step 10: Extracting edit address nonce from billing page...")
            non_edit = extract_nonce(response_billing.text, "woocommerce-edit-address-nonce")

            if non_edit:
                logger.info(f"✓ Success! Registration completed successfully")
                logger.info(f"Edit Address Nonce: {non_edit}")
                return True
            else:
                logger.warning("Failed to get edit address nonce from billing page")
                logger.debug(f"Response text: {response_billing.text[:500]}")
                return False
        
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting registration script")
    logger.info("=" * 60)
    
    try:
        result = asyncio.run(main())
        
        if result:
            logger.info("=" * 60)
            logger.info("✓ Script completed successfully")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.info("=" * 60)
            logger.info("✗ Script failed")
            logger.info("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
