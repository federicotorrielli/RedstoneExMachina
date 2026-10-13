"""Hotkey cheat sheet: one data table, rendered as an in-game dialog and as HTML.
Also writes the pack VERSION into the title screen credit and Prism's ExportVersion.

usage: hotkeys.py <html out> <isxander-main-menu-credits.json | instance.cfg>...
"""

import html
import json
import re
import sys

VERSION = '0.1.4'
RED = '#FF3333'

# (title, [(keys, description, row icon)]). In keys, '+' joins keys pressed together
# (hold the first, press the next) and ' / ' separates alternatives. A leading '~' marks plain text.
SECTIONS = [
    ('Circuit timing', [
        ('F6', 'Add or remove a multimeter meter on the targeted block', 'minecraft:target'),
        ('F7', 'Show or hide the multimeter timeline', 'minecraft:clock'),
        ('F8', 'Multimeter screen', 'minecraft:repeater'),
        ('F10', 'Multimeter settings', 'minecraft:comparator'),
        (', / .', 'Step the multimeter timeline back / forward', 'minecraft:redstone_torch'),
        ('Left Alt+Scroll', 'Scroll the multimeter timeline', 'minecraft:compass'),
        ('G', 'G4mespeed: change the tick rate', 'minecraft:daylight_detector'),
        ('F12', 'Chunk Debug map (loaded and ticking chunks)', 'minecraft:filled_map'),
        ('~Empty hand click on a piston', 'Pistorder: show block movement order', 'minecraft:piston'),
        ('Delete', 'Pistorder: clear the displays', 'minecraft:sticky_piston'),
    ]),
    ('Block info', [
        ('N+I', 'Info view on / off: comparator level and hopper cooldown of the block you look at', 'minecraft:comparator'),
        ('Right Alt', 'Hold: show redstone dust update order', 'minecraft:redstone'),
        ('N+B', 'Block event throttler on / off (huge piston builds)', 'minecraft:slime_block'),
        ('N+C', 'TweakerMore settings', 'minecraft:writable_book'),
    ]),
    ('Placing blocks', [
        ('X+F', 'Flexible block placement on / off', 'minecraft:observer'),
        ('X+A', 'Accurate block placement on / off', 'minecraft:dispenser'),
        ('Mouse 4 / Mouse 5', 'Hold while placing: rotate / offset the block', 'minecraft:dropper'),
        ('Z+1…6', 'Placement restriction: plane, face, column, line, diagonal, layer', 'minecraft:scaffolding'),
        ('X+R', 'Hand restock on / off', 'minecraft:bundle'),
        ('Left Alt+1…3', 'Swap the hotbar with inventory row 1, 2 or 3', 'minecraft:chest'),
        ('X+C', 'Tweakeroo settings', 'minecraft:writable_book'),
    ]),
    ('Schematics', [
        ('M', 'Litematica main menu', 'minecraft:structure_block'),
        ('M+E', 'Easy place on / off', 'minecraft:stone'),
        ('M+P', 'Schematic placements', 'minecraft:map'),
        ('M+L', 'Material list', 'minecraft:paper'),
        ('M+V', 'Schematic verifier', 'minecraft:spyglass'),
        ('M+G / M+R', 'Toggle schematic rendering / all rendering', 'minecraft:glass'),
        ('Page Up / Page Down', 'Next / previous render layer', 'minecraft:ladder'),
        ('I', 'Info overlay of the targeted schematic block', 'minecraft:name_tag'),
        ('M+T', 'Selection tool on / off', 'minecraft:stick'),
        ('Ctrl+Alt+S', 'Save the area selection as a schematic', 'minecraft:writable_book'),
        ('J+C', 'Technical Utilities settings (schematic container contents)', 'minecraft:barrel'),
    ]),
    ('HUD and view', [
        ('H', 'MiniHUD info lines on / off', 'minecraft:oak_sign'),
        ('H+L', 'Light level overlay', 'minecraft:torch'),
        ('H+C', 'MiniHUD settings: slime chunks, spawn chunks, random ticks and more', 'minecraft:slime_ball'),
        ('F3+G', 'Chunk borders', 'minecraft:grass_block'),
        ('F3+B', 'Hitboxes', 'minecraft:armor_stand'),
        ('C', 'Zoom', 'minecraft:spyglass'),
        ('K', 'Shaders on / off (if item icons vanish, change GUI Scale and back)', 'minecraft:ender_eye'),
        ('Y / B / U', 'Minimap settings / new waypoint / waypoint list', 'minecraft:compass'),
    ]),
    ('Inventories', [
        ('Left Alt+R', 'Sort the inventory under the cursor', 'minecraft:chest'),
        ('Shift+Drag', 'Move stacks', 'minecraft:hopper'),
        ('Alt+Click', 'Move all matching items', 'minecraft:hopper_minecart'),
        ('Ctrl+Shift+Q', 'Drop all matching items', 'minecraft:dropper'),
        ('Insert', 'Chest Tracker: remembered containers', 'minecraft:ender_chest'),
        ('End', 'Find containers holding the hovered item', 'minecraft:compass'),
        ('R / U', 'JEI: recipe / uses of the hovered item', 'minecraft:crafting_table'),
        ('I+C', 'Item Scroller settings', 'minecraft:writable_book'),
    ]),
    ('Other', [
        ('A+C', 'All technical mod settings in one list', 'minecraft:bookshelf'),
        ('F9', '4K screenshot', 'minecraft:painting'),
        ('F2', 'Screenshot', 'minecraft:item_frame'),
        ('Right Shift', 'Meteor Client menu', 'minecraft:command_block'),
        ('V', 'Meteor freecam', 'minecraft:ender_pearl'),
    ]),
]

