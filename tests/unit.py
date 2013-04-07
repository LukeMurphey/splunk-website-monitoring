import unittest
import sys
import os
from StringIO import StringIO

sys.path.append( os.path.join("..", "src", "bin") )

from web_ping import URLField, DurationField, WebPing
from modular_input import Field, FieldValidationException

class TestURLField(unittest.TestCase):
    
    def test_url_field_valid(self):
        url_field = URLField( "test_url_field_valid", "title", "this is a test" )
        
        self.assertEqual( url_field.to_python("http://google.com").geturl(), "http://google.com" )
        self.assertEqual( url_field.to_python("http://google.com/with/path").geturl(), "http://google.com/with/path" )
        self.assertEqual( url_field.to_python("http://google.com:8080/with/port").geturl(), "http://google.com:8080/with/port" )
        
    def test_url_field_invalid(self):
        url_field = URLField( "test_url_field_invalid", "title", "this is a test" )
        
        self.assertRaises( FieldValidationException, lambda: url_field.to_python("hxxp://google.com") )
        self.assertRaises( FieldValidationException, lambda: url_field.to_python("http://") )
        self.assertRaises( FieldValidationException, lambda: url_field.to_python("google.com") )
    
class TestDurationField(unittest.TestCase):
    
    def test_duration_valid(self):
        duration_field = DurationField( "test_duration_valid", "title", "this is a test" )
        
        self.assertEqual( duration_field.to_python("1m"), 60 )
        self.assertEqual( duration_field.to_python("5m"), 300 )
        self.assertEqual( duration_field.to_python("5 minute"), 300 )
        self.assertEqual( duration_field.to_python("5"), 5 )
        self.assertEqual( duration_field.to_python("5h"), 18000 )
        self.assertEqual( duration_field.to_python("2d"), 172800 )
        self.assertEqual( duration_field.to_python("2w"), 86400 * 7 * 2 )
        
    def test_url_field_invalid(self):
        duration_field = DurationField( "test_url_field_invalid", "title", "this is a test" )
        
        self.assertRaises( FieldValidationException, lambda: duration_field.to_python("1 treefrog") )
        self.assertRaises( FieldValidationException, lambda: duration_field.to_python("minute") )   
    
class TestWebPing(unittest.TestCase):
    
    def test_ping(self):
        
        url_field = URLField( "test_ping", "title", "this is a test" )
        
        result = WebPing.ping( url_field.to_python("https://www.google.com/") )
        
        self.assertEquals(result.response_code, 200)
        self.assertGreater(result.connection_time, 0)
        self.assertGreater(result.request_time, 0)
        self.assertGreater(result.total_time, 0)
        
    def test_ping_timeout(self):
        url_field = URLField( "test_ping_timeout", "title", "this is a test" )
        
        result = WebPing.ping( url_field.to_python("https://10.0.23.23/"), timeout=3 )
        
        self.assertEquals(result.timed_out, True)
        
    def test_send_result(self):
        web_ping = WebPing()
        
        url_field = URLField( "test_ping", "title", "this is a test" )
        result = WebPing.ping( url_field.to_python("https://www.google.com/") )
        
        out = StringIO()
        
        web_ping.send_result(result, "stanza", "title", unbroken=True, close=True, out=out)
        
        self.assertEqual(out.getvalue(), "")