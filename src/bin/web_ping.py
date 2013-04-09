
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from modular_input import Field, FieldValidationException, ModularInput

import re
import logging
from logging import handlers
import httplib
import hashlib
import socket
import json
from urlparse import urlparse
import sys
import time
import os

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('web_availability_modular_input')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'web_availability_modular_input.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

class URLField(Field):
    
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
    def __init__(self, verbose=False):
        self.verbose = verbose

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs

class WebPing(ModularInput):
    
    PARSE_URL_RE = re.compile( r"http[s]?[:]//(.*)", re.IGNORECASE)
    
    class Result(object):
        
        def __init__(self, connection_time, request_time, response_code, timed_out, url):
            
            self.request_time = request_time
            self.connection_time = connection_time
            self.response_code = response_code
            self.timed_out = timed_out
            self.url = url
            
        @property
        def total_time(self):
            return self.connection_time + self.request_time
    
    def __init__(self, timeout=30):

        scheme_args = {'title': "Website Availability Check",
                       'description': "Connects to a website in order to obtain performance statistics",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}
        
        args = [
                Field("title", "Title", "A short description (typically just the domain name)", empty_allowed=False),
                URLField("url", "URL", "The URL to connect to (must be be either HTTP or HTTPS protocol)", empty_allowed=False),
                DurationField("interval", "Interval", "The interval defining how often to perform the check; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False)
                ]
        
        ModularInput.__init__( self, scheme_args, args )
        
        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 30
        
    @classmethod
    def ping(cls, url, timeout=30):
        
        logger.debug('Performing ping, url="%s"', url.geturl())
        
        # Make the connection
        if( url.scheme == 'https' ):
            connection = httplib.HTTPSConnection(url.netloc, timeout=timeout)
        else:
            connection = httplib.HTTPConnection(url.netloc, timeout=timeout)
            
        connection_time = 0
        request_time    = 0
        response_code   = 0
        timed_out       = False
        
        try:
            
            # Connect to the host
            with Timer() as timer:
                connection.connect()
            
            connection_time = timer.msecs
                
            # Perform the request
            with Timer() as timer:
                connection.request("GET", url.path)
                response = connection.getresponse()
                
                response_code = response.status
            
            request_time = timer.msecs
            
        # Handle time outs    
        except socket.timeout:
            
            # Note that the connection timed out    
            timed_out = True
            
        except socket.error as e:
            
            if e.errno in [60, 61]:
                timed_out = True
            
        finally:
            
            # Make sure to always close the connection
            connection.close()
            
        # Finally, return the result
        return cls.Result( connection_time, request_time, response_code, timed_out, url.geturl())
        
    def send_result(self, result, stanza, title, index=None, source=None, sourcetype=None, unbroken=True, close=True, out=sys.stdout ):
        
        data = {
                'response_code': result.response_code if result.response_code > 0 else '',
                'connection_time': round(result.connection_time ,2) if result.connection_time > 0 else '',
                'request_time': round(result.request_time, 2) if result.request_time > 0 else '',
                'total_time': round(result.total_time, 2) if result.total_time > 0 else '',
                'timed_out': result.timed_out,
                'title': title,
                'url': result.url
                }
        
        return self.send_event(data, stanza, index=index, source=source, sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
        
    def create_event_string(self, data_dict, stanza, sourcetype, source, index, unbroken=False, close=False ):
        
        # Make the content of the event
        data_str   = ''
        
        for k, v in data_dict.items():
            data_str += ' %s=%s' % (k, v)
        
        # Make the event
        event_dict = {'stanza': stanza,
                      'data' : data_str}
        
        
        if index is not None:
            event_dict['index'] = index
            
        if sourcetype is not None:
            event_dict['sourcetype'] = sourcetype
            
        if source is not None:
            event_dict['source'] = source
        
        event = self._create_event(self.document, 
                                   params=event_dict,
                                   stanza=stanza,
                                   unbroken=False,
                                   close=False)
        
        # If using unbroken events, the last event must have been 
        # added with a "</done>" tag.
        return self._print_event(self.document, event)
        
    def send_event(self, data_dict, stanza, index=None, sourcetype=None, source=None, unbroken=False, close=False, out=sys.stdout ):
        
        output = self.create_event_string(data_dict, stanza, sourcetype, source, index, unbroken, close)
        
        out.write(output)
        out.flush()
        
    @staticmethod
    def get_file_path( checkpoint_dir, stanza ):
        return os.path.join( checkpoint_dir, hashlib.md5(stanza).hexdigest() + ".json" )
        
    @classmethod
    def last_ran( cls, checkpoint_dir, stanza ):
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
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza), 'w' )
            
            d = { 'last_run' : last_run }
            
            json.dump(d, fp)
        except:
            if fp is not None:
                fp.close()
    
    @staticmethod
    def is_expired( last_run, interval, cur_time=None ):
        
        if cur_time is None:
            cur_time = time.time()
        
        if (last_run + interval) < cur_time:
            return True
        else:
            return False
        
    def run(self, stanza, cleaned_params, input_config):
        
        interval   = cleaned_params["interval"]
        title      = cleaned_params["title"]
        url        = cleaned_params["url"]
        timeout    = self.timeout
        sourcetype = "web_availability_check"
        index      = "main"
        source     = "web_availability_check"
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Perform the ping
            result = WebPing.ping(url, timeout)
            
            # Send the event
            self.send_result( result, stanza, title, index=index, source=source, sourcetype=sourcetype, unbroken=True, close=True )
            
            self.save_checkpoint(input_config.checkpoint_dir, stanza, int(time.time()) )
        
            
if __name__ == '__main__':
    web_ping = WebPing()
    web_ping.execute()
    sys.exit(0)