INTRO = ('"H+C" means: hold H, then press C. The first key names the mod: '
         'H MiniHUD, M Litematica, X Tweakeroo, N TweakerMore, I Item Scroller, J Technical Utilities. '
         'Other keys can be searched in Options → Controls.')


def title(sub):
    return [{'text': 'REDSTONE EX MACHINA', 'color': RED, 'bold': True}, {'text': f'  ·  {sub}', 'color': 'gray'}]


def key_text(keys):
    if keys.startswith('~'):
        return {'text': keys[1:], 'color': 'gray', 'italic': True}
    return {'text': keys, 'color': '#FF6A4D', 'bold': True}


def section_dialog(name, rows):
    """Category page: one row per hotkey, item icon on the left. Close returns to the pause menu."""
    body = [{'type': 'minecraft:item', 'item': {'id': row_icon}, 'show_decoration': False, 'show_tooltip': False,
             'description': {'contents': {'text': '', 'extra': [key_text(keys), {'text': f'  {desc}', 'color': 'white'}]},
                             'width': 380}}
            for keys, desc, row_icon in rows]
    return {
        'type': 'minecraft:notice',
        'title': title(name),
        'external_title': {'text': name, 'color': 'white'},
        'body': body,
        'action': {'label': 'Close', 'width': 150},
    }


def dialog():
    return {
        'type': 'minecraft:dialog_list',
        'title': title('Hotkeys'),
        'body': [
            {'type': 'minecraft:item', 'item': {'id': 'minecraft:redstone'}, 'show_decoration': False,
             'show_tooltip': False, 'width': 32, 'height': 32},
            {'type': 'minecraft:plain_message', 'contents': {'text': INTRO, 'color': 'gray'}, 'width': 360},
        ],
        'dialogs': [section_dialog(*s) for s in SECTIONS],
        'columns': 2,
        'button_width': 160,
        'exit_action': {'label': 'Close', 'width': 160},
    }


def pause_link():
    return {'text': '⚡ Press here for hotkeys', 'color': RED, 'bold': True,
            'click_event': {'action': 'show_dialog', 'dialog': dialog()},
            'hover_event': {'action': 'show_text', 'value': 'Open the RedstoneExMachina hotkey menu'}}


def version_credit():
    return {'text': 'RedstoneExMachina ', 'color': RED, 'bold': True,
            'extra': [{'text': f'v{VERSION}', 'color': 'gray', 'bold': False}],
            'hover_event': {'action': 'show_text',
                            'value': 'Based on Fabulously Optimized 14.1.0. Configured for technical redstone building.'}}


def html_keys(keys):
    if keys.startswith('~'):
        return html.escape(keys[1:])
    return ' / '.join('+'.join(f'<kbd>{html.escape(k)}</kbd>' for k in alt.split('+')) for alt in keys.split(' / '))


def page():
    sections = '\n'.join(
        f'<section><h2>{html.escape(name)}</h2><table>'
        + ''.join(f'<tr><td>{html_keys(k)}</td><td>{html.escape(d)}</td></tr>' for k, d, _ in rows)
        + '</table></section>'
        for name, rows in SECTIONS)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>RedstoneExMachina hotkeys</title>
<style>
:root {{ --red: {RED}; --dark: #1b1414; --panel: #2a1f1f; --line: #4a2a2a; --text: #e8e0e0; --muted: #a89a9a; }}
body {{ background: var(--dark); color: var(--text); font: 15px/1.5 system-ui, sans-serif; margin: 0; padding: 2rem; }}
h1 {{ color: var(--red); letter-spacing: .08em; margin: 0 0 .2rem; }} h1 small {{ color: var(--muted); font-size: .5em; letter-spacing: 0; }}
p {{ color: var(--muted); max-width: 60rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(26rem, 1fr)); gap: 1rem; }}
section {{ background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--red); padding: .6rem 1rem 1rem; }}
h2 {{ font-size: 1.05rem; margin: .3rem 0 .6rem; color: #ffb0a0; }}
table {{ width: 100%; border-collapse: collapse; }} td {{ padding: .25rem .3rem; border-top: 1px solid var(--line); vertical-align: top; }}
td:first-child {{ white-space: nowrap; width: 10rem; }}
kbd {{ background: #3a2626; border: 1px solid #6a3a3a; border-bottom-width: 2px; border-radius: 3px; padding: 0 .35rem; font: 13px ui-monospace, monospace; color: #fff; }}
</style></head><body>
<h1>REDSTONE EX MACHINA <small>v{VERSION} hotkeys</small></h1>
<p>{html.escape(INTRO)} In game: pause menu → Press here for hotkeys.</p>
<div class="grid">
{sections}
</div></body></html>
'''


def set_export_version(path):
    with open(path) as f:
        cfg = f.read()
    with open(path, 'w') as f:
        f.write(re.sub(r'^ExportVersion=.*$', f'ExportVersion={VERSION}', cfg, flags=re.M))


def main():
    html_out, *configs = sys.argv[1:]
    with open(html_out, 'w') as f:
        f.write(page())
    for path in configs:
        if path.endswith('instance.cfg'):
            set_export_version(path)
            print(path)
            continue
        with open(path) as f:
            cfg = json.load(f)
        menu = cfg['pause_menu']['bottom_right']
        menu[:] = [e for e in menu if 'hotkeys' not in e.get('text', '').lower()] + [pause_link()]
        title_menu = cfg['main_menu']['bottom_right']
        title_menu[:] = [version_credit() if e.get('text', '').startswith('RedstoneExMachina') else e for e in title_menu]
        with open(path, 'w') as f:
            f.write(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n')
        print(path)


if __name__ == '__main__':
    main()
