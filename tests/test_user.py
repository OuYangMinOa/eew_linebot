import unittest
from src.user    import Subsriber

class TestUser(unittest.TestCase):
    
    def test_FlaskResponse(self):
        sub = Subsriber()
        sub.id = "1234"
        sub.pos = "臺北市"
        sub.country = ["tw","jp"]
        self.assertEqual(sub.__str__(), "1234_臺北市_tw_jp")
        self.assertEqual(sub.__repr__(), "1234_臺北市_tw_jp")

        
