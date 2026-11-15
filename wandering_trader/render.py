import io
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND = os.path.join(BASE, "assets", "background.png")
FONT = os.path.join(BASE, "assets", "DejaVuSans-Bold.ttf")
PICTURE_BOX = (1120, 560, 2048, 1380)
ITEMS_BOX = (90, 420, 465, 1600)


def fit_font(draw, text, max_width, start, minimum):
    size = start
    while size > minimum:
        font = ImageFont.truetype(FONT, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(FONT, minimum)


def cover(image, size):
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def render_trader(lines, picture):
    canvas = Image.open(BACKGROUND).convert("RGBA")
    if picture:
        try:
            art = Image.open(io.BytesIO(picture)).convert("RGBA")
        except OSError:
            art = None
        if art is not None:
            size = (PICTURE_BOX[2] - PICTURE_BOX[0], PICTURE_BOX[3] - PICTURE_BOX[1])
            canvas.alpha_composite(cover(art, size), (PICTURE_BOX[0], PICTURE_BOX[1]))
    draw = ImageDraw.Draw(canvas)
    left, top, right, bottom = ITEMS_BOX
    slot = (bottom - top) // max(len(lines), 1)
    name_size = min(fit_font(draw, name, right - left, 64, 28).size for name, _ in lines)
    price_size = min(fit_font(draw, price, right - left, 52, 24).size for _, price in lines)
    name_font = ImageFont.truetype(FONT, name_size)
    price_font = ImageFont.truetype(FONT, price_size)
    for index, (name, price) in enumerate(lines):
        y = top + index * slot
        draw.text((left, y), name, font=name_font, fill="black")
        draw.text((left, y + name_font.size + 14), price, font=price_font, fill=(40, 40, 40))
    canvas = canvas.resize((1024, 1024), Image.LANCZOS)
    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, "PNG")
    buffer.seek(0)
    return buffer
