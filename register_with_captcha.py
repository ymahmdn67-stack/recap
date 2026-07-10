#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import re
import json
import base64
import random
import time
import requests
from faker import Faker

# =====================================================================
# 1. قسم الفحص الذكي والتثبيت التلقائي وإعادة التشغيل عبر Xvfb
# =====================================================================

def init_environment():
    """تهيئة البيئة بالكامل: تثبيت الاعتماديات وإعادة التشغيل داخل Xvfb"""
    
    # أ. التحقق من تثبيت مكتبة Playwright و Faker
    for package in ["playwright", "faker"]:
        try:
            __import__(package)
        except ImportError:
            print(f"📦 مكتبة {package} غير مثبتة. جاري التثبيت...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # ب. التحقق من تثبيت متصفحات Playwright وملفاتها للنظام
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
    except Exception:
        print("⚙️ متصفحات Playwright أو ملفات النظام ناقصة. جاري تحميلها...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps"])

    # ج. التحقق من وجود الشاشة وإعادة التشغيل تلقائياً عبر xvfb-run (للبيئات السحابية)
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
        if "XVFB_AUTO_LAUNCHED" not in os.environ:
            print("🖥️ تم اكتشاف بيئة سحابية بدون شاشة (Linux Server).")
            print("⏳ جاري تشغيل الكود تلقائياً عبر xvfb-run لتأمين توكن عالي الموثوقية...")
            
            os.environ["XVFB_AUTO_LAUNCHED"] = "1"
            cmd = ['xvfb-run', '-a', sys.executable] + sys.argv
            
            try:
                subprocess.check_call(cmd)
                sys.exit(0)
            except FileNotFoundError:
                print("❌ أداة xvfb غير مثبتة على السيرفر. جاري تثبيتها الآن تلقائياً...")
                try:
                    subprocess.check_call(['sudo', 'apt-get', 'update', '-y'])
                    subprocess.check_call(['sudo', 'apt-get', 'install', '-y', 'xvfb'])
                    print("✅ تم تثبيت xvfb بنجاح. جاري إعادة تشغيل الكود...")
                    subprocess.check_call(cmd)
                    sys.exit(0)
                except Exception as e:
                    print(f"❌ فشل تثبيت xvfb تلقائياً: {e}")
                    sys.exit(1)

# تشغيل التهيئة الذكية قبل بدء أي شيء آخر
init_environment()

# =====================================================================
# 2. استخراج التوكن عبر Playwright (مخفي ومحاكي للسلوك البشري)
# =====================================================================

from playwright.sync_api import sync_playwright

CAPTCHA_TOKEN = None
TARGET_DOMAIN = "example.com"  # استبدله بالنطاق المطلوب لبيئة الاختبار الخاصة بك
TARGET_URL = f"https://{TARGET_DOMAIN}/my-account/"

def check_network_response(response):
    global CAPTCHA_TOKEN
    # اصطياد طلب الكابتشا من الشبكة
    if "recaptcha/api2/reload" in response.url:
        try:
            body = response.text()
            match = re.search(r'rresp","(.+?)"', body)
            if match:
                CAPTCHA_TOKEN = match.group(1)
        except Exception:
            pass

print("\n🌐 جاري فتح المتصفح والتقاط التوكن بموثوقية عالية...")
with sync_playwright() as p:
    # تشغيل المتصفح بوضع مرئي لأنه محمي داخل الشاشة الوهمية لـ Xvfb
    browser = p.chromium.launch(
        headless=False, 
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    )
    
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    page = context.new_page()
    page.on("response", check_network_response)
    
    page.goto(TARGET_URL, wait_until="commit")
    
    # محاكاة حركة ماوس طبيعية لرفع تقييم التفاعل البشري
    page.mouse.move(100, 100)
    page.wait_for_timeout(400)
    page.mouse.move(300, 400)
    
    # الانتظار لحين التقاط التوكن
    while CAPTCHA_TOKEN is None:
        page.wait_for_timeout(500)
        
    print(f"🎉 تم التقاط التوكن بنجاح! \nTOKEN = {CAPTCHA_TOKEN[:30]}...")
    
    # حفظ التوكن احتياطياً في ملف نصي
    with open("valid_token.txt", "w") as f_out:
        f_out.write(CAPTCHA_TOKEN)
        
    browser.close()

# تعيين التوكن المستخرج للمتغير cap لاستخدامه في طلبات الـ Requests
cap = CAPTCHA_TOKEN

# =====================================================================
# 3. قسم إرسال الطلبات (Requests) وإنشاء الحساب
# =====================================================================

fake = Faker("en_UK")
f = fake.first_name()
l = fake.last_name()
e = f"{f.lower()}.{l.lower()}@gmail.com"

r = requests.Session()

headers_get = {
    'authority': TARGET_DOMAIN,
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

# الطلب الأول: جلب صفحة التسجيل لاستخراج الـ Nonce
response_get = r.get(TARGET_URL, headers=headers_get)

non_search = re.search(
    r'name="woocommerce-register-nonce"[^>]*value="([^"]+)"',
    response_get.text
)

if non_search:
    non = non_search.group(1)
    print(f"✅ تم العثور على Nonce الـ Register: {non}")
else:
    print("❌ Nonce not found")
    non = ""

# إعداد هيدرز طلب الـ POST
headers_post = {
    'authority': TARGET_DOMAIN,
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'cache-control': 'max-age=0',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': f'https://{TARGET_DOMAIN}',
    'referer': TARGET_URL,
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
    'wc_order_attribution_session_entry': TARGET_URL,
    'wc_order_attribution_session_start_time': '2026-07-09 22:38:43',
    'wc_order_attribution_session_pages': '2',
    'wc_order_attribution_session_count': '1',
    'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    'woocommerce-register-nonce': non,
    '_wp_http_referer': '/my-account/',
    'register': 'Register',
}

# إرسال طلب إنشاء الحساب (POST)
print("\n🚀 جاري إرسال بيانات التسجيل...")
response_post = r.post(TARGET_URL, headers=headers_post, data=data)

print(f"[+] حالة استجابة طلب التسجيل (Status Code): {response_post.status_code}")

# الفحص الذكي لحالة الاستجابة والتحقق من الأخطاء
target_error = "Error:</strong> <strong>ERROR</strong>: reCAPTCHA verification failed.<br /><br />Please try again."

if target_error in response_post.text:
    print("❌ النتيجة: فشل التحقق (تم العثور على خطأ reCAPTCHA المحدد)")
else:
    print("✅ النتيجة: لم يتم العثور على خطأ reCAPTCHA في الاستجابة (تم قبول التوكن بنجاح)")

# الجلب الإضافي لصفحة العناوين للتأكد من حالة الجلسة
headers_billing = {
    'authority': TARGET_DOMAIN,
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'ar-IQ,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'referer': f'https://{TARGET_DOMAIN}/my-account/edit-address/',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

response_billing = r.get(f'https://{TARGET_DOMAIN}/my-account/edit-address/billing/', headers=headers_billing)

non_billing = re.search(
    r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
    response_billing.text
)

if non_billing:
    print(f"✅ تم العثور على Nonce العنوان: {non_billing.group(1)}")
else:
    print("⚠️ لم يتم العثور على Nonce العنوان (قد يتطلب ذلك تسجيل دخول صحيح)")
