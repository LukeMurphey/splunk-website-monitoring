
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.models.base import SplunkAppObjModel
from modular_input import Field, FieldValidationException, ModularInput
from splunk.models.field import Field as ModelField
from splunk.models.field import IntField as ModelIntField 

import re
import logging
from logging import handlers
import hashlib
import socket
import json
from urlparse import urlparse
import sys
import time
import os
import splunk

import httplib2
from httplib2 import socks

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('web_availability_modular_input')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'web_availability_modular_input.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

class URLField(Field):
    """
    Represents a URL. The URL is converted to a Python object that was created via urlparse.
    """
    
    def to_python(self, value):
        Field.to_python(self, value)
        
        parsed_value = urlparse(value)
        
        if parsed_value.hostname is None or len(parsed_value.hostname) <= 0:
            raise FieldValidationException("The value of '%s' for the '%s' parameter does not contain a host name" % (str(value), self.name))
        
        if parsed_value.scheme not in ["http", "https"]:
            raise FieldValidationException("The value of '%s' for the '%s' parameter does not contain a valid protocol (only http and https are supported)" % (str(value), self.name))
    
        return parsed_value
    
    def to_string(self, value):
        return value.geturl()

class DurationField(Field):
    """
    The duration field represents a duration as represented by a string such as 1d for a 24 hour period.
    
    The string is converted to an integer indicating the number of seconds.
    """
    
    DURATION_RE = re.compile("(?P<duration>[0-9]+)\s*(?P<units>[a-z]*)", re.IGNORECASE)
    
    MINUTE = 60
    HOUR   = 60 * MINUTE
    DAY    = 24 * HOUR
    WEEK   = 7 * DAY
    
    UNITS = {
             'w'       : WEEK,
             'week'    : WEEK,
             'd'       : DAY,
             'day'     : DAY,
             'h'       : HOUR,
             'hour'    : HOUR,
             'm'       : MINUTE,
             'min'     : MINUTE,
             'minute'  : MINUTE,
             's'       : 1
             }
    
    def to_python(self, value):
        Field.to_python(self, value)
        
        # Parse the duration
        m = DurationField.DURATION_RE.match(value)

        # Make sure the duration could be parsed
        if m is None:
            raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid duration" % (str(value), self.name))
        
        # Get the units and duration
        d = m.groupdict()
        
        units = d['units']
        
        # Parse the value provided
        try:
            duration = int(d['duration'])
        except ValueError:
            raise FieldValidationException("The duration '%s' for the '%s' parameter is not a valid number" % (d['duration'], self.name))
        
        # Make sure the units are valid
        if len(units) > 0 and units not in DurationField.UNITS:
            raise FieldValidationException("The unit '%s' for the '%s' parameter is not a valid unit of duration" % (units, self.name))
        
        # Convert the units to seconds
        if len(units) > 0:
            return duration * DurationField.UNITS[units]
        else:
            return duration

    def to_string(self, value):        
        return str(value)
    
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
                ]
        
        ModularInput.__init__( self, scheme_args, args )
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 30
        
    @classmethod
    def resolve_proxy_type(cls, proxy_type):
        
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
            logger.warn("Proxy type is not recognized: %s", proxy_type)
            return None
        
    @classmethod
    def ping(cls, url, timeout=30, proxy_type=None, proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None):
        """
        Perform a ping to a website. Returns a WebPing.Result instance.
        
        Argument:
        url -- The url to connect to. This object ought to be an instance derived from using urlparse.
        timeout -- The amount of time to quit waiting on a connection.
        proxy_type -- The type of the proxy server (must be one of: socks4, socks5, http)
        proxy_server -- The proxy server to use.
        proxy_port -- The port on the proxy server to use.
        proxy_user -- The proxy server to use.
        proxy_password -- The port on the proxy server to use.
        """
        
        logger.debug('Performing ping, url="%s"', url.geturl())
        
        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = cls.resolve_proxy_type(proxy_type)
        
        # Setup the proxy info if so configured
        if resolved_proxy_type is not None and proxy_server is not None and len(proxy_server.strip()) > 0:
            proxy_info = httplib2.ProxyInfo(resolved_proxy_type, proxy_server, proxy_port, proxy_user=proxy_user, proxy_pass=proxy_password)
        else:
            # No proxy is being used
            proxy_info = None
        
        request_time    = 0
        response_code   = 0
        response_md5    = None
        response_sha224 = None
        timed_out       = False
        response_size   = None
        
        try:
            
            # Make the HTTP object
            http = httplib2.Http(proxy_info=proxy_info, timeout=timeout, disable_ssl_certificate_validation=True)
            
            # Perform the request
            with Timer() as timer:
                response, content = http.request( url.geturl(), 'GET')
                
                # Get the hash of the content
                response_md5 = hashlib.md5(content).hexdigest()
                response_sha224 = hashlib.sha224(content).hexdigest()
                
                # Get the size of the content
                response_size = len(content)
                
            response_code = response.status    
            request_time = timer.msecs
            
        # Handle time outs    
        except socket.timeout:
            
            # Note that the connection timed out    
            timed_out = True
            
        except socket.error as e:
            
            if e.errno in [60, 61]:
                timed_out = True
                
        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            logger.exception("An error occurred when attempting to communicate with the proxy")
        
        except Exception as e:
            logger.exception("A general exception was thrown when executing a web request")
            
        # Finally, return the result
        return cls.Result(request_time, response_code, timed_out, url.geturl(), response_size, response_md5, response_sha224)
        
    def output_result(self, result, stanza, title, index=None, source=None, sourcetype=None, unbroken=True, close=True, proxy_server=None, proxy_port=None, proxy_user=None, proxy_type=None, out=sys.stdout ):
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
                
        return self.output_event(data, stanza, index=index, source=source, sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
        
    @staticmethod
    def get_file_path( checkpoint_dir, stanza ):
        """
        Get the path to the checkpoint file.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        return os.path.join( checkpoint_dir, hashlib.md5(stanza).hexdigest() + ".json" )
        
    @classmethod
    def last_ran( cls, checkpoint_dir, stanza ):
        """
        Determines the date that the analysis was last performed for the given input (denoted by the stanza name).
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza) )
            checkpoint_dict = json.load(fp)
                
            return checkpoint_dict['last_run']
    
        finally:
            if fp is not None:
                fp.close()
        
    @classmethod
    def needs_another_run(cls, checkpoint_dir, stanza, interval, cur_time=None):
        """
        Determines if the given input (denoted by the stanza name) ought to be executed.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        interval -- The frequency that the analysis ought to be performed
        cur_time -- The current time (will be automatically determined if not provided)
        """
        
        try:
            last_ran = cls.last_ran(checkpoint_dir, stanza)
            
            return cls.is_expired(last_ran, interval, cur_time)
            
        except IOError as e:
            # The file likely doesn't exist
            return True
        
        except ValueError as e:
            # The file could not be loaded
            return True
        
        # Default return value
        return True
    
    @classmethod
    def save_checkpoint(cls, checkpoint_dir, stanza, last_run):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza), 'w' )
            
            d = { 'last_run' : last_run }
            
            json.dump(d, fp)
            
        except Exception:
            logger.exception("Failed to save checkpoint directory") 
            
        finally:
            if fp is not None:
                fp.close()
    
    @staticmethod
    def is_expired( last_run, interval, cur_time=None ):
        """
        Indicates if the last run time is expired based .
        
        Arguments:
        last_run -- The time that the analysis was last done
        interval -- The interval that the analysis ought to be done (as an integer)
        cur_time -- The current time (will be automatically determined if not provided)
        """
        
        if cur_time is None:
            cur_time = time.time()
        
        if (last_run + interval) < cur_time:
            return True
        else:
            return False
        
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
            
            logger.debug("Proxy information loaded, stanza=%s", stanza)
            
        except splunk.ResourceNotFound:
            logger.error("Unable to find the proxy configuration for the specified configuration stanza=%s", stanza)
            raise
        
        return website_monitoring_config.proxy_type, website_monitoring_config.proxy_server, website_monitoring_config.proxy_port, website_monitoring_config.proxy_user, website_monitoring_config.proxy_password
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval      = cleaned_params["interval"]
        title         = cleaned_params["title"]
        url           = cleaned_params["url"]
        timeout       = self.timeout
        sourcetype    = cleaned_params.get("sourcetype", "web_ping")
        index         = cleaned_params.get("index", "default")
        conf_stanza   = cleaned_params.get("configuration", None)
        source        = stanza
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Get the proxy configuration
            try:
                proxy_type, proxy_server, proxy_port, proxy_user, proxy_password = self.get_proxy_config(input_config.session_key, conf_stanza)
            except splunk.ResourceNotFound:
                logger.error("The proxy configuration could not be loaded. The execution will be skipped for this input with stanza=%s", stanza)
                return
            
            # Perform the ping
            result = WebPing.ping(url, timeout, proxy_type, proxy_server, proxy_port, proxy_user, proxy_password)
            
            # Send the event
            self.output_result( result, stanza, title, index=index, source=source, sourcetype=sourcetype, unbroken=True, close=True, proxy_server=proxy_server, proxy_port=proxy_port, proxy_user=proxy_user, proxy_type=proxy_type )
            
            # Save the checkpoint so that we remember when we last 
            self.save_checkpoint(input_config.checkpoint_dir, stanza, int(time.time()) )
        
            
if __name__ == '__main__':
    try:
        web_ping = WebPing()
        web_ping.execute()
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception was caught, this may be due to a defect in the script") # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
        raise e