from pathlib import Path
from ast import literal_eval
import subprocess
import random
import argparse
from Pylette import extract_colors


def darkfactor(color: tuple[int, int, int]) -> float:
    return 1 - (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255


def lightfactor(color: tuple[int, int, int]) -> float:
    return 1 - darkfactor(color)


def mode_check(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> bool:
    if DARK:
        return abs(darkfactor(c1) - darkfactor(c2)) <= 0.15
    return abs(lightfactor(c1) - lightfactor(c2)) >= 0.15


def purify_css(css: str) -> dict[str, str]:
    data = {}
    for line in css.splitlines():
          if line.strip().startswith('--'):
                key, value = line.split(':')
                data[key.strip()] = value.strip(' ;')
    return data


def random_set():
    print("Randomizing colors")
    consumed, picked = set(), set()
    for k, v in themes.items():
        if k in consumed or "important" in v:
            continue
        pattern_v = literal_eval(v.replace('rgba', ''))
        picks = [i for i in luminance if mode_check(i.rgb, pattern_v)]
        if not picks:
            picks = [i for i in palette if mode_check(i.rgb, pattern_v)]
        picks = [i for i in picks if i not in picked]
        if not picks:
            x = random.choice([i for i in palette if i not in picked] + [i for i in luminance if i not in picked])
        else:
            x = random.choice(picks)
        for a, b in themes.items():
            if b == v:
                themes[a] = f"rgba({x.rgb[0]}, {x.rgb[1]}, {x.rgb[2]}, {pattern_v[3]})"
                consumed.add(a)
        picked.add(x)


def optimal_set():
    print("Optimizing colors")
    consumed , picked = set(), set()
    for k, v in themes.items():
        if k in consumed or "important" in v:
            continue
        pattern_v, pick = literal_eval(v.replace('rgba', '')), None
        for i in [i for i in luminance if i not in picked]:
            if abs(darkfactor(i.rgb) - darkfactor(pattern_v)) <= 0.15:
                pick = i
                break
        else:
            for i in [i for i in palette if i not in picked]:
                if abs(darkfactor(i.rgb) - darkfactor(pattern_v)) <= 0.15:
                    pick = i
                    break
            else:
                pick = random.choice([i for i in palette if i not in picked] + [i for i in luminance if i not in picked])
        for a, b in themes.items():
            if b == v:
                themes[a] = f"rgba({pick.rgb[0]}, {pick.rgb[1]}, {pick.rgb[2]}, {pattern_v[3]})"
                consumed.add(a)
        picked.add(pick)


parser = argparse.ArgumentParser(description='Generate a custom theme for GNOME')

parser.add_argument('-p', '--path', type=str, help='Path to the theme folder', required=False)
parser.add_argument('-r', '--random', help='Randomize the colors', action='store_true')
parser.add_argument('-d', '--dark', help='Dark mode', action='store_true')
parser.add_argument('-g', '--generate', help='Generate a new theme else generate from the generated.css file', action='store_true')


args = parser.parse_args()
target = Path(args.path) if args.path else Path(__file__).parent


if not target.exists():
    print("Invalid path")
    exit()


RANDOM = args.random
DARK = args.dark
GENERATE = args.generate
print(f"Config: Random: {RANDOM}, Dark: {DARK}, Generate: {GENERATE}")
print(f"Path: {target}")


if not (target / 'template.css').exists():
    print("template.css not found")
    exit()

with open(target / 'template.css') as f:
    template = f.read()


if GENERATE:
    if not (target / 'themes.css').exists():
        print("themes.css not found")
        exit()
    with open(target / 'themes.css') as f:
        themes = purify_css(f.read())
    n = len(set(themes.values()))
    image = subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.background', 'picture-uri']).decode('utf-8').strip()[8:-1]
    palette = extract_colors(image, palette_size=n + 3, resize=True, mode='MC', sort_mode="frequency")
    luminance = extract_colors(image, palette_size=n + 8, resize=True, mode='MC', sort_mode="luminance")
    optimal_set() if not RANDOM else random_set()
    with open(target / "generated.css", "w") as f:
        string = ":root {\n"
        for k, v in themes.items():
            string += f"    {k}: {v};\n"
        string += "}"
        f.write(string)
    print("Generated.css file created")
else:
    print("Using generated.css file")
    try:
        with open(target / "generated.css") as f:
            themes = purify_css(f.read())
    except FileNotFoundError:
        print("No generated.css file found")
        exit()

for k, v in themes.items():
    if "important" in v:
        v = v.replace("!important", "").strip()
    if not DARK and "font" in k:
        p = literal_eval(v.replace('rgba', ''))
        p = tuple([max((45, int(i * 0.45),)) for i in p[:3]]) + (p[3],)
        v = f"rgba({p[0]}, {p[1]}, {p[2]}, {p[3]})"
    template = template.replace(f"var({k})", v)
print("Important variables replaced")

with open(target / 'gnome-shell.css', 'w') as f:
    f.write(template)

print("gnome-shell.css file created")

subprocess.call('gsettings set org.gnome.shell.extensions.user-theme name "default"'.split())
subprocess.call('gsettings set org.gnome.shell.extensions.user-theme name "CustomTheme"'.split())
print("Theme applied")
