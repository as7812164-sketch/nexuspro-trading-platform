"""
HERMES AI • HIGH-DEFINITION TRADINGVIEW DARK CHART GENERATOR
===========================================================
1:1 TradingView Parity from User Image 2:
  - Pure OLED Dark Theme (#08080C)
  - Deep Candle History (95-120 candles showing entire OB Origin & First Tap)
  - Attached Green Demand Boxes & Red Supply Boxes with 50% MT Midline & Star Labels
  - Bright Green Arrow (⬆) pointing directly at the First Tap Entry candle (Red ⬇ for Short)
  - Color-coded price lines: Entry (Cyan), TP 1 & TP 2 (Green), Hard SL (Red)
  - Elegant Right Price Scale with Teal/Green Live Price Pill
  - Watermark: ⚡ Hermes SMC Engine v1.0
"""

import io
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
try:
    from config import get_ist_now
except Exception:
    from datetime import timezone, timedelta
    def get_ist_now() -> datetime:
        return datetime.now(timezone(timedelta(hours=5, minutes=30)))


def get_font(size: int = 12, bold: bool = False) -> ImageFont.ImageFont:
    """Helper to load standard fonts across Windows and Linux, fallback to default."""
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "arial.ttf"
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_htf_ob_chart(
    symbol: str,
    candles: List[Dict[str, Any]],
    zone: Dict[str, Any],
    zones: Optional[List[Dict[str, Any]]] = None,
    timeframe: str = "1h"
) -> bytes:
    """
    Renders an institutional 1:1 TradingView OLED Dark Theme chart for the Higher Timeframe (1H or 4H).
    Displays 95-120 candles of deep history so the origin swing of the Order Block
    and the First Tap are both fully visible in historical context.
    """
    width = 1100
    height = 680

    # 1. Canvas OLED Dark Background (#08080c)
    img = Image.new("RGBA", (width, height), (8, 9, 13, 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    f_title = get_font(18, bold=True)
    f_sub = get_font(12, bold=False)
    f_badge = get_font(11, bold=True)
    f_axis = get_font(11, bold=False)
    f_small = get_font(10, bold=False)
    f_watermark = get_font(13, bold=True)
    f_label = get_font(11, bold=True)

    # Layout Paddings
    pad_left = 25
    pad_right = 115
    pad_top = 75
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    # Deep history: display last 95 candles (or all available if < 95)
    display_candles = candles[-95:] if len(candles) > 95 else candles
    if not display_candles:
        draw.text((width // 2 - 80, height // 2), f"{symbol} No Market Data", fill=(100, 116, 139, 255), font=f_title)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    lows = [float(c["low"]) for c in display_candles]
    highs = [float(c["high"]) for c in display_candles]

    side = str(zone.get("side") or "BUY").upper()
    is_long = side in ("BUY", "LONG")

    entry_p = float(zone.get("entry_price") or display_candles[-1]["close"])
    tp_p = float(zone.get("tp_price") or zone.get("tp2_price") or (entry_p * 1.030 if is_long else entry_p * 0.970))
    sl_p = float(zone.get("hard_sl_price") or (entry_p * 0.970 if is_long else entry_p * 1.030))

    ob_top = float(zone.get("ob_top") or zone.get("ob_high") or (entry_p * 1.005))
    ob_bottom = float(zone.get("ob_bottom") or zone.get("ob_low") or (entry_p * 0.995))

    # Bounds
    all_prices = lows + highs + [entry_p, tp_p, sl_p, ob_top, ob_bottom]
    min_p = min(all_prices)
    max_p = max(all_prices)
    p_range = max_p - min_p
    if p_range <= 0:
        p_range = max_p * 0.05 or 1.0

    plot_min = min_p - (p_range * 0.08)
    plot_max = max_p + (p_range * 0.08)
    plot_range = plot_max - plot_min

    def to_y(p: float) -> int:
        ratio = (p - plot_min) / plot_range
        return int(pad_top + plot_h - (ratio * plot_h))

    def to_x(i: int) -> int:
        step = plot_w / len(display_candles)
        return int(pad_left + (i * step) + (step / 2))

    def format_px(p: float) -> str:
        if p >= 1000:
            return f"{p:,.1f}"
        elif p >= 10:
            return f"{p:.3f}"
        elif p >= 1:
            return f"{p:.4f}"
        else:
            return f"{p:.6f}"

    # 2. Draw Subtle TradingView Grid Lines
    grid_lines = 8
    for g in range(grid_lines + 1):
        gp = plot_min + (plot_range * (g / grid_lines))
        gy = to_y(gp)
        draw.line([(pad_left, gy), (pad_left + plot_w, gy)], fill=(255, 255, 255, 12), width=1)
        draw.text((pad_left + plot_w + 12, gy - 7), format_px(gp), fill=(132, 142, 156, 255), font=f_axis)

    # Right Axis separator border
    draw.line([(pad_left + plot_w, pad_top), (pad_left + plot_w, pad_top + plot_h)], fill=(30, 34, 45, 255), width=1)

    # 3. Semi-Transparent Order Block Boxes (Attached to origin candles)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    ob_origin_idx = 0
    for idx in range(len(display_candles) - 1, -1, -1):
        c = display_candles[idx]
        if is_long and float(c["low"]) <= ob_bottom * 1.002:
            ob_origin_idx = max(0, idx - 15)
            break
        elif not is_long and float(c["high"]) >= ob_top * 0.998:
            ob_origin_idx = max(0, idx - 15)
            break

    ob_x1 = to_x(ob_origin_idx)
    ob_x2 = pad_left + plot_w
    ob_y1 = to_y(ob_top)
    ob_y2 = to_y(ob_bottom)

    box_fill = (76, 175, 80, 48) if is_long else (244, 67, 54, 45)
    box_border = (76, 175, 80, 220) if is_long else (244, 67, 54, 220)

    ov_draw.rectangle(
        [ob_x1, min(ob_y1, ob_y2), ob_x2, max(ob_y1, ob_y2)],
        fill=box_fill, outline=box_border, width=1
    )

    # 50% Mean Threshold Dashed Midline
    ob_mid_y = int((ob_y1 + ob_y2) / 2)
    for dx in range(ob_x1, ob_x2, 8):
        ov_draw.line([(dx, ob_mid_y), (min(dx + 4, ob_x2), ob_mid_y)], fill=box_border, width=1)

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Order Block Tag
    ob_label = f"{timeframe.upper()} OB ▲ (Demand Floor)" if is_long else f"{timeframe.upper()} OB ▼ (Supply Ceiling)"
    ob_label_color = (76, 175, 80, 240) if is_long else (244, 67, 54, 240)
    draw.text((ob_x1 + 6, min(ob_y1, ob_y2) - 16), ob_label, fill=ob_label_color, font=f_label)

    # 4. Draw Candlesticks
    c_step = plot_w / len(display_candles)
    c_w = max(3, int(c_step * 0.68))
    green_body = (0, 192, 135, 255)
    red_body = (246, 70, 93, 255)

    for i, c in enumerate(display_candles):
        cx = to_x(i)
        y_open = to_y(float(c["open"]))
        y_close = to_y(float(c["close"]))
        y_high = to_y(float(c["high"]))
        y_low = to_y(float(c["low"]))

        is_bull = float(c["close"]) >= float(c["open"])
        c_color = green_body if is_bull else red_body

        draw.line([(cx, y_high), (cx, y_low)], fill=c_color, width=1)

        top_y = min(y_open, y_close)
        bot_y = max(y_open, y_close)
        if bot_y - top_y < 1:
            bot_y = top_y + 1

        x1 = cx - (c_w // 2)
        x2 = cx + (c_w // 2)
        draw.rectangle([x1, top_y, x2, bot_y], fill=c_color, outline=None)

    # 5. First Tap Indicator (Bright Arrow pointing at the tap candle)
    tap_idx = len(display_candles) - 1
    tap_cx = to_x(tap_idx)

    if is_long:
        tap_y = to_y(float(display_candles[tap_idx]["low"]))
        arrow_color = (0, 200, 83, 255)
        arrow_tip_y = tap_y + 12
        arrow_base_y = arrow_tip_y + 36

        # Upward Arrow
        draw.polygon([
            (tap_cx, arrow_tip_y),
            (tap_cx - 9, arrow_tip_y + 15),
            (tap_cx + 9, arrow_tip_y + 15)
        ], fill=arrow_color)
        draw.rectangle([tap_cx - 3, arrow_tip_y + 13, tap_cx + 3, arrow_base_y], fill=arrow_color)
        draw.text((tap_cx - 32, arrow_base_y + 4), "FIRST TAP", fill=arrow_color, font=f_badge)
        draw.text((tap_cx - 40, arrow_base_y + 17), f"{timeframe.upper()} POI TAP", fill=(255, 255, 255, 220), font=f_small)
    else:
        tap_y = to_y(float(display_candles[tap_idx]["high"]))
        arrow_color = (244, 67, 54, 255)
        arrow_tip_y = tap_y - 12
        arrow_base_y = arrow_tip_y - 36

        # Downward Arrow
        draw.polygon([
            (tap_cx, arrow_tip_y),
            (tap_cx - 9, arrow_tip_y - 15),
            (tap_cx + 9, arrow_tip_y - 15)
        ], fill=arrow_color)
        draw.rectangle([tap_cx - 3, arrow_base_y, tap_cx + 3, arrow_tip_y - 13], fill=arrow_color)
        draw.text((tap_cx - 32, arrow_base_y - 18), "FIRST TAP", fill=arrow_color, font=f_badge)
        draw.text((tap_cx - 40, arrow_base_y - 7), f"{timeframe.upper()} POI TAP", fill=(255, 255, 255, 220), font=f_small)

    # 6. Price Targets & Stop Loss Reference Overlays
    # Entry Line (Cyan dashed)
    ey = to_y(entry_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, ey), (min(dx + 4, pad_left + plot_w), ey)], fill=(56, 189, 248, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, ey - 9, pad_left + plot_w + 105, ey + 9], fill=(14, 165, 233, 240))
    draw.text((pad_left + plot_w + 6, ey - 6), f"ENTRY {format_px(entry_p)}", fill=(255, 255, 255, 255), font=f_small)

    # Take Profit Line (Green dashed: Direct +15% ROI)
    tp_y = to_y(tp_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, tp_y), (min(dx + 4, pad_left + plot_w), tp_y)], fill=(34, 197, 94, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, tp_y - 9, pad_left + plot_w + 105, tp_y + 9], fill=(22, 101, 52, 240))
    draw.text((pad_left + plot_w + 6, tp_y - 6), f"TP (+15% ROI) {format_px(tp_p)}", fill=(134, 239, 172, 255), font=f_small)

    # Hard SL Line (Red dashed)
    sl_y = to_y(sl_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, sl_y), (min(dx + 4, pad_left + plot_w), sl_y)], fill=(239, 68, 68, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, sl_y - 9, pad_left + plot_w + 105, sl_y + 9], fill=(153, 27, 27, 240))
    draw.text((pad_left + plot_w + 6, sl_y - 6), f"SL (-15.0% ROI)", fill=(254, 202, 202, 255), font=f_small)

    # Current Live Price Pill (Teal/Green box on right axis)
    last_p = float(display_candles[-1]["close"])
    last_y = to_y(last_p)
    draw.rectangle([pad_left + plot_w + 2, last_y - 11, pad_left + plot_w + 105, last_y + 11], fill=(0, 192, 135, 255))
    draw.text((pad_left + plot_w + 6, last_y - 7), format_px(last_p), fill=(0, 0, 0, 255), font=f_badge)

    # 7. Modern Institutional Header
    draw.rectangle([0, 0, width, 55], fill=(12, 14, 20, 255))
    draw.line([(0, 55), (width, 55)], fill=(30, 34, 45, 255), width=1)

    # Title & Pair
    lev = int(zone.get("leverage") or 5)
    clean_sym = symbol.replace("USDT", "")
    draw.text((pad_left, 12), f"{clean_sym} / TetherUS PERP  {timeframe.upper()}  BINANCE FUTURES", fill=(255, 255, 255, 255), font=f_title)
    draw.text((pad_left, 34), f"HTF Structure: {side} ({lev}x Isolated)  •  Last: {format_px(last_p)}  •  Order Block First Tap", fill=(0, 192, 135, 255) if is_long else (246, 70, 93, 255), font=f_sub)

    # Strategy Badge on right side of header
    draw.rectangle([width - 340, 14, width - pad_left, 42], fill=(18, 24, 38, 255), outline=(56, 189, 248, 180), width=1)
    draw.text((width - 325, 20), f"🏛️ STEP 1: {timeframe.upper()} HTF POI TAP", fill=(56, 189, 248, 255), font=f_badge)

    # 8. Bottom Timeline & Watermark
    draw.line([(pad_left, pad_top + plot_h), (pad_left + plot_w, pad_top + plot_h)], fill=(30, 34, 45, 255), width=1)
    ist_time_str = get_ist_now().strftime("%d %b %Y • %I:%M %p IST")
    draw.text((pad_left + 10, pad_top + plot_h + 10), f"Binance Futures Live Feed • {ist_time_str}", fill=(100, 116, 139, 255), font=f_axis)

    # Watermark (Bottom Right)
    draw.text((pad_left + plot_w - 270, pad_top + plot_h - 26), "🏛️ Step 1 • Macro OB Tap", fill=(56, 189, 248, 180), font=f_watermark)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    return buf.getvalue()


