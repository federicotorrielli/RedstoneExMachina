"""Render a title screen mockup from the built pack: preview.py <pack.zip> <re-OCD title dir> <out.png>."""

import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

pack, title, out = sys.argv[1:4]
z = zipfile.ZipFile(pack)
load = lambda name: Image.open(z.open(name)).convert('RGBA')
W, H = 1024, 640
c = Image.open(f'{title}/background/panorama_0.png').convert('RGBA').resize((W, H))
c.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 110)))
c.alpha_composite(Image.open(f'{title}/minecraft.png').convert('RGBA').resize((768, 192), Image.NEAREST), (128, 20))
c.alpha_composite(load('assets/minecraft/textures/gui/title/edition.png').resize((384, 48), Image.NEAREST), (320, 168))
font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 22)
d = ImageDraw.Draw(c)
sp = 'assets/minecraft/textures/gui/sprites/widget/'
rows = [('button', 'Singleplayer', 'white'), ('button_highlighted', 'Multiplayer (hover)', (255, 255, 160)),
        ('button_disabled', 'Realms (disabled)', (160, 160, 160))]
for i, (name, label, color) in enumerate(rows):
    y = 270 + i * 56
    c.alpha_composite(load(sp + name + '.png').resize((400, 40), Image.NEAREST), (312, y))
    d.text((512, y + 20), label, fill=color, font=font, anchor='mm')
d.text((W - 8, H - 8), 'RedstoneExMachina v0.1.1', fill=(255, 59, 59), font=font, anchor='rd')
zoom = load(sp + 'button_highlighted.png').resize((800, 80), Image.NEAREST)
c.alpha_composite(zoom, (112, 470))
zoom = load(sp + 'button.png').resize((800, 80), Image.NEAREST)
c.alpha_composite(zoom, (112, 555))
c.save(out)
