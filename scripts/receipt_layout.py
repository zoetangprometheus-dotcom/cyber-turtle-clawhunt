"""One monochrome receipt renderer shared by the browser preview and ESC/POS."""
import base64
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

WIDTH = 384
SONGTI = '/System/Library/Fonts/Supplemental/Songti.ttc'
HEITI = '/System/Library/Fonts/STHeiti Medium.ttc'
ORIGINS = {'ai': 'AI 创作  仅供自我探索', 'sample': '编辑排版样张  非 AI 生成',
           'demo': '卦象联调  非正式签文'}


@lru_cache(maxsize=32)
def font(size, bold=False, sans=False):
    path = HEITI if sans else SONGTI
    if not Path(path).exists():
        raise RuntimeError('Receipt rendering requires the documented macOS Chinese fonts')
    return ImageFont.truetype(path, size, index=1 if bold or sans else 6)


def wrap(text, face, width, balance=True):
    lines, line = [], ''
    for char in text:
        if line and face.getlength(line + char) > width:
            # Keep common Chinese closing punctuation off the next line's start.
            if char in '，。！？；：、）》】」』' and len(line) > 1:
                lines.append(line[:-1]); line = line[-1] + char
            else:
                lines.append(line); line = char
        else:
            line += char
    if line: lines.append(line)
    if balance and len(lines)>1:
        target=min(width,face.getlength(text)/len(lines)+face.size/2)
        balanced=wrap(text,face,target,balance=False)
        if len(balanced)==len(lines): return balanced
    return lines


def render(hexagram, base=None, origin='ai'):
    if origin not in ORIGINS: raise ValueError('Unknown receipt origin')
    if base is None: origin = 'demo'
    image = Image.new('L', (WIDTH, 1800), 255)
    draw = ImageDraw.Draw(image)

    def centered(text, y, size=24, bold=False, sans=False, spacing=0):
        face = font(size, bold, sans)
        width = face.getlength(text) + max(0, len(text)-1) * spacing
        x = (WIDTH - width) / 2
        top = face.getbbox(text, anchor='la')[1]
        for char in text:
            draw.text((round(x), y-top), char, fill=0, font=face, anchor='la')
            x += face.getlength(char) + spacing

    def diamond(x, y, size=4):
        draw.polygon([(x,y-size),(x+size,y),(x,y+size),(x-size,y)], fill=0)

    def rule(y, label=None):
        if label:
            face = font(19, sans=True)
            gap = int(face.getlength(label)/2) + 16
            draw.line((26,y,WIDTH//2-gap,y),fill=0,width=1)
            draw.line((WIDTH//2+gap,y,WIDTH-27,y),fill=0,width=1)
            centered(label,y-9,19,sans=True)
        else:
            draw.line((28,y,WIDTH-29,y),fill=0,width=1)
            for x in (23,WIDTH-24): diamond(x,y,3)

    # Receipt header and enlarged hexagram occupy most of the printable width.
    draw.line((22,18,WIDTH-23,18),fill=0,width=3)
    centered('CYBER TURTLE',33,16,sans=True,spacing=3)
    centered('赛博龟壳',65,30,bold=True,spacing=8)
    centered('第 %02d 签' % hexagram['hexagram_id'],111,18,sans=True)
    left,right,top=48,WIDTH-49,150
    for row,yang in enumerate(reversed(hexagram['lines_bottom_to_top'])):
        y=top+row*22
        if yang:
            draw.rectangle((left,y,right,y+12),fill=0)
        else:
            draw.rectangle((left,y,WIDTH//2-24,y+12),fill=0)
            draw.rectangle((WIDTH//2+24,y,right,y+12),fill=0)
    centered('上卦 %s   ·   下卦 %s' % (hexagram['upper_trigram'],hexagram['lower_trigram']),294,22)
    rule(337)

    # Large name, open corner frame and stepped sides echo the supplied reference.
    name=hexagram['name_zh']
    face_size=82 if len(name)==1 else 64
    centered(name,373,face_size,bold=True,spacing=5)
    for x,sign in ((34,1),(WIDTH-35,-1)):
        draw.line([(x+sign*22,366),(x,366),(x,389),(x-sign*7,389),(x-sign*7,433),(x,433),(x,456),(x+sign*22,456)],fill=0,width=2)
    y=493
    title=base['title'] if base else '此刻与你相遇'
    for line in wrap(title,font(34,bold=True),WIDTH-80):
        centered(line,y,34,bold=True); y+=47
    y+=29
    rule(y,'此刻的签'); y+=35
    message=base['message'] if base else '这一卦已为你留下\u3000AI 解读尚未启用'
    for line in wrap(message,font(25),WIDTH-80):
        centered(line,y,25); y+=37
    y+=29
    rule(y,'今日一小步'); y+=39
    action=base['action'] if base else '请先在电脑配置窗口启用 AI 纸签'
    action_lines=wrap(action,font(26,bold=True),WIDTH-104)
    box_top=y-14
    for line in action_lines:
        centered(line,y,26,bold=True); y+=39
    draw.line((36,box_top,36,y+3),fill=0,width=2)
    draw.line((WIDTH-37,box_top,WIDTH-37,y+3),fill=0,width=2)
    for x,direction in ((36,1),(WIDTH-37,-1)):
        for edge in (box_top,y+3): draw.line((x,edge,x+direction*12,edge),fill=0,width=2)
    y+=45
    # A small geometric seal uses no invented scores, auspiciousness or lucky data.
    for x in (WIDTH//2-27,WIDTH//2+27):
        draw.ellipse((x-18,y-18,x+18,y+18),outline=0,width=2)
        draw.line((x-10,y,x+10,y),fill=0,width=2)
    diamond(WIDTH//2,y,4)
    y+=42
    rule(y); y+=22
    centered(ORIGINS[origin],y,17,sans=True); y+=29
    centered('扫描设备屏幕  展开这一签',y,17); y+=34
    centered('CYBER TURTLE',y,15,sans=True,spacing=2); y+=30
    draw.line((22,y,WIDTH-23,y),fill=0,width=3)
    y+=25
    if y>image.height: raise ValueError('Receipt content exceeds canvas')
    # Threshold instead of halftoning keeps thermal text and thin lines clean.
    return image.crop((0,0,WIDTH,y)).point(lambda value: 255 if value>=160 else 0,mode='1')


def png_data(image):
    output=BytesIO(); image.save(output,format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii')


def escpos(image):
    if image.width != WIDTH or image.mode != '1': raise ValueError('Expected 384-dot monochrome receipt')
    payload=bytearray(b'\x1b@\x1ba\x00')
    # 120-row bands stay near the size of the original verified graphic sample.
    for top in range(0,image.height,120):
        band=image.crop((0,top,WIDTH,min(top+120,image.height)))
        bits=ImageOps.invert(band.convert('L')).convert('1',dither=Image.Dither.NONE).tobytes()
        payload.extend(b'\x1dv0\x00'+bytes([WIDTH//8,0,band.height & 255,band.height>>8])+bits)
    payload.extend(b'\n\n\n\x1b@')
    return bytes(payload)
