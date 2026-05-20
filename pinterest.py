"""
Pinterest自動ピン投稿 (SleepScapeDaily)
- 商品カタログからランダム選択
- DALL-Eで縦長ライフスタイル画像生成 (1024x1536)
- テキストオーバーレイ + SleepScapeブランディング
- Pinterest API v5でボードに自動投稿
- 履歴管理で重複防止
"""

import os, json, base64, io, random, time, sys, webbrowser, pickle, urllib.parse, logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

DIR          = os.path.dirname(__file__)
ENV_FILE     = os.path.join(DIR, ".env")
TOKEN_FILE   = os.path.join(DIR, "token_pinterest.pickle")
HISTORY_FILE = os.path.join(DIR, "pinterest_history.json")
FONT_BOLD    = os.path.join(DIR, "fonts", "Cinzel-Bold.ttf")
FONT_REG     = "/System/Library/Fonts/Helvetica.ttc"
FONT_EMOJI   = "/System/Library/Fonts/Apple Color Emoji.ttc"

PINTEREST_BASE = "https://api.pinterest.com/v5"
REDIRECT_URI   = "https://localhost/"
HISTORY_LIMIT  = 10   # この件数は連続して選ばない


# ─── .env 読み込み ─────────────────────────────────────────────
def _load_env() -> dict:
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


