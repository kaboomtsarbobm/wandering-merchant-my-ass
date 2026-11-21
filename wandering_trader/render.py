import io
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
BACKGROUND = os.path.join(BASE, "assets", "background.png")
FONT = os.path.join(BASE, "assets", "DejaVuSans-Bold.ttf")
FONT_DIR = os.path.join(BASE, "assets")
PICTURE_BOX = (1120, 560, 2048, 1380)
ITEMS_BOX = (90, 420, 465, 1600)


def font_path(name):
    if name:
        path = os.path.join(FONT_DIR, os.path.basename(name))
        if os.path.isfile(path):
            try:
                ImageFont.truetype(path, 10)
                return path
            except OSError:
                pass
    return FONT


def parse_fill(value, default):
    value = (value or "").lstrip("#")
    if len(value) != 6:
        return default
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def fit_font(draw, text, max_width, start, minimum, path=FONT):
    size = start
    while size > minimum:
        font = ImageFont.truetype(path, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(path, minimum)


def cover(image, size):
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def contain(image, size):
    scale = min(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.alpha_composite(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return layer


def load_layer(data, size):
    if not data:
        return None
    try:
        return cover(Image.open(io.BytesIO(data)).convert("RGBA"), size)
    except OSError:
        return None


def render_trader(lines, picture, background=None, overlay=None, font="", size=0, colour=""):
    canvas = Image.open(BACKGROUND).convert("RGBA")
    custom = load_layer(background, canvas.size)
    if custom is not None:
        canvas = custom
    if picture:
        try:
            art = Image.open(io.BytesIO(picture)).convert("RGBA")
        except OSError:
            art = None
        if art is not None:
            box = (PICTURE_BOX[2] - PICTURE_BOX[0], PICTURE_BOX[3] - PICTURE_BOX[1])
            canvas.alpha_composite(contain(art, box), (PICTURE_BOX[0], PICTURE_BOX[1]))
    draw = ImageDraw.Draw(canvas)
    left, top, right, bottom = ITEMS_BOX
    slot = (bottom - top) // max(len(lines), 1)
    path = font_path(font)
    name_start = size or 64
    price_start = round(name_start * 52 / 64)
    name_size = min(
        fit_font(draw, name, right - left, name_start, min(28, name_start), path).size for name, _ in lines
    )
    price_size = min(
        fit_font(draw, price, right - left, price_start, min(24, price_start), path).size for _, price in lines
    )
    name_font = ImageFont.truetype(path, name_size)
    price_font = ImageFont.truetype(path, price_size)
    name_fill = parse_fill(colour, "black")
    price_fill = parse_fill(colour, (40, 40, 40))
    for index, (name, price) in enumerate(lines):
        y = top + index * slot
        draw.text((left, y), name, font=name_font, fill=name_fill)
        draw.text((left, y + name_font.size + 14), price, font=price_font, fill=price_fill)
    layer = load_layer(overlay, canvas.size)
    if layer is not None:
        canvas.alpha_composite(layer)
    canvas = canvas.resize((1024, 1024), Image.LANCZOS)
    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, "PNG")
    buffer.seek(0)
    return buffer
