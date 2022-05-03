"""
This module serves a basic HTTP proxy which just passes on HTTP requests.
"""
from six.moves.socketserver import TCPServer
from six.moves.urllib.request import urlopen
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler
import time

WAITING_FOR_PORT_SLEEP_TIME = 4
WAITING_FOR_PORT_ATTEMPT_LIMIT = 75
class Proxy(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.copyfile(urlopen(self.path), self.wfile)

def get_server(port):
    """
    Call proxyd.shutdown() to stop the server
    """
    attempts = 0
    while attempts < WAITING_FOR_PORT_ATTEMPT_LIMIT:
        try:
            proxyd = TCPServer(("", port), Proxy)
            return proxyd
                
        except IOError:
            time.sleep(WAITING_FOR_PORT_SLEEP_TIME)
            attempts = attempts + 1
        
    raise IOError("Could not start proxy server")


