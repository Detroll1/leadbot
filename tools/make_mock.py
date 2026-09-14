"""Генератор макета диалога бота — docs/demo-mock.png.

Нужен, чтобы показать клиенту интерфейс до того, как подставлен настоящий
токен: картинка рисуется программно (Pillow) и честно подписана «МАКЕТ».
Реальный бот ведёт себя так же, но с эмодзи в кнопках (на макете опущены).

Запуск из корня проекта:  python tools/make_mock.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo-mock.png"

WIDTH = 780
MAX_BUBBLE_W = 560
PAD_X = 20
GAP = 14
BUBBLE_PAD = 16
BUBBLE_R = 16
FONT_SIZE = 23
LINE_H = 32

BG = (233, 237, 242)
HEADER_BG = (52, 144, 235)
HEADER_TEXT = (255, 255, 255)
IN_BUBBLE = (255, 255, 255)
OUT_BUBBLE = (228, 255, 211)
TEXT = (28, 30, 33)
SUBTLE = (138, 148, 158)
KB_TEXT = (47, 124, 196)
WATERMARK = (120, 130, 142, 60)

REGULAR = ("segoeui.ttf", "arial.ttf")
BOLD = ("segoeuib.ttf", "arialbd.ttf")


def _font(candidates, size):
    for name in candidates:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT = _font(REGULAR, FONT_SIZE)
FONT_SMALL = _font(REGULAR, FONT_SIZE - 5)
FONT_BOLD = _font(BOLD, FONT_SIZE)
FONT_TITLE = _font(BOLD, 26)
FONT_MARK = _font(BOLD, 64)

# (сторона, текст, кнопки построчно); сторона: "in" — бот, "out" — клиент
DIALOG = [
    ("in", "Здравствуйте!\nЭто демо-бот приёма заявок: подходит салонам красоты, "
           "автосервисам, клинингу и другим сферам малого бизнеса.\n\n"
           "Нажмите «Оставить заявку» — задам 4 коротких вопроса и передам "
           "заявку администратору.", None),
    ("out", "Оставить заявку", None),
    ("in", "Шаг 1 из 4 — выберите услугу:",
     [["Стрижка и укладка", "Окрашивание"],
      ["Маникюр и педикюр", "Косметология"],
      ["Массаж", "Другое / консультация"],
      ["Отмена"]]),
    ("out", "Стрижка и укладка", None),
    ("in", "Шаг 2 из 4 — как вас зовут?", None),
    ("out", "Анна", None),
    ("in", "Шаг 3 из 4 — оставьте телефон для связи: кнопкой ниже или сообщением.",
     [["Отправить мой номер"], ["Отмена"]]),
    ("out", "+7 (999) 123-45-67", None),
    ("in", "Шаг 4 из 4 — когда вам удобно? Например: «завтра после 18:00».", None),
    ("out", "завтра после 18:00", None),
    ("in", "Проверьте заявку:\n\nУслуга: Стрижка и укладка\nИмя: Анна\n"
           "Телефон: +7 (999) 123-45-67\nВремя: завтра после 18:00\n\n"
           "Всё верно — жмите «Отправить заявку».",
     [["Отправить заявку"], ["Заполнить заново"], ["Отмена"]]),
    ("out", "Отправить заявку", None),
    ("in", "Заявка №1 принята! Администратор свяжется с вами по указанному "
           "телефону.", None),
]

HEADER_H = 92
DATE_H = 46
FOOTER_H = 54
KB_BTN_H = 50
KB_GAP = 10


def _wrap(text, font, max_w, draw):
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_w or not line:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def _bubble_geometry(draw, side, text):
    inner_max = MAX_BUBBLE_W - BUBBLE_PAD * 2
    lines = _wrap(text, FONT, inner_max, draw)
    text_w = max(draw.textlength(line, font=FONT) for line in lines)
    bubble_w = min(MAX_BUBBLE_W, int(text_w) + BUBBLE_PAD * 2)
    bubble_h = len(lines) * LINE_H + BUBBLE_PAD * 2 - 6
    return lines, bubble_w, bubble_h


def _kb_height(rows):
    return len(rows) * (KB_BTN_H + KB_GAP) if rows else 0


def _draw_kb(draw, rows, top):
    left = PAD_X + 44
    kb_w = WIDTH - left - PAD_X
    y = top
    for row in rows:
        cols = len(row)
        btn_w = (kb_w - KB_GAP * (cols - 1)) // cols
        x = left
        for label in row:
            draw.rounded_rectangle(
                [x, y, x + btn_w, y + KB_BTN_H],
                radius=12,
                fill=(255, 255, 255),
                outline=(210, 218, 226),
                width=1,
            )
            tw = draw.textlength(label, font=FONT_SMALL)
            draw.text(
                (x + (btn_w - tw) / 2, y + (KB_BTN_H - FONT_SIZE + 8) / 2),
                label,
                font=FONT_SMALL,
                fill=KB_TEXT,
            )
            x += btn_w + KB_GAP
        y += KB_BTN_H + KB_GAP


def _draw_watermarks(image):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mark = Image.new("RGBA", (int(WIDTH * 1.6), 140), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(mark)
    mdraw.text((10, 20), "МАКЕТ", font=FONT_MARK, fill=WATERMARK)
    mark = mark.rotate(28, expand=True)
    for x, y in ((-60, 380), (280, 980), (-40, 1700)):
        overlay.alpha_composite(mark, (x, y))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def main():
    # Первый проход: считаем высоту.
    probe = Image.new("RGB", (WIDTH, 10))
    pdraw = ImageDraw.Draw(probe)
    blocks = []
    total = HEADER_H + DATE_H + GAP
    for side, text, kb_rows in DIALOG:
        lines, bubble_w, bubble_h = _bubble_geometry(pdraw, side, text)
        kb_h = _kb_height(kb_rows)
        block_h = bubble_h + (kb_h + 12 if kb_rows else 0)
        blocks.append((side, lines, bubble_w, bubble_h, kb_rows, block_h))
        total += block_h + GAP
    total += FOOTER_H

    image = Image.new("RGB", (WIDTH, total), BG)
    draw = ImageDraw.Draw(image)

    # Шапка чата.
    draw.rectangle([0, 0, WIDTH, HEADER_H], fill=HEADER_BG)
    draw.text((PAD_X, 24), "‹", font=_font(BOLD, 40), fill=HEADER_TEXT)
    draw.text((74, 16), "LeadBot — приём заявок", font=FONT_TITLE, fill=HEADER_TEXT)
    draw.text((76, 52), "бот", font=FONT_SMALL, fill=(219, 234, 252))

    y = HEADER_H + 12
    # Плашка даты.
    label = "Сегодня"
    lw = draw.textlength(label, font=FONT_SMALL)
    draw.rounded_rectangle(
        [(WIDTH - lw - 36) / 2, y + 6, (WIDTH + lw + 36) / 2, y + 38],
        radius=16,
        fill=(215, 222, 231),
    )
    draw.text(((WIDTH - lw) / 2, y + 12), label, font=FONT_SMALL, fill=SUBTLE)
    y += DATE_H

    # Второй проход: рисуем.
    for side, lines, bubble_w, bubble_h, kb_rows, block_h in blocks:
        if side == "in":
            x0 = PAD_X
        else:
            x0 = WIDTH - PAD_X - bubble_w
        draw.rounded_rectangle(
            [x0, y, x0 + bubble_w, y + bubble_h],
            radius=BUBBLE_R,
            fill=OUT_BUBBLE if side == "out" else IN_BUBBLE,
        )
        ty = y + BUBBLE_PAD - 4
        for line in lines:
            draw.text((x0 + BUBBLE_PAD, ty), line, font=FONT, fill=TEXT)
            ty += LINE_H
        y += bubble_h
        if kb_rows:
            _draw_kb(draw, kb_rows, y + 12)
            y += _kb_height(kb_rows) + 12
        y += GAP

    # Подвал-пояснение.
    draw.rectangle([0, total - FOOTER_H, WIDTH, total], fill=(250, 251, 252))
    note = "МАКЕТ интерфейса — сгенерирован скриптом tools/make_mock.py"
    nw = draw.textlength(note, font=FONT_SMALL)
    draw.text(((WIDTH - nw) / 2, total - FOOTER_H + 14), note, font=FONT_SMALL, fill=SUBTLE)

    image = _draw_watermarks(image)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG")
    print(f"Готово: {OUT} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
