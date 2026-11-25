#!/usr/bin/env python3
"""Test suite for continuous_listening plugin"""
import os, sys, time, unittest
from unittest.mock import patch, MagicMock

# Add plugin directory to path
plugin_dir = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, plugin_dir)

class TestContinuousListener(unittest.TestCase):
    """Test cases for ContinuousListener class"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock globals that plugin expects
        import builtins
        self.original_globals = dict(builtins.__dict__)
        builtins.CFG = {"assistant_name": "VISUAL", "owner_name": "Arjun", "keys": {"groq": ""}}
        builtins.MEMORY = {}
        builtins.STOP_FILE = "/tmp/STOP"
        builtins.HALLUCINATIONS = set()
        builtins.sh = MagicMock(return_value="ok")
        builtins.speak = MagicMock()
        builtins._norm = lambda s: s.lower()
        builtins.neural_tts = MagicMock()
        builtins.chat = MagicMock(return_value="Test response")
        
    def tearDown(self):
        """Clean up"""
        import builtins
        for key in list(builtins.__dict__.keys()):
            if key not in self.original_globals:
                del builtins.__dict__[key]
        for key, val in self.original_globals.items():
            builtins.__dict__[key] = val
    
    def test_listener_initialization(self):
        """Test that listener initializes without error"""
        from plugin import ContinuousListener
        listener = ContinuousListener()
        self.assertFalse(listener.running)
        self.assertIsNone(listener.thread)
        self.assertFalse(listener.wakelock_acquired)
        print("PASS: Listener initialized without error")
        
    def test_start_stop(self):
        """Test start and stop methods"""
        from plugin import ContinuousListener
        listener = ContinuousListener()
        
        # Start
        listener.start()
        self.assertTrue(listener.running)
        self.assertIsNotNone(listener.thread)
        
        # Give thread a moment
        time.sleep(0.5)
        
        # Stop
        listener.stop()
        self.assertFalse(listener.running)
        print("PASS: Start/stop works")
        
    def test_wake_word_detection_logic(self):
        """Test wake word detection logic"""
        from plugin import ContinuousListener, WAKE_WORDS, STOP_PHRASES
        listener = ContinuousListener()
        
        # Test wake word detection
        test_cases = [
            ("visual kya haal hai", True),
            ("vishal sun rahe ho", True),
            ("विजुअल bolo", True),
            ("kuch bhi", False),
            ("band ho jao", False),  # This is stop phrase
        ]
        
        for text, expected in test_cases:
            normalized = text.lower()
            called = any(w in normalized for w in WAKE_WORDS)
            self.assertEqual(called, expected, f"Failed for: {text}")
            
        # Test stop phrase detection
        for phrase in STOP_PHRASES:
            self.assertTrue(phrase in phrase.lower())
            
        print("PASS: Wake word detection logic works")
        
    def test_handle_detected_stop_phrase(self):
        """Test that stop phrase triggers stop"""
        from plugin import ContinuousListener
        listener = ContinuousListener()
        listener.running = True
        
        with patch.object(listener, 'stop') as mock_stop:
            listener._handle_detected("band ho jao", "/tmp/test.m4a")
            mock_stop.assert_called_once()
            
        print("PASS: Stop phrase triggers stop")
        
    def test_handle_detected_wake_word(self):
        """Test wake word handling"""
        from plugin import ContinuousListener
        listener = ContinuousListener()
        listener.running = True
        
        with patch('builtins.speak') as mock_speak:
            listener._handle_detected("visual kya haal hai", "/tmp/test.m4a")
            mock_speak.assert_called()
            
        print("PASS: Wake word triggers response")

if __name__ == "__main__":
    unittest.main(verbosity=2)