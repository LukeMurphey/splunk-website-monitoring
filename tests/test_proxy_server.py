import urllib
import SimpleHTTPServer
import SocketServer


class Proxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.copyfile(urllib.urlopen(self.path), self.wfile)

def get_server(port):
    """
    Call proxyd.shutdown() to stop the server
    """
    
    proxyd = SocketServer.TCPServer(("", port), Proxy)
    return proxyd