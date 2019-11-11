from six.moves.socketserver import TCPServer
from six.moves.urllib.request import urlopen
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler

class Proxy(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.copyfile(urlopen(self.path), self.wfile)

def get_server(port):
    """
    Call proxyd.shutdown() to stop the server
    """
    
    proxyd = TCPServer(("", port), Proxy)
    return proxyd