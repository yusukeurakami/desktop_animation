from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/0000404949/Downloads/Liberty-pixel.png")
SOURCE_COPY = ROOT / "assets" / "source" / "Liberty-pixel.png"
GENERATED_RUN_SHEET = ROOT / "assets" / "source" / "run-generated-sheet.png"
OUT = ROOT / "assets" / "frames"
PET_HEIGHT = 190
PAD_LEFT = 50
PAD_RIGHT = 150
PAD_Y = 32


def remove_border_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    seen = set()
    queue: deque[tuple[int, int]] = deque()

    def is_background(x: int, y: int) -> bool:
        r, g, b, _ = pixels[x, y]
        return r >= 222 and g >= 214 and b >= 214

    for x in range(width):
        for y in (0, height - 1):
            if is_background(x, y):
                queue.append((x, y))
                seen.add((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if (x, y) not in seen and is_background(x, y):
                queue.append((x, y))
                seen.add((x, y))

    while queue:
        x, y = queue.popleft()
        pixels[x, y] = (255, 255, 255, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and is_background(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))

    bbox = rgba.getbbox()
    if bbox is None:
        raise RuntimeError("No pet pixels found after background removal.")
    rgba = rgba.crop(bbox)
    scale = PET_HEIGHT / rgba.height
    return rgba.resize((round(rgba.width * scale), PET_HEIGHT), Image.Resampling.NEAREST)


def canvas_for(image: Image.Image, pad_left: int = PAD_LEFT, pad_right: int = PAD_RIGHT, pad_y: int = PAD_Y) -> tuple[Image.Image, tuple[int, int]]:
    canvas = Image.new("RGBA", (image.width + pad_left + pad_right, image.height + pad_y * 2), (0, 0, 0, 0))
    return canvas, (pad_left, pad_y)


def paste_transformed(base: Image.Image, dx: int, dy: int, angle: float = 0) -> Image.Image:
    frame, origin = canvas_for(base)
    sprite = base.rotate(angle, resample=Image.Resampling.NEAREST, expand=True)
    x = origin[0] + dx - (sprite.width - base.width) // 2
    y = origin[1] + dy - (sprite.height - base.height) // 2
    frame.alpha_composite(sprite, (x, y))
    return frame


def shifted_patch(base: Image.Image, box: tuple[int, int, int, int], dx: int, dy: int) -> Image.Image:
    patch = Image.new("RGBA", base.size, (0, 0, 0, 0))
    part = base.crop(box)
    patch.alpha_composite(part, (box[0] + dx, box[1] + dy))
    return patch


def animated_run_base(base: Image.Image, step: int) -> Image.Image:
    run = base.copy()
    leg_regions = [
        (0, 130, 72, 172),
        (82, 120, 118, 178),
        (174, 150, 218, 190),
    ]
    for box in leg_regions:
        blank = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
        run.paste(blank, box)

    stride = [
        ((-10, 2), (8, -2), (12, 2)),
        ((-4, -3), (4, 1), (6, -4)),
        ((8, 1), (-8, 2), (-10, 1)),
        ((4, 4), (-4, -2), (-6, 4)),
        ((-10, 2), (8, -2), (12, 2)),
        ((-4, -3), (4, 1), (6, -4)),
        ((8, 1), (-8, 2), (-10, 1)),
        ((4, 4), (-4, -2), (-6, 4)),
    ][step % 8]
    for box, (dx, dy) in zip(leg_regions, stride):
        run = Image.alpha_composite(run, shifted_patch(base, box, dx, dy))
    return run


def is_chroma_green(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    return a == 0 or (
        g > 42
        and g > r + 18
        and g > b + 18
        and g > r * 1.12
        and g > b * 1.12
    )


def remove_green_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            if is_chroma_green(pixels[x, y]):
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def bbox_for_alpha(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getbbox()
    if bbox is None:
        raise RuntimeError("Generated run frame contains no visible pixels.")
    return bbox


def remove_tiny_components(image: Image.Image, min_pixels: int = 45) -> Image.Image:
    cleaned = image.copy()
    pix = cleaned.load()
    width, height = cleaned.size
    seen: set[tuple[int, int]] = set()
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pix[x, y][3] == 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                points.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and pix[nx, ny][3] != 0:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if len(points) < min_pixels:
                for px, py in points:
                    pix[px, py] = (0, 0, 0, 0)
    return cleaned


def generated_run_frames() -> list[Image.Image] | None:
    if not GENERATED_RUN_SHEET.exists():
        return None

    sheet = Image.open(GENERATED_RUN_SHEET).convert("RGBA")
    transparent = remove_green_background(sheet)
    pix = transparent.load()
    width, height = transparent.size
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pix[x, y][3] == 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            min_x = max_x = x
            min_y = max_y = y
            count = 0
            while queue:
                cx, cy = queue.popleft()
                count += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and pix[nx, ny][3] != 0:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if count > 1000:
                pad = 8
                components.append((count, max(0, min_x - pad), max(0, min_y - pad), min(width, max_x + pad + 1), min(height, max_y + pad + 1)))

    if len(components) != 8:
        raise RuntimeError(f"Expected 8 generated run poses, found {len(components)} in {GENERATED_RUN_SHEET}")

    sprites: list[Image.Image] = []
    max_h = 0
    for _, x1, y1, x2, y2 in sorted(components, key=lambda item: item[1]):
        crop = transparent.crop((x1, y1, x2, y2))
        crop = crop.crop(bbox_for_alpha(crop))
        crop = remove_tiny_components(crop)
        sprites.append(crop)
        max_h = max(max_h, crop.height)

    scale = PET_HEIGHT / max_h
    frames: list[Image.Image] = []
    target_w = PET_HEIGHT + 185
    target_h = PET_HEIGHT + PAD_Y * 2
    baseline = PAD_Y + PET_HEIGHT
    for idx, sprite in enumerate(sprites):
        resized = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)), Image.Resampling.NEAREST)
        frame = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        x = 38 + [0, 8, 14, 10, 0, -6, -12, -6][idx]
        y = baseline - resized.height + [2, -4, 0, 3, 2, -4, 0, 3][idx]
        frame.alpha_composite(resized, (x, y))
        frames.append(frame)
    return frames


def draw_heart(draw: ImageDraw.ImageDraw, x: int, y: int, color: str = "#ff5f9a", edge: str = "#8f2f55") -> None:
    pixels = [
        "01100110",
        "11111111",
        "11111111",
        "01111110",
        "00111100",
        "00011000",
    ]
    scale = 3
    for row, line in enumerate(pixels):
        for col, bit in enumerate(line):
            if bit == "1":
                draw.rectangle((x + col * scale, y + row * scale, x + col * scale + scale - 1, y + row * scale + scale - 1), fill=edge)
    for row, line in enumerate(pixels[1:5], start=1):
        for col, bit in enumerate(line):
            if bit == "1" and 1 <= col <= 6:
                draw.rectangle((x + col * scale, y + row * scale, x + col * scale + scale - 1, y + row * scale + scale - 1), fill=color)


def draw_sparkle(draw: ImageDraw.ImageDraw, x: int, y: int, color: str = "#ffe45c") -> None:
    draw.rectangle((x + 3, y, x + 5, y + 11), fill=color)
    draw.rectangle((x, y + 4, x + 11, y + 6), fill=color)
    draw.rectangle((x + 3, y + 4, x + 5, y + 6), fill="#fff6a2")


def draw_happy_effects(frame: Image.Image, progress: int, origin: tuple[int, int]) -> None:
    draw = ImageDraw.Draw(frame)
    head_x = origin[0] + 206
    head_y = origin[1] + 34
    bob = [0, -3, -5, -3, 0, -2, -4, -2][progress % 8]
    draw_heart(draw, head_x + 54, head_y - 22 + bob)
    if progress % 2 == 0:
        draw_sparkle(draw, head_x + 32, head_y - 16 + bob)
    else:
        draw_sparkle(draw, head_x + 74, head_y - 8 + bob, "#fff2a0")


def draw_meat(frame: Image.Image, progress: int) -> None:
    draw = ImageDraw.Draw(frame)
    meat_x = PAD_LEFT + PET_HEIGHT + 128 - min(progress, 4) * 5
    meat_y = frame.height // 2 + 18 + min(progress, 3) * 2
    edge = "#7a4a24"
    fat = "#fff4df"
    meat = "#f76861"
    dark_meat = "#df4f49"
    shine = "#ff9a92"
    clear = (0, 0, 0, 0)

    outline = [
        (14, 18, 18, 14), (18, 14, 34, 10), (34, 10, 56, 10), (56, 10, 76, 14),
        (76, 14, 94, 24), (94, 24, 106, 36), (106, 36, 108, 48), (108, 48, 102, 58),
        (102, 58, 88, 64), (88, 64, 52, 64), (52, 64, 20, 58), (20, 58, 10, 48),
        (10, 48, 8, 34), (8, 34, 14, 18),
    ]
    draw.polygon([(x1 + meat_x, y1 + meat_y) for x1, y1, *_ in outline], fill=edge)
    draw.rounded_rectangle((meat_x + 14, meat_y + 14, meat_x + 104, meat_y + 60), radius=14, fill=edge)
    draw.rounded_rectangle((meat_x + 18, meat_y + 18, meat_x + 100, meat_y + 56), radius=12, fill=fat)
    draw.rounded_rectangle((meat_x + 24, meat_y + 22, meat_x + 88, meat_y + 50), radius=10, fill=meat)
    draw.polygon(
        [
            (meat_x + 18, meat_y + 40),
            (meat_x + 32, meat_y + 56),
            (meat_x + 62, meat_y + 58),
            (meat_x + 100, meat_y + 48),
            (meat_x + 100, meat_y + 56),
            (meat_x + 18, meat_y + 56),
        ],
        fill=dark_meat,
    )
    draw.rectangle((meat_x + 18, meat_y + 25, meat_x + 25, meat_y + 52), fill=dark_meat)
    draw.rectangle((meat_x + 78, meat_y + 38, meat_x + 98, meat_y + 48), fill=fat)
    draw.rectangle((meat_x + 28, meat_y + 28, meat_x + 38, meat_y + 34), fill=shine)
    draw.rectangle((meat_x + 50, meat_y + 25, meat_x + 62, meat_y + 29), fill=shine)
    draw.rectangle((meat_x + 48, meat_y + 40, meat_x + 54, meat_y + 52), fill=shine)
    draw.rectangle((meat_x + 70, meat_y + 28, meat_x + 76, meat_y + 42), fill=shine)
    draw.line((meat_x + 14, meat_y + 47, meat_x + 102, meat_y + 54), fill=edge, width=3)

    if progress >= 4:
        draw.rectangle((meat_x + 92, meat_y + 22, meat_x + 106, meat_y + 42), fill=clear)
    if progress >= 6:
        draw.rectangle((meat_x + 82, meat_y + 20, meat_x + 106, meat_y + 52), fill=clear)


def draw_petting_hand(frame: Image.Image, progress: int, origin: tuple[int, int]) -> None:
    draw = ImageDraw.Draw(frame)
    hand_x = origin[0] + 192 + [0, 4, 8, 4, 0, -3, 0, 3][progress % 8]
    hand_y = origin[1] + 8 + [0, 5, 9, 5, 0, 4, 8, 4][progress % 8]
    edge = "#6a3f22"
    skin = "#ffd8b4"
    draw.rectangle((hand_x + 9, hand_y, hand_x + 17, hand_y + 34), fill=edge)
    draw.rectangle((hand_x + 12, hand_y + 3, hand_x + 20, hand_y + 31), fill=skin)
    for i in range(4):
        x = hand_x + i * 7
        draw.rectangle((x, hand_y + 20, x + 8, hand_y + 30), fill=edge)
        draw.rectangle((x + 1, hand_y + 20, x + 8, hand_y + 27), fill=skin)
    draw.line((hand_x - 8, hand_y + 40, hand_x + 8, hand_y + 34), fill="#ffe45c", width=3)
    draw.line((hand_x + 32, hand_y + 35, hand_x + 46, hand_y + 43), fill="#ffe45c", width=3)
    draw_heart(draw, origin[0] + 244, origin[1] + 20 + (progress % 3) * -2, "#ff6fa8")


def petting_frame(base: Image.Image, progress: int) -> Image.Image:
    body = base.copy()
    head_box = (132, 0, 275, 132)
    head = body.crop(head_box)
    body.paste(Image.new("RGBA", (head_box[2] - head_box[0], head_box[3] - head_box[1]), (0, 0, 0, 0)), head_box)
    head_dx = [0, 2, 4, 2, 0, -1, 1, 0][progress % 8]
    head_dy = [0, 3, 6, 3, 0, 2, 4, 1][progress % 8]
    body.alpha_composite(head, (head_box[0] + head_dx, head_box[1] + head_dy))

    frame, origin = canvas_for(body)
    frame.alpha_composite(body, origin)
    draw_petting_hand(frame, progress, origin)
    return frame


def save_frames(base: Image.Image, name: str, frames: list[Image.Image]) -> None:
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    for idx, frame in enumerate(frames):
        frame.save(folder / f"{name}_{idx:02d}.png")


def main() -> None:
    SOURCE_COPY.write_bytes(SOURCE.read_bytes())
    base = remove_border_background(Image.open(SOURCE))
    base.save(OUT / "liberty_base.png")

    idle_offsets = [0, 1, 2, 1, 0, -1, 0, 1]
    idle = [paste_transformed(base, 0, y) for y in idle_offsets]

    run = generated_run_frames()
    if run is None:
        run = []
        run_offsets = [(0, 0, -2), (8, -5, 1), (14, 0, 2), (8, 4, -1), (0, 0, -2), (-6, -4, 1), (-10, 0, 2), (-4, 4, -1)]
        for idx, (dx, dy, angle) in enumerate(run_offsets):
            stride_base = animated_run_base(base, idx)
            frame = paste_transformed(stride_base, dx, dy, angle)
            run.append(frame)

    eat = []
    eat_offsets = [(0, 0, 0), (2, 3, 1), (4, 6, 2), (5, 8, 2), (3, 6, 1), (1, 4, 0), (0, 2, -1), (0, 0, 0)]
    for idx, (dx, dy, angle) in enumerate(eat_offsets):
        frame = paste_transformed(base, dx, dy, angle)
        draw_meat(frame, idx)
        draw_happy_effects(frame, idx, (PAD_LEFT + dx, PAD_Y + dy))
        eat.append(frame)

    sleep = [paste_transformed(base, -1, 4), paste_transformed(base, 0, 5), paste_transformed(base, 1, 4), paste_transformed(base, 0, 3)]
    pet = [petting_frame(base, idx) for idx in range(8)]

    save_frames(base, "idle", idle)
    save_frames(base, "idle_left", [ImageOps.mirror(frame) for frame in idle])
    save_frames(base, "run", run)
    save_frames(base, "run_left", [ImageOps.mirror(frame) for frame in run])
    save_frames(base, "eat", eat)
    save_frames(base, "eat_left", [ImageOps.mirror(frame) for frame in eat])
    save_frames(base, "pet", pet)
    save_frames(base, "pet_left", [ImageOps.mirror(frame) for frame in pet])
    save_frames(base, "sleep", sleep)
    save_frames(base, "sleep_left", [ImageOps.mirror(frame) for frame in sleep])

    print(f"Generated frames under {OUT}")


if __name__ == "__main__":
    main()
