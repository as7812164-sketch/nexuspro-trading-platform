import os
import math
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

ARTIFACT_DIR = r"C:\Users\power\.gemini\antigravity\brain\dcc51f2a-4d4e-4c0e-9f17-414b6ff083d5"

def get_font(size=14, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "arial.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_dashed_line(draw, x1, y1, x2, y2, color, width=1, dash=6, gap=4):
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0:
        return
    dx = (x2 - x1) / dist
    dy = (y2 - y1) / dist
    curr = 0
    while curr < dist:
        end = min(curr + dash, dist)
        draw.line([
            (x1 + dx * curr, y1 + dy * curr),
            (x1 + dx * end, y1 + dy * end)
        ], fill=color, width=width)
        curr += dash + gap

# ==============================================================================
# CHART 1: 1-HOUR TIMEFRAME (1H POI & FIRST TAP)
# ==============================================================================
def build_1h_chart():
    width = 1600
    height = 920
    img = Image.new("RGBA", (width, height), (19, 23, 34, 255)) # TradingView Dark #131722
    draw = ImageDraw.Draw(img)

    f_title = get_font(20, bold=True)
    f_sub = get_font(13, bold=False)
    f_badge = get_font(12, bold=True)
    f_label = get_font(14, bold=True)
    f_desc = get_font(12, bold=False)
    f_price = get_font(11, bold=False)

    pad_left = 60
    pad_right = 110
    pad_top = 80
    pad_bottom = 70
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    candles = [
        {"o": 66400, "h": 66650, "l": 66320, "c": 66600}, # 0
        {"o": 66600, "h": 66780, "l": 66510, "c": 66720}, # 1
        {"o": 66720, "h": 66900, "l": 66650, "c": 66810}, # 2
        {"o": 66810, "h": 66850, "l": 66600, "c": 66650}, # 3
        {"o": 66650, "h": 67020, "l": 66610, "c": 66980}, # 4
        # Candle 5: 1H BULLISH ORDER BLOCK ($66,780 - $67,200)
        {"o": 66980, "h": 67200, "l": 66780, "c": 66820}, # 5 (1H OB)
        # Strong Impulse
        {"o": 66820, "h": 67650, "l": 66800, "c": 67580}, # 6
        {"o": 67580, "h": 68120, "l": 67500, "c": 68050}, # 7
        {"o": 68050, "h": 68400, "l": 67950, "c": 68350}, # 8
        {"o": 68350, "h": 68650, "l": 68200, "c": 68600}, # 9
        {"o": 68600, "h": 68850, "l": 68450, "c": 68750}, # 10 (High $68,850)
        # Correction down
        {"o": 68750, "h": 68800, "l": 68320, "c": 68400}, # 11
        {"o": 68400, "h": 68580, "l": 68150, "c": 68250}, # 12
        {"o": 68250, "h": 68420, "l": 67950, "c": 68000}, # 13
        {"o": 68000, "h": 68150, "l": 67700, "c": 67750}, # 14
        {"o": 67750, "h": 68050, "l": 67650, "c": 67980}, # 15
        {"o": 67980, "h": 68020, "l": 67550, "c": 67600}, # 16
        {"o": 67600, "h": 67800, "l": 67420, "c": 67480}, # 17
        {"o": 67480, "h": 67650, "l": 67350, "c": 67400}, # 18
        {"o": 67400, "h": 67550, "l": 67280, "c": 67320}, # 19
        {"o": 67320, "h": 67480, "l": 67220, "c": 67260}, # 20
        # Candle 21: THE 1H FIRST TAP! Wick taps into $67,180 (inside 1H POI top $67,200)
        {"o": 67260, "h": 67380, "l": 67180, "c": 67310}, # 21
    ]

    all_highs = [c["h"] for c in candles]
    all_lows = [c["l"] for c in candles]
    min_p = min(all_lows) - 200
    max_p = max(all_highs) + 200
    p_range = max_p - min_p

    def to_y(p):
        return pad_top + plot_h - int(((p - min_p) / p_range) * plot_h)

    n = len(candles)
    c_w = plot_w // (n + 5)
    gap = max(4, c_w // 4)
    body_w = c_w - gap

    def to_x(i):
        return pad_left + i * c_w + c_w // 2

    # Grid Lines
    for p_step in range(int(min_p // 400 * 400), int(max_p + 400), 400):
        if min_p <= p_step <= max_p:
            gy = to_y(p_step)
            draw.line([(pad_left, gy), (pad_left + plot_w, gy)], fill=(42, 46, 57, 180), width=1)
            draw.text((pad_left + plot_w + 12, gy - 7), f"{p_step:,.0f}", fill=(132, 142, 156, 255), font=f_price)

    draw.line([(pad_left + plot_w, pad_top), (pad_left + plot_w, pad_top + plot_h)], fill=(42, 46, 57, 255), width=1)

    # 1H POI Box
    ob_top_p = 67200
    ob_bot_p = 66780
    ob_y1 = to_y(ob_top_p)
    ob_y2 = to_y(ob_bot_p)
    ob_x1 = to_x(5) - body_w // 2
    ob_x2 = pad_left + plot_w

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([ob_x1, ob_y1, ob_x2, ob_y2], fill=(8, 153, 129, 45), outline=(8, 153, 129, 230), width=2)
    mid_y = (ob_y1 + ob_y2) // 2
    draw_dashed_line(ov_draw, ob_x1, mid_y, ob_x2, mid_y, color=(8, 153, 129, 160), width=1)
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Candlesticks
    for i, c in enumerate(candles):
        cx = to_x(i)
        is_green = c["c"] >= c["o"]
        c_color = (8, 153, 129, 255) if is_green else (242, 54, 69, 255)
        # Wick
        y_high = to_y(c["h"])
        y_low = to_y(c["l"])
        draw.line([(cx, y_high), (cx, y_low)], fill=c_color, width=2)
        # Body
        y_top = to_y(max(c["o"], c["c"]))
        y_bot = to_y(min(c["o"], c["c"]))
        if y_bot == y_top:
            y_bot += 1
        x1 = cx - body_w // 2
        x2 = cx + body_w // 2
        draw.rectangle([x1, y_top, x2, y_bot], fill=c_color)

    # 1H POI Label (Drawn with dark background pill to avoid candle overlap)
    lbl_x = to_x(7)
    lbl_y = ob_y1 + 10
    draw.rectangle([lbl_x - 10, lbl_y - 4, lbl_x + 470, lbl_y + 44], fill=(16, 24, 38, 240), outline=(38, 166, 154, 200), width=1)
    draw.text((lbl_x, lbl_y), "1H HTF POI (BULLISH DEMAND ORDER BLOCK)", fill=(38, 166, 154, 255), font=f_label)
    draw.text((lbl_x, lbl_y + 22), f"Zone: ${ob_bot_p:,.0f} - ${ob_top_p:,.0f} | Created by Institutional Displacement", fill=(160, 200, 190, 240), font=f_desc)

    # HIGHLIGHT THE 1H FIRST TAP
    tap_i = 21
    tap_c = candles[tap_i]
    tap_cx = to_x(tap_i)
    tap_wick_y = to_y(tap_c["l"])

    draw.ellipse([tap_cx - 16, tap_wick_y - 16, tap_cx + 16, tap_wick_y + 16], outline=(255, 215, 0, 255), width=3)
    draw.ellipse([tap_cx - 26, tap_wick_y - 26, tap_cx + 26, tap_wick_y + 26], outline=(255, 215, 0, 140), width=2)

    arrow_tip_y = tap_wick_y + 24
    arrow_base_y = tap_wick_y + 60
    draw.polygon([
        (tap_cx, tap_wick_y + 6),
        (tap_cx - 10, arrow_tip_y),
        (tap_cx + 10, arrow_tip_y)
    ], fill=(255, 215, 0, 255))
    draw.rectangle([tap_cx - 4, arrow_tip_y, tap_cx + 4, arrow_base_y], fill=(255, 215, 0, 255))

    card_x = tap_cx - 240
    card_y = arrow_base_y + 10
    draw.rectangle([card_x, card_y, card_x + 480, card_y + 90], fill=(24, 28, 42, 250), outline=(255, 215, 0, 220), width=2)
    draw.text((card_x + 16, card_y + 12), ">> STEP 1: 1H ORDER BLOCK FIRST TAP!", fill=(255, 215, 0, 255), font=f_label)
    draw.text((card_x + 16, card_y + 36), f"Price wick pierced 1H POI at ${tap_c['l']:,} (Inside ${ob_top_p:,})", fill=(255, 255, 255, 255), font=f_desc)
    draw.text((card_x + 16, card_y + 58), "RULE: DO NOT ENTER ON 1H! Switch immediately to 5M Timeframe!", fill=(56, 189, 248, 255), font=f_badge)

    # Header
    draw.rectangle([0, 0, width, 60], fill=(19, 23, 34, 255))
    draw.line([(0, 60), (width, 60)], fill=(42, 46, 57, 255), width=1)
    draw.text((pad_left, 16), "BTCUSDT.P  *  1H  *  BINANCE FUTURES", fill=(255, 255, 255, 255), font=f_title)
    draw.text((pad_left + 430, 20), "STAGE 1: HIGHER TIMEFRAME (1H) POI IDENTIFICATION & FIRST TAP", fill=(255, 215, 0, 255), font=f_badge)

    draw.rectangle([width - 340, 14, width - pad_right + 10, 46], fill=(28, 32, 48, 255), outline=(56, 189, 248, 120), width=1)
    draw.text((width - 325, 20), "HERMES MSOB 2.0 * 1H MASTER", fill=(56, 189, 248, 255), font=f_badge)

    # Footer
    draw.line([(pad_left, pad_top + plot_h), (pad_left + plot_w, pad_top + plot_h)], fill=(42, 46, 57, 255), width=1)
    draw.text((pad_left + 10, pad_top + plot_h + 12), "1H Candlestick Flow (Approaching Demand Order Block) * Time Axis", fill=(132, 142, 156, 255), font=f_price)

    out_path = os.path.join(ARTIFACT_DIR, "step1_1h_poi_first_tap.png")
    img.save(out_path, format="PNG")
    print("Saved 1H Chart to:", out_path)
    return out_path


# ==============================================================================
# CHART 2: 5-MINUTE TIMEFRAME (ZOOMED IN: DOWNTREND -> MSS -> 5M POI RETEST ENTRY)
# ==============================================================================
def build_5m_chart():
    width = 1600
    height = 920
    img = Image.new("RGBA", (width, height), (19, 23, 34, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(20, bold=True)
    f_sub = get_font(13, bold=False)
    f_badge = get_font(12, bold=True)
    f_label = get_font(14, bold=True)
    f_desc = get_font(12, bold=False)
    f_price = get_font(11, bold=False)

    pad_left = 60
    pad_right = 110
    pad_top = 80
    pad_bottom = 70
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    # Zoomed-in 5M Candlesticks (Micro Structure of 1H Tap)
    candles = [
        {"o": 67390, "h": 67450, "l": 67360, "c": 67420}, # 0
        {"o": 67420, "h": 67470, "l": 67350, "c": 67370}, # 1 (LH1 = $67,470)
        {"o": 67370, "h": 67390, "l": 67290, "c": 67310}, # 2
        {"o": 67310, "h": 67330, "l": 67250, "c": 67260}, # 3 (LL1 = $67,250)
        {"o": 67260, "h": 67320, "l": 67260, "c": 67310}, # 4
        # Candle 5: RECENT LOWER HIGH ($67,320)
        {"o": 67310, "h": 67320, "l": 67240, "c": 67250}, # 5 (Recent LH = $67,320)
        {"o": 67250, "h": 67270, "l": 67190, "c": 67200}, # 6
        {"o": 67200, "h": 67230, "l": 67180, "c": 67190}, # 7
        # Candle 8: 1H POI Tap Wick touches $67,180! (LL2)
        {"o": 67190, "h": 67230, "l": 67180, "c": 67220}, # 8 (LL2 / 1H Tap = $67,180)
        # Candle 9: 5M LAST POI (Base candle of bullish impulse: $67,205 - $67,245)
        {"o": 67220, "h": 67245, "l": 67205, "c": 67235}, # 9 (5M Last POI)
        # Breakout leg breaking above Recent LH ($67,320)
        {"o": 67235, "h": 67290, "l": 67230, "c": 67285}, # 10
        {"o": 67285, "h": 67360, "l": 67280, "c": 67355}, # 11 (Breaks $67,320! MSS confirmed!)
        {"o": 67355, "h": 67420, "l": 67350, "c": 67410}, # 12 (Displacement high $67,420)
        # Pullback towards 5M Last POI
        {"o": 67410, "h": 67415, "l": 67330, "c": 67340}, # 13
        {"o": 67340, "h": 67350, "l": 67280, "c": 67290}, # 14
        {"o": 67290, "h": 67300, "l": 67245, "c": 67255}, # 15
        # Candle 16: RETEST TAP OF 5M LAST POI! Wick touches $67,220 -> ENTRY!
        {"o": 67255, "h": 67290, "l": 67220, "c": 67280}, # 16 (ENTRY CANDLE)
        # Expansion towards TP
        {"o": 67280, "h": 67370, "l": 67275, "c": 67360}, # 17
        {"o": 67360, "h": 67450, "l": 67355, "c": 67440}, # 18
        {"o": 67440, "h": 67540, "l": 67430, "c": 67530}, # 19
    ]

    all_highs = [c["h"] for c in candles]
    all_lows = [c["l"] for c in candles]
    min_p = 67050
    max_p = 67600
    p_range = max_p - min_p

    def to_y(p):
        return pad_top + plot_h - int(((p - min_p) / p_range) * plot_h)

    n = len(candles)
    c_w = plot_w // (n + 4)
    gap = max(4, c_w // 4)
    body_w = c_w - gap

    def to_x(i):
        return pad_left + i * c_w + c_w // 2

    # Grid Lines
    for p_step in range(int(min_p // 50 * 50), int(max_p + 50), 50):
        if min_p <= p_step <= max_p:
            gy = to_y(p_step)
            draw.line([(pad_left, gy), (pad_left + plot_w, gy)], fill=(42, 46, 57, 180), width=1)
            draw.text((pad_left + plot_w + 12, gy - 7), f"{p_step:,.0f}", fill=(132, 142, 156, 255), font=f_price)

    draw.line([(pad_left + plot_w, pad_top), (pad_left + plot_w, pad_top + plot_h)], fill=(42, 46, 57, 255), width=1)

    # 1. 1H POI Zone Top Boundary Line at $67,200
    htf_y = to_y(67200)
    draw_dashed_line(draw, pad_left, htf_y, pad_left + plot_w, htf_y, color=(8, 153, 129, 200), width=2, dash=8, gap=4)
    draw.text((pad_left + 10, htf_y + 6), "^ 1H DEMAND POI TOP BOUNDARY ($67,200)", fill=(38, 166, 154, 255), font=f_badge)

    # 2. 5M Last POI Box (Candle 9: $67,205 - $67,245)
    poi_top_p = 67245
    poi_bot_p = 67205
    poi_y1 = to_y(poi_top_p)
    poi_y2 = to_y(poi_bot_p)
    poi_x1 = to_x(9) - body_w // 2
    poi_x2 = pad_left + plot_w - 30

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # 5M POI Box
    ov_draw.rectangle([poi_x1, poi_y1, poi_x2, poi_y2], fill=(0, 240, 255, 40), outline=(0, 240, 255, 240), width=2)
    draw_dashed_line(ov_draw, poi_x1, (poi_y1 + poi_y2) // 2, poi_x2, (poi_y1 + poi_y2) // 2, color=(0, 240, 255, 140), width=1)

    # TradingView Long Position Shading from Candle 16 Entry to Right Axis
    entry_p = 67220
    entry_y = to_y(entry_p)
    tp_p = 67550 # Visual TP level
    tp_y = to_y(tp_p)
    sl_p = 67100 # Visual SL level
    sl_y = to_y(sl_p)
    entry_x = to_x(16)

    # Profit Zone (Green tint)
    ov_draw.rectangle([entry_x, tp_y, pad_left + plot_w, entry_y], fill=(8, 153, 129, 30), outline=None)
    # Risk Zone (Red tint)
    ov_draw.rectangle([entry_x, entry_y, pad_left + plot_w, sl_y], fill=(242, 54, 69, 30), outline=None)

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # 4. Draw Candlesticks FIRST so annotations sit cleanly on top
    for i, c in enumerate(candles):
        cx = to_x(i)
        is_green = c["c"] >= c["o"]
        c_color = (8, 153, 129, 255) if is_green else (242, 54, 69, 255)
        # Wick
        y_high = to_y(c["h"])
        y_low = to_y(c["l"])
        draw.line([(cx, y_high), (cx, y_low)], fill=c_color, width=2)
        # Body
        y_top = to_y(max(c["o"], c["c"]))
        y_bot = to_y(min(c["o"], c["c"]))
        if y_bot == y_top:
            y_bot += 1
        x1 = cx - body_w // 2
        x2 = cx + body_w // 2
        draw.rectangle([x1, y_top, x2, y_bot], fill=c_color)

    # 5M POI Label (Clean pill on right side)
    poi_lbl_x = to_x(12) + 20
    poi_lbl_y = poi_y1 + 8
    draw.rectangle([poi_lbl_x - 6, poi_lbl_y - 4, poi_lbl_x + 350, poi_lbl_y + 24], fill=(16, 24, 38, 240), outline=(0, 240, 255, 200), width=1)
    draw.text((poi_lbl_x, poi_lbl_y), "[5M LAST POI] ENTRY ZONE ($67,205 - $67,245)", fill=(0, 240, 255, 255), font=f_badge)

    # 3. MSS Breakout Level (Recent Lower High Candle 5 = $67,320)
    lh_p = 67320
    lh_y = to_y(lh_p)
    lh_x = to_x(5)
    mss_end_x = to_x(12) + 40
    draw_dashed_line(draw, lh_x, lh_y, mss_end_x, lh_y, color=(245, 158, 11, 255), width=2, dash=6, gap=4)

    # Circle on LH5
    draw.ellipse([lh_x - 8, lh_y - 8, lh_x + 8, lh_y + 8], outline=(245, 158, 11, 255), width=2)
    draw.text((lh_x - 30, lh_y - 24), "Recent LH ($67,320)", fill=(245, 158, 11, 255), font=f_desc)

    # MSS Break text (Clean callout pill above breakout)
    mss_lbl_x = to_x(6)
    mss_lbl_y = to_y(67490)
    draw.rectangle([mss_lbl_x - 10, mss_lbl_y - 4, mss_lbl_x + 440, mss_lbl_y + 26], fill=(24, 28, 42, 240), outline=(255, 215, 0, 220), width=1)
    draw.text((mss_lbl_x, mss_lbl_y), ">> MSS CONFIRMED! (Recent LH Broken by Wick or Body)", fill=(255, 215, 0, 255), font=f_label)

    # Annotate Lower Lows and Lower Highs structure
    draw.text((to_x(1) - 15, to_y(67470) - 20), "LH 1", fill=(132, 142, 156, 255), font=f_desc)
    draw.text((to_x(3) - 15, to_y(67250) + 10), "LL 1", fill=(132, 142, 156, 255), font=f_desc)
    draw.text((to_x(8) - 25, to_y(67180) + 12), "LL 2 (1H Tap)", fill=(255, 215, 0, 255), font=f_badge)

    # 5. HIGHLIGHT ENTRY AT CANDLE 16 RETEST TAP ($67,220)
    entry_cx = to_x(16)
    arrow_tip_y = entry_y + 8
    arrow_base_y = entry_y + 55
    draw.polygon([
        (entry_cx, arrow_tip_y),
        (entry_cx - 10, arrow_tip_y + 16),
        (entry_cx + 10, arrow_tip_y + 16)
    ], fill=(0, 255, 136, 255))
    draw.rectangle([entry_cx - 4, arrow_tip_y + 14, entry_cx + 4, arrow_base_y], fill=(0, 255, 136, 255))

    # Entry Box Annotation
    box_x = entry_cx - 200
    box_y = arrow_base_y + 10
    draw.rectangle([box_x, box_y, box_x + 400, box_y + 85], fill=(16, 24, 38, 250), outline=(0, 255, 136, 220), width=2)
    draw.text((box_x + 14, box_y + 10), ">> STEP 2: 5M POI RETEST ENTRY EXECUTED!", fill=(0, 255, 136, 255), font=f_label)
    draw.text((box_x + 14, box_y + 34), f"Limit Fill on 5M Last POI Retest Tap @ ${entry_p:,.0f}", fill=(255, 255, 255, 255), font=f_desc)
    draw.text((box_x + 14, box_y + 56), "STOP LOSS: -15.0% ROI  |  TAKE PROFIT: +15.0% ROI", fill=(56, 189, 248, 255), font=f_badge)

    # 6. Price Target Lines
    # Entry Line
    draw_dashed_line(draw, entry_cx, entry_y, pad_left + plot_w, entry_y, color=(56, 189, 248, 255), width=2, dash=8, gap=4)
    draw.rectangle([pad_left + plot_w + 2, entry_y - 10, pad_left + plot_w + 105, entry_y + 10], fill=(14, 165, 233, 240))
    draw.text((pad_left + plot_w + 6, entry_y - 7), f"ENTRY {entry_p:,.0f}", fill=(255, 255, 255, 255), font=f_price)

    # TP Line (+15.0% ROI)
    draw_dashed_line(draw, entry_cx, tp_y, pad_left + plot_w, tp_y, color=(8, 153, 129, 255), width=2, dash=8, gap=4)
    draw.rectangle([pad_left + plot_w + 2, tp_y - 10, pad_left + plot_w + 105, tp_y + 10], fill=(8, 153, 129, 240))
    draw.text((pad_left + plot_w + 6, tp_y - 7), "TP (+15% ROI)", fill=(255, 255, 255, 255), font=f_price)

    # SL Line (-15.0% ROI)
    draw_dashed_line(draw, entry_cx, sl_y, pad_left + plot_w, sl_y, color=(242, 54, 69, 255), width=2, dash=8, gap=4)
    draw.rectangle([pad_left + plot_w + 2, sl_y - 10, pad_left + plot_w + 105, sl_y + 10], fill=(242, 54, 69, 240))
    draw.text((pad_left + plot_w + 6, sl_y - 7), "SL (-15% ROI)", fill=(255, 255, 255, 255), font=f_price)

    # Top Header
    draw.rectangle([0, 0, width, 60], fill=(19, 23, 34, 255))
    draw.line([(0, 60), (width, 60)], fill=(42, 46, 57, 255), width=1)
    draw.text((pad_left, 16), "BTCUSDT.P  *  5M  *  BINANCE FUTURES", fill=(255, 255, 255, 255), font=f_title)
    draw.text((pad_left + 430, 20), "STAGE 2: 5M MARKET STRUCTURE SHIFT (MSS) & LAST POI RETEST ENTRY", fill=(0, 255, 136, 255), font=f_badge)

    draw.rectangle([width - 340, 14, width - pad_right + 10, 46], fill=(28, 32, 48, 255), outline=(0, 255, 136, 120), width=1)
    draw.text((width - 325, 20), "HERMES MSOB 2.0 * 5M SNIPER", fill=(0, 255, 136, 255), font=f_badge)

    # Footer
    draw.line([(pad_left, pad_top + plot_h), (pad_left + plot_w, pad_top + plot_h)], fill=(42, 46, 57, 255), width=1)
    draw.text((pad_left + 10, pad_top + plot_h + 12), "5M Micro Structure (Downtrend -> Recent LH Break (MSS) -> 5M Last POI Retest Tap -> ENTRY)", fill=(132, 142, 156, 255), font=f_price)

    out_path = os.path.join(ARTIFACT_DIR, "step2_5m_mss_retest_entry.png")
    img.save(out_path, format="PNG")
    print("Saved 5M Chart to:", out_path)
    return out_path

if __name__ == "__main__":
    build_1h_chart()
    build_5m_chart()
