"""
Pinterest ピン素材自動生成 (SleepScapeDaily)
- 商品カタログからランダム選択
- DALL-E (gpt-image-1) で高品質縦長ライフスタイル画像生成 (1024x1536)
- テキストオーバーレイ + SleepScapeブランディング
- 画像 + 説明文を pins_output/ に保存 → Pinterest に手動投稿
- 履歴管理で重複防止 (10件クールダウン)
"""

import os, json, base64, io, random, sys, logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

DIR         = os.path.dirname(__file__)
ENV_FILE    = os.path.join(DIR, ".env")
HISTORY_FILE = os.path.join(DIR, "pinterest_history.json")
OUTPUT_DIR  = os.path.join(DIR, "pins_output")
FONT_BOLD   = os.path.join(DIR, "fonts", "Cinzel-Bold.ttf")
FONT_REG    = "/System/Library/Fonts/Helvetica.ttc"
FONT_EMOJI  = "/System/Library/Fonts/Apple Color Emoji.ttc"
HISTORY_LIMIT = 10


# ─── .env 読み込み ──────────────────────────────────────────────
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
        "headline": "The best sleep of\nyour life starts here",
        "description": (
            "Struggling to fall asleep? A white noise machine drowns out distractions "
            "and creates the perfect sleep environment — every single night.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/3R3qsMx\n\n"
            "#WhiteNoise #SleepBetter #SleepTips #BedtimeRoutine #SleepScape"
        ),
        "dalle_prompt": (
            "cozy minimalist bedroom at night, soft warm glow from a small nightstand lamp, "
            "plush white bedding perfectly arranged, sheer curtains with faint moonlight, "
            "a glass of water on the nightstand, peaceful and inviting atmosphere, "
            "no people, high-end interior photography style, warm neutral tones, "
            "ultra sharp, Pinterest lifestyle aesthetic, vertical portrait"
        ),
    },
    {
        "id": "sleep_headphones",
        "title": "Sleep Headphones",
        "headline": "Fall asleep to\nyour favorite sounds",
        "description": (
            "These ultra-thin Bluetooth sleep headphones stay comfortable all night — "
            "even for side sleepers. Pair them with ambient sounds for the perfect sleep experience.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4fjALG3\n\n"
            "#SleepHeadphones #AmbientSounds #SleepScape #BetterSleep #SleepHacks"
        ),
        "dalle_prompt": (
            "dreamy cozy bedroom in golden hour light, soft chunky knit blanket draped over "
            "crisp white pillows, warm amber lamp glow, small stack of books on nightstand, "
            "calm and inviting, no people, editorial bedroom photography, "
            "warm earthy tones, ultra detailed, Pinterest cozy bedroom aesthetic, vertical"
        ),
    },
    {
        "id": "blackout_sleep_mask",
        "title": "Blackout Sleep Mask",
        "headline": "Total darkness.\nTotal rest.",
        "description": (
            "Block 100% of light and wake up completely rested. "
            "This adjustable silk-feel eye mask is a game changer for travelers and light-sensitive sleepers.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/42CF7Rg\n\n"
            "#SleepMask #BlackoutMask #SleepBetter #TravelSleep #SleepScape"
        ),
        "dalle_prompt": (
            "luxurious minimalist bedroom, smooth silk bedding in ivory and soft grey, "
            "subtle morning light filtering through blackout curtains, "
            "fresh flowers on the nightstand, serene and calm atmosphere, "
            "no people, luxury hotel room aesthetic, soft diffused light, "
            "ultra detailed, Pinterest bedroom inspo, vertical"
        ),
    },
    {
        "id": "weighted_blanket",
        "title": "Weighted Blanket",
        "headline": "Like a hug that\nhelps you sleep",
        "description": (
            "Reduce anxiety and fall asleep faster with a weighted blanket. "
            "Science-backed comfort that works from the very first night.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/3YbTKDV\n\n"
            "#WeightedBlanket #AnxietyRelief #SleepBetter #CozyHome #SleepScape"
        ),
        "dalle_prompt": (
            "ultra cozy autumn bedroom corner, chunky knit weighted blanket draped over "
            "a plush reading chair, warm string lights on the wall, steaming ceramic mug "
            "on a small wooden side table, fallen leaves outside the window, "
            "warm amber and terracotta tones, no people, hygge aesthetic, "
            "ultra detailed, Pinterest cozy fall bedroom, vertical"
        ),
    },
    {
        "id": "pillow_speaker",
        "title": "Pillow Speaker",
        "headline": "8 hours of ambient\nsound, just for you",
        "description": (
            "An ultra-thin speaker that fits inside your pillowcase. "
            "Listen to SleepScape ambient sounds all night at low volume — "
            "without disturbing anyone next to you.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4doJIvg\n\n"
            "#PillowSpeaker #AmbientSound #SleepScape #SleepTech #BetterSleep"
        ),
        "dalle_prompt": (
            "serene minimalist bedroom, pristine white pillow arrangement on clean linen sheets, "
            "soft diffused morning light, small succulent plant on windowsill, "
            "peaceful and airy atmosphere, no people, Scandinavian interior style, "
            "soft whites and natural tones, ultra sharp, Pinterest minimal bedroom, vertical"
        ),
    },
    # ── Study / Focus ───────────────────────────────────────────
    {
        "id": "noise_canceling_headphones",
        "title": "Noise-Canceling Headphones",
        "headline": "Deep focus starts\nwith silence",
        "description": (
            "Enter a flow state and get more done. "
            "Premium noise-canceling headphones for studying, working from home, or unwinding "
            "with SleepScape ambient sounds.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4wvOyQh\n\n"
            "#NoiseCanceling #StudyTips #FocusMode #WorkFromHome #SleepScape"
        ),
        "dalle_prompt": (
            "aesthetic home study desk setup, warm wooden desk surface, open notebook with neat handwriting, "
            "steaming pour-over coffee, stack of books, small potted plant, "
            "golden hour light streaming through a window, dust particles in the light beam, "
            "no people, editorial study aesthetic, warm tones, ultra detailed, "
            "Pinterest desk setup inspo, vertical"
        ),
    },
    {
        "id": "led_desk_lamp",
        "title": "LED Desk Lamp",
        "headline": "Light up your\nfocus zone",
        "description": (
            "Adjustable brightness and color temperature LED lamp — easy on your eyes "
            "during long study or work sessions. Your desk deserves better light.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4wAAgxM\n\n"
            "#DeskSetup #StudyRoom #DeskLamp #ProductivityTips #SleepScape"
        ),
        "dalle_prompt": (
            "cozy study corner at night, warm amber desk lamp casting a beautiful glow, "
            "open planner and fountain pen, small cactus, wooden desk organizer, "
            "dark moody background contrasting warm light pool, "
            "no people, moody study aesthetic, editorial quality, "
            "ultra sharp, Pinterest night study vibes, vertical"
        ),
    },
    {
        "id": "blue_light_glasses",
        "title": "Blue Light Blocking Glasses",
        "headline": "Work late.\nStill sleep well.",
        "description": (
            "Stylish blue light blocking glasses reduce digital eye strain "
            "and help you sleep better even after long screen sessions.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4dzFSQb\n\n"
            "#BlueLight #EyeCare #SleepBetter #WorkFromHome #SleepScape"
        ),
        "dalle_prompt": (
            "bright modern home office, clean white desk with open laptop, "
            "architectural plants like a monstera in background, "
            "large window with natural daylight, minimalist and productive atmosphere, "
            "no people, high-end interior photography, crisp whites and greens, "
            "ultra detailed, Pinterest workspace aesthetic, vertical"
        ),
    },
    # ── Fantasy / Cozy ──────────────────────────────────────────
    {
        "id": "scented_candles_fantasy",
        "title": "Fantasy Scented Candles",
        "headline": "Set the mood\nfor adventure",
        "description": (
            "Forest, sandalwood, and amber scented candles that transform any space "
            "into a cozy fantasy realm — perfect for tabletop RPG sessions and reading nights.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4npvJd8\n\n"
            "#ScentedCandles #CozyVibes #TTRPG #DnD #SleepScape #FantasyAesthetic"
        ),
        "dalle_prompt": (
            "moody fantasy reading nook, multiple pillar candles of different heights "
            "casting dramatic warm shadows, leather-bound books and a brass compass, "
            "dark wood shelves with dried botanicals, rich dark green and amber tones, "
            "no people, dark academia aesthetic, editorial quality lighting, "
            "ultra detailed, Pinterest dark academia, vertical"
        ),
    },
    {
        "id": "dnd_starter_set",
        "title": "D&D Starter Set",
        "headline": "Every great story\nneeds a beginning",
        "description": (
            "New to tabletop RPG? The Dungeons & Dragons Starter Set is everything "
            "you need to start an epic campaign tonight.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4nyf7Ak\n\n"
            "#DungeonsAndDragons #TTRPG #TabletopRPG #DnD #SleepScape #FantasyGaming"
        ),
        "dalle_prompt": (
            "dramatic tabletop RPG scene, polyhedral dice scattered on a hand-drawn parchment map, "
            "miniature figurines mid-battle, warm candlelight from an iron candelabra, "
            "dark oak table surface with carved patterns, moody and cinematic atmosphere, "
            "no people, dark fantasy aesthetic, editorial photography, "
            "ultra detailed, Pinterest TTRPG aesthetic, vertical"
        ),
    },
    {
        "id": "essential_oil_diffuser",
        "title": "Essential Oil Diffuser",
        "headline": "Fill your room\nwith calm",
        "description": (
            "Ultrasonic aromatherapy diffuser with a soothing LED mood light. "
            "Lavender for sleep, eucalyptus for focus, cedarwood for relaxation.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/3R3qsMx\n\n"
            "#Aromatherapy #EssentialOils #SelfCare #SleepScape #WellnessRoutine"
        ),
        "dalle_prompt": (
            "serene wellness corner, elegant white ceramic diffuser releasing soft wispy mist, "
            "small amber glass essential oil bottles arranged neatly, "
            "air plants and a smooth river stone, natural linen cloth underneath, "
            "soft morning window light, spa-like calm, no people, "
            "clean wellness aesthetic, ultra detailed, Pinterest wellness inspo, vertical"
        ),
    },
    {
        "id": "himalayan_salt_lamp",
        "title": "Himalayan Salt Lamp",
        "headline": "Warm glow for\nsleep and calm",
        "description": (
            "A natural Himalayan pink salt lamp creates a warm amber glow "
            "that makes any bedroom feel like a sanctuary.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/3R3qsMx\n\n"
            "#SaltLamp #CozyBedroom #SleepScape #BedroomDecor #WarmLighting"
        ),
        "dalle_prompt": (
            "cozy bedroom shelf styled with a glowing pink himalayan salt lamp, "
            "surrounding succulents and trailing ivy, small framed art print, "
            "warm amber light filling the frame, dark background for contrast, "
            "no people, cozy bedroom shelf styling, editorial quality, "
            "ultra detailed, Pinterest bedroom decor, vertical"
        ),
    },
    # ── Travel ───────────────────────────────────────────────────
    {
        "id": "travel_neck_pillow",
        "title": "Travel Neck Pillow",
        "headline": "Sleep anywhere.\nArrive refreshed.",
        "description": (
            "Memory foam travel neck pillow with ergonomic support. "
            "Sleep better on planes, trains, and long road trips — and actually arrive feeling rested.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/43doCLH\n\n"
            "#TravelTips #TravelSleep #NeckPillow #SleepScape #TravelHacks"
        ),
        "dalle_prompt": (
            "atmospheric airplane window seat at night, deep dark sky with stars visible, "
            "faint city lights far below on the horizon, soft overhead reading light, "
            "cozy travel blanket folded on seat, small journal and pen in the pocket, "
            "no people, cinematic travel photography, cool blue and warm amber tones, "
            "ultra detailed, Pinterest travel aesthetic, vertical"
        ),
    },
    {
        "id": "wireless_earbuds",
        "title": "Wireless Earbuds",
        "headline": "Your soundtrack,\neverywhere",
        "description": (
            "Premium noise-canceling wireless earbuds for travel, commuting, and working out. "
            "Crystal clear audio, long battery life, zero wires.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4ufS1AG\n\n"
            "#WirelessEarbuds #TravelEssentials #SleepScape #TechGadgets #NoiseCanceling"
        ),
        "dalle_prompt": (
            "clean minimal flat lay on soft natural linen, white wireless earbuds case "
            "open beside a worn leather passport holder, small journal, "
            "dried pampas grass sprig, all arranged artfully, "
            "soft natural side light with gentle shadows, no people, "
            "minimalist travel flat lay, ultra detailed, Pinterest travel flat lay, vertical"
        ),
    },
    # ── Fan / Air ────────────────────────────────────────────────
    {
        "id": "tower_fan",
        "title": "Quiet Tower Fan",
        "headline": "Cool air.\nBetter sleep.",
        "description": (
            "A whisper-quiet tower fan with multiple speeds, sleep timer, and remote control. "
            "The perfect addition to any bedroom for hot summer nights.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/4fb6Sbh\n\n"
            "#TowerFan #SummerSleep #CoolBedroom #SleepScape #SleepTips"
        ),
        "dalle_prompt": (
            "bright airy summer bedroom, crisp white linen bedding, "
            "sheer curtains billowing gently in a warm breeze from an open window, "
            "sunlight casting soft shadows across the bed, small potted herbs on the windowsill, "
            "clean and fresh morning atmosphere, no people, "
            "summer bedroom editorial photography, bright and airy, "
            "ultra detailed, Pinterest summer bedroom, vertical"
        ),
    },
    {
        "id": "air_purifier",
        "title": "HEPA Air Purifier",
        "headline": "Breathe clean.\nSleep clean.",
        "description": (
            "A HEPA air purifier removes 99.97% of dust, pollen, and odors "
            "for a healthier bedroom environment and better sleep quality.\n\n"
            "🛒 Shop on Amazon → https://amzn.to/492onGS\n\n"
            "#AirPurifier #CleanAir #HealthyHome #SleepScape #BedroomEssentials"
        ),
        "dalle_prompt": (
            "serene minimalist bedroom with large windows, lush monstera and fiddle leaf fig plants, "
            "crisp white walls and natural oak wood furniture, "
            "soft morning light flooding the room, fresh and clean atmosphere, "
            "no people, Japandi interior aesthetic, ultra detailed, "
            "Pinterest minimal bedroom inspo, vertical"
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


# ─── テキスト描画ヘルパー ───────────────────────────────────────
def _draw_outlined_text(draw, xy, text, font, fill=(255, 255, 255), outline=(0, 0, 0), stroke=3):
    x, y = xy
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _fit_font(path, text, max_width, max_size, min_size=28):
    size = max_size
    while size >= min_size:
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()
        w = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)[2]
        if w <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(path, min_size)


# ─── ピン画像生成 ──────────────────────────────────────────────
def generate_pin_image(product: dict) -> Image.Image:
    env = _load_env()
    client = OpenAI(api_key=env["OPENAI_API_KEY"])

    logging.info(f"  Generating image: {product['id']}...")
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=product["dalle_prompt"],
            size="1024x1536",
            quality="high",
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        logging.info("  Image generated OK")
    except Exception as e:
        logging.warning(f"  DALL-E failed ({e}), using gradient fallback")
        img = Image.new("RGB", (1024, 1536), (25, 20, 45))

    W, H = img.size  # 1024 x 1536

    # ── 下部グラデーションオーバーレイ（滑らか）──
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad_start = int(H * 0.55)
    for y in range(grad_start, H):
        t = (y - grad_start) / (H - grad_start)
        alpha = int(200 * (t ** 1.4))
        for x in range(W):
            overlay.putpixel((x, y), (0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── SleepScape ブランドバッジ（右上）──
    try:
        font_brand = ImageFont.truetype(FONT_REG, 34)
        font_moon  = ImageFont.truetype(FONT_EMOJI, 40)
    except Exception:
        font_brand = font_moon = ImageFont.load_default()

    moon  = "🌙"
    label = " SleepScape"
    mw = draw.textbbox((0, 0), moon, font=font_moon)[2]
    lw = draw.textbbox((0, 0), label, font=font_brand)[2]
    bx = W - mw - lw - 20
    by = 18
    draw.text((bx, by), moon, font=font_moon, embedded_color=True)
    _draw_outlined_text(draw, (bx + mw, by + 6), label, font=font_brand,
                        fill=(255, 255, 255), outline=(0, 0, 0), stroke=2)

    # ── 商品タイトル（下部）──
    font_path = FONT_BOLD if os.path.exists(FONT_BOLD) else FONT_REG
    margin = 48
    lines  = product["headline"].split("\n")

    # フォントサイズを行幅に合わせて自動調整
    font_title = _fit_font(font_path, max(lines, key=len), W - margin * 2, max_size=80)
    lh = draw.textbbox((0, 0), "A", font=font_title)[3] + 8

    y_text = H - 110 - lh * len(lines)
    for line in lines:
        lw = draw.textbbox((0, 0), line, font=font_title)[2]
        _draw_outlined_text(draw, ((W - lw) // 2, y_text), line, font=font_title,
                            fill=(255, 255, 255), outline=(0, 0, 0), stroke=4)
        y_text += lh

    # ── CTA ──
    try:
        font_cta = ImageFont.truetype(FONT_REG, 32)
    except Exception:
        font_cta = ImageFont.load_default()

    cta   = "Shop on Amazon  →"
    cta_w = draw.textbbox((0, 0), cta, font=font_cta)[2]
    _draw_outlined_text(draw, ((W - cta_w) // 2, H - 68), cta, font=font_cta,
                        fill=(255, 210, 80), outline=(0, 0, 0), stroke=2)

    return img


# ─── 保存 ──────────────────────────────────────────────────────
def save_pin(product: dict, img: Image.Image):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    base = f"{date_str}_{product['id']}"

    img_path = os.path.join(OUTPUT_DIR, f"{base}.jpg")
    txt_path = os.path.join(OUTPUT_DIR, f"{base}.txt")

    img.save(img_path, format="JPEG", quality=95)

    with open(txt_path, "w") as f:
        f.write(f"Title: {product['title']}\n\n")
        f.write(product["description"])

    logging.info(f"  Saved: {img_path}")
    logging.info(f"  Saved: {txt_path}")
    return img_path


# ─── メイン ────────────────────────────────────────────────────
def main():
    logging.info("=== Pinterest Pin Generator ===")
    product = pick_product()
    logging.info(f"Product: {product['title']}")
    img = generate_pin_image(product)
    save_pin(product, img)
    logging.info("Done.")


if __name__ == "__main__":
    main()
