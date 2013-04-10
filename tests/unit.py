import unittest
import sys
import os
import time
import shutil
import tempfile
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
    
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp( prefix="TestWebPing" )
        #os.makedirs(self.tmp_dir)
        
    def tearDown(self):
        shutil.rmtree( self.tmp_dir )
        
    def test_get_file_path(self):
        self.assertEquals( WebPing.get_file_path( "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping", "web_ping://TextCritical.com"), "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping/35163af7282b92013f810b2b4822d7df.json")
    
    def test_ping(self):
        
        url_field = URLField( "test_ping", "title", "this is a test" )
        
        result = WebPing.ping( url_field.to_python("https://www.google.com/") )
        
        self.assertEquals(result.response_code, 200)
        self.assertGreater(result.connection_time, 0)
        self.assertGreater(result.request_time, 0)
        self.assertGreater(result.total_time, 0)
        
    def test_ping_timeout(self):
        url_field = URLField( "test_ping_timeout", "title", "this is a test" )
        
        result = WebPing.ping( url_field.to_python("https://192.168.30.23/"), timeout=3 )
        
        self.assertEquals(result.timed_out, True)
        
    def test_save_checkpoint(self):
        WebPing.save_checkpoint(self.tmp_dir, "web_ping://TextCritical.com", 100)
        self.assertEquals( WebPing.last_ran(self.tmp_dir, "web_ping://TextCritical.com"), 100)
        
    def test_is_expired(self):
        self.assertFalse( WebPing.is_expired(time.time(), 30) )
        self.assertTrue( WebPing.is_expired(time.time() - 31, 30) )
        
    def get_test_dir(self):
        return os.path.dirname(os.path.abspath(__file__))
        
    def test_needs_another_run(self):
        
        # Test case where file does not exist
        self.assertTrue( WebPing.needs_another_run( "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping", "web_ping://DoesNotExist", 60 ) )
        
        # Test an interval right at the earlier edge
        self.assertFalse( WebPing.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "web_ping://TextCritical.com", 60, 1365486765 ) )
        
        # Test an interval at the later edge
        self.assertFalse( WebPing.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "web_ping://TextCritical.com", 10, 1365486775 ) )
        
        # Test interval beyond later edge
        self.assertTrue( WebPing.needs_another_run( os.path.join( self.get_test_dir(), "configs" ), "web_ping://TextCritical.com", 10, 1365486776 ) )
        
    def test_output_result(self):
        web_ping = WebPing(timeout=3)
        
        url_field = URLField( "test_ping", "title", "this is a test" )
        result = WebPing.ping( url_field.to_python("https://www.google.com/") )
        
        out = StringIO()
        
        web_ping.output_result(result, "stanza", "title", unbroken=True, close=True, out=out)
        
        self.assertTrue(out.getvalue().find("response_code=200") >= 0)
        
    def test_output_result_unavailable(self):
        web_ping = WebPing(timeout=3)
        
        url_field = URLField( "test_ping", "title", "this is a test" )
        result = WebPing.ping( url_field.to_python("http://192.168.30.23/"), timeout=3 )
        
        out = StringIO()
        
        web_ping.output_result(result, "stanza", "title", unbroken=True, close=True, out=out)
        
        self.assertTrue(out.getvalue().find("timed_out=True") >= 0)