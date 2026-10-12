"""独立于显示器的规则回归：python -m unittest discover。"""
import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from engine import Game, CARDS, SECTS, EVENTS, RELICS, effects, definition


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = Game(self.tmp.name)
        self.g.start('sword', seed=101)

    def tearDown(self):
        self.tmp.cleanup()

    def battle(self, kind='battle'):
        self.g.start_battle(kind)
        b = self.g.battle
        b['enemy'].update(hp=999,maxHp=999,damage=8,pattern=['attack','block','weak'])
        b['hand'],b['draw'],b['discard'] = [],[],[]
        return b

    def card(self, cid, upgraded=False):
        self.g.battle['hand'].append(dict(id=cid,upgraded=upgraded))
        return len(self.g.battle['hand'])-1

    def test_content_counts(self):
        self.assertEqual(len(CARDS),60)
        self.assertEqual(Counter(c['rarity'] for c in CARDS.values()), {'基础':10,'进阶':25,'稀有':15,'传说':5,'天劫':5})
        self.assertEqual(len(RELICS),24)
        self.assertEqual(len(EVENTS),12)
        for s in SECTS:
            self.assertEqual(len(s['starter']),12)
            for cid in s['starter']: self.assertIn(cid,CARDS)

    def test_map_blocks_teleport_and_battle_navigation(self):
        self.assertFalse(self.g.choose_node(1,0))
        self.assertTrue(self.g.choose_node(0,0))
        self.assertFalse(self.g.choose_node(0,0))
        self.assertFalse(self.g.choose_node(1,0))
        self.assertEqual(len(self.g.s['visited']),1)

    def test_start_draws_five_and_pays_energy(self):
        self.g.start_battle('battle')
        self.assertEqual(len(self.g.battle['hand']),5)
        b = self.battle()
        i = self.card('strike')
        self.assertTrue(self.g.play(i))
        self.assertEqual(b['qi'],2)
        self.assertEqual(b['enemy']['hp'],992)
        self.assertEqual(len(b['discard']),1)
        b['qi']=0
        self.assertFalse(self.g.play(self.card('strike')))

    def test_draw_shuffle_and_hand_limit(self):
        b = self.battle()
        b['discard'] = [dict(id='strike',upgraded=False) for _ in range(12)]
        self.g.draw(20)
        self.assertEqual(len(b['hand']),10)
        self.assertEqual(len(b['draw']),2)
        self.assertEqual(len(b['discard']),0)

    def test_block_protects_then_clears_and_intent_advances(self):
        b=self.battle()
        b['hand']=[dict(id='strike',upgraded=False)]
        b['block']=6
        self.assertEqual(self.g.intent()['damage'],8)
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],74)
        self.assertEqual(b['block'],0)
        self.assertEqual(b['turn'],2)
        self.assertEqual(b['enemy']['turn'],1)
        self.assertEqual(self.g.intent()['action'],'block')
        self.assertEqual(b['qi'],3)

    def test_next_turn_block(self):
        b=self.battle()
        self.g.play(self.card('iron-skin'))
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],76)
        self.assertEqual(b['block'],3)

    def test_piercing_leaves_ignored_block(self):
        b=self.battle()
        b['enemy']['block']=10
        self.g.play(self.card('sword-pierce'))
        self.assertEqual(b['enemy']['hp'],989)
        self.assertEqual(b['enemy']['block'],8)

    def test_conditions_and_mood_damage(self):
        b=self.battle()
        b['block']=8
        self.g.play(self.card('mountain-crash'))
        self.assertEqual(b['enemy']['hp'],973)
        b['qi']=3
        b['mood']=2
        self.g.play(self.card('sword-rain'))
        self.assertEqual(b['enemy']['hp'],951)

    def test_fire_poison_and_combo(self):
        b=self.battle()
        b['enemy']['statuses'].update(burn=3,poison=2)
        self.g.play(self.card('alchemy-venom'))
        self.assertEqual(b['enemy']['hp'],987)
        self.g.end_turn()
        self.assertEqual(b['enemy']['hp'],962)
        self.assertEqual(b['enemy']['statuses']['burn'],2)
        self.assertEqual(b['enemy']['statuses']['poison'],7)

    def test_self_damage_bypasses_block_and_can_kill(self):
        b=self.battle()
        b['block']=99
        b['enemy']['hp']=1
        self.g.s['hp']=3
        self.g.play(self.card('demon-flame'))
        self.assertEqual(self.g.s['mode'],'result')
        self.assertFalse(self.g.s['end']['win'])
        self.assertEqual(b['enemy']['hp'],1)
        self.assertEqual(self.g.s['gold'],60)

    def test_tribulation_disables_block(self):
        b=self.battle()
        b['block']=10
        self.g.play(self.card('thunder-tribulation'))
        self.g.play(self.card('guard'))
        self.assertEqual(b['block'],0)
        self.assertTrue(b['lockBlock'])
        self.assertEqual(len(b['exhaust']),1)
        self.g.end_turn()
        self.assertFalse(b['lockBlock'])

    def test_persistent_power_upgrade_does_not_downgrade(self):
        b=self.battle()
        self.g.play(self.card('sword-oath',True))
        b['qi']=3
        self.g.play(self.card('sword-oath'))
        self.assertTrue(b['powers']['comboMood'])
        self.assertEqual(len(b['exhaust']),2)

    def test_healing_power_counts_actual_healing_only(self):
        b=self.battle()
        b['powers']['healQi']=False
        self.g.s['hp']=60
        self.g.heal(1,card=True)
        self.assertEqual(b['qi'],4)
        self.g.heal(1,card=True)
        self.assertEqual(b['qi'],4)
        self.g.s['hp']=self.g.s['maxHp']
        b['healingTriggers']=0
        self.g.heal(1,card=True)
        self.assertEqual(b['qi'],4)

    def test_paper_doll_temporary_does_not_remove_permanent(self):
        b=self.battle()
        self.g.play(self.card('paper-doll',True))
        b['qi']=3
        self.g.play(self.card('paper-doll'))
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],76)
        self.assertEqual(b['dodge'],2)
        self.assertEqual(b['dodgeTemp'],0)

    def test_weak_and_vulnerability(self):
        b=self.battle()
        self.g.play(self.card('seal',True))
        self.assertEqual(self.g.intent()['damage'],3)
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],73)
        self.assertEqual(b['enemy']['statuses']['weak'],0)

    def test_relics_have_effects(self):
        self.g.obtain_relic('jade')
        self.g.obtain_relic('dragon')
        self.g.obtain_relic('shell')
        self.g.obtain_relic('incense')
        self.g.start_battle('battle')
        self.assertEqual(self.g.s['maxHp'],84)
        self.assertEqual(self.g.battle['qi'],4)
        self.assertEqual(self.g.battle['block'],3)
        self.assertEqual(len(self.g.battle['hand']),6)
        gold=self.g.s['gold']
        self.g.obtain_relic('jade')
        self.assertEqual(self.g.s['maxHp'],84)
        self.assertEqual(self.g.s['gold'],gold+15)

    def test_armor_mirror_and_dodge_order(self):
        b=self.battle()
        self.g.obtain_relic('mirror')
        b['statuses']['armor']=2
        b['block']=2
        self.assertEqual(self.g.hurt(10),3)
        self.assertTrue(b['mirrorUsed'])
        self.assertEqual(self.g.hurt(10),8)
        self.assertEqual(self.g.hurt(10,attack=False),10)

    def test_forty_card_turn_cap(self):
        b=self.battle()
        b['turnPlayed']=40
        self.assertFalse(self.g.play(self.card('focus')))
        self.g.end_turn()
        self.assertEqual(b['turnPlayed'],0)

    def test_boss_preview_accounts_for_dot_phase_change(self):
        b=self.battle('boss')
        b['enemy'].update(hp=505,maxHp=1000,damage=8)
        b['enemy']['statuses']['burn']=2
        self.assertEqual(self.g.intent()['damage'],12)
        hp=self.g.s['hp']
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],hp-12)
        self.assertEqual(b['enemy']['phase'],2)

    def test_boss_forecast_does_not_double_apply_dot(self):
        b=self.battle('boss')
        b['enemy'].update(hp=509,maxHp=1000,damage=8)
        b['enemy']['statuses']['burn']=2
        self.assertEqual(self.g.intent()['damage'],8)
        hp=self.g.s['hp']
        self.g.end_turn()
        self.assertEqual(self.g.s['hp'],hp-8)
        self.assertEqual(b['enemy']['phase'],1)

    def test_event_insufficient_cost_is_atomic(self):
        self.g.s.update(mode='event',event=copy.deepcopy(EVENTS[2]),gold=0)
        before=copy.deepcopy(self.g.s)
        self.assertFalse(self.g.event_choice(0))
        self.assertEqual(before,self.g.s)

    def test_event_cancel_cannot_repeat_gain(self):
        self.g.s.update(mode='event',event=copy.deepcopy(EVENTS[0]))
        self.g.event_choice(0)
        self.assertEqual(self.g.s['insight'],1)
        self.assertEqual(self.g.s['mode'],'picker')
        self.g.cancel_picker()
        self.assertEqual(self.g.s['mode'],'map')
        self.assertEqual(self.g.s['row'],1)
        self.assertFalse(self.g.event_choice(0))
        self.assertEqual(self.g.s['insight'],1)

    def test_shop_remove_one_time_and_upgrade(self):
        self.g.make_shop()
        self.g.s['gold']=100
        self.assertTrue(self.g.begin_remove())
        self.assertTrue(self.g.pick_card(0))
        self.assertEqual(len(self.g.s['deck']),11)
        self.assertEqual(self.g.s['gold'],50)
        self.assertFalse(self.g.begin_remove())
        self.g.s['mode']='rest'
        self.g.rest('upgrade')
        self.g.pick_card(0)
        self.assertTrue(self.g.s['deck'][0]['upgraded'])
        self.assertEqual(self.g.s['mode'],'map')

    def test_restored_randomness_and_mid_battle_save(self):
        self.g.choose_node(0,0)
        self.g.save()
        second=Game(self.tmp.name)
        self.assertTrue(second.resume())
        self.assertEqual(second.s,self.g.s)
        second.end_turn()
        self.g.end_turn()
        self.assertEqual(second.s,self.g.s)
        self.assertEqual(second.reward_cards(),self.g.reward_cards())

    def test_all_card_effects_execute_base_and_upgrade(self):
        for cid in CARDS:
            for upgraded in (False,True):
                with self.subTest(cid=cid,upgraded=upgraded):
                    b=self.battle()
                    self.g.s['hp']=40
                    b['qi']=6
                    b['block']=12
                    b['mood']=3
                    b['statuses']['heart']=2
                    b['enemy']['statuses']['burn']=3
                    self.assertTrue(self.g.play(self.card(cid,upgraded)))
                    self.assertGreaterEqual(b['qi'],0)
                    self.assertLessEqual(b['qi'],6)
                    self.assertGreaterEqual(self.g.s['hp'],0)
                    self.assertLessEqual(self.g.s['hp'],self.g.s['maxHp'])

    def test_all_three_floors_and_realms(self):
        for floor in (1,2,3):
            for row in range(12):
                self.assertEqual(self.g.s['floor'],floor)
                self.assertEqual(self.g.s['row'],row)
                self.g.s['map'][row] = [dict(id=f'{floor}-{row}-0',type='boss' if row==11 else 'battle',label='斗法')]
                self.g.choose_node(row,0)
                self.g.battle['enemy']['hp']=1
                self.g.battle['qi']=6
                self.g.battle['hand']=[dict(id='strike',upgraded=False)]
                self.g.play(0)
                self.assertEqual(self.g.s['mode'],'reward')
                self.g.take_reward(None)
        self.assertEqual(self.g.s['mode'],'result')
        self.assertEqual(self.g.s['realm'],4)
        self.assertEqual(self.g.s['cleared'],36)
        self.assertEqual(self.g.profile['wins'],1)
        self.assertTrue(self.g.s['end']['win'])
        self.assertIn('shell',self.g.s['relics'])
        self.assertIn('fox',self.g.s['relics'])

    def test_corrupt_save_does_not_crash(self):
        (Path(self.tmp.name)/'run.json').write_text('{}','utf-8')
        self.assertFalse(self.g.resume())
        self.assertTrue(self.g.load_error)


if __name__=='__main__':
    unittest.main()
