import threading
import time
import unittest
from unittest.mock import patch
import numpy as np
from luma.audio import tts, io


class NaturalSpeechTests(unittest.TestCase):
    def test_short_connected_sentences_keep_prosody_context(self):
        text="Hey, you're home. Long day? Tell me what happened."
        self.assertEqual(tts.speech_chunks(text),[text])
    def test_formatting_is_not_read_but_values_are_preserved(self):
        spoken=tts.spoken_text('## Your reminder\n**Mom**: meet at `3:15 PM`. Price $12.50; quantity 2.\n- Bring the keys.')
        self.assertIn('Mom: meet at 3:15 PM. Price $12.50; quantity 2.',spoken)
        self.assertIn('Bring the keys.',spoken)
        self.assertNotIn('**',spoken)
    def test_voice_controls_are_bounded_and_explicit(self):
        self.assertEqual(tts.validate_preferences({'voice':'luma','speed':1.03}),{'voice':'luma','speed':1.03})
        for value in [{'voice':'clone','speed':1},{'voice':'luma','speed':float('nan')},{'voice':'luma','speed':True},{'voice':'luma','speed':3}]:
            with self.assertRaises((ValueError,TypeError)):tts.validate_preferences(value)
    def test_synthesis_prefetches_next_phrase_during_playback(self):
        next_ready=threading.Event();calls=[]
        def samples(text,*args):
            calls.append(text)
            if len(calls)==2: next_ready.set()
            return np.ones(100,dtype=np.int16),24000
        def playback(chunks,should_stop):
            it=iter(chunks);next(it)
            self.assertTrue(next_ready.wait(1),'The next phrase must not wait for previous playback to finish')
            self.assertEqual(len(list(it)),1)
            return True
        text='First '+('word '*35)+'. Second '+('word '*35)+'.'
        with patch.object(tts,'_samples',side_effect=samples),patch.object(io,'play_chunks',side_effect=playback):
            self.assertTrue(tts.speak(text))
        self.assertEqual(len(calls),2)
    def test_cancel_during_native_synthesis_never_plays_stale_audio(self):
        entered=threading.Event();release=threading.Event();cancel=threading.Event();out=[]
        def samples(*args):
            entered.set();release.wait(2)
            return np.ones(100,dtype=np.int16),24000
        with patch.object(tts,'_samples',side_effect=samples),patch.object(io.sd,'OutputStream') as stream:
            worker=threading.Thread(target=lambda:out.append(tts.speak('A connected sentence.',should_stop=cancel.is_set)))
            worker.start();self.assertTrue(entered.wait(1));cancel.set();worker.join(1)
            self.assertEqual(out,[False]);stream.assert_not_called()
            release.set()
    def test_one_audio_stream_spans_multiple_generated_phrases(self):
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def write(self,data):pass
            def abort(self):pass
        with patch.object(io.sd,'query_devices',return_value=[]),patch.object(io.sd,'OutputStream',return_value=Stream()) as stream:
            self.assertTrue(io.play_chunks([(np.ones(100,dtype=np.int16),24000),(np.ones(100,dtype=np.int16),24000)]))
            self.assertEqual(stream.call_count,1)

if __name__=='__main__':unittest.main()
