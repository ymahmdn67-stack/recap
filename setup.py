import sys
import subprocess

def run_command(command_list):
    """دالة مساعدة لتنفيذ الأوامر بأمان"""
    try:
        subprocess.check_call(command_list)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ فشل تنفيذ الأمر: {' '.join(command_list)}")
        return False

def main():
    print("🚀 بدء تهيئة وتثبيت البيئة البرمجية بالكامل...")

    # 1. ترقية أداة pip لحل مشكلة عدم العثور على الحزم الظاهرة في الصورة
    print("\n🔄 [خطوة 1] جاري ترقية أداة pip إلى أحدث إصدار...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    # 2. تثبيت المكتبات الأساسية المطلوبة للسكربت
    required_libraries = ["faker", "curl_cffi", "playwright"]
    print(f"\n📦 [خطوة 2] جاري تثبيت المكتبات الأساسية: {', '.join(required_libraries)}")
    
    for library in required_libraries:
        print(f"⏳ جاري تثبيت {library}...")
        run_command([sys.executable, "-m", "pip", "install", library])

    # 3. تحميل المتصفحات والملفات الاعتمادية لنظام التشغيل (Linux/Codespaces)
    print("\n⚙️ [خطوة 3] جاري تحميل متصفحات وملفات نظام Playwright (قد يستغرق ذلك دقيقة)...")
    success = run_command([sys.executable, "-m", "playwright", "install", "--with-deps"])

    if success:
        print("\n✨ تم إعداد بيئة العمل بالكامل بنجاح! يمكنك الآن تشغيل كود التسجيل الأساسي بدون مشاكل.")
    else:
        print("\n⚠️ تم تثبيت المكتبات، ولكن واجه السكربت مشكلة في تحميل متصفحات النظام.")

if __name__ == "__main__":
    main()
