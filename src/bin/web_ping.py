from splunk.models.base import SplunkAppObjModel
from modular_input import Field, ModularInput, URLField, DurationField
from splunk.models.field import Field as ModelField
from splunk.models.field import IntField as ModelIntField 

import re
import hashlib
import sys
import time
import splunk
import os

import socket
from website_monitoring_app import socks
from website_monitoring_app import requests
from website_monitoring_app.requests_ntlm import HttpNtlmAuth

# Disable the SSL certificate warning
# http://lukemurphey.net/issues/1390
# We don't support SSL certicate checking at this point because I haven;t found a good way to include the SSL cert libraries into a SPlunk app.
from website_monitoring_app.requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
class Timer(object):
    """
    This class is used to time durations.
    """
    
    def __init__(self, verbose=False):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs

class WebsiteMonitoringConfig(SplunkAppObjModel):
    
    resource       = '/admin/website_monitoring'
    proxy_server   = ModelField()
    proxy_port     = ModelIntField()
    proxy_type     = ModelField()
    proxy_user     = ModelField()
    proxy_password = ModelField()

class WebPing(ModularInput):
    """
    The web ping modular input connects to a website to determine if the site is operational and tracks the time it takes to respond.
    """
    
    PARSE_URL_RE = re.compile( r"http[s]?[:]//(.*)", re.IGNORECASE)
    
    HTTP_AUTH_BASIC = 'basic'
    HTTP_AUTH_DIGEST = 'digest'
    HTTP_AUTH_NTLM = 'ntlm'
    HTTP_AUTH_NONE = None
    
    class Result(object):
        """
        The results object designates the results of connecting to a website.
        """
        
        def __init__(self, request_time, response_code, timed_out, url, response_size=None, response_md5=None, response_sha224=None):
            
            self.request_time = request_time
            self.response_code = response_code
            self.timed_out = timed_out
            self.url = url
            self.response_size = response_size
            self.response_md5 = response_md5
            self.response_sha224 = response_sha224
    
    def __init__(self, timeout=30):

        scheme_args = {'title': "Website Availability Check",
                       'description': "Connects to a website in order to obtain performance statistics",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                Field("title", "Title", "A short description (typically just the domain name)", empty_allowed=False),
                URLField("url", "URL", "The URL to connect to (must be be either HTTP or HTTPS protocol)", empty_allowed=False),
                DurationField("interval", "Interval", "The interval defining how often to perform the check; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False),
                Field("configuration", "Configuration", "Defines a specific proxy configuration to use (in website_monitoring.spec) if not using the default; only used if you want to have multiple proxy servers", none_allowed=True, empty_allowed=True),
                Field("client_certificate", "Client Certificate Path", "Defines the path to the client certificate (if the website requires client SSL authentication)", none_allowed=True, empty_allowed=True),
                Field("client_certificate_key", "Client Certificate Key Path", "Defines the path to the client certificate key (necessary of the key is in a separate file from the certificate)", none_allowed=True, empty_allowed=True),
                Field("username", "Username", "The username to use for authenticating (only HTTP authentication supported)", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False),
                Field("password", "Password", "The password to use for authenticating (only HTTP authentication supported)", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False),
                Field("user_agent", "User Agent", "The user-agent to use when communicating with the server", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False)
                ]
        
        ModularInput.__init__( self, scheme_args, args, logger_name='web_availability_modular_input' )
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 30
        
    @classmethod
    def resolve_proxy_type(cls, proxy_type, logger=None):
        """
        Determine the type of the proxy to be used based on the string.
        
        Argument:
        proxy_type -- A string representing the proxy type (e.g. "socks4")
        logger -- The logger object to use for logging
        """
        
        # Make sure the proxy string is not none
        if proxy_type is None:
            return None
        
        # Prepare the string so that the proxy type can be matched more reliably
        t = proxy_type.strip().lower()
        
        if t == "socks4":
            return socks.PROXY_TYPE_SOCKS4
        elif t == "socks5":
            return socks.PROXY_TYPE_SOCKS5
        elif t == "http":
            return socks.PROXY_TYPE_HTTP
        elif t == "":
            return None
        else:
            if logger:
                logger.warn("Proxy type is not recognized: %s", proxy_type)
            return None
        
    @classmethod
    def determine_auth_type(cls, url, proxies=None, timeout=None, cert=None, logger=None):
        """
        Determine the authentication type that is appropriate to authenticate to the given web-server.
        
        Argument:
        url -- The url to connect to. This object ought to be an instance derived from using urlparse
        proxies -- The proxies to use
        timeout -- The amount of time to quit waiting on a connection
        cert -- A tuple representing the certificate to use
        logger -- The logger object to use for logging
        """
        
        # Perform a request to the URL and see what authentication method is required
        try:
            
            # Make the GET
            http = requests.get(url.geturl(), proxies=proxies, timeout=timeout, cert=cert, verify=False)
            
            # Determine if the authentication header is present and use it to determine the authentication type
            if 'WWW-Authenticate' in http.headers:
                auth_header = http.headers['WWW-Authenticate']
                
                if auth_header is not None:
                    m = re.search('^([a-zA-Z0-9]+) ', auth_header)
                    auth_type = m.group(1)
                    return auth_type.lower()
                
            # No authentication header is present
            else:
                if logger:
                    logger.warn("Unable to determine authentication type (no www-authenticate header); will default to basic authentication")
                
                return cls.HTTP_AUTH_NONE
            
        except Exception:
            
            if logger:
                logger.exception("Unable to determine authentication type")
                
    @classmethod
    def create_auth_for_request(cls, auth_type, username, password, logger=None):
        """
        Create the auth object for the requests library so that any HTTP authentication is taken care of.
        
        Argument:
        auth_type -- A string indicating the type of authentication require (e.g. "digest")
        username -- The password to use for authentication
        password -- The username to use for authentication
        logger -- The logger object to use for logging
        """
        
        # No authentication
        if auth_type == cls.HTTP_AUTH_NONE:
            return None
        
        # Digest authentication
        elif auth_type == cls.HTTP_AUTH_DIGEST:
            return requests.auth.HTTPDigestAuth(username, password)
        
        # NTLM authentication
        elif auth_type == cls.HTTP_AUTH_NTLM:
            return HttpNtlmAuth(username, password)
        
        # Basic authentication
        elif auth_type == cls.HTTP_AUTH_BASIC:
            return requests.auth.HTTPBasicAuth(username, password)
        
        # Unknown authentication type
        else:
            
            if logger:
                logger.warn('Unknown type of authentication requested, auth_type=%s', auth_type)
            
            return (username, password)
        
    @classmethod
    def ping(cls, url, username=None, password=None, timeout=30, proxy_type=None, proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None, client_certificate=None, client_certificate_key=None, user_agent=None, logger=None):
        """
        Perform a ping to a website. Returns a WebPing.Result instance.
        
        Argument:
        url -- The url to connect to. This object ought to be an instance derived from using urlparse.
        username -- The password to use for authentication
        password -- The username to use for authentication
        timeout -- The amount of time to quit waiting on a connection.
        proxy_type -- The type of the proxy server (must be one of: socks4, socks5, http)
        proxy_server -- The proxy server to use.
        proxy_port -- The port on the proxy server to use.
        proxy_user -- The proxy server to use.
        proxy_password -- The port on the proxy server to use.
        client_certificate -- The path to the client certificate to use.
        client_certificate_key -- The path to the client key to use.
        user_agent -- The string to use for the user-agent
        logger -- The logger object to use for logging
        """
        
        if logger:
            logger.info('Performing ping, url="%s"', url.geturl())
        
        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = cls.resolve_proxy_type(proxy_type, logger=logger)
        
        # Make sure that a timeout is not None since that is infinite
        if timeout is None:
            timeout = 30
        
        # Setup the proxy info if so configured
        proxies = {}
        
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            
            if proxy_type == "http":
                
                # Use the username and password if provided
                if proxy_password is not None and proxy_user is not None:
                    proxies = {
                      "http": "http://" + proxy_user + ":" + proxy_password + "@" + proxy_server + ":" + str(proxy_port),
                      "https": "http://" + proxy_user + ":" + proxy_password + "@" + proxy_server + ":" + str(proxy_port)
                    }
                else:
                    proxies = {
                      "http": "http://" + proxy_server + ":" + str(proxy_port),
                      "https": "http://" + proxy_server + ":" + str(proxy_port)
                    }
                
            else:
                socks.setdefaultproxy(resolved_proxy_type, proxy_server, proxy_port)
                socket.socket = socks.socksocket
            
        else:
            # No proxy is being used
            pass
        
        # Setup the client certificate parameter
        if client_certificate is not None and client_certificate_key is not None:
            cert = (client_certificate, client_certificate_key)
        elif client_certificate is not None:
            cert = client_certificate
        else:
            cert = None
            
        if logger:
            logger.debug("Using client certificate %s", cert)
        
        request_time    = 0
        response_code   = 0
        response_md5    = None
        response_sha224 = None
        timed_out       = False
        response_size   = None
        
        # Setup the headers as necessary
        headers = {}
        
        if user_agent is not None:
            if logger:
                logger.info("Setting user-agent=%s", user_agent)
            headers['User-Agent'] = user_agent
        
        # Make an auth object if necessary
        auth = None
        auth_type = None
        
        if username is not None and password is not None:
            
            # Determine the auth type
            auth_type = cls.determine_auth_type(url, proxies=proxies, timeout=timeout, cert=cert, logger=logger)
            
            # The authentication type could not be determined. However, we know that authentication is required since a username and password was provided. Default to 
            if auth_type == cls.HTTP_AUTH_NONE:
                auth_type = cls.HTTP_AUTH_BASIC
                
                if logger:
                    logger.info("Authentication type could not be automatically discovered; auth_type=%s", auth_type)
                    
            elif logger is not None:
                logger.debug("Discovered auth_type=%s", auth_type)
            
            # Get the authentication class for request
            auth = cls.create_auth_for_request(auth_type, username, password, logger)
        
        try:
            
            # Perform the request
            with Timer() as timer:
                
                # Make the client
                http = requests.get(url.geturl(), proxies=proxies, timeout=timeout, cert=cert, verify=False, auth=auth, headers=headers)
                
                # Get the hash of the content
                response_md5 = hashlib.md5(http.text).hexdigest()
                response_sha224 = hashlib.sha224(http.text).hexdigest()
                
                # Get the size of the content
                response_size = len(http.text)
                
            response_code = http.status_code    
            request_time = timer.msecs
            
        # Handle time outs
        except requests.exceptions.Timeout:
            
            # Note that the connection timed out
            timed_out = True
            
        except requests.exceptions.SSLError as e:
            
            if logger:
                logger.error("An SSL exception was thrown when executing a web request: " + str(e))
            
        except requests.exceptions.ConnectionError as e:
            
            if e.args is not None and len(e.args) > 0 and hasattr(e.args[0], 'reason') and hasattr(e.args[0].reason, 'errno') and e.args[0].reason.errno in [60, 61]:
                timed_out = True
                
            elif logger:
                logger.exception("A connection exception was thrown when executing a web request, this can happen if the domain name, IP address is invalid or if network connectivity is down or blocked by a firewall, see url=http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Troubleshooting")
                
        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            if logger:
                logger.exception("An error occurred when attempting to communicate with the proxy")
        
        except Exception as e:
            if logger:
                logger.exception("A general exception was thrown when executing a web request")
            
        # Finally, return the result
        return cls.Result(request_time, response_code, timed_out, url.geturl(), response_size, response_md5, response_sha224)
        
    def output_result(self, result, stanza, title, index=None, source=None, sourcetype=None, host=None, unbroken=True, close=True, proxy_server=None, proxy_port=None, proxy_user=None, proxy_type=None, out=sys.stdout ):
        """
        Create a string representing the event.
        
        Argument:
        result -- A result instance from a call to WebPing.ping
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source field value
        index -- The index to send the event to
        unbroken -- 
        close -- 
        out -- The stream to send the event to (defaults to standard output)
        """
        
        data = {
                'response_code': result.response_code if result.response_code > 0 else '',
                'total_time': round(result.request_time, 2) if result.request_time > 0 else '',
                'request_time': round(result.request_time, 2) if result.request_time > 0 else '',
                'timed_out': result.timed_out,
                'title': title,
                'url': result.url
                }
        
        # Log proxy server information
        if proxy_server is not None:
            data['proxy_server'] = proxy_server
            data['proxy_type'] = proxy_type
            
            if proxy_user is not None and len(proxy_user) > 0:
                data['proxy_user'] = proxy_user
            
            if proxy_port is not None:
                data['proxy_port'] = proxy_port
        
        # Add the MD5 of the response of available
        if result.response_md5 is not None:
            data['content_md5'] = result.response_md5
        
        # Add the SHA-224 of the response of available
        if result.response_sha224 is not None:
            data['content_sha224'] = result.response_sha224
            
        # Add the MD5 of the response of available
        if result.response_size is not None:
            data['content_size'] = result.response_size
                
        return self.output_event(data, stanza, index=index, host=host, source=source, sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
    
    @classmethod
    def get_file_path( cls, checkpoint_dir, stanza ):
        """
        Get the path to the checkpoint file.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        return os.path.join( checkpoint_dir, hashlib.md5(stanza).hexdigest() + ".json" )
    
    def save_checkpoint(self, checkpoint_dir, stanza, last_run):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        """
                
        self.save_checkpoint_data(checkpoint_dir, stanza, { 'last_run' : last_run })
        
    def get_proxy_config(self, session_key, stanza="default"):
        """
        Get the proxy configuration
        
        Arguments:
        session_key -- The session key to use when connecting to the REST API
        stanza -- The stanza to get the proxy information from (defaults to "default")
        """
        
        # If the stanza is empty, then just use the default
        if stanza is None or stanza.strip() == "":
            stanza = "default"
        
        # Get the proxy configuration
        try:
            website_monitoring_config = WebsiteMonitoringConfig.get( WebsiteMonitoringConfig.build_id( stanza, "website_monitoring", "nobody"), sessionKey=session_key )
            
            self.logger.debug("Proxy information loaded, stanza=%s", stanza)
            
        except splunk.ResourceNotFound:
            self.logger.error('Unable to find the proxy configuration for the specified configuration stanza=%s, error="not found"', stanza)
            raise
        except splunk.SplunkdConnectionException:
            self.logger.error('Unable to find the proxy configuration for the specified configuration stanza=%s error="splunkd connection error"', stanza)
            raise
        
        return website_monitoring_config.proxy_type, website_monitoring_config.proxy_server, website_monitoring_config.proxy_port, website_monitoring_config.proxy_user, website_monitoring_config.proxy_password
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval               = cleaned_params["interval"]
        title                  = cleaned_params["title"]
        url                    = cleaned_params["url"]
        client_certificate     = cleaned_params.get("client_certificate", None)
        client_certificate_key = cleaned_params.get("client_certificate_key", None)
        username               = cleaned_params.get("username", None)
        password               = cleaned_params.get("password", None)
        timeout                = self.timeout
        sourcetype             = cleaned_params.get("sourcetype", "web_ping")
        host                   = cleaned_params.get("host", None)
        index                  = cleaned_params.get("index", "default")
        conf_stanza            = cleaned_params.get("configuration", None)
        user_agent             = cleaned_params.get("user_agent", None)
        source                 = stanza
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Get the proxy configuration
            try:
                proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = self.get_proxy_config(input_config.session_key, conf_stanza)
            except splunk.ResourceNotFound:
                self.logger.error("The proxy configuration could not be loaded (was not found). The execution will be skipped for this input with stanza=%s", stanza)
                return
            except splunk.SplunkdConnectionException:
                self.logger.error("The proxy configuration could not be loaded (Splunkd connection exception). The execution will be skipped for this input with stanza=%s", stanza)
                return
            
            # Perform the ping
            result = WebPing.ping(url, username, password, timeout, proxy_type, proxy_server, proxy_port, proxy_user, proxy_password, client_certificate, client_certificate_key, user_agent, logger=self.logger)
            
            # Send the event
            self.output_result( result, stanza, title, host=host, index=index, source=source, sourcetype=sourcetype, unbroken=True, close=True, proxy_server=proxy_server, proxy_port=proxy_port, proxy_user=proxy_user, proxy_type=proxy_type )
            
            # Get the time that the input last ran
            last_ran = self.last_ran(input_config.checkpoint_dir, stanza)
            
            # Save the checkpoint so that we remember when we last 
            self.save_checkpoint(input_config.checkpoint_dir, stanza, self.get_non_deviated_last_run(last_ran, interval, stanza) )
            
if __name__ == '__main__':
    try:
        web_ping = WebPing()
        web_ping.execute()
        sys.exit(0)
    except Exception as e:
        #self.logger.exception("Unhandled exception was caught, this may be due to a defect in the script") # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
        raise e
