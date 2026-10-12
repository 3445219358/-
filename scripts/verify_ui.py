"""验证原生界面快捷键调度，使用独立存档和无显示器 SDL。"""
import os
import sys
import tempfile
from pathlib import Path

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
from main import App

with tempfile.TemporaryDirectory() as save_dir:
    app = App(save_dir)
    app.game.start('sword', seed=101)
    app.menu = False
    app.game.choose_node(0, 0)
    battle = app.game.battle
    battle['hand'] = [{'id': 'strike', 'upgraded': False}]
    battle['qi'] = 3
    hp_before = battle['enemy']['hp']
    app.key(pygame.K_1)
    assert battle['qi'] == 2
    assert battle['enemy']['hp'] == hp_before - 7
    assert len(battle['hand']) == 0
    turn_before = battle['turn']
    app.key(pygame.K_SPACE)
    assert battle['turn'] == turn_before + 1
    assert battle['qi'] == 3
    app.key(pygame.K_ESCAPE)
    assert app.modal == 'pause'
    app.key(pygame.K_SPACE)
    assert battle['turn'] == turn_before + 1
    app.key(pygame.K_ESCAPE)
    assert app.modal is None
    app.key(pygame.K_m)
    assert app.muted
    app.open_modal('deck')
    app.draw()
    app.inspect_card(app.game.s['deck'][0])
    app.draw()
    assert app.modal == 'card'
    app.key(pygame.K_ESCAPE)
    assert app.modal == 'deck'
    app.to_menu()
    app.open_modal('codex')
    app.draw()
    pygame.quit()

print('原生界面校验通过：数字键出牌、空格回合、暂停屏蔽、静音、卡牌详情与图鉴。')
