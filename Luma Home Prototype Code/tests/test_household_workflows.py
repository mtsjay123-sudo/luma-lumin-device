import tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.integrations.providers import Providers
from tests.test_bookings import CalFixture

class HouseholdWorkflows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name);self.store=Store(p/'db',p/'key');self.agent=Agent(store=self.store,use_model=False)
    def tearDown(self):self.store.close();self.temp.cleanup()
    @patch('luma.agent.runtime.MacMessages')
    def test_named_mac_message_waits_for_review_and_submits_exactly_once(self,mac):
        self.agent.contacts.save({'name':'Mom','phone':'+19195550123'});self.agent.set_message_route('mac_imessage')
        mac.return_value.send.return_value={'provider':'mac_messages','status':'accepted','summary':'Fixture accepted, delivery unconfirmed'}
        pending=self.agent.prepare_message('my mom','Can you pick up the groceries?')
        self.assertEqual(pending['arguments']['transport'],'imessage');mac.return_value.send.assert_not_called()
        result=self.agent.confirm(pending['action'],pending['confirm_token'])
        mac.return_value.send.assert_called_once_with({'to':'+19195550123','body':'Can you pick up the groceries?'})
        self.assertEqual(result['status'],'accepted')
        with self.assertRaises(ValueError):self.agent.confirm(pending['action'],pending['confirm_token'])
    @patch('luma.agent.runtime.MacMessages')
    def test_changing_the_mac_texting_route_cancels_execution_authority(self,mac):
        self.agent.set_message_route('mac_imessage');pending=self.agent.prepare_message('+19195550123','Fixture only')
        self.agent.set_message_route('mac_sms')
        with self.assertRaises(ValueError):self.agent.confirm(pending['action'],pending['confirm_token'])
        mac.return_value.send.assert_not_called()
    def test_actual_offered_booking_is_reviewed_before_provider_submission(self):
        http=CalFixture();env={'CAL_COM_API_KEY':'fixture-only','LUMA_CAL_EVENT_TYPES_JSON':'{"consultation":42}'}
        agent=Agent(store=self.store,providers=Providers(env,request=http),use_model=False,now=lambda:datetime(2026,9,7,12,tzinfo=timezone.utc).timestamp());agent.enable('booking',True)
        slots=agent.propose('booking.availability',{'service':'consultation','start':'2026-09-08','end':'2026-09-09','time_zone':'America/New_York'})
        pending=agent.propose('booking.create',{'offer_id':slots['slots'][0]['offer_id'],'name':'Fixture Attendee','email':'fixture@example.test'})
        self.assertEqual(pending['review']['attendee']['name'],'Fixture Attendee');self.assertFalse(http.posts)
        receipt=agent.confirm(pending['action'],pending['confirm_token']);self.assertTrue(receipt['confirmed']);self.assertEqual(len(http.posts),1)
        with self.assertRaises(ValueError):agent.confirm(pending['action'],pending['confirm_token'])
    def test_natural_grocery_text_preserves_items_without_model_invention(self):
        self.agent.contacts.save({'name':'Mom','phone':'+19195550123'});self.agent.use_model=True
        self.agent.planner=lambda *args:self.fail('Known natural text requests do not need a model rewrite')
        result=self.agent.chat('Hey Luma can you text my mom to pick up the groceries while she is out')
        body=result['message_draft']['body'];self.assertIn('groceries',body);self.assertNotIn('milk',body);self.assertNotIn('eggs',body)
        self.assertEqual(result['message_draft']['to'],'+19195550123')
    def test_conversational_style_change_is_saved_for_later_turns(self):
        self.agent.use_model=True
        self.agent.planner=lambda *args:{'type':'tool','name':'personality.set_style','arguments':{'tone':'warm','language_style':'contemporary','verbosity':'brief'}}
        self.agent.chat('Talk to me more casually and keep it short')
        self.assertEqual(self.agent.profile['language_style'],'contemporary');self.assertEqual(self.agent.profile['verbosity'],'brief')
    def test_language_model_cannot_select_and_book_an_unreviewed_slot(self):
        self.agent.enable('booking',True);self.agent.use_model=True
        self.agent.planner=lambda *args:{'type':'tool','name':'booking.create','arguments':{'offer_id':'invented','name':'invented','email':'fake@example.test'}}
        self.assertIn('No action was taken',self.agent.chat('Find me a time tomorrow')['text'])
        self.assertFalse(self.store.all('action'))

if __name__=='__main__':unittest.main()
