"""Build the RedstoneExMachina UI resource pack (title subtitle and redstone buttons)."""

import json
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance

PACK_FORMAT = 88
# usage: make_ui_pack.py <out.zip> <block textures dir with redstone_block.png>
OUT, BLOCKS = Path(sys.argv[1]), Path(sys.argv[2])

# 5x7 glyphs, '#' = filled
FONT = {
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    'X': ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
    'M': ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'C': ['.####', '#....', '#....', '#....', '#....', '#....', '.####'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'I': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'],
    ' ': ['...'] * 7,
}

OUTLINE = (0, 0, 0, 255)


def dust(power):
    """Vanilla redstone dust tint for a power level (RedStoneWireBlock)."""
    f = power / 15
    r = f * 0.6 + (0.4 if f > 0 else 0.3)
    g = max(0.0, min(1.0, f * f * 0.7 - 0.5))
    b = max(0.0, min(1.0, f * f * 0.6 - 0.7))
    return tuple(int(c * 255) for c in (r, g, b)) + (255,)


RED, RED_DARK = dust(15), dust(4)


def subtitle(text='REDSTONE EX MACHINA', size=(512, 64), sx=4, sy=6, bold=2, depth=6, outline=3):
    """Bold blocky subtitle with an extruded side, drawn in the vanilla edition slot."""
    mask = Image.new('L', size)
    width = sum(len(FONT[c][0]) + 1 for c in text) - 1
    x = (size[0] - width * sx - bold) // 2
    y0 = outline
    draw = ImageDraw.Draw(mask)
    for c in text:
        for row, line in enumerate(FONT[c]):
            for col, px in enumerate(line):
                if px == '#':
                    draw.rectangle([x + col * sx, y0 + row * sy,
                                    x + (col + 1) * sx - 1 + bold, y0 + (row + 1) * sy - 1], fill=255)
        x += (len(FONT[c][0]) + 1) * sx

    def grow(src, offsets):
        out = Image.new('L', size)
        for d in offsets:
            out.paste(255, d, src)
        return out

    side = grow(mask, [(d, d) for d in range(depth + 1)])
    ring = grow(side, [(dx, dy) for dx in range(-outline, outline + 1) for dy in range(-outline, outline + 1)])
    img = Image.new('RGBA', size)
    img.paste(OUTLINE, (0, 0), ring)
    img.paste(RED_DARK, (0, 0), side)
    img.paste(RED, (0, 0), mask)
    shifted = Image.new('L', size)
    shifted.paste(mask, (0, 2))
    img.paste((255, 140, 110, 255), (0, 0), ImageChops.subtract(mask, shifted))
    return img


def button(brightness, saturation=1.0, block='redstone_block'):
    """200x20 nine-slice button tiled from a block texture, with a black outline."""
    tex = Image.open(BLOCKS / f'{block}.png').convert('RGBA')
    tex = ImageEnhance.Color(ImageEnhance.Brightness(tex).enhance(brightness)).enhance(saturation)
    w, h = 200, 20
    img = Image.new('RGBA', (w, h))
    for x in range(0, w, 16):
        for y in range(-2, h, 16):
            img.paste(tex, (x, y))
    ImageDraw.Draw(img).rectangle([0, 0, w - 1, h - 1], outline=OUTLINE)
    return img


WELCOME = ('§cWelcome to §lRedstoneExMachina§r§c!§r\n'
           '§e⚡§r Every hotkey: pause menu → §cPress here for hotkeys§r\n'
           '§f🪟§r MiniHUD, Litematica, Tweakeroo, Redstone Multimeter - ready to use\n'
           '§e✨§r Photon shaders - press §7K§r to toggle\n'
           '§8Built on Fabulously Optimized§r')


def png(img):
    buf = BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def main():
    sprites = 'assets/minecraft/textures/gui/sprites/widget/'
    nine = json.dumps({'gui': {'scaling': {'type': 'nine_slice', 'width': 200, 'height': 20,
                                           'border': {'left': 20, 'top': 4, 'right': 20, 'bottom': 4}}}}, indent=2)
    files = {
        'pack.mcmeta': json.dumps({'pack': {'description': '§cRedstoneExMachina§7 interface',
                                            'min_format': PACK_FORMAT, 'max_format': PACK_FORMAT}}, indent=2),
        'assets/minecraft/textures/gui/title/edition.png': png(subtitle()),
        # replaces Fabulously Optimized's first-launch welcome text (higher pack priority wins)
        'assets/redstoneexmachina/lang/en_us.json': json.dumps({'accessibility.onboarding.screen.title': WELCOME},
                                                               ensure_ascii=False, indent=2),
        sprites + 'button.png': png(button(0.45)),
        sprites + 'button_highlighted.png': png(button(0.75)),
        sprites + 'button_disabled.png': png(button(0.4, saturation=0.15)),
    }
    for name in ('button', 'button_highlighted', 'button_disabled'):
        files[sprites + name + '.png.mcmeta'] = nine
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    print(OUT)


if __name__ == '__main__':
    main()
