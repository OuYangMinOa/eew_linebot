import unittest
from src.app    import app

class TestFlask(unittest.TestCase):
    
    def test_FlaskResponse(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)
