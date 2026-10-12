"""太虚问道：纯 Python 规则内核；界面与打包均不依赖浏览器。"""
from __future__ import annotations

import copy
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ASSET_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
CONTENT = json.loads((ASSET_ROOT / 'content.json').read_text(encoding='utf-8'))
CARDS = {c['id']: c for c in CONTENT['cards']}
SECTS = CONTENT['sects']
SECT_NAMES = {s['id']: s['name'] for s in SECTS}
NODE_NAMES = {'battle': '斗法', 'elite': '精英', 'event': '奇遇', 'shop': '灵宝铺',
              'rest': '静室', 'treasure': '遗宝', 'boss': '首领'}
REALMS = ('练气', '筑基', '金丹', '元婴', '化神')
RELICS = [
    dict(id='jade', name='青玉佩', rarity='普通', effect='最大气血 +8，并回复 8 点气血。'),
    dict(id='dragon', name='龙纹玉简', rarity='稀有', effect='每回合恢复的灵力 +1，上限 6。'),
    dict(id='incense', name='定神香', rarity='普通', effect='每场战斗首回合多抽 1 张牌。'),
    dict(id='tiger', name='虎魄石', rarity='稀有', effect='每次攻击命中伤害 +2。'),
    dict(id='lotus', name='并蒂莲', rarity='稀有', effect='每个节点完成后回复 3 点气血。'),
    dict(id='mirror', name='照心镜', rarity='传说', effect='每场战斗首次受到攻击的气血伤害减半。'),
    dict(id='shell', name='玄龟甲片', rarity='首领', effect='每回合开始获得 3 点格挡。'),
    dict(id='fox', name='九尾灵契', rarity='首领', effect='每场战斗首次打出身法，获得 1 点灵力。'),
    dict(id='pearl', name='夜明灵珠', rarity='普通', effect='每场战斗开始获得 1 层意境。'),
    dict(id='bell', name='清心铃', rarity='普通', effect='每场战斗首次收到减益时，将层数减少 1。'),
    dict(id='book', name='残卷心经', rarity='普通', effect='每场战斗首次打出功法，抽 1 张牌。'),
    dict(id='herb', name='千年灵芝', rarity='普通', effect='调息额外回复 6 点气血。'),
    dict(id='coin', name='聚宝钱', rarity='普通', effect='普通与精英战斗奖励额外获得 6 灵石。'),
    dict(id='flint', name='离火石', rarity='普通', effect='每场战斗首次攻击，施加 1 层灼烧。'),
    dict(id='ribbon', name='逐云带', rarity='普通', effect='每场战斗首回合获得 4 点格挡。'),
    dict(id='ink', name='朱砂砚', rarity='稀有', effect='你施加的易伤额外增加 1 层。'),
    dict(id='flask', name='玉净瓶', rarity='稀有', effect='卡牌回复气血时额外回复 2 点。'),
    dict(id='stone', name='镇山石', rarity='稀有', effect='每场战斗开始获得 2 层护体。'),
    dict(id='bead', name='菩提子', rarity='稀有', effect='跳过奖励时额外获得 5 灵石。'),
    dict(id='map', name='洞天残图', rarity='稀有', effect='进入新楼层时获得 30 灵石。'),
    dict(id='brush', name='点睛笔', rarity='稀有', effect='获得卡牌时有 25% 概率直接升级。'),
    dict(id='soul', name='养魂木', rarity='传说', effect='每场战斗前两次失去气血后，抽 1 张牌。'),
    dict(id='hourglass', name='逆流沙漏', rarity='传说', effect='每场战斗第一回合灵力 +1。'),
    dict(id='crown', name='太虚道冠', rarity='传说', effect='每回合打出第 5 张牌时，获得 5 点格挡。'),
]
RELIC_INDEX = {r['id']: r for r in RELICS}

