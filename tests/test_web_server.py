from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
import os
import base64

from six.moves.urllib.parse import urlparse, parse_qs
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from six import binary_type, text_type

class TestWebServerHandler(BaseHTTPRequestHandler):
    ''' Main class to present webpages and authentication. '''
    DEBUG = False

    def get_header(self, header_name):
        return self.headers.get(header_name.lower())

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def write_string(self, content):
        if isinstance(content, text_type):
            return self.wfile.write(content.encode('utf-8'))
        else:
            return self.wfile.write(content)

    def get_file(self, dirname, fname):
        with open(os.path.join(dirname, fname), "rb") as webfile:
            self.wfile.write(webfile.read())

    def do_GET(self):
        try:
            username = 'admin'
            password = 'changeme'
            combined_user_pass = username + ":" + password

            if not isinstance(combined_user_pass, binary_type):
                combined_user_pass = combined_user_pass.encode('utf-8')

            encoded_password = base64.b64encode(combined_user_pass)

            if isinstance(encoded_password, binary_type):
                encoded_password = encoded_password.decode('utf-8')

            basic_auth_header = 'Basic ' + encoded_password

            # Present header reflection page
            if self.path == "/header_reflection":
                self.do_HEAD()
                self.write_string('<html><body><div class="user-agent">%s</div></body></html>' % str(self.headers['user-agent']))
                
            # Check the user-agent and return 201 when the user-agent is "USER_AGENT_CHECK"
            if self.path == "/user_agent_check":

                if 'user-agent' in self.headers and self.headers['user-agent'] == 'USER_AGENT_CHECK':
                    self.send_response(201)
                else:
                    print("user-agent was not set to 'USER_AGENT_CHECK'")

                self.do_HEAD()
                self.write_string('<html><body></body></html>')

            # Present the HTML page with no authentication
            if self.path.startswith("/test_page"):
                self.do_HEAD()
                self.get_file("web_files", "test_page.html")

            # Present the HTML page with optional authentication
            elif self.path == "/optional_auth":
                if self.DEBUG:
                    print('Auth header:', self.get_header('Authorization'), ", it ought to be", basic_auth_header) 
                if self.get_header('Authorization') == None:
                    self.send_response(202)
                    self.end_headers()
                    self.write_string('not authenticated')

                elif self.get_header('Authorization') == basic_auth_header:
                    self.send_response(203)
                    self.end_headers()
                    self.write_string('authenticated')

                else:
                    self.send_response(403)
                    self.end_headers()
                    self.write_string('authenticated failed')
                
            # Present the HTML page with NTLM authentication
            # This is basically a fake NTLM session. This is the best I can do in a unit test since simulating a AD environment and a web-server with NTLM auth is not easy.
            elif self.path == "/ntlm_auth" or self.path == "/ntlm_auth_negotiate":

                if self.path == "/ntlm_auth_negotiate":
                    auth_header = "Negotiate, NTLM"
                else:
                    auth_header = "NTLM"
                
                if self.get_header('Authorization') == None:
                    self.send_response(401)
                    self.send_header('WWW-Authenticate', auth_header)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.write_string('not authenticated')
                    
                # Do the challenge
                elif len(self.get_header('Authorization')) < 200: #self.get_header('Authorization') == "NTLM TlRMTVNTUAABAAAAB7IIogQABAA2AAAADgAOACgAAAAFASgKAAAAD0xNVVJQSEVZLU1CUDE1VVNFUg==":
                    # NTLM TlRMTVNTUAABAAAAB7IIogQABAA2AAAADgAOACgAAAAFASgKAAAAD0xNVVJQSEVZLU1CUDE1VVNFUg==
                    self.send_response(401)
                    self.send_header('WWW-Authenticate', 'NTLM TlRMTVNTUAACAAAAAAAAACgAAAABAAAAAAAAAAAAAAA=') # The challenge
                    self.end_headers()
                    self.write_string('not authenticated, step two')
                
                else: # elif self.get_header('Authorization') == "NTLM TlRMTVNTUAADAAAAGAAYAHgAAAAYABgAkAAAAAgACABIAAAADAAMAFAAAAAcABwAXAAAAAAAAACoAAAABYKIogUBKAoAAAAPVQBTAEUAUgBkAG8AbQBhAGkAbgBMAE0AVQBSAFAASABFAFkALQBNAEIAUAAxADUAjkdanfmkRwLTvPN8tRWYl1fpobeVQMN00VGvOdOFEzgb0gY0ZnA0W8LL0pJ3BlOW":
                    # NTLM TlRMTVNTUAADAAAAGAAYAHgAAAAYABgAkAAAAAgACABIAAAADAAMAFAAAAAcABwAXAAAAAAAAACoAAAABYKIogUBKAoAAAAPVQBTAEUAUgBkAG8AbQBhAGkAbgBMAE0AVQBSAFAASABFAFkALQBNAEIAUAAxADUAjkdanfmkRwLTvPN8tRWYl1fpobeVQMN00VGvOdOFEzgb0gY0ZnA0W8LL0pJ3BlOW
                    self.send_response(200)
                    self.end_headers()
                    self.write_string('authenticated')
                    
                #else:
                #    print "Auth header not the expected value=", self.get_header('Authorization')
                
            # Present frontpage with user authentication.
            elif self.get_header('Authorization') == None:
                self.do_AUTHHEAD()
                self.write_string('no auth header received')
                
            elif self.get_header('Authorization') == basic_auth_header:
                self.do_HEAD()
                #self.write_string(self.get_header('Authorization'))
                #self.write_string('authenticated!')
                self.get_file("web_files", "test_page.html")
                
            else:
                self.do_AUTHHEAD()
                self.write_string(self.headers['Authorization'])
                self.write_string('not authenticated')
        except Exception as e:
            print("Exception has been generated")
            print(e)