# ─── 商品カタログ ──────────────────────────────────────────────
PRODUCTS = [
    # ── Sleep ──────────────────────────────────────────────────
    {
        "id": "white_noise_machine",
        "title": "White Noise Machine",
        "headline": "The best sleep of your life\nstarts here",
        "description": (
            "Drown out distractions and sleep deeper with a white noise machine. "
            "Perfect for light sleepers, city dwellers, and anyone who struggles to unwind. "
            "🌙 SleepScape recommends it."
        ),
        "amazon_url": "https://amzn.to/3R3qsMx",
        "themes": ["sleep", "rain", "fan"],
        "dalle_prompt": (
            "cozy minimalist bedroom at night, soft moonlight through sheer curtains, "
            "perfectly made bed with fluffy pillows, warm ambient nightstand lamp, "
            "peaceful and serene, no people, Pinterest lifestyle aesthetic, vertical composition"
        ),
    },
    {
        "id": "sleep_headphones",
        "title": "Sleep Headphones",
        "headline": "Fall asleep to\nyour favorite sounds",
        "description": (
            "Ultra-soft Bluetooth headphones designed for sleeping. "
            "Thin speakers that stay comfortable all night — perfect for side sleepers and travelers. "
            "🎧 Pair with SleepScape ambient sounds."
        ),
        "amazon_url": "https://amzn.to/4fjALG3",
        "themes": ["sleep", "study", "travel"],
        "dalle_prompt": (
            "dreamy cozy bedroom at dusk, soft pillows and chunky knit blanket, "
            "warm golden lamp light, peaceful and inviting, no people, "
            "minimalist Pinterest lifestyle aesthetic, vertical"
        ),
    },
    {
        "id": "blackout_sleep_mask",
        "title": "Blackout Sleep Mask",
        "headline": "Total darkness.\nTotal rest.",
        "description": (
            "Block 100% of light for deeper, longer sleep. "
            "Adjustable silk-feel eye mask — great for travel, night shifts, or bright bedrooms. "
            "😴 Sleep like you mean it."
        ),
        "amazon_url": "https://amzn.to/42CF7Rg",
        "themes": ["sleep", "travel"],
        "dalle_prompt": (
            "luxurious minimalist bedroom, soft silk bedding in neutral tones, "
            "gentle morning light barely peeking through blackout curtains, "
            "calm and restful atmosphere, no people, Pinterest bedroom aesthetic, vertical"
        ),
    },
    {
        "id": "weighted_blanket",
        "title": "Weighted Blanket",
        "headline": "Like a hug that\nhelps you sleep",
        "description": (
            "Reduce anxiety and improve sleep quality with a weighted blanket. "
            "Science-backed comfort that works for adults and kids alike. "
            "🛏️ Feel the difference from night one."
        ),
        "amazon_url": "https://amzn.to/3YbTKDV",
        "themes": ["sleep", "cozy"],
        "dalle_prompt": (
            "ultra cozy bedroom corner, chunky knit blanket draped over a comfortable chair, "
            "warm fairy string lights, steaming mug on small wooden table, "
            "autumn evening atmosphere, no people, Pinterest cozy hygge aesthetic, vertical"
        ),
    },
    {
        "id": "pillow_speaker",
        "title": "Pillow Speaker",
        "headline": "Ambient sound\nwithout disturbing anyone",
        "description": (
            "Ultra-thin speaker that fits inside your pillowcase. "
            "Listen to sleep sounds all night at a low volume only you can hear. "
            "🔈 Perfect with SleepScape 8-hour streams."
        ),
        "amazon_url": "https://amzn.to/4doJIvg",
        "themes": ["sleep"],
        "dalle_prompt": (
            "minimalist white bedroom, plush pillow arrangement on clean white bedding, "
            "soft morning diffused light, peaceful and clean aesthetic, "
            "no people, Pinterest minimal bedroom aesthetic, vertical"
        ),
    },
    # ── Study / Focus ───────────────────────────────────────────
    {
        "id": "noise_canceling_headphones",
        "title": "Noise-Canceling Headphones",
        "headline": "Deep focus starts\nwith silence",
        "description": (
            "Enter a flow state and tune out the world. "
            "Premium noise-canceling headphones for studying, working from home, or unwinding. "
            "🎧 Elevate every study session."
        ),
        "amazon_url": "https://amzn.to/4wvOyQh",
        "themes": ["study", "fantasy", "travel"],
        "dalle_prompt": (
            "aesthetic study desk setup, warm wooden desk with open notebook, "
            "steaming coffee cup, stack of books, cozy home library in background, "
            "golden hour light through window, no people, Pinterest study aesthetic, vertical"
        ),
    },
    {
        "id": "led_desk_lamp",
        "title": "LED Desk Lamp",
        "headline": "Light up\nyour focus zone",
        "description": (
            "Adjustable brightness and color temperature to match your mood and time of day. "
            "Easy on your eyes during long study sessions. "
            "💡 Your desk deserves better light."
        ),
        "amazon_url": "https://amzn.to/4wAAgxM",
        "themes": ["study"],
        "dalle_prompt": (
            "cozy minimalist study corner at night, warm amber desk lamp glowing, "
            "open books and planner on wooden desk, pencil cup and small plant, "
            "focused productive night study atmosphere, no people, Pinterest desk aesthetic, vertical"
        ),
    },
    {
        "id": "blue_light_glasses",
        "title": "Blue Light Blocking Glasses",
        "headline": "Protect your eyes.\nSleep better.",
        "description": (
            "Reduce digital eye strain and improve your sleep quality. "
            "Stylish frames that block harmful blue light from screens. "
            "🕶️ Work late without wrecking your sleep."
        ),
        "amazon_url": "https://amzn.to/4dzFSQb",
        "themes": ["study"],
        "dalle_prompt": (
            "bright minimalist home office, clean white desk with laptop and plants, "
            "natural window light, productive and fresh atmosphere, "
            "no people, Pinterest workspace aesthetic, vertical"
        ),
    },
    # ── Fantasy / Cozy ──────────────────────────────────────────
    {
        "id": "scented_candles_fantasy",
        "title": "Fantasy Scented Candles",
        "headline": "Set the mood\nfor adventure",
        "description": (
            "Forest, sandalwood, and amber scented candles that transform your space "
            "for tabletop RPG sessions, cozy reading nights, or just unwinding. "
            "🕯️ Your dungeon deserves ambiance."
        ),
        "amazon_url": "https://amzn.to/4npvJd8",
        "themes": ["fantasy", "cozy", "fireplace"],
        "dalle_prompt": (
            "atmospheric fantasy reading nook, multiple flickering candles on an old wooden table, "
            "leather-bound books stacked beside a cozy armchair, warm amber candlelight, "
            "mystical and inviting evening atmosphere, no people, Pinterest fantasy cozy aesthetic, vertical"
        ),
    },
    {
        "id": "dnd_monster_manual",
        "title": "D&D Monster Manual",
        "headline": "Every dungeon\nneeds a master",
        "description": (
            "The essential Dungeons & Dragons Monster Manual for game masters and players alike. "
            "Hundreds of creatures, lore, and stats for unforgettable campaigns. "
            "🐉 Roll for initiative."
        ),
        "amazon_url": "https://amzn.to/4nyf7Ak",
        "themes": ["fantasy"],
        "dalle_prompt": (
            "tabletop RPG flat lay on dark wood surface, polyhedral dice, hand-drawn dungeon map, "
            "open fantasy rulebook, small metal miniatures, warm candlelight, "
            "no people, Pinterest flat lay TTRPG aesthetic, vertical"
        ),
    },
    {
        "id": "essential_oil_diffuser",
        "title": "Essential Oil Diffuser",
        "headline": "Fill your room\nwith calm",
        "description": (
            "Ultrasonic aromatherapy diffuser with soothing LED mood light. "
            "Lavender for sleep, eucalyptus for focus, peppermint for energy. "
            "🌿 Breathe in, stress out."
        ),
        "amazon_url": "https://amzn.to/3R3qsMx",
        "themes": ["sleep", "nature", "cozy"],
        "dalle_prompt": (
            "serene bedroom corner, white ceramic diffuser releasing soft mist, "
            "small succulent and air plant arrangement, natural linen textures, "
            "soft morning light, peaceful and minimal wellness aesthetic, no people, Pinterest vertical"
        ),
    },
    {
        "id": "himalayan_salt_lamp",
        "title": "Himalayan Salt Lamp",
        "headline": "Warm glow for\nsleep and calm",
        "description": (
            "Natural Himalayan pink salt lamp creates a warm amber glow "
            "perfect for winding down and better sleep. "
            "🌟 Beautiful, functional, and calming."
        ),
        "amazon_url": "https://amzn.to/3R3qsMx",
        "themes": ["sleep", "cozy", "fireplace"],
        "dalle_prompt": (
            "cozy bedroom shelf corner glowing with warm pink-amber light, "
            "small potted plants and books beside the lamp, "
            "soft and serene evening atmosphere, no people, Pinterest cozy bedroom aesthetic, vertical"
        ),
    },
    # ── Travel ───────────────────────────────────────────────────
    {
        "id": "travel_neck_pillow",
        "title": "Travel Neck Pillow",
        "headline": "Sleep anywhere.\nArrive refreshed.",
        "description": (
            "Memory foam travel neck pillow with ergonomic support and washable cover. "
            "Sleep better on planes, trains, and long road trips. "
            "✈️ Never arrive exhausted again."
        ),
        "amazon_url": "https://amzn.to/43doCLH",
        "themes": ["travel"],
        "dalle_prompt": (
            "airplane window seat at night, stars and city lights far below through oval window, "
            "soft travel blanket and book on tray table, calm peaceful journey atmosphere, "
            "no people, Pinterest travel aesthetic, vertical"
        ),
    },
    {
        "id": "wireless_earbuds",
        "title": "Wireless Earbuds",
        "headline": "Your soundtrack,\neverywhere",
        "description": (
            "Premium noise-canceling wireless earbuds with long battery life. "
            "Perfect for travel, commuting, gym, and working. "
            "🎵 Crystal clear sound, zero wires."
        ),
        "amazon_url": "https://amzn.to/4ufS1AG",
        "themes": ["travel", "study"],
        "dalle_prompt": (
            "minimal flat lay on soft linen surface, white wireless earbuds case open, "
            "passport, small notebook and pen, dried flowers for styling, "
            "clean and aesthetic travel vibes, no people, Pinterest flat lay, vertical"
        ),
    },
    # ── Fan / Air ────────────────────────────────────────────────
    {
        "id": "tower_fan",
        "title": "Quiet Tower Fan",
        "headline": "Cool air.\nBetter sleep.",
        "description": (
            "Whisper-quiet tower fan perfect for bedrooms. "
            "Multiple speeds, sleep timer, and remote control. "
            "🌀 Fall asleep cool and wake up refreshed."
        ),
        "amazon_url": "https://amzn.to/4fb6Sbh",
        "themes": ["fan"],
        "dalle_prompt": (
            "airy modern bedroom in summer, light white and natural linen bedding, "
            "sheer curtains gently billowing in a warm breeze from an open window, "
            "bright and fresh morning light, no people, Pinterest summer bedroom aesthetic, vertical"
        ),
    },
    {
        "id": "air_purifier",
        "title": "HEPA Air Purifier",
        "headline": "Breathe clean.\nSleep clean.",
        "description": (
            "True HEPA air purifier removes 99.97% of dust, pollen, and odors. "
            "Ultra-quiet night mode for undisturbed sleep. "
            "🌬️ Cleaner air for a healthier bedroom."
        ),
        "amazon_url": "https://amzn.to/492onGS",
        "themes": ["fan", "nature"],
        "dalle_prompt": (
            "minimalist bright bedroom interior, soft diffused morning light, "
            "green potted plants on windowsill, clean white walls and bedding, "
            "fresh healthy atmosphere, no people, Pinterest minimal wellness aesthetic, vertical"
        ),
    },
]

PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}


# ─── 履歴管理 ──────────────────────────────────────────────────
def _load_history() -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def _save_history(history: list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-HISTORY_LIMIT:], f, indent=2)


def pick_product() -> dict:
    recent = _load_history()
    pool = [p for p in PRODUCTS if p["id"] not in recent]
    if not pool:
        pool = PRODUCTS
    product = random.choice(pool)
    recent.append(product["id"])
    _save_history(recent)
    return product


# ─── Pinterest OAuth ────────────────────────────────────────────
class _OAuthHandler(BaseHTTPRequestHandler):
    code = None
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _OAuthHandler.code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>Authenticated! You can close this tab.</h1>")
    def log_message(self, *args):
        pass


def _authenticate(app_id: str, app_secret: str) -> dict:
    state  = base64.urlsafe_b64encode(os.urandom(16)).decode()
    params = urllib.parse.urlencode({
        "client_id":     app_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         "pins:write,boards:read",
        "state":         state,
    })
    url = f"https://www.pinterest.com/oauth/?{params}"
    print(f"\nOpen this URL in your browser:\n{url}\n")
    webbrowser.open(url)

    # ローカルサーバーでコードをキャプチャ（リダイレクト先がlocalhostの場合）
    print("Waiting for redirect... (If nothing happens, paste the 'code' parameter from the URL manually)")
    code = input("Paste the 'code' from the redirect URL: ").strip()

    r = requests.post(
        f"{PINTEREST_BASE}/oauth/token",
        auth=(app_id, app_secret),
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    r.raise_for_status()
    return r.json()


def _refresh_token(app_id: str, app_secret: str, refresh_token: str) -> dict:
    r = requests.post(
        f"{PINTEREST_BASE}/oauth/token",
        auth=(app_id, app_secret),
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    r.raise_for_status()
    return r.json()


def get_access_token() -> str:
    env = _load_env()
    app_id     = env.get("PINTEREST_APP_ID", "")
    app_secret = env.get("PINTEREST_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("PINTEREST_APP_ID / PINTEREST_APP_SECRET が .env に未設定です")

    token_data = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            token_data = pickle.load(f)

    if token_data and token_data.get("refresh_token"):
        try:
            new = _refresh_token(app_id, app_secret, token_data["refresh_token"])
            token_data.update(new)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(token_data, f)
            return token_data["access_token"]
        except Exception as e:
            logging.warning(f"Token refresh failed: {e}. Re-authenticating...")

    token_data = _authenticate(app_id, app_secret)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump(token_data, f)
    return token_data["access_token"]


# ─── ボードID取得 ───────────────────────────────────────────────
def get_board_id(access_token: str, board_name: str = None) -> str:
    env = _load_env()
    if env.get("PINTEREST_BOARD_ID"):
        return env["PINTEREST_BOARD_ID"]

    r = requests.get(
        f"{PINTEREST_BASE}/boards",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page_size": 25},
    )
    r.raise_for_status()
    boards = r.json().get("items", [])
    if not boards:
        raise RuntimeError("ボードが見つかりません。Pinterest でボードを作成してください。")

    for b in boards:
        print(f"  {b['id']}  {b['name']}")

    if board_name:
        for b in boards:
            if board_name.lower() in b["name"].lower():
                return b["id"]

    return boards[0]["id"]


# ─── 画像生成 ───────────────────────────────────────────────────
def _draw_outlined_text(draw, xy, text, font, fill=(255, 255, 255), outline=(0, 0, 0), stroke=3):
    x, y = xy
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def generate_pin_image(product: dict) -> Image.Image:
    env = _load_env()
    client = OpenAI(api_key=env["OPENAI_API_KEY"])

    logging.info(f"  DALL-E generating image for {product['id']}...")
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=product["dalle_prompt"],
            size="1024x1536",
            quality="low",
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
    except Exception as e:
        logging.warning(f"  DALL-E failed ({e}), using gradient fallback")
        img = Image.new("RGB", (1024, 1536), (30, 20, 50))

    W, H = img.size  # 1024 x 1536

    # 下部グラデーションオーバーレイ
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y in range(H // 2, H):
        alpha = int(210 * ((y - H // 2) / (H // 2)) ** 1.5)
        for x in range(W):
            overlay.putpixel((x, y), (0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── SleepScape ブランドバッジ（右上）──
    try:
        font_brand = ImageFont.truetype(FONT_REG, 36)
        font_moon  = ImageFont.truetype(FONT_EMOJI, 40)
    except Exception:
        font_brand = font_moon = ImageFont.load_default()

    moon_w  = draw.textbbox((0, 0), "🌙", font=font_moon)[2]
    brand_w = draw.textbbox((0, 0), " SleepScape", font=font_brand)[2]
    bx = W - moon_w - brand_w - 20
    by = 18
    draw.text((bx, by), "🌙", font=font_moon, embedded_color=True)
    _draw_outlined_text(draw, (bx + moon_w + 4, by + 4), "SleepScape", font=font_brand,
                        fill=(255, 255, 255), outline=(0, 0, 0), stroke=2)

    # ── 商品タイトル（下部）──
    try:
        font_title = ImageFont.truetype(FONT_BOLD, 72) if os.path.exists(FONT_BOLD) \
            else ImageFont.truetype(FONT_REG, 72)
    except Exception:
        font_title = ImageFont.load_default()

    margin = 40
    lines  = product["headline"].split("\n")
    y_text = H - 220

    for line in reversed(lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        lw   = bbox[2] - bbox[0]
        lh   = bbox[3] - bbox[1]
        _draw_outlined_text(draw, ((W - lw) // 2, y_text - lh),
                            line, font=font_title,
                            fill=(255, 255, 255), outline=(0, 0, 0), stroke=4)
        y_text -= lh + 8

    # ── CTA ──
    try:
        font_cta = ImageFont.truetype(FONT_REG, 38)
    except Exception:
        font_cta = ImageFont.load_default()

    cta   = "Shop on Amazon →"
    cta_w = draw.textbbox((0, 0), cta, font=font_cta)[2]
    _draw_outlined_text(draw, ((W - cta_w) // 2, H - 65), cta, font=font_cta,
                        fill=(255, 210, 100), outline=(0, 0, 0), stroke=2)

    return img


# ─── Pinterest 投稿 ─────────────────────────────────────────────
def post_pin(access_token: str, board_id: str, product: dict, img: Image.Image):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    body = {
        "board_id": board_id,
        "title":    product["title"],
        "description": product["description"],
        "link":     product["amazon_url"],
        "media_source": {
            "source_type":   "image_base64",
            "content_type":  "image/jpeg",
            "data":          img_b64,
        },
    }

    r = requests.post(
        f"{PINTEREST_BASE}/pins",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        json=body,
    )
    r.raise_for_status()
    return r.json()


# ─── メイン ────────────────────────────────────────────────────
def main():
    logging.info("=== Pinterest Auto Pin ===")

    access_token = get_access_token()
    board_id     = get_board_id(access_token)
    logging.info(f"Board ID: {board_id}")

    product = pick_product()
    logging.info(f"Product: {product['id']} — {product['title']}")

    img    = generate_pin_image(product)
    result = post_pin(access_token, board_id, product, img)

    pin_id  = result.get("id", "?")
    pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
    logging.info(f"✅ Posted: {pin_url}")
    return result


if __name__ == "__main__":
    main()