# 事件效果用纯数据描述，可序列化并在未完成事件中继续游戏。
EVENTS = [
    dict(name='问剑石壁', story='无字石壁上，一道剑痕三百年未散。指尖触石，旧日剑修的低语便响在耳边。', choices=[
        ('领悟剑痕', '升级一张卡牌，获得 1 层初始意境。', {'upgrade': 1, 'insight': 1}),
        ('取走石屑', '获得 35 灵石，失去 5 点气血。', {'gold': 35, 'hp': -5})]),
    dict(name='丹炉遗火', story='荒庙中的丹炉仍有余温。半颗金丹悬在炉底，时而透出雷光。', choices=[
        ('吞服金丹', '回复 20 点气血，加入天劫·问心。', {'hp': 20, 'card': 'tribulation-oath'}),
        ('取下炉芯', '获得遗物「定神香」。', {'relic': 'incense'}),
        ('炼化业火', '获得 25 灵石，加入天劫·业火。', {'gold': 25, 'card': 'tribulation-flame'})]),
    dict(name='渡劫商旅', story='商旅在云海边摆摊，铃铛里封着一段不属于你的记忆。', choices=[
        ('以灵石换忆', '支付 25 灵石，升级一张卡牌。', {'cost': 25, 'upgrade': 1}),
        ('以血换忆', '失去 10 点气血，获得本流派稀有牌。', {'hp': -10, 'rarity': '稀有'})]),
    dict(name='心魔叩门', story='夜半门外是另一个你。它说，只要开门，便替你挡下一劫。', choices=[
        ('开门', '获得「照心镜」，加入天劫·九霄雷。', {'relic': 'mirror', 'card': 'thunder-tribulation'}),
        ('闭门静坐', '回复 12 点气血，获得 1 层初始意境。', {'hp': 12, 'insight': 1})]),
    dict(name='灵泉三问', story='泉水问你：所求为何？水面映出三条不同的路。', choices=[
        ('求财', '获得 40 灵石，下场敌人气血 +15%。', {'gold': 40, 'enemyBoost': 1.15}),
        ('求稳', '最大气血 +5，回复 10 点气血。', {'maxHp': 5, 'hp': 10}),
        ('求道', '失去 12 点气血，获得本流派传说牌。', {'hp': -12, 'rarity': '传说'})]),
    dict(name='断桥残碑', story='碑上写着「退一步，海阔天高」。桥下雷云正翻涌着。', choices=[
        ('步入雷云', '失去 16 点气血，获得「龙纹玉简」。', {'hp': -16, 'relic': 'dragon'}),
        ('绕路', '获得 18 灵石。', {'gold': 18})]),
    dict(name='白鹿报恩', story='白鹿叼来一颗沾露的朱果，眼神像从未见过杀伐。', choices=[
        ('收下朱果', '回复 25 点气血。', {'hp': 25}),
        ('以灵石回礼', '支付 18 灵石，获得「青玉佩」。', {'cost': 18, 'relic': 'jade'})]),
    dict(name='古修棋局', story='黑白棋子摆出一局未完的天道。落子后，因果便不再由你掌控。', choices=[
        ('落黑子', '获得 30 灵石，加入心魔焚身。', {'gold': 30, 'card': 'demon-flame'}),
        ('落白子', '选择移除一张卡牌。', {'remove': 1})]),
    dict(name='月下听潮', story='潮声从九天之上来，一枚刻着「静」字的贝壳落在脚边。', choices=[
        ('静坐', '下场战斗首回合灵力 +1。', {'nextQi': 1}),
        ('拾贝', '失去 6 点气血，获得 2 层初始意境。', {'hp': -6, 'insight': 2}),
        ('潜入寒潮', '回复 10 点气血，加入天劫·寒渊。', {'hp': 10, 'card': 'tribulation-frost'})]),
    dict(name='药王谷门人', story='弟子拦住去路：你的气息里有一味药，正是他缺的。', choices=[
        ('交换药方', '选择移除一张牌，再回复 15 点气血。', {'remove': 1, 'hp': 15}),
        ('婉拒', '获得 22 灵石。', {'gold': 22})]),
    dict(name='天河落星', story='一颗星子落在掌心，温度像刚刚熄灭的火。', choices=[
        ('炼入兵刃', '选择升级一张卡牌。', {'upgrade': 1}),
        ('放归天河', '获得 40 灵石。', {'gold': 40})]),
    dict(name='无名碑林', story='每块碑都刻着一个失败者的名字，最深处的一块却空着。', choices=[
        ('刻下自己的名', '最大气血 +10，加入天劫·九霄雷。', {'maxHp': 10, 'hp': 10, 'card': 'thunder-tribulation'}),
        ('转身离去', '获得「并蒂莲」。', {'relic': 'lotus'}),
        ('抹去前世', '获得 35 灵石，加入天劫·逆命。', {'gold': 35, 'card': 'tribulation-fate'})]),
]


def save_directory() -> Path:
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'TaixuAscension'


def definition(card):
    return CARDS[card['id']]


