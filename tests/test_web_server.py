import SimpleHTTPServer
import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import os
import base64
from StringIO import StringIO

class Handler(BaseHTTPRequestHandler):
    ''' Main class to present webpages and authentication. '''
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        username = 'admin'
        password = 'changeme'
        
        encoded_password = base64.b64encode(username + ":" + password)
        
        # Present header reflection page
        if self.path == "/header_reflection":
            self.do_HEAD()
            self.wfile.write('<html><body><div class="user-agent">%s</div></body></html>' % str(self.headers['user-agent']))
            
        # Present the HTML page with no authentication
        if self.path == "/test_page":
            self.do_HEAD()
            
            with open( os.path.join("web_files", "test_page.html"), "r") as webfile:
                self.wfile.write(webfile.read())#.replace('\n', '')
        
        # Present frontpage with user authentication.
        elif self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received')
            
        elif self.headers.getheader('Authorization') == ('Basic ' + encoded_password):
            self.do_HEAD()
            #self.wfile.write(self.headers.getheader('Authorization'))
            #self.wfile.write('authenticated!')
            
            with open( os.path.join("web_files", "test_page.html"), "r") as webfile:
                self.wfile.write(webfile.read())#.replace('\n', '')
            
        else:
            self.do_AUTHHEAD()
            self.wfile.write(self.headers.getheader('Authorization'))
            self.wfile.write('not authenticated')
     
def get_server(port):
    """
    Call httpd.shutdown() to stop the server
    """
    
    httpd = SocketServer.TCPServer(("", port), Handler)
    return httpd
