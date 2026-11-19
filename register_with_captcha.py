import requests

proxy = "http://krake73891:kraken@proxies.toolz.ovh:8443"
proxies = {"http": proxy, "https": proxy}

try:
    print("Testing proxy...")
    response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=15)
    print("✅ Proxy is ALIVE! Your IP is:", response.text)
except Exception as e:
    print("❌ Proxy is DEAD or Blocked:", e)