def render_ltf_entry_chart(
    symbol: str,
    candles: List[Dict[str, Any]],
    zone: Dict[str, Any],
    confirm: Dict[str, Any],
    timeframe: str = "5m"
) -> bytes:
    """
    Renders an institutional 1:1 TradingView OLED Dark Theme chart for the Lower Timeframe (5m or 15m).
    Highlights:
      - MSS Break Level (Gold dashed line where Recent LH/HL broke)
      - Latest 5m/15m POI (Base candle of impulsive breakout)
      - Retest Tap Entry Point with bright arrow
      - Dynamic Stop Loss (-15.0% ROI) and Take Profit (+15.0% ROI)
    """
    width = 1100
    height = 680

    img = Image.new("RGBA", (width, height), (8, 9, 13, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(18, bold=True)
    f_sub = get_font(12, bold=False)
    f_badge = get_font(11, bold=True)
    f_axis = get_font(11, bold=False)
    f_small = get_font(10, bold=False)
    f_watermark = get_font(13, bold=True)
    f_label = get_font(11, bold=True)

    pad_left = 25
    pad_right = 115
    pad_top = 75
    pad_bottom = 45
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom

    display_candles = candles[-60:] if len(candles) > 60 else candles
    if not display_candles:
        return b""

    lows = [float(c["low"]) for c in display_candles]
    highs = [float(c["high"]) for c in display_candles]

    side = str(zone.get("side") or "BUY").upper()
    is_long = side in ("BUY", "LONG")

    entry_p = float(zone.get("entry_price") or display_candles[-1]["close"])
    tp_p = float(zone.get("tp_price") or (entry_p * 1.030 if is_long else entry_p * 0.970))
    sl_p = float(zone.get("hard_sl_price") or (entry_p * 0.970 if is_long else entry_p * 1.030))

    mss_level = float(confirm.get("mss_level") or (entry_p * 1.003 if is_long else entry_p * 0.997))
    poi_top = float(confirm.get("poi_top") or (entry_p * 1.0015 if is_long else entry_p * 1.003))
    poi_bot = float(confirm.get("poi_bot") or (entry_p * 0.9985 if is_long else entry_p * 0.997))

    all_prices = lows + highs + [entry_p, tp_p, sl_p, mss_level, poi_top, poi_bot]
    min_p = min(all_prices)
    max_p = max(all_prices)
    p_range = max_p - min_p
    if p_range <= 0:
        p_range = max_p * 0.05 or 1.0

    plot_min = min_p - (p_range * 0.08)
    plot_max = max_p + (p_range * 0.08)
    plot_range = plot_max - plot_min

    def to_y(p: float) -> int:
        ratio = (p - plot_min) / plot_range
        return int(pad_top + plot_h - (ratio * plot_h))

    def to_x(i: int) -> int:
        step = plot_w / len(display_candles)
        return int(pad_left + (i * step) + (step / 2))

    def format_px(p: float) -> str:
        if p >= 1000:
            return f"{p:,.1f}"
        elif p >= 10:
            return f"{p:.3f}"
        elif p >= 1:
            return f"{p:.4f}"
        else:
            return f"{p:.6f}"

    # Grid Lines
    grid_lines = 8
    for g in range(grid_lines + 1):
        gp = plot_min + (plot_range * (g / grid_lines))
        gy = to_y(gp)
        draw.line([(pad_left, gy), (pad_left + plot_w, gy)], fill=(255, 255, 255, 12), width=1)
        draw.text((pad_left + plot_w + 12, gy - 7), format_px(gp), fill=(132, 142, 156, 255), font=f_axis)

    draw.line([(pad_left + plot_w, pad_top), (pad_left + plot_w, pad_top + plot_h)], fill=(30, 34, 45, 255), width=1)

    # Latest 5m/15m POI Box
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    poi_origin_idx = max(0, len(display_candles) - 18)
    poi_x1 = to_x(poi_origin_idx)
    poi_x2 = pad_left + plot_w
    poi_y1 = to_y(poi_top)
    poi_y2 = to_y(poi_bot)

    box_fill = (0, 223, 192, 45) if is_long else (244, 67, 54, 45)
    box_border = (0, 223, 192, 220) if is_long else (244, 67, 54, 220)

    ov_draw.rectangle([poi_x1, min(poi_y1, poi_y2), poi_x2, max(poi_y1, poi_y2)], fill=box_fill, outline=box_border, width=1)

    poi_mid_y = int((poi_y1 + poi_y2) / 2)
    for dx in range(poi_x1, poi_x2, 8):
        ov_draw.line([(dx, poi_mid_y), (min(dx + 4, poi_x2), poi_mid_y)], fill=box_border, width=1)

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    poi_label = f"{timeframe.upper()} LAST POI (Base of Breakout)" if is_long else f"{timeframe.upper()} LAST POI (Base of Breakdown)"
    draw.text((poi_x1 + 6, min(poi_y1, poi_y2) - 16), poi_label, fill=(0, 223, 192, 240) if is_long else (244, 67, 54, 240), font=f_label)

    # MSS Breakout Line (Gold/Yellow dashed line across chart)
    mss_y = to_y(mss_level)
    for dx in range(pad_left, pad_left + plot_w, 8):
        draw.line([(dx, mss_y), (min(dx + 4, pad_left + plot_w), mss_y)], fill=(250, 204, 21, 220), width=1)
    draw.rectangle([pad_left + 15, mss_y - 10, pad_left + 240, mss_y + 10], fill=(30, 26, 10, 240), outline=(250, 204, 21, 240), width=1)
    draw.text((pad_left + 22, mss_y - 6), f"⚡ MSS BREAK LEVEL: {format_px(mss_level)}", fill=(250, 204, 21, 255), font=f_badge)

    # Candlesticks
    c_step = plot_w / len(display_candles)
    c_w = max(4, int(c_step * 0.68))
    green_body = (0, 192, 135, 255)
    red_body = (246, 70, 93, 255)

    for i, c in enumerate(display_candles):
        cx = to_x(i)
        y_open = to_y(float(c["open"]))
        y_close = to_y(float(c["close"]))
        y_high = to_y(float(c["high"]))
        y_low = to_y(float(c["low"]))

        is_bull = float(c["close"]) >= float(c["open"])
        c_color = green_body if is_bull else red_body

        draw.line([(cx, y_high), (cx, y_low)], fill=c_color, width=1)

        top_y = min(y_open, y_close)
        bot_y = max(y_open, y_close)
        if bot_y - top_y < 1:
            bot_y = top_y + 1

        x1 = cx - (c_w // 2)
        x2 = cx + (c_w // 2)
        draw.rectangle([x1, top_y, x2, bot_y], fill=c_color, outline=None)

    # Retest Entry Arrow on latest candle
    tap_idx = len(display_candles) - 1
    tap_cx = to_x(tap_idx)
    if is_long:
        tap_y = to_y(float(display_candles[tap_idx]["low"]))
        arrow_color = (0, 223, 192, 255)
        arrow_tip_y = tap_y + 10
        arrow_base_y = arrow_tip_y + 36
        draw.polygon([(tap_cx, arrow_tip_y), (tap_cx - 9, arrow_tip_y + 15), (tap_cx + 9, arrow_tip_y + 15)], fill=arrow_color)
        draw.rectangle([tap_cx - 3, arrow_tip_y + 13, tap_cx + 3, arrow_base_y], fill=arrow_color)
        draw.text((tap_cx - 48, arrow_base_y + 4), "🟢 ENTRY EXECUTED", fill=arrow_color, font=f_badge)
        draw.text((tap_cx - 40, arrow_base_y + 17), "MSS SNIPER RETEST", fill=(255, 255, 255, 220), font=f_small)
    else:
        tap_y = to_y(float(display_candles[tap_idx]["high"]))
        arrow_color = (244, 67, 54, 255)
        arrow_tip_y = tap_y - 10
        arrow_base_y = arrow_tip_y - 36
        draw.polygon([(tap_cx, arrow_tip_y), (tap_cx - 9, arrow_tip_y - 15), (tap_cx + 9, arrow_tip_y - 15)], fill=arrow_color)
        draw.rectangle([tap_cx - 3, arrow_base_y, tap_cx + 3, arrow_tip_y - 13], fill=arrow_color)
        draw.text((tap_cx - 48, arrow_base_y - 18), "🔴 ENTRY EXECUTED", fill=arrow_color, font=f_badge)
        draw.text((tap_cx - 40, arrow_base_y - 7), "MSS SNIPER RETEST", fill=(255, 255, 255, 220), font=f_small)

    # Target & SL Lines
    ey = to_y(entry_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, ey), (min(dx + 4, pad_left + plot_w), ey)], fill=(56, 189, 248, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, ey - 9, pad_left + plot_w + 105, ey + 9], fill=(14, 165, 233, 240))
    draw.text((pad_left + plot_w + 6, ey - 6), f"ENTRY {format_px(entry_p)}", fill=(255, 255, 255, 255), font=f_small)

    tp_y = to_y(tp_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, tp_y), (min(dx + 4, pad_left + plot_w), tp_y)], fill=(34, 197, 94, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, tp_y - 9, pad_left + plot_w + 105, tp_y + 9], fill=(22, 101, 52, 240))
    draw.text((pad_left + plot_w + 6, tp_y - 6), f"TP (+15% ROI) {format_px(tp_p)}", fill=(134, 239, 172, 255), font=f_small)

    sl_y = to_y(sl_p)
    for dx in range(to_x(max(0, len(display_candles) - 25)), pad_left + plot_w, 8):
        draw.line([(dx, sl_y), (min(dx + 4, pad_left + plot_w), sl_y)], fill=(239, 68, 68, 200), width=1)
    draw.rectangle([pad_left + plot_w + 2, sl_y - 9, pad_left + plot_w + 105, sl_y + 9], fill=(153, 27, 27, 240))
    draw.text((pad_left + plot_w + 6, sl_y - 6), f"SL (-15.0% ROI)", fill=(254, 202, 202, 255), font=f_small)

    last_p = float(display_candles[-1]["close"])
    last_y = to_y(last_p)
    draw.rectangle([pad_left + plot_w + 2, last_y - 11, pad_left + plot_w + 105, last_y + 11], fill=(0, 192, 135, 255))
    draw.text((pad_left + plot_w + 6, last_y - 7), format_px(last_p), fill=(0, 0, 0, 255), font=f_badge)

    # Header
    draw.rectangle([0, 0, width, 55], fill=(12, 14, 20, 255))
    draw.line([(0, 55), (width, 55)], fill=(30, 34, 45, 255), width=1)
    lev = int(zone.get("leverage") or 5)
    clean_sym = symbol.replace("USDT", "")
    draw.text((pad_left, 12), f"{clean_sym} / TetherUS PERP  {timeframe.upper()}  BINANCE FUTURES", fill=(255, 255, 255, 255), font=f_title)
    draw.text((pad_left, 34), f"Execution: {side} ({lev}x Isolated)  •  Last: {format_px(last_p)}  •  MSS Sniper", fill=(0, 192, 135, 255) if is_long else (246, 70, 93, 255), font=f_sub)

    # Right Strategy Badge
    draw.rectangle([width - 380, 14, width - pad_left, 42], fill=(24, 30, 20, 255), outline=(0, 223, 192, 180), width=1)
    draw.text((width - 368, 20), f"🎯 STEP 2: {timeframe.upper()} MSS & LAST POI RETEST", fill=(0, 223, 192, 255), font=f_badge)

    # Bottom
    draw.line([(pad_left, pad_top + plot_h), (pad_left + plot_w, pad_top + plot_h)], fill=(30, 34, 45, 255), width=1)
    ist_time_str = get_ist_now().strftime("%d %b %Y • %I:%M %p IST")
    draw.text((pad_left + 10, pad_top + plot_h + 10), f"Binance Futures Live Feed • {ist_time_str}", fill=(100, 116, 139, 255), font=f_axis)
    draw.text((pad_left + plot_w - 290, pad_top + plot_h - 26), "🎯 Step 2 • LTF MSS Sniper Entry", fill=(0, 223, 192, 180), font=f_watermark)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    return buf.getvalue()


def render_smc_chart_image(
    symbol: str,
    candles: List[Dict[str, Any]],
    zone: Dict[str, Any],
    zones: Optional[List[Dict[str, Any]]] = None,
    timeframe: str = "4h"
) -> bytes:
    """Backward compatibility wrapper calling render_htf_ob_chart."""
    return render_htf_ob_chart(symbol, candles, zone, zones=zones, timeframe=timeframe)
