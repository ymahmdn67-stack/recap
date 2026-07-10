import re
import json
import base64
import random
import time
import requests
from faker import Faker
from playwright.sync_api import sync_playwright

BASE_URL = "https://greenmethods.com"
DOMAIN = "greenmethods.com"

fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
k = f"{f} {l}"
e = f"{f.lower()}.{l.lower()}@gmail.com"

cap = None

def check_network_response(response):
    global cap
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            match = re.search(r'rresp","(.+?)"', body)
            if match:
                cap = match.group(1)
        except Exception:
            pass

def fetch_captcha_token():
    global cap
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, 
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.on("response", check_network_response)
        
        page.goto(f"{BASE_URL}/my-account/", wait_until="commit")
        
        page.mouse.move(100, 100)
        page.wait_for_timeout(500)
        page.mouse.move(250, 300)
        
        while cap is None:
            page.wait_for_timeout(500)
            
        browser.close()
    return cap

def main():
    global cap
    
    cap = fetch_captcha_token()
    r = requests.Session()
    
    headers_get = {
        'authority': DOMAIN,
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
    
    response = r.get(f'{BASE_URL}/my-account/', headers=headers_get)
    
    non_register = re.search(
        r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"',
        response.text
    )
    
    register_nonce_val = ""
    if non_register:
        register_nonce_val = non_register.group(1)
    
    headers_post = {
        'authority': DOMAIN,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': BASE_URL,
        'referer': f'{BASE_URL}/my-account/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }
    
    data = {
        'email': e,
        'password': 'Willia5766ms#123CR7',
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
        'wc_order_attribution_session_entry': f'{BASE_URL}/my-account/',
        'wc_order_attribution_session_start_time': '2026-07-09 22:38:43',
        'wc_order_attribution_session_pages': '2',
        'wc_order_attribution_session_count': '1',
        'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'woocommerce-register-nonce': register_nonce_val,
        '_wp_http_referer': '/my-account/',
        'register': 'Register',
    }
    
    response = r.post(f'{BASE_URL}/my-account/', headers=headers_post, data=data)
    
    headers_billing = {
        'authority': DOMAIN,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
        'referer': f'{BASE_URL}/my-account/edit-address/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }
    
    response = r.get(f'{BASE_URL}/my-account/edit-address/billing/', headers=headers_billing)
    
    non_billing = re.search(
        r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
        response.text
    )

if __name__ == "__main__":
    main()
