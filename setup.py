import sys
import subprocess


def run_command(command_list):
    try:
        subprocess.check_call(command_list)
        return True
    except (subprocess.CalledProcessError, OSError):
        print(f"❌ فشل تنفيذ الأمر: {' '.join(command_list)}")
        return False


def main():
    print("🚀 بدء تهيئة وتثبيت البيئة البرمجية...")

    print("\n🔄 [خطوة 1] جاري ترقية pip...")
    if not run_command([
        sys.executable, "-m", "pip", "install", "--upgrade", "pip"
    ]):
        return

    required_libraries = ["faker", "curl_cffi", "camoufox"]
    print(
        f"\n📦 [خطوة 2] جاري تثبيت المكتبات: "
        f"{', '.join(required_libraries)}"
    )

    for library in required_libraries:
        print(f"⏳ جاري تثبيت {library}...")
        if not run_command([
            sys.executable, "-m", "pip", "install", library
        ]):
            return

    print("\n⚙️ [خطوة 3] جاري تحميل متصفح Camoufox...")
    if not run_command([
        sys.executable, "-m", "camoufox", "fetch"
    ]):
        return

    print("\n✨ تم تثبيت المكتبات وتنزيل متصفح Camoufox بنجاح.")
    print("قد يحتاج Linux إلى مكتبات نظام إضافية لتشغيل المتصفح.")


if __name__ == "__main__":
    main()
