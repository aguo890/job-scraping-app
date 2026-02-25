import unittest
from datetime import datetime
import pytz
import sys
import os

# Add the parent directory to sys.path so we can import scheduler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scheduler import is_peak_hour, is_offpeak_hour

class TestSchedulerTimeLogic(unittest.TestCase):
    
    def setUp(self):
        self.tz = pytz.timezone('America/New_York')

    def test_peak_hours(self):
        # Test 8:00 AM (Start of peak)
        peak_start = datetime(2024, 1, 1, 8, 0, 0, tzinfo=self.tz)
        self.assertTrue(is_peak_hour(peak_start))
        self.assertFalse(is_offpeak_hour(peak_start))

        # Test 12:59 PM (End of peak)
        peak_end = datetime(2024, 1, 1, 12, 59, 0, tzinfo=self.tz)
        self.assertTrue(is_peak_hour(peak_end))
        self.assertFalse(is_offpeak_hour(peak_end))

    def test_offpeak_hours(self):
        # Test 7:59 AM (Just before peak)
        morning_offpeak = datetime(2024, 1, 1, 7, 59, 0, tzinfo=self.tz)
        self.assertFalse(is_peak_hour(morning_offpeak))
        self.assertTrue(is_offpeak_hour(morning_offpeak))

        # Test 1:00 PM (Just after peak ends)
        afternoon_offpeak = datetime(2024, 1, 1, 13, 0, 0, tzinfo=self.tz)
        self.assertFalse(is_peak_hour(afternoon_offpeak))
        self.assertTrue(is_offpeak_hour(afternoon_offpeak))

    def test_midnight_and_noon(self):
        # Test Midnight (Off-peak)
        midnight = datetime(2024, 1, 1, 0, 0, 0, tzinfo=self.tz)
        self.assertFalse(is_peak_hour(midnight))
        self.assertTrue(is_offpeak_hour(midnight))

        # Test Noon (Peak)
        noon = datetime(2024, 1, 1, 12, 0, 0, tzinfo=self.tz)
        self.assertTrue(is_peak_hour(noon))
        self.assertFalse(is_offpeak_hour(noon))

if __name__ == '__main__':
    unittest.main()
