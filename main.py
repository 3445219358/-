"""太虚问道 — Windows 原生离线卡牌游戏。"""
from __future__ import annotations

import argparse
import array
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from engine import Game, CARDS, SECTS, SECT_NAMES, REALMS, RELIC_INDEX, NODE_NAMES, definition, text, save_directory

W, H = 1440, 900
INK = (13, 28, 32)
PANEL = (21, 41, 44)
EDGE = (61, 89, 87)
JADE = (128, 197, 173)
GOLD = (215, 183, 119)
WHITE = (229, 229, 209)
MUTED = (148, 166, 157)
RED = (216, 115, 101)
SECT_COLORS = {'neutral': JADE, 'sword': (95, 177, 194), 'alchemy': (211, 139, 94),
               'talisman': (219, 192, 106), 'body': (214, 123, 111), 'demon': (173, 149, 213)}
RARITY = {'基础': MUTED, '进阶': JADE, '稀有': (113, 174, 224), '传说': GOLD, '天劫': RED}
STATUS_NAMES = {'poison': '中毒', 'burn': '灼烧', 'weak': '虚弱', 'vulnerable': '易伤', 'armor': '护体', 'heart': '心魔'}


class App:
    def __init__(self, save_dir=None):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
        pygame.display.set_caption('太虚问道 · 原生桌面版')
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.game = Game(save_dir)
        self.running = True
        self.menu = True
        self.sect = 'sword'
        self.modal = None
        self.page = 0
        self.hand_page = 0
        self.hits = []
        self.mouse = (0, 0)
        self.fonts = {}
        self.toast = ''
        self.toast_until = 0
        self.flash_until = 0
        self.flash_color = JADE
        self.muted = False
        self.fullscreen = False
        self.sounds = {}
        self.last_mode = None
        self.last_turn = 0
        self.detail_card = None
        self.detail_back = None
        self.detail_page = 0
        self.particles = []
        self.background = self.make_background()
        icon = pygame.Surface((64, 64))
        icon.fill(INK)
        pygame.draw.circle(icon, GOLD, (32, 32), 27, 2)
        pygame.draw.line(icon, JADE, (18, 47), (45, 16), 5)
        pygame.draw.line(icon, GOLD, (17, 33), (33, 47), 3)
        pygame.display.set_icon(icon)
        self.make_sounds()

    def font(self, size, title=False):
        key = (size, title)
        if key not in self.fonts:
            candidates = ['C:/Windows/Fonts/simsun.ttc', 'C:/Windows/Fonts/msyh.ttc'] if title else ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf']
            path = next((p for p in candidates if Path(p).is_file()), None)
            self.fonts[key] = pygame.font.Font(path, size)
        return self.fonts[key]

    def label(self, value, pos, size=20, color=WHITE, center=False, title=False):
        image = self.font(size, title).render(str(value), True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.canvas.blit(image, rect)
        return rect

    def wrap(self, value, x, y, width, size=19, color=WHITE, line_height=None):
        line_height = line_height or size + 10
        font = self.font(size)
        line = ''
        for char in str(value):
            if char == '\n' or font.size(line + char)[0] > width:
                self.label(line, (x, y), size, color)
                y += line_height
                line = '' if char == '\n' else char
            else:
                line += char
        if line:
            self.label(line, (x, y), size, color)
            y += line_height
        return y

    def panel(self, rect, color=PANEL, border=EDGE, radius=12):
        pygame.draw.rect(self.canvas, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.canvas, border, rect, 1, border_radius=radius)

    def button(self, rect, title, action, enabled=True, accent=False, small=False):
        rect = pygame.Rect(rect)
        hover = enabled and rect.collidepoint(self.mouse)
        self.panel(rect, (48, 77, 72) if hover else ((39, 66, 61) if accent else PANEL),
                   GOLD if accent else (JADE if hover else EDGE), 7)
        self.label(title, rect.center, 17 if small else 20, (GOLD if accent else WHITE) if enabled else (85, 108, 102), True)
        if enabled:
            self.hits.append((rect, action))

    def make_background(self):
        bg = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            pygame.draw.line(bg, (int(17-6*t), int(37-11*t), int(42-12*t)), (0, y), (W, y))
        rng = random.Random(70)
        for layer in range(4):
            points = [(0, H)]
            base = 340 + layer * 112
            for x in range(-100, W+150, 110):
                points.append((x, base + rng.randrange(-120, 40)))
            points.append((W, H))
            pygame.draw.polygon(bg, (24-layer*3, 49-layer*4, 51-layer*4), points)
        for _ in range(110):
            x, y = rng.randrange(W), rng.randrange(500)
            pygame.draw.circle(bg, (53, 76, 75), (x, y), 1)
        pygame.draw.circle(bg, (48, 76, 76), (1100, 180), 83)
        pygame.draw.circle(bg, (78, 106, 98), (1100, 180), 64, 1)
        for y in (365, 418, 520):
            pygame.draw.line(bg, (37, 62, 61), (0, y), (W, y+24), 1)
        return bg

    def make_sounds(self):
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            for name, freq, length in [('play', 420, .12), ('turn', 200, .18), ('reward', 640, .22), ('click', 520, .07)]:
                count = int(22050*length)
                samples = array.array('h', (int(2500 * math.sin(2*math.pi*freq*i/22050) * (1-i/count)**2) for i in range(count)))
                self.sounds[name] = pygame.mixer.Sound(buffer=samples)
        except pygame.error:
            self.sounds = {}

    def sound(self, kind='click'):
        if not self.muted and kind in self.sounds:
            self.sounds[kind].play()

    def notice(self, value):
        self.toast, self.toast_until = value, time.monotonic() + 3.5

    def art(self, rect, sect, enemy=False):
        rect = pygame.Rect(rect)
        x, y = rect.center
        r = min(rect.w, rect.h)*.36
        c = SECT_COLORS.get(sect, GOLD)
        if enemy:
            c = RED
        pygame.draw.circle(self.canvas, tuple(int(v*.43) for v in c), (int(x), int(y)), int(r), 1)
        pygame.draw.circle(self.canvas, tuple(int(v*.28) for v in c), (int(x), int(y)), int(r*1.19), 1)
        if sect == 'sword':
            pygame.draw.polygon(self.canvas, c, [(x-r*.48,y+r*.7), (x+r*.56,y-r*.84), (x+r*.3,y-r*.18)])
            pygame.draw.line(self.canvas, GOLD, (x-r*.54,y+r*.15), (x-r*.04,y+r*.52), 3)
            pygame.draw.line(self.canvas, c, (x-r*.37,y+r*.51), (x-r*.56,y+r*.8), 4)
        elif sect == 'alchemy':
            pygame.draw.ellipse(self.canvas,c,(x-r*.65,y-r*.35,r*1.3,r*.95),3)
            pygame.draw.line(self.canvas,c,(x-r*.73,y-r*.32),(x+r*.73,y-r*.32),3)
            for dx in (-.4, .4):
                pygame.draw.line(self.canvas,c,(x+r*dx,y+r*.5),(x+r*dx*1.4,y+r*.72),4)
            pygame.draw.polygon(self.canvas,GOLD,[(x-r*.15,y-r*.49),(x+r*.05,y-r*.95),(x+r*.22,y-r*.56),(x+r*.11,y-r*.34)])
        elif sect == 'talisman':
            pygame.draw.polygon(self.canvas,c,[(x-r*.42,y-r*.8),(x+r*.47,y-r*.6),(x+r*.34,y+r*.81),(x-r*.5,y+r*.6)],2)
            pygame.draw.lines(self.canvas,GOLD,False,[(x+r*.15,y-r*.55),(x-r*.15,y-r*.1),(x+r*.15,y-r*.1),(x-r*.12,y+r*.49)],3)
        elif sect == 'body':
            pygame.draw.polygon(self.canvas,c,[(x,y-r*.85),(x+r*.65,y-r*.42),(x+r*.55,y+r*.29),(x,y+r*.8),(x-r*.55,y+r*.29),(x-r*.65,y-r*.42)],3)
            pygame.draw.line(self.canvas,GOLD,(x,y-r*.49),(x,y+r*.41),3)
            pygame.draw.line(self.canvas,GOLD,(x-r*.28,y-r*.1),(x+r*.28,y-r*.1),3)
        elif sect == 'demon':
            pygame.draw.circle(self.canvas,c,(int(x),int(y)),int(r*.67),3)
            pygame.draw.polygon(self.canvas,c,[(x-r*.53,y-r*.43),(x-r*.64,y-r*.9),(x-r*.16,y-r*.55)])
            pygame.draw.polygon(self.canvas,c,[(x+r*.53,y-r*.43),(x+r*.64,y-r*.9),(x+r*.16,y-r*.55)])
            pygame.draw.lines(self.canvas,GOLD,False,[(x-r*.35,y+r*.03),(x,y+r*.25),(x+r*.35,y+r*.03)],3)
        else:
            pygame.draw.circle(self.canvas,c,(int(x),int(y)),int(r*.5),2)
            pygame.draw.lines(self.canvas,c,False,[(x-r*.8,y),(x,y-r*.8),(x+r*.8,y),(x,y+r*.8),(x-r*.8,y)],2)

    def card(self, card, rect, action=None, disabled=False, number=None):
        rect = pygame.Rect(rect)
        d = definition(card)
        hover = action and not disabled and rect.collidepoint(self.mouse)
        if hover:
            rect.y -= 8
        self.panel(rect, (31, 53, 53) if not disabled else (25, 39, 41), RARITY[d['rarity']], 9)
        pygame.draw.rect(self.canvas, SECT_COLORS[d['sect']], (rect.x+1,rect.y+1,rect.w-2,5),border_radius=3)
        self.label(d['cost'], (rect.x+19,rect.y+21), 25, JADE, True)
        self.label(d['name'] + (' +' if card['upgraded'] else ''), (rect.x+38,rect.y+12), 19 if rect.w >= 200 else 17, GOLD if card['upgraded'] else WHITE)
        self.label(d['type']+' · '+d['rarity'], (rect.x+15,rect.y+43), 14, MUTED)
        compact = rect.h < 240
        self.art((rect.x+rect.w//2-45,rect.y+56,90,48 if compact else 80),d['sect'])
        desc_y = rect.y+(111 if compact else 140)
        font_size = 15 if compact else 16
        available = rect.bottom-desc_y-22
        while font_size > 12:
            line, lines = '', 1
            for ch in text(card):
                if self.font(font_size).size(line+ch)[0] > rect.w-30:
                    lines += 1
                    line = ch
                else:
                    line += ch
            if lines*(font_size+6) <= available:
                break
            font_size -= 1
        self.wrap(text(card),rect.x+15,desc_y,rect.w-30,font_size,line_height=font_size+6)
        if number is not None:
            self.label(str(number), (rect.right-18,rect.bottom-15), 14, MUTED,True)
        if disabled:
            self.label('灵力不足' if self.game.s and self.game.s['mode']=='battle' else '已选 / 不可用', (rect.centerx, rect.bottom-15), 13, RED,True)
        if action and not disabled:
            self.hits.append((rect,action))

    def bar(self, x, y, width, value, maximum, color=RED, caption=None):
        pygame.draw.rect(self.canvas, (32, 47, 48), (x,y,width,13), border_radius=4)
        pygame.draw.rect(self.canvas, color, (x,y,max(0,int(width*min(1,value/max(1,maximum)))),13), border_radius=4)
        if caption:
            self.label(caption,(x+width/2,y+31),17,WHITE,True)

    def open_modal(self, kind):
        self.modal, self.page = kind, 0

    def inspect_card(self, card):
        self.detail_card = card.copy()
        self.detail_back, self.detail_page = self.modal, self.page
        self.modal = 'card'

    def close_detail(self):
        self.modal, self.page = self.detail_back, self.detail_page

    def start(self):
        if self.game.has_save:
            self.modal = 'confirm'
        else:
            self.new_run()

    def new_run(self):
        self.game.start(self.sect)
        self.menu, self.modal, self.hand_page = False, None, 0
        self.notice('观察敌方意图，点击卡牌出招。空格结束回合。')

    def resume(self):
        if self.game.resume():
            self.menu, self.modal, self.hand_page = False, None, 0
        else:
            self.notice(self.game.load_error)

    def act(self, method, *args):
        before = self.game.s['mode'] if self.game.s else ''
        if method(*args):
            after = self.game.s['mode']
            self.sound('reward' if after == 'reward' else 'play' if before == 'battle' else 'click')
            self.flash_until = time.monotonic()+.18
            self.flash_color = JADE if method != self.game.end_turn else RED
            if before == 'battle':
                self.particles = [(random.randrange(600,1100),random.randrange(310,540),random.uniform(-70,70),random.uniform(-80,0),time.monotonic()+.5) for _ in range(18)]
            self.hand_page = min(self.hand_page, max(0,(len(self.game.battle['hand'])-1)//5)) if after == 'battle' else 0
        else:
            self.notice('当前无法执行：请检查灵力、灵石或气血。')

    def draw_menu(self):
        self.label('太 虚 问 道',(W/2,156),76,GOLD,True,True)
        self.label('以一副牌，问一条长生路',(W/2,242),25,JADE,True,True)
        self.label('三重仙山  /  五脉道统  /  一局一命',(W/2,297),17,MUTED,True)
        self.label('择一道统，踏入修行',(56,352),22,WHITE)
        for i,s in enumerate(SECTS):
            r = pygame.Rect(56+i*268,396,252,260)
            selected = self.sect == s['id']
            self.panel(r,(33,60,57) if selected else PANEL,GOLD if selected else EDGE)
            self.art((r.x+73,r.y+14,106,102),s['id'])
            self.label(s['name'],(r.centerx,r.y+132),28,SECT_COLORS[s['id']],True,True)
            self.label(s['tag'],(r.centerx,r.y+174),16,WHITE,True)
            self.wrap(s['desc'],r.x+22,r.y+205,210,15,MUTED,23)
            self.hits.append((r,lambda sect=s['id']:setattr(self,'sect',sect)))
        self.button((440,705,270,58),'开始修行',self.start,accent=True)
        self.button((730,705,270,58),'继续修行',self.resume,self.game.has_save)
        self.button((416,790,185,44),'卡牌图鉴 · 60',lambda:self.open_modal('codex'),small=True)
        self.button((617,790,185,44),'修行指南',lambda:self.open_modal('guide'),small=True)
        self.button((818,790,185,44),'离开',lambda:setattr(self,'running',False),small=True)
        self.label('原生离线版 0.2  ·  F11 全屏  ·  M 静音',(W/2,872),14,MUTED,True)

    def draw_top(self):
        s = self.game.s
        self.panel((20,18,1400,76), (18,36,40), EDGE)
        self.label('太虚问道',(40,39),27,GOLD,title=True)
        self.label(SECT_NAMES[s['sect']]+' · '+REALMS[s['realm']],(205,41),22,JADE)
        self.label(f'气血 {s["hp"]} / {s["maxHp"]}',(430,40),22,RED)
        self.label(f'灵石 {s["gold"]}',(638,40),22,GOLD)
        self.button((845,34,158,43),f'卡组 {len(s["deck"])}',lambda:self.open_modal('deck'),small=True)
        self.button((1017,34,158,43),f'遗物 {len(s["relics"])}',lambda:self.open_modal('relics'),small=True)
        self.button((1189,34,105,43),'指南',lambda:self.open_modal('guide'),small=True)
        self.button((1307,34,94,43),'暂停',lambda:self.open_modal('pause'),small=True)

    def draw_map(self):
        s = self.game.s
        self.panel((20,112,286,766),(17,34,37),EDGE)
        self.label(f'第 {s["floor"]} 重 · '+['青岚山','赤霄境','太虚天'][s['floor']-1],(39,132),23,GOLD,title=True)
        self.label(f'路程 {min(s["row"]+1,12)} / 12',(39,171),16,MUTED)
        for row in range(12):
            y = 218+row*49
            active = row == s['row']
            self.label(f'{row+1:02}',(33,y+8),13,JADE if active else MUTED)
            nodes = s['map'][row]
            width = 224/len(nodes)
            if row < 11:
                pygame.draw.line(self.canvas,EDGE,(175,y+37),(175,y+50),1)
            for i,node in enumerate(nodes):
                r = pygame.Rect(63+i*width,y,width-5,36)
                visited = node['id'] in s['visited']
                self.panel(r,(44,71,63) if visited else ((32,60,56) if active else (21,37,39)),GOLD if active else EDGE,6)
                label = {'shop':'商店','treasure':'遗宝','battle':'斗法','elite':'精英','event':'奇遇','rest':'静室','boss':'首领'}[node['type']]
                self.label(label,r.center,14,JADE if visited else (GOLD if active else MUTED),True)
                if active and s['mode']=='map':
                    self.hits.append((r,lambda row=row,i=i:self.act(self.game.choose_node,row,i)))
        self.wrap('玉色为已走过的路。\n金色为当前可选节点。\n选择后向前，无法回头。',39,818,244,13,MUTED,19)

    def draw_map_scene(self):
        s = self.game.s
        self.label('仙 路 在 前',(876,200),52,GOLD,True,True)
        self.label('从左侧金色节点中，选择下一步。',(876,276),22,JADE,True)
        self.art((721,335,310,270),s['sect'])
        self.label('斗法得牌  ·  静室调息  ·  奇遇问心',(876,661),23,WHITE,True)
        self.label('每重十二步。击败守关首领，方可破境。',(876,710),18,MUTED,True)
        self.panel((485,757,782,70),PANEL,EDGE)
        hint = '初入仙途：先补足伤害，再用格挡对付敌人的攻击回合。' if s['floor']==1 else '修行提示：精简卡组，让功法与关键牌更早到手。'
        self.label(hint,(876,792),18,JADE,True)

    def statuses(self, values, x, y, width=400):
        entries = [f'{STATUS_NAMES[k]} {v}' for k,v in values.items() if v and k in STATUS_NAMES]
        if not entries:
            self.label('无附加状态',(x,y),14,MUTED)
        else:
            self.wrap('  ·  '.join(entries),x,y,width,15,JADE,23)

    def draw_battle(self):
        s,b = self.game.s,self.game.battle
        e = b['enemy']
        self.label(e['name'],(864,141),33,GOLD,True,True)
        self.label(e['epithet'] + (' · 第二阶段' if e['phase']==2 else ''),(864,187),17,MUTED,True)
        self.panel((1148,220,270,343),(18,35,38),EDGE)
        self.label('斗 法 记 录',(1170,240),17,JADE)
        y = 280
        for line in b['log'][-6:]:
            y = self.wrap(line,1170,y,229,14,MUTED,22)+9
        self.panel((677,218,389,53),(44,45,38),GOLD)
        self.label('敌方意图  ·  '+self.game.intent()['text'],(871,245),21,RED,True)
        enemy_sect = 'body' if '龟' in e['name'] or '甲' in e['name'] else ('demon' if '狐' in e['name'] else 'sword')
        self.art((725,285,292,220),enemy_sect,True)
        self.bar(720,524,306,e['hp'],e['maxHp'],RED,f'气血 {e["hp"]} / {e["maxHp"]}  ·  格挡 {e["block"]}')
        self.statuses(e['statuses'],704,583,395)
        self.art((348,296,240,190),s['sect'])
        self.label('你',(467,283),22,JADE,True)
        self.bar(359,508,218,s['hp'],s['maxHp'],JADE)
        self.label(f'格挡 {b["block"]}  ·  意境 {b["mood"]}',(359,544),20,WHITE)
        self.statuses(b['statuses'],359,584,270)
        power_names = {'comboMood':'太白剑誓','healQi':'金丹炉心','armorAura':'不坏金身','demonHeart':'魔心借道'}
        powers = [power_names[k]+(' +' if v else '') for k,v in b['powers'].items()]
        if powers:
            self.wrap('功法：'+' · '.join(powers),348,234,276,13,JADE,19)
        self.label(f'第 {b["turn"]} 回合',(356,125),18,MUTED)
        self.label(f'灵力 {b["qi"]} / {s["maxQi"]}',(356,162),29,JADE)
        self.label(f'抽牌 {len(b["draw"])}  ·  弃牌 {len(b["discard"])}  ·  消耗 {len(b["exhaust"])}',(356,207),15,MUTED)
        self.button((1175,582,218,49),'结束回合  [空格]',lambda:self.act(self.game.end_turn),accent=True)
        self.label('点击出牌  ·  1–5 快捷出牌  ·  ← → 翻页',(864,625),15,MUTED,True)
        hand = b['hand']
        self.hand_page = min(self.hand_page,max(0,(len(hand)-1)//5))
        start = self.hand_page*5
        for i,c in enumerate(hand[start:start+5]):
            idx = start+i
            self.card(c,(328+i*218,645,208,234),lambda idx=idx:self.act(self.game.play,idx),not self.game.can_play(idx),i+1)
        if not hand:
            self.label('手牌已空，结束回合抽取新的五张牌。',(871,756),24,MUTED,True)
        if len(hand)>5:
            self.button((1251,119,45,37),'←',lambda:setattr(self,'hand_page',max(0,self.hand_page-1)),self.hand_page>0,small=True)
            self.label(f'{self.hand_page+1}/2',(1321,137),15,MUTED,True)
            self.button((1345,119,45,37),'→',lambda:setattr(self,'hand_page',min(1,self.hand_page+1)),self.hand_page<1,small=True)

    def draw_reward(self):
        r = self.game.s['reward']
        self.label('斗 法 告 捷',(867,175),48,GOLD,True,True)
        self.label(f'获得 {r["gold"]} 灵石 · 选择一张牌加入卡组',(867,251),21,JADE,True)
        if r['relic']:
            relic = RELIC_INDEX[r['relic']]
            self.label('获得遗物：'+relic['name'],(867,296),20,GOLD,True)
            self.wrap(relic['effect'],535,327,665,17,MUTED)
        for i,c in enumerate(r['cards']):
            self.card(c,(453+i*281,397,258,276),lambda i=i:self.act(self.game.take_reward,i))
        skip = 12 + (5 if 'bead' in self.game.s['relics'] else 0)
        self.button((686,742,360,57),f'跳过奖励 · 获得 {skip} 灵石',lambda:self.act(self.game.take_reward,None))

    def draw_event(self):
        s = self.game.s
        event = s['event']
        self.label(event['name'],(869,187),45,GOLD,True,True)
        self.wrap(event['story'],465,282,810,23,WHITE,38)
        for i,(title,desc,effect) in enumerate(event['choices']):
            r = pygame.Rect(464,421+i*112,812,96)
            enabled = s['gold'] >= effect.get('cost',0) and s['hp'] > -effect.get('hp',0)
            hover = enabled and r.collidepoint(self.mouse)
            self.panel(r,(36,64,58) if hover else PANEL,JADE if hover else EDGE)
            self.label(title,(r.x+23,r.y+13),23,GOLD if enabled else MUTED)
            self.label(desc,(r.x+23,r.y+53),17,WHITE if enabled else RED)
            if enabled:
                self.hits.append((r,lambda i=i:self.act(self.game.event_choice,i)))

    def draw_rest(self):
        s = self.game.s
        self.label('一 炉 香 · 半 日 闲',(865,214),45,GOLD,True,True)
        self.wrap('云海将喧嚣隔在山下。你可以调息养伤，也可以推演一道未竟的法诀。',505,321,724,22,WHITE,38)
        heal = math.ceil(s['maxHp']*.25)+(6 if 'herb' in s['relics'] else 0)
        self.button((492,472,343,82),f'调息 · 回复 {heal} 点气血',lambda:self.act(self.game.rest,'heal'),accent=True)
        self.button((875,472,343,82),'悟道 · 升级一张牌',lambda:self.act(self.game.rest,'upgrade'))
        self.label('两项只能选择一项。',(861,609),19,MUTED,True)

    def draw_treasure(self):
        relic = RELIC_INDEX.get(self.game.s.get('treasure'))
        self.label('旧 洞 天 · 新 机 缘',(867,211),43,GOLD,True,True)
        self.art((731,303,271,218),'neutral')
        self.label(relic['name'] if relic else '灵石遗藏',(867,558),29,JADE,True)
        self.wrap((relic['effect'] if relic else '所有遗物均已收集，转为 25 灵石。')+' 另获得 25 灵石。',537,620,660,20,WHITE,32)
        self.button((708,749,315,58),'收下机缘，继续前行',lambda:self.act(self.game.finish_node),accent=True)

    def draw_shop(self):
        s = self.game.s
        self.label('灵 宝 铺',(867,158),43,GOLD,True,True)
        for i,offer in enumerate(s['shop']):
            self.card(offer['card'],(468+i*271,249,245,265))
            self.button((468+i*271,532,245,46),'已售出' if offer['bought'] else f'购入 · {offer["price"]} 灵石',lambda i=i:self.act(self.game.buy,i),not offer['bought'] and s['gold']>=offer['price'],small=True)
        relic = s['shopRelic']
        self.panel((469,612,784,119),PANEL,EDGE)
        if relic['id']:
            d = RELIC_INDEX[relic['id']]
            self.label('遗物 · '+d['name'],(489,628),21,GOLD)
            self.wrap(d['effect'],489,667,503,16,MUTED)
            self.button((1030,645,200,47),'已售出' if relic['bought'] else '购入 · 85 灵石',lambda:self.act(self.game.buy_relic),not relic['bought'] and s['gold']>=85,small=True)
        self.button((469,780,354,53),'移除一张牌 · 50 灵石',lambda:self.act(self.game.begin_remove),s['gold']>=50 and not s['shopRemoved'] and len(s['deck'])>5,small=True)
        self.button((911,780,343,53),'离开商店',lambda:self.act(self.game.finish_node),accent=True)

    def draw_picker(self):
        p = self.game.s['picker']
        self.canvas.blit(self.background,(0,0))
        self.panel((74,79,1292,794),(16,32,36),EDGE)
        self.hits = []
        self.draw_collection(self.game.s['deck'],'选择一张牌 · '+('升级' if p['kind']=='upgrade' else '移除'),pick=True)

    def draw_result(self):
        s = self.game.s
        win = s['end']['win']
        self.label('羽 化 飞 升' if win else '此 途 未 尽',(864,209),58,GOLD if win else RED,True,True)
        self.label('你的道，已越过最后一重天。' if win else '长生路上，每一次失败都留下一道剑痕。',(864,301),23,WHITE,True)
        self.art((739,355,255,224),s['sect'])
        mins,secs = divmod(s['end']['duration'],60)
        self.label(f'{SECT_NAMES[s["sect"]]}  ·  {REALMS[s["realm"]]}  ·  第 {s["floor"]} 重  ·  {mins:02}:{secs:02}',(864,624),23,JADE,True)
        self.label(f'通过 {s["cleared"]} 个节点  ·  {len(s["deck"])} 张牌  ·  {len(s["relics"])} 件遗物',(864,678),19,MUTED,True)
        self.button((704,768,320,58),'回山门，再问道',lambda:setattr(self,'menu',True),accent=True)

    def draw_collection(self, cards, title, pick=False):
        self.label(title,(720,121),31,GOLD,True,True)
        per_page = 10
        pages = max(1,math.ceil(len(cards)/per_page))
        self.page = min(self.page,pages-1)
        for i,c in enumerate(cards[self.page*per_page:(self.page+1)*per_page]):
            idx = self.page*per_page+i
            rect = (100+(i%5)*251,183+(i//5)*279,234,258)
            disabled = pick and ((self.game.s['picker']['kind']=='upgrade' and c['upgraded']) or (self.game.s['picker']['kind']=='remove' and len(cards)<=5))
            self.card(c,rect,lambda idx=idx,c=c:self.act(self.game.pick_card,idx) if pick else self.inspect_card(c),disabled)
        self.button((380,782,154,44),'上一页',lambda:setattr(self,'page',max(0,self.page-1)),self.page>0,small=True)
        self.label(f'{self.page+1} / {pages} · 共 {len(cards)} 张',(720,805),17,MUTED,True)
        self.button((907,782,154,44),'下一页',lambda:setattr(self,'page',min(pages-1,self.page+1)),self.page<pages-1,small=True)
        action = lambda:self.act(self.game.cancel_picker) if pick else setattr(self,'modal',None)
        self.button((1153,106,185,43),'放弃选择' if pick and self.game.s['picker']['origin']=='event' else '返回',action,small=True)
        if pick:
            self.label('点击卡牌完成选择。事件中放弃选择会直接结束该奇遇。',(720,858),15,MUTED,True)

    def draw_modal(self):
        shade = pygame.Surface((W,H),pygame.SRCALPHA)
        shade.fill((5,13,16,230))
        self.canvas.blit(shade,(0,0))
        self.hits = []
        kind = self.modal
        self.panel((74,79,1292,794),(16,32,36),EDGE)
        if kind in ('deck','codex'):
            cards = self.game.s['deck'] if kind=='deck' else [dict(id=c,upgraded=False) for c in CARDS]
            self.draw_collection(cards,'当前卡组' if kind=='deck' else '六十道法 · 卡牌图鉴')
        elif kind == 'card':
            c = self.detail_card
            d = definition(c)
            self.label(d['name'],(720,139),38,GOLD,True,True)
            self.label(SECT_NAMES.get(d['sect'],'通用')+' · '+d['type']+' · '+d['rarity'],(720,197),20,JADE,True)
            self.art((592,247,256,185),d['sect'])
            self.panel((163,465,523,227),PANEL,EDGE)
            self.panel((750,465,523,227),PANEL,GOLD)
            self.label('原始 · 灵力 '+str(d['cost']),(187,481),24,WHITE)
            self.wrap(d['desc'],187,539,473,22,WHITE,34)
            self.label('升级 · 灵力 '+str(d['cost']),(774,481),24,GOLD)
            self.wrap(d['up'],774,539,473,22,WHITE,34)
            self.label(d.get('flavor','问道不问归途。'),(720,748),23,MUTED,True,True)
            self.button((1111,108,206,44),'返回卡牌列表',self.close_detail,small=True)
        elif kind == 'relics':
            relics = self.game.s['relics']
            self.label('随 身 灵 宝',(720,130),31,GOLD,True,True)
            pages = max(1,math.ceil(len(relics)/8))
            self.page = min(self.page,pages-1)
            for i,rid in enumerate(relics[self.page*8:self.page*8+8]):
                r = (127+(i%2)*604,210+(i//2)*132,576,113)
                self.panel(r,PANEL,EDGE)
                d = RELIC_INDEX[rid]
                self.label(d['name']+' · '+d['rarity'],(r[0]+23,r[1]+15),23,GOLD)
                self.wrap(d['effect'],r[0]+23,r[1]+56,527,18,WHITE,28)
            if not relics:
                self.label('尚未获得遗物。精英、遗宝、商店与奇遇均可寻得。',(720,446),23,MUTED,True)
            self.button((380,782,154,44),'上一页',lambda:setattr(self,'page',max(0,self.page-1)),self.page>0,small=True)
            self.label(f'{self.page+1} / {pages}',(720,805),17,MUTED,True)
            self.button((907,782,154,44),'下一页',lambda:setattr(self,'page',min(pages-1,self.page+1)),self.page<pages-1,small=True)
            self.button((1155,110,170,43),'返回',lambda:setattr(self,'modal',None),small=True)
        elif kind == 'guide':
            self.label('修 行 指 南',(720,135),36,GOLD,True,True)
            lines = [
                ('一 · 仙路', '每局 3 重、每重 12 步。点左侧金色节点前进；斗法后选牌，静室中回血或升级。'),
                ('二 · 回合', '每回合恢复 3 点灵力、抽 5 张牌。先看敌方意图，再点击出牌；空格结束回合。'),
                ('三 · 格挡', '格挡先承受敌方攻击，下个玩家回合清零。护体每层减少 1 点攻击伤害，战斗内持续。'),
                ('四 · 状态', '意境（剑修称剑意）每层使每次攻击 +1。虚弱使伤害 -40%，易伤使伤害 +20%，每敌方行动后减 1 层。'),
                ('五 · 毒火', '回合结束每层中毒造成 2 点、灼烧造成 3 点气血伤害，随后减 1 层。绕过格挡。'),
                ('六 · 卡牌', '消耗只移出本场战斗，下场仍在卡组。持续功法同名不叠加。每回合最多 40 次出牌，手牌最多 10 张。'),
                ('七 · 存档', '每次行动自动存档。退出后点击继续修行；新局会覆盖旧局。F11 全屏，M 静音，Esc 暂停。'),
            ]
            for i,(title,body) in enumerate(lines):
                y = 212+i*82
                self.label(title,(139,y),23,JADE)
                self.wrap(body,294,y,1005,19,WHITE,28)
            self.button((1137,798,177,43),'明白了',lambda:setattr(self,'modal',None),accent=True,small=True)
        elif kind == 'pause':
            self.label('静 心',(720,225),53,GOLD,True,True)
            self.label('当前修行已自动保存。',(720,310),22,MUTED,True)
            self.button((550,375,340,61),'继续修行',lambda:setattr(self,'modal',None),accent=True)
            self.button((550,463,340,61),'声音：'+('关闭' if self.muted else '开启'),lambda:setattr(self,'muted',not self.muted))
            self.button((550,551,340,61),'回到山门',self.to_menu)
            self.button((550,639,340,61),'保存并退出',lambda:setattr(self,'running',False))
        elif kind == 'confirm':
            self.label('另 开 仙 路',(720,281),44,GOLD,True,True)
            self.label('新修行将覆盖上一局存档。',(720,389),23,WHITE,True)
            self.button((402,502,283,64),'返回',lambda:setattr(self,'modal',None))
            self.button((755,502,283,64),'确认开始新局',self.new_run,accent=True)

    def to_menu(self):
        self.menu, self.modal = True, None

    def draw(self):
        self.canvas.blit(self.background,(0,0))
        self.hits = []
        if self.menu:
            self.draw_menu()
        else:
            self.draw_top()
            self.draw_map()
            mode = self.game.s['mode']
            if mode != self.last_mode:
                self.page = 0
                self.last_mode = mode
            {'map':self.draw_map_scene,'battle':self.draw_battle,'reward':self.draw_reward,
             'event':self.draw_event,'rest':self.draw_rest,'shop':self.draw_shop,
             'treasure':self.draw_treasure,'picker':self.draw_picker,'result':self.draw_result}[mode]()
        if self.modal:
            self.draw_modal()
        if self.game.notice:
            self.notice(self.game.notice)
            self.game.notice = ''
        if self.toast and time.monotonic()<self.toast_until:
            self.panel((340,30,760,53),(40,63,54),JADE)
            self.label(self.toast,(720,56),18,WHITE,True)
        if time.monotonic()<self.flash_until:
            pygame.draw.rect(self.canvas,self.flash_color,(325,103,1095,783),2,border_radius=14)
        now = time.monotonic()
        for x,y,vx,vy,end in self.particles:
            if now<end:
                dt = .5-(end-now)
                pygame.draw.circle(self.canvas,self.flash_color,(int(x+vx*dt),int(y+vy*dt)),max(1,int((end-now)*7)))
        sw,sh = self.screen.get_size()
        scale = min(sw/W,sh/H)
        size = (max(1,int(W*scale)),max(1,int(H*scale)))
        self.offset = ((sw-size[0])//2,(sh-size[1])//2)
        self.scale = scale
        self.screen.fill((6,15,18))
        self.screen.blit(pygame.transform.smoothscale(self.canvas,size),self.offset)
        pygame.display.flip()

    def key(self, key):
        if key==pygame.K_F11:
            self.fullscreen = not self.fullscreen
            self.screen = pygame.display.set_mode((0,0) if self.fullscreen else (1280,800),pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
        elif key==pygame.K_m:
            self.muted = not self.muted
            self.notice('声音已关闭' if self.muted else '声音已开启')
        elif key==pygame.K_ESCAPE:
            if self.modal:
                if self.modal == 'card':self.close_detail()
                else:self.modal = None
            elif not self.menu:
                self.open_modal('pause')
        elif not self.menu and not self.modal and self.game.s['mode']=='battle':
            if key == pygame.K_SPACE:
                self.act(self.game.end_turn)
            elif pygame.K_1 <= key <= pygame.K_5:
                self.act(self.game.play,self.hand_page*5+key-pygame.K_1)
            elif key in (pygame.K_LEFT,pygame.K_RIGHT):
                self.hand_page = max(0,min((len(self.game.battle['hand'])-1)//5,self.hand_page+(-1 if key==pygame.K_LEFT else 1)))

    def run(self):
        self.draw()
        while self.running:
            mx,my = pygame.mouse.get_pos()
            self.mouse = ((mx-self.offset[0])/self.scale,(my-self.offset[1])/self.scale)
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    self.running = False
                elif event.type==pygame.KEYDOWN:
                    self.key(event.key)
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    self.mouse = ((event.pos[0]-self.offset[0])/self.scale,(event.pos[1]-self.offset[1])/self.scale)
                    for rect,action in reversed(self.hits):
                        if rect.collidepoint(self.mouse):
                            self.sound()
                            action()
                            break
                elif event.type==pygame.MOUSEWHEEL and self.modal in ('deck','codex','relics'):
                    self.page = max(0,self.page-event.y)
            self.draw()
            hovering = any(rect.collidepoint(self.mouse) for rect,_ in self.hits)
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hovering else pygame.SYSTEM_CURSOR_ARROW)
            self.clock.tick(60)
        self.game.save()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--save-dir')
    parser.add_argument('--smoke-dir')
    args = parser.parse_args()
    app = App(args.save_dir)
    if args.smoke_dir:
        target = Path(args.smoke_dir)
        target.mkdir(parents=True,exist_ok=True)
        app.draw()
        pygame.image.save(app.canvas,target/'menu.png')
        app.game.start('sword',seed=101)
        app.menu=False
        for mode in ('map','battle','reward','event','rest','shop','treasure','picker','result'):
            app.game.s['mode'] = 'map'
            if mode in ('battle','reward'):
                app.game.start_battle('battle')
                if mode=='reward': app.game.win_battle()
            elif mode=='event':
                from engine import EVENTS
                app.game.s.update(mode='event',event=EVENTS[0])
            elif mode=='shop': app.game.make_shop()
            elif mode=='treasure': app.game.s.update(mode='treasure',treasure='jade')
            elif mode=='picker': app.game.s.update(mode='picker',picker=dict(kind='upgrade',origin='rest'))
            elif mode=='result': app.game.end_run(True)
            else: app.game.s['mode']=mode
            app.draw()
            pygame.image.save(app.canvas,target/(mode+'.png'))
        for kind in ('codex','deck','guide','pause','confirm','relics'):
            app.open_modal(kind)
            app.draw()
            pygame.image.save(app.canvas,target/(kind+'.png'))
        pygame.quit()
        return
    app.run()


if __name__=='__main__':
    try:
        main()
    except Exception:
        directory = save_directory()
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'error.log').write_text(traceback.format_exc(),'utf-8')
        raise