def effects(card):
    base = copy.deepcopy(definition(card)['effect'])
    if card.get('upgraded'):
        base.update(definition(card).get('upgrade', {}))
    return base


def text(card):
    d = definition(card)
    return d['up'] if card.get('upgraded') else d['desc']


class Game:
    SAVE_VERSION = 1

    def __init__(self, save_dir=None):
        self.save_dir = Path(save_dir) if save_dir else save_directory()
        self.rng = random.Random()
        self.s = None
        self.notice = ''
        self.profile = {'runs': 0, 'wins': 0, 'discovered': []}
        self.load_error = ''
        try:
            self.profile.update(json.loads((self.save_dir / 'profile.json').read_text('utf-8')))
        except (OSError, ValueError, TypeError):
            pass

    @property
    def has_save(self):
        return (self.save_dir / 'run.json').is_file()

    @property
    def battle(self):
        return self.s.get('battle') if self.s else None

    def start(self, sect, seed=None):
        if sect not in SECT_NAMES:
            raise ValueError('未知道统')
        seed = seed if seed is not None else random.SystemRandom().randrange(1, 2147483647)
        self.rng.seed(seed)
        self.s = dict(sect=sect, seed=seed, floor=1, realm=0, hp=76, maxHp=76, maxQi=3,
                      insight=0, gold=60, deck=[], relics=[], map=[], row=0, mode='map',
                      visited=[], battle=None, cleared=0, enemyBoost=1, nextQi=0,
                      started=time.time(), end=None, reward=None)
        starter = next(x['starter'] for x in SECTS if x['id'] == sect)
        for card_id in starter:
            self.add_card(card_id, roll_upgrade=False)
        self.generate_map()
        self.profile['runs'] += 1
        self.save()
        return True

    def generate_map(self):
        s = self.s
        rows = []
        for row in range(12):
            if row == 0:
                types = ['battle']
            elif row == 11:
                types = ['boss']
            elif row == 10:
                types = ['rest']
            elif row == 8:
                types = ['treasure']
            elif row in (2, 4, 7):
                types = self.rng.sample(['battle', 'event', 'shop', 'elite'], 3)
            elif row == 5:
                types = ['rest', 'event']
            elif row == 9:
                types = ['battle', 'elite']
            else:
                types = [self.rng.choice(['battle', 'battle', 'event']), 'event']
            rows.append([dict(type=t, id=f'{s["floor"]}-{row}-{i}', label=NODE_NAMES[t])
                         for i, t in enumerate(types)])
        s.update(map=rows, row=0, visited=[], mode='map', battle=None)

    def choose_node(self, row, index):
        s = self.s
        if s['mode'] != 'map' or row != s['row'] or not 0 <= index < len(s['map'][row]):
            return False
        node = s['map'][row][index]
        s['node'] = node
        s['visited'].append(node['id'])
        t = node['type']
        if t in ('battle', 'elite', 'boss'):
            self.start_battle(t)
        elif t == 'event':
            s.update(mode='event', event=copy.deepcopy(self.rng.choice(EVENTS)))
        elif t == 'shop':
            self.make_shop()
        elif t == 'rest':
            s['mode'] = 'rest'
        elif t == 'treasure':
            relic = self.random_relic()
            s.update(mode='treasure', treasure=relic)
            self.obtain_relic(relic)
            s['gold'] += 25
        self.save()
        return True

    def start_battle(self, kind):
        s = self.s
        floor = str(s['floor'])
        enemy = copy.deepcopy(CONTENT['bosses'][floor] if kind == 'boss'
                              else self.rng.choice(CONTENT['enemies'][floor]))
        if kind == 'elite':
            enemy['name'] = '精英 · ' + enemy['name']
            enemy['hp'] = round(enemy['hp'] * 1.35)
            enemy['damage'] = round(enemy['damage'] * 1.2)
            enemy['pattern'].append('elitePulse')
        enemy['hp'] = round(enemy['hp'] * s['enemyBoost'])
        enemy.update(maxHp=enemy['hp'], turn=0, phase=1, block=0,
                     statuses=dict(poison=0, burn=0, vulnerable=0, weak=0), weakPower=.4)
        s['enemyBoost'] = 1
        draw = copy.deepcopy(s['deck'])
        self.rng.shuffle(draw)
        s['battle'] = dict(kind=kind, enemy=enemy, draw=draw, discard=[], exhaust=[], hand=[],
                           qi=0, turn=0, block=0, nextBlock=0, powers={}, mood=s['insight'],
                           statuses=dict(poison=0, burn=0, vulnerable=0, weak=0, armor=0, heart=0),
                           played=0, turnPlayed=0, healingTriggers=0, damageTotal=0, soulDraws=0,
                           mirrorUsed=False, bellUsed=False, flintUsed=False, foxUsed=False,
                           bookUsed=False, dodge=0, dodgeTemp=0, lockBlock=False,
                           log=['战斗开始。先观察意图，再决定你的落子。'])
        if 'pearl' in s['relics']:
            self.battle['mood'] += 1
        if 'stone' in s['relics']:
            self.battle['statuses']['armor'] += 2
        s['mode'] = 'battle'
        self.begin_turn()

    def log(self, line):
        if self.battle:
            self.battle['log'] = (self.battle['log'] + [line])[-20:]

    def begin_turn(self):
        s, b = self.s, self.battle
        b['turn'] += 1
        b.update(qi=s['maxQi'], block=b['nextBlock'], nextBlock=0, turnPlayed=0,
                 healingTriggers=0, lockBlock=False)
        b['block'] += 3 if 'shell' in s['relics'] else 0
        if b['turn'] == 1:
            b['qi'] = min(6, b['qi'] + s['nextQi'] + int('hourglass' in s['relics']))
            s['nextQi'] = 0
            b['block'] += 4 if 'ribbon' in s['relics'] else 0
        self.draw(5 + int(b['turn'] == 1 and 'incense' in s['relics']))
        self.log(f'第 {b["turn"]} 回合 · {self.intent()["text"]}')

    def draw(self, amount):
        b = self.battle
        for _ in range(amount):
            if len(b['hand']) >= 10:
                break
            if not b['draw']:
                b['draw'], b['discard'] = b['discard'], []
                self.rng.shuffle(b['draw'])
            if not b['draw']:
                break
            b['hand'].append(b['draw'].pop())

    def intent(self, forecast=True):
        b = self.battle
        e = b['enemy']
        action = e['pattern'][e['turn'] % len(e['pattern'])]
        projected_hp = e['hp'] - (e['statuses']['poison']*2 + e['statuses']['burn']*3 if forecast else 0)
        enters_phase_two = b['kind'] == 'boss' and e['phase'] == 1 and 0 < projected_hp <= e['maxHp']/2
        base = e['damage'] + (4 if e['phase'] == 2 or enters_phase_two else 0)
        base += max(0, b['turn'] - 15) * 2
        damage = base + {'blockAttack': 3, 'quake': 8, 'swordRain': 10,
                         'tribulation': 12, 'elitePulse': 5}.get(action, 0)
        if e['statuses']['weak']:
            damage = math.floor(damage * (1 - e['weakPower']))
        if b['statuses']['vulnerable']:
            damage = math.floor(damage * 1.2)
        actions = dict(attack=f'攻击 {damage}', blockAttack=f'攻击 {damage} · 格挡 8',
                       swordRain=f'剑雨 {damage}', block='格挡 12', poison='中毒 +2',
                       burn='灼烧 +2', weak='虚弱 +1', vulnerable='易伤 +1',
                       quake=f'震岳 {damage}', illusion='幻象 · 格挡 16',
                       tribulation=f'天劫 {damage}', elitePulse=f'蓄势强攻 {damage}')
        return dict(action=action, damage=damage, text=actions[action],
                    attack=action in ('attack', 'blockAttack', 'swordRain', 'quake', 'tribulation', 'elitePulse'))

    def can_play(self, index):
        b = self.battle
        return bool(self.s and self.s['mode'] == 'battle' and b and
                    b['turnPlayed'] < 40 and 0 <= index < len(b['hand']) and
                    definition(b['hand'][index])['cost'] <= b['qi'])

    def play(self, index):
        if not self.can_play(index):
            return False
        s, b = self.s, self.battle
        card = b['hand'].pop(index)
        d, f = definition(card), effects(card)
        b['qi'] -= d['cost']
        b['played'] += 1
        b['turnPlayed'] += 1
        self.log('打出「' + d['name'] + (' +' if card['upgraded'] else '') + '」。')
        if f.get('selfDamage'):
            self.hurt(f['selfDamage'], attack=False)
            if s['hp'] <= 0:
                self.end_run(False)
                return True
        if f.get('tribulation'):
            b['block'] = 0
            b['lockBlock'] = True
        if f.get('damage'):
            damage = f['damage']
            if b['mood'] and f.get('ifMood'):
                damage += f['ifMood']
            if b['block'] >= 8:
                damage += f.get('blockDamage', 0)
            damage += b['statuses']['heart'] * f.get('heartBonus', 0)
            self.damage(damage, f.get('pierce', 0))
        for _ in range(f.get('multi', 0)):
            self.damage(f['multiDamage'])
            if self.rng.random() < (.4 if card['upgraded'] else .25):
                self.enemy_status('vulnerable', 1)
        if f.get('comboDamage') and b['enemy']['statuses']['burn'] >= 3:
            self.damage(f['comboDamage'])
        if 'blockStrike' in f:
            self.damage(b['block'] + f['blockStrike'])
            b['block'] //= 2
        if f.get('block') and not b['lockBlock']:
            b['block'] += f['block']
        b['nextBlock'] += f.get('nextBlock', 0)
        if f.get('heal'):
            self.heal(f['heal'] + (f.get('lowHeal', 0) if s['hp'] * 2 < s['maxHp'] else 0), card=True)
        if f.get('draw'):
            self.draw(f['draw'])
        b['mood'] = min(30, b['mood'] + f.get('mood', 0))
        for status in ('burn', 'poison', 'vulnerable', 'weak'):
            if f.get(status):
                self.enemy_status(status, f[status])
                if status == 'weak':
                    b['enemy']['weakPower'] = f.get('weakPower', .4)
        b['qi'] = min(6, b['qi'] + f.get('gainQi', 0))
        power = f.get('passive')
        if power == 'dodge':
            b['dodge' if card['upgraded'] else 'dodgeTemp'] += 2 if card['upgraded'] else 1
        elif power:
            already_active = power in b['powers']
            b['powers'][power] = b['powers'].get(power, False) or bool(card['upgraded'])
            if power == 'demonHeart' and not already_active:
                b['damageTotal'] = 0
        if 'comboMood' in b['powers'] and b['played'] % (2 if b['powers']['comboMood'] else 3) == 0:
            b['mood'] = min(30, b['mood'] + 1)
        if 'fox' in s['relics'] and d['type'] == '身法' and not b['foxUsed']:
            b['foxUsed'] = True
            b['qi'] = min(6, b['qi'] + 1)
        if 'book' in s['relics'] and d['type'] == '功法' and not b['bookUsed']:
            b['bookUsed'] = True
            self.draw(1)
        if 'crown' in s['relics'] and b['turnPlayed'] == 5 and not b['lockBlock']:
            b['block'] += 5
        if power or f.get('exhaust') or d['rarity'] == '天劫':
            b['exhaust'].append(card)
        else:
            b['discard'].append(card)
        self.check_boss_phase()
        if b['enemy']['hp'] <= 0:
            self.win_battle()
        self.save()
        return True

    def enemy_status(self, status, amount):
        if status == 'vulnerable' and 'ink' in self.s['relics']:
            amount += 1
        self.battle['enemy']['statuses'][status] += amount

    def damage(self, amount, pierce=0):
        s, b = self.s, self.battle
        e = b['enemy']
        damage = amount + b['mood'] + int('tiger' in s['relics']) * 2
        if b['statuses']['weak']:
            damage = math.floor(damage * .6)
        if e['statuses']['vulnerable']:
            damage = math.floor(damage * 1.2)
        blocked = min(max(0, e['block'] - pierce), damage)
        e['block'] -= blocked
        dealt = max(0, damage - blocked)
        e['hp'] = max(0, e['hp'] - dealt)
        self.log(f'造成 {dealt} 点伤害' + (f'，抵挡 {blocked} 点。' if blocked else '。'))
        if 'flint' in s['relics'] and not b['flintUsed']:
            b['flintUsed'] = True
            self.enemy_status('burn', 1)

    def hurt(self, amount, attack=True):
        s, b = self.s, self.battle
        damage = amount
        if attack:
            damage = max(0, damage - b['statuses']['armor'])
            blocked = min(b['block'], damage)
            b['block'] -= blocked
            damage -= blocked
            if damage > 0 and (b['dodge'] or b['dodgeTemp']):
                key = 'dodgeTemp' if b['dodgeTemp'] else 'dodge'
                b[key] -= 1
                damage = 0
                self.log('纸人替身挡下了这次伤害。')
            if damage > 0 and 'mirror' in s['relics'] and not b['mirrorUsed']:
                b['mirrorUsed'] = True
                damage = math.ceil(damage / 2)
                self.log('照心镜：首次伤害减半。')
        s['hp'] = max(0, s['hp'] - damage)
        if damage:
            self.log(f'失去 {damage} 点气血。')
            b['damageTotal'] += damage
            if 'demonHeart' in b['powers']:
                threshold = 8 if b['powers']['demonHeart'] else 10
                times, b['damageTotal'] = divmod(b['damageTotal'], threshold)
                b['statuses']['heart'] += times
                b['qi'] = min(6, b['qi'] + times)
            if 'soul' in s['relics'] and b['soulDraws'] < 2:
                b['soulDraws'] += 1
                self.draw(1)
        return damage

    def heal(self, amount, card=False):
        s = self.s
        if card and 'flask' in s['relics']:
            amount += 2
        healed = min(amount, s['maxHp'] - s['hp'])
        s['hp'] += healed
        if self.battle:
            self.log(f'回复 {healed} 点气血。')
            b = self.battle
            if card and healed > 0 and 'healQi' in b['powers']:
                cap = 2 if b['powers']['healQi'] else 1
                if b['healingTriggers'] < cap:
                    b['qi'] = min(6, b['qi'] + 1)
                    b['healingTriggers'] += 1
        return healed

    def check_boss_phase(self):
        b = self.battle
        e = b['enemy']
        if b['kind'] == 'boss' and e['phase'] == 1 and 0 < e['hp'] <= e['maxHp'] / 2:
            e['phase'] = 2
            self.log('首领破入第二阶段：后续攻击伤害 +4。')

    def end_turn(self):
        s, b = self.s, self.battle
        if not s or s['mode'] != 'battle':
            return False
        b['discard'].extend(b['hand'])
        b['hand'] = []
        if 'armorAura' in b['powers'] and b['block'] >= (8 if b['powers']['armorAura'] else 10):
            b['statuses']['armor'] += 1
        for status, damage in (('poison', 2), ('burn', 3)):
            if b['statuses'][status]:
                self.hurt(b['statuses'][status] * damage, attack=False)
                b['statuses'][status] -= 1
        if s['hp'] <= 0:
            self.end_run(False)
            self.save()
            return True
        e = b['enemy']
        for status, damage in (('poison', 2), ('burn', 3)):
            if e['statuses'][status]:
                e['hp'] = max(0, e['hp'] - e['statuses'][status] * damage)
                e['statuses'][status] -= 1
        if e['hp'] <= 0:
            self.win_battle()
            self.save()
            return True
        self.check_boss_phase()
        intent = self.intent(forecast=False)
        action = intent['action']
        for status in ('weak', 'vulnerable'):
            b['statuses'][status] = max(0, b['statuses'][status] - 1)
        e['block'] = 0
        if intent['attack']:
            self.hurt(intent['damage'])
        if action in ('block', 'blockAttack', 'illusion'):
            e['block'] = {'block': 12, 'blockAttack': 8, 'illusion': 16}[action]
        if action in ('poison', 'burn', 'weak', 'vulnerable'):
            count = 2 if action in ('poison', 'burn') else 1
            if 'bell' in s['relics'] and not b['bellUsed']:
                b['bellUsed'] = True
                count -= 1
            b['statuses'][action] += count
            self.log(f'敌人施加 {count} 层' + {'poison': '中毒', 'burn': '灼烧', 'weak': '虚弱', 'vulnerable': '易伤'}[action] + '。')
        e['turn'] += 1
        e['statuses']['weak'] = max(0, e['statuses']['weak'] - 1)
        e['statuses']['vulnerable'] = max(0, e['statuses']['vulnerable'] - 1)
        b['dodgeTemp'] = 0
        if s['hp'] <= 0:
            self.end_run(False)
        else:
            self.begin_turn()
        self.save()
        return True

    def win_battle(self):
        if self.s['mode'] != 'battle':
            return
        s, b = self.s, self.battle
        gold = {'battle': 18, 'elite': 32, 'boss': 45}[b['kind']]
        if b['kind'] != 'boss' and 'coin' in s['relics']:
            gold += 6
        s['gold'] += gold
        choices = self.reward_cards(3, rare=b['kind'] != 'battle')
        relic = None
        if b['kind'] == 'elite':
            relic = self.random_relic()
        if b['kind'] == 'boss' and s['floor'] < 3:
            relic = 'shell' if s['floor'] == 1 else 'fox'
        if relic:
            self.obtain_relic(relic)
        s.update(mode='reward', reward=dict(cards=choices, gold=gold, relic=relic,
                                            boss=b['kind'] == 'boss'))

    def reward_cards(self, count=3, rare=False):
        s = self.s
        pool = [c for c in CARDS.values() if c['sect'] in ('neutral', s['sect'])
                and c['rarity'] != '天劫' and (s['realm'] >= 2 or c['rarity'] != '传说')]
        weights = {'基础': 15, '进阶': 55, '稀有': 24 if rare else 26, '传说': 6 if rare else 4}
        result = []
        for _ in range(min(count, len(pool))):
            rarities = [r for r in weights if any(c['rarity'] == r for c in pool)]
            rarity = self.rng.choices(rarities, weights=[weights[r] for r in rarities], k=1)[0]
            c = self.rng.choice([c for c in pool if c['rarity'] == rarity])
            result.append(dict(id=c['id'], upgraded=False))
            pool.remove(c)
        return result

    def take_reward(self, index=None):
        s = self.s
        if s['mode'] != 'reward':
            return False
        reward = s['reward']
        if index is None:
            s['gold'] += 12 + (5 if 'bead' in s['relics'] else 0)
        elif 0 <= index < len(reward['cards']):
            self.add_card(reward['cards'][index]['id'])
        else:
            return False
        if reward['boss']:
            s['cleared'] += 1
            if s['floor'] == 3:
                self.ascend(4)
                self.end_run(True)
            else:
                self.ascend(s['floor'] + 1)
                s['floor'] += 1
                self.heal(20)
                if 'map' in s['relics']:
                    s['gold'] += 30
                self.generate_map()
        else:
            self.finish_node()
        self.save()
        return True

    def ascend(self, realm):
        if realm > self.s['realm']:
            self.s['realm'] = realm
            self.s['maxHp'] += 8
            self.heal(8)
            self.notice = '破境成功 · ' + REALMS[realm] + '，最大气血 +8'

    def finish_node(self):
        s = self.s
        s['cleared'] += 1
        s['row'] += 1
        if s['floor'] == 1 and s['row'] == 6:
            self.ascend(1)
        if 'lotus' in s['relics']:
            self.heal(3)
        s['mode'] = 'map'
        s['battle'] = None
        self.save()
        return True

    def random_relic(self):
        pool = [r for r in RELICS if r['id'] not in self.s['relics'] and r['rarity'] != '首领']
        return self.rng.choice(pool)['id'] if pool else None

    def obtain_relic(self, relic):
        if not relic:
            self.s['gold'] += 25
            return
        if relic in self.s['relics']:
            self.s['gold'] += 15
            return
        self.s['relics'].append(relic)
        if relic == 'jade':
            self.s['maxHp'] += 8
            self.heal(8)
        elif relic == 'dragon':
            self.s['maxQi'] = min(6, self.s['maxQi'] + 1)
        self.notice = '获得遗物 · ' + RELIC_INDEX[relic]['name']

    def add_card(self, card_id, roll_upgrade=True):
        upgraded = roll_upgrade and 'brush' in self.s['relics'] and self.rng.random() < .25
        self.s['deck'].append(dict(id=card_id, upgraded=bool(upgraded)))
        if card_id not in self.profile['discovered']:
            self.profile['discovered'].append(card_id)

    def make_shop(self):
        self.s['mode'] = 'shop'
        cards = self.reward_cards(3, rare=True)
        prices = {'基础': 25, '进阶': 38, '稀有': 75, '传说': 115}
        self.s['shop'] = [dict(card=c, price=prices[definition(c)['rarity']], bought=False) for c in cards]
        self.s['shopRelic'] = dict(id=self.random_relic(), price=85, bought=False)
        self.s['shopRemoved'] = False

    def buy(self, index):
        if self.s['mode'] != 'shop':
            return False
        offer = self.s['shop'][index]
        if offer['bought'] or self.s['gold'] < offer['price']:
            return False
        self.s['gold'] -= offer['price']
        offer['bought'] = True
        self.add_card(offer['card']['id'])
        self.save()
        return True

    def buy_relic(self):
        if self.s['mode'] != 'shop':
            return False
        offer = self.s['shopRelic']
        if not offer['id'] or offer['bought'] or self.s['gold'] < offer['price']:
            return False
        self.s['gold'] -= offer['price']
        offer['bought'] = True
        self.obtain_relic(offer['id'])
        self.save()
        return True

    def event_choice(self, index):
        s = self.s
        if s['mode'] != 'event':
            return False
        effect = s['event']['choices'][index][2]
        if s['gold'] < effect.get('cost', 0) or s['hp'] <= -effect.get('hp', 0):
            return False
        s['gold'] += effect.get('gold', 0) - effect.get('cost', 0)
        s['maxHp'] += effect.get('maxHp', 0)
        s['hp'] = min(s['maxHp'], max(1, s['hp'] + effect.get('hp', 0)))
        s['insight'] = min(8, s['insight'] + effect.get('insight', 0))
        s['enemyBoost'] = effect.get('enemyBoost', s['enemyBoost'])
        s['nextQi'] += effect.get('nextQi', 0)
        if effect.get('card'):
            self.add_card(effect['card'])
        if effect.get('rarity'):
            pool = [c for c in CARDS.values() if c['sect'] == s['sect'] and c['rarity'] == effect['rarity']]
            self.add_card(self.rng.choice(pool)['id'])
        if effect.get('relic'):
            self.obtain_relic(effect['relic'])
        if effect.get('upgrade') or effect.get('remove'):
            s['picker'] = dict(kind='upgrade' if effect.get('upgrade') else 'remove', origin='event')
            s['mode'] = 'picker'
        else:
            self.finish_node()
        self.save()
        return True

    def rest(self, choice):
        if self.s['mode'] != 'rest':
            return False
        if choice == 'heal':
            amount = math.ceil(self.s['maxHp'] * .25) + (6 if 'herb' in self.s['relics'] else 0)
            restored = self.heal(amount)
            self.notice = f'调息完成 · 回复 {restored} 点气血'
            self.finish_node()
        elif choice == 'upgrade':
            self.s.update(mode='picker', picker=dict(kind='upgrade', origin='rest'))
        else:
            return False
        self.save()
        return True

    def begin_remove(self):
        s = self.s
        if s['mode'] != 'shop' or s['gold'] < 50 or s['shopRemoved'] or len(s['deck']) <= 5:
            return False
        s.update(mode='picker', picker=dict(kind='remove', origin='shop'))
        self.save()
        return True

    def pick_card(self, index):
        s = self.s
        if s['mode'] != 'picker' or not 0 <= index < len(s['deck']):
            return False
        p = s['picker']
        if p['kind'] == 'upgrade':
            if s['deck'][index]['upgraded']:
                return False
            s['deck'][index]['upgraded'] = True
        elif len(s['deck']) > 5:
            s['deck'].pop(index)
        else:
            return False
        if p['origin'] == 'shop':
            s['gold'] -= 50
            s['shopRemoved'] = True
            s['mode'] = 'shop'
        else:
            self.finish_node()
        self.save()
        return True

    def cancel_picker(self):
        if self.s['mode'] != 'picker':
            return False
        if self.s['picker']['origin'] == 'event':
            self.finish_node()
        else:
            self.s['mode'] = self.s['picker']['origin']
        self.save()
        return True

    def end_run(self, win):
        if self.s['mode'] == 'result':
            return
        self.s.update(mode='result', end=dict(win=win, duration=int(time.time() - self.s['started'])))
        if win:
            self.profile['wins'] += 1

    def save(self):
        if not self.s:
            return
        try:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            payload = dict(version=self.SAVE_VERSION, run=self.s, rng=self.rng.getstate())
            path = self.save_dir / 'run.json'
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)
            profile = self.save_dir / 'profile.json'
            temp_profile = profile.with_suffix('.tmp')
            temp_profile.write_text(json.dumps(self.profile, ensure_ascii=False), encoding='utf-8')
            temp_profile.replace(profile)
        except OSError:
            self.notice = '自动存档失败，请检查磁盘空间与目录权限。'

    def resume(self):
        try:
            data = json.loads((self.save_dir / 'run.json').read_text('utf-8'))
            if data['version'] != self.SAVE_VERSION:
                raise ValueError('存档版本不兼容')
            s = data['run']
            if s['sect'] not in SECT_NAMES or not 1 <= s['floor'] <= 3 or any(c['id'] not in CARDS for c in s['deck']):
                raise ValueError('存档内容无效')
            def tuples(x):
                return tuple(tuples(i) for i in x) if isinstance(x, list) else x
            self.rng.setstate(tuples(data['rng']))
            self.s = s
            return True
        except (OSError, ValueError, TypeError, KeyError):
            self.load_error = '无法读取当前存档。可以重新选择道统开始。'
            return False
