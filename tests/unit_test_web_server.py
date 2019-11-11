import unittest
import sys
import os
import time
import threading
from six.moves.socketserver import TCPServer

# There needs to be a file named test_web_server next to this file with a class named TestWebServerHandler that inherits from BaseHTTPServer.BaseHTTPRequestHandler
from test_web_server import TestWebServerHandler

class UnitTestWithWebServer(unittest.TestCase):
    """
    This test class runs a web-server for the purposes of testing with a live web-server.
    """
    
    DEFAULT_TEST_WEB_SERVER_PORT = 8888
    warned_about_no_httpd = False
    httpd = None
    
    @classmethod
    def setUpClass(cls):
        
        cls.web_server_port = int(os.environ.get("TEST_WEB_SERVER_PORT", cls.DEFAULT_TEST_WEB_SERVER_PORT))
        
        # Stop if the web-server was already started
        if UnitTestWithWebServer.httpd is not None:
            return
        
        attempts = 0
         
        sys.stdout.write("Waiting for web-server to start ...")
        sys.stdout.flush()
        
        while UnitTestWithWebServer.httpd is None and attempts < 75:
            try:
                UnitTestWithWebServer.httpd = cls.get_server(cls.web_server_port)
                
                print(" Done")
                    
            except IOError:
                UnitTestWithWebServer.httpd = None
                time.sleep(4)
                attempts = attempts + 1
                sys.stdout.write(".")
                sys.stdout.flush()
                        
        if UnitTestWithWebServer.httpd is None:
            print("Web-server could not be started")
            return
        
        def start_server(httpd):
            if httpd is not None:
                httpd.serve_forever()
        
        t = threading.Thread(target=start_server, args = (UnitTestWithWebServer.httpd,))
        t.daemon = True
        t.start()
    
    @classmethod
    def shutdownServer(cls):
        if UnitTestWithWebServer.httpd is not None:
            UnitTestWithWebServer.httpd.shutdown()
            UnitTestWithWebServer.httpd = None
    
    def test_if_web_server_is_running(self):
        if UnitTestWithWebServer.httpd is None and not UnitTestWithWebServer.warned_about_no_httpd:
            UnitTestWithWebServer.warned_about_no_httpd = True
            self.fail("The test web-server is not running; tests that rely on the built-in web-server will fail or be skipped")
        
    @classmethod
    def get_server(cls, port):
        """
        Call httpd.shutdown() to stop the server
        """
        
        httpd = TCPServer(("", port), TestWebServerHandler)
        return httpd
        
def skipIfNoServer(func):
    def _decorator(self, *args, **kwargs):
        if self.httpd is None:
            # Don't run the test if the server is not running
            self.skipTest("The web-server is not running")
        else:
            return func(self, *args, **kwargs)
        
    return _decorator