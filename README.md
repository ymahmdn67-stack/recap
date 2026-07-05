# Recaptcha Token Capture

هذا المشروع يقوم باعتراض شبكة المتصفح لالتقاط رمز (Token) الخاص بـ reCAPTCHA باستخدام مكتبة Playwright.

## المميزات
- يعتمد على البرمجة غير المتزامنة (Async/Await) لأداء أفضل.
- يحتوي على إعدادات لتجنب الاكتشاف (Detection Avoidance).
- مهيأ للعمل مباشرة في GitHub Codespaces أو VS Code.
- يستخدم المتغيرات البيئية لإدارة الإعدادات.

## التشغيل في GitHub Codespaces
المشروع مهيأ بالكامل للعمل في Codespaces. عند فتح المشروع في Codespace:
1. سيتم تثبيت جميع المتطلبات والمكاتب تلقائياً.
2. سيتم تثبيت متصفح Chromium الخاص بـ Playwright تلقائياً.
3. يمكنك تشغيل الملف `main.py` مباشرة من خلال زر "Run" أو بالضغط على `F5` في VS Code.

## التشغيل المحلي (Local Development)

### المتطلبات
- Python 3.10 أو أحدث.

### خطوات التثبيت
1. قم بإنشاء بيئة وهمية (Virtual Environment):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # في Linux/Mac
   # أو
   .venv\Scripts\activate     # في Windows
   ```

2. قم بتثبيت الحزم المطلوبة:
   ```bash
   pip install -r requirements.txt
   ```

3. قم بتثبيت متصفح Playwright:
   ```bash
   playwright install chromium
   ```

4. قم بنسخ ملف المتغيرات البيئية:
   ```bash
   cp .env.example .env
   ```

### التشغيل
لتشغيل السكربت:
```bash
python main.py
```
