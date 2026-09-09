import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.llm.inference import GenerationCancelled


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); root=Path(self.temp.name)
        self.store=Store(root/'state.db',root/'key')
        self.agent=Agent(store=self.store,use_model=False,now=lambda:1788897600)
    def tearDown(self):
        self.agent.device.close();self.store.close();self.temp.cleanup()
    def test_fast_tool_turn_is_retained_and_tomorrow_edits_same_reminder(self):
        first=self.agent.chat('remind me in 20 minutes to check the oven')
        second=self.agent.chat('actually, tomorrow')
        self.assertEqual(first['task']['id'],second['task']['id'])
        self.assertEqual(len(self.store.all('task')),1)
        self.assertEqual(len(self.agent.history),4)
        self.assertGreater(second['task']['due'],first['task']['due'])
    def test_personality_change_keeps_conversation_and_requires_adult_choice(self):
        self.agent.chat('remember my keys are in the drawer')
        self.agent.set_preset('playful')
        self.assertEqual(len(self.agent.history),2)
        with self.assertRaises(ValueError): self.agent.set_preset('unfiltered')
        self.agent.set_preset('unfiltered',True)
        self.assertEqual(self.agent.profile['preset'],'unfiltered')
        self.agent.set_mode('kids')
        with self.assertRaises(ValueError): self.agent.set_preset('unfiltered',True)
        self.assertEqual(self.agent.history,[])
    def test_interrupt_does_not_wait_for_model_lock_or_execute_late_proposal(self):
        entered=threading.Event();release=threading.Event();results=[]
        def planner(*args):
            entered.set(); release.wait(2)
            return {'type':'tool','name':'memory.remember','arguments':{'text':'should not be saved'}}
        self.agent.use_model=True;self.agent.planner=planner
        worker=threading.Thread(target=lambda:results.append(self.agent.chat('Save the requested detail')))
        worker.start(); self.assertTrue(entered.wait(1))
        before=time.monotonic();self.agent.interrupt()
        self.assertLess(time.monotonic()-before,.1)
        release.set();worker.join(2)
        self.assertEqual(results[0]['state'],'interrupted')
        self.assertEqual(self.store.all('memory'),[])
    def test_multistep_run_saves_verified_steps_and_stops_duplicate(self):
        answers=iter([
            {'type':'tool','name':'memory.remember','arguments':{'text':'Spare keys in drawer'}},
            {'type':'tool','name':'tasks.create','arguments':{'title':'Give Dad the keys','due':'2026-09-10T12:00:00-04:00'}},
            {'type':'reply','text':'Your note and reminder are saved.'},
        ])
        self.agent.use_model=True;self.agent.planner=lambda *a:next(answers)
        result=self.agent.chat('Remember where the keys are and remind me to give them to Dad',agent_mode=True)
        self.assertEqual(len(result['workflow']['steps']),2)
        self.assertTrue(all(s['state']=='succeeded' for s in result['workflow']['steps']))
        self.assertEqual(len(self.store.all('memory')),1)
        self.agent.planner=lambda *a:{'type':'tool','name':'memory.remember','arguments':{'text':'Only once'}}
        result=self.agent.chat('Remember Only once',agent_mode=True)
        self.assertEqual(len(result['workflow']['steps']),1)
        self.assertEqual(result['workflow']['state'],'paused')
    def test_agent_stops_at_review_and_stop_revokes_review(self):
        self.agent.use_model=True;self.agent.set_message_route('twilio')
        self.agent.contacts.save({'name':'Mom','phone':'+19195550123'})
        self.agent.planner=lambda *a:{'type':'tool','name':'messages.prepare','arguments':{'recipient':'Mom','body':'Fixture only'}}
        result=self.agent.chat('Text Mom Fixture only',agent_mode=True)
        self.assertEqual(result['state'],'pending')
        self.assertEqual(result['workflow']['state'],'review')
        self.assertNotIn('confirm_token',result['workflow']['steps'][0]['observation'])
        self.agent.workflows.stop(result['workflow']['id'])
        self.assertEqual(self.store.get('action',result['action'])['state'],'cancelled')
    def test_household_tool_recall_and_timer_tick(self):
        self.agent.propose('household.save',{'category':'location','title':'Keys','details':'Blue drawer'})
        found=self.agent.propose('household.find',{'query':'keys'})
        self.assertEqual(found['records'][0]['title'],'Keys')
        result=self.agent.chat('Start a 3 minute pasta timer')
        self.assertEqual(result['timer']['duration_seconds'],180)
        result=self.agent.chat('pause the pasta timer')
        self.assertEqual(result['timer']['state'],'paused')
    def test_restart_pauses_workflow_without_replaying(self):
        self.store.put('workflow',{'goal':'fixture','mode':'friend','state':'running','steps':[]})
        second=Agent(store=self.store,use_model=False)
        self.assertEqual(second.workflows.list()[0]['state'],'paused')
        self.assertEqual(self.store.all('action'),[])
        second.device.close()

if __name__=='__main__':unittest.main()
