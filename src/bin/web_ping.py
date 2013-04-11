
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

class WebPing(ModularInput):
    """
    The web ping modular input connects to a website to determine if the site is operational and tracks the time it takes to respond.
    """
    
    PARSE_URL_RE = re.compile( r"http[s]?[:]//(.*)", re.IGNORECASE)
    
    class Result(object):
        """
        The results object designates the results of connecting to a website.
        """
        
        def __init__(self, connection_time, request_time, response_code, timed_out, url):
            
            self.request_time = request_time
            self.connection_time = connection_time
            self.response_code = response_code
            self.timed_out = timed_out
            self.url = url
            
        @property
        def total_time(self):
            """
            Returns the total time it took to get a response from a website including both the connection time and the HTTP response time.
            """
            
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
        """
        Perform a ping to a website. Returns a WebPing.Result instance.
        
        Argument:
        url -- The url to connect to. This object ought to be an instance derived from using urlparse.
        timeout -- The amount of time to quit waiting on a connection.
        """
        
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
        
    def output_result(self, result, stanza, title, index=None, source=None, sourcetype=None, unbroken=True, close=True, out=sys.stdout ):
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
                'connection_time': round(result.connection_time ,2) if result.connection_time > 0 else '',
                'request_time': round(result.request_time, 2) if result.request_time > 0 else '',
                'total_time': round(result.total_time, 2) if result.total_time > 0 else '',
                'timed_out': result.timed_out,
                'title': title,
                'url': result.url
                }
        
        return self.output_event(data, stanza, index=index, source=source, sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)
        
    def create_event_string(self, data_dict, stanza, sourcetype, source, index, unbroken=False, close=False ):
        """
        Create a string representing the event.
        
        Argument:
        data_dict -- A dictionary containing the fields
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source field value
        index -- The index to send the event to
        unbroken -- 
        close -- 
        """
        
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
        
    def output_event(self, data_dict, stanza, index=None, sourcetype=None, source=None, unbroken=False, close=False, out=sys.stdout ):
        """
        Output the given even so that Splunk can see it.
        
        Arguments:
        data_dict -- A dictionary containing the fields
        stanza -- The stanza used for the input
        sourcetype -- The sourcetype
        source -- The source to use
        index -- The index to send the event to
        unbroken -- 
        close -- 
        out -- The stream to send the event to (defaults to standard output)
        """
        
        output = self.create_event_string(data_dict, stanza, sourcetype, source, index, unbroken, close)
        
        out.write(output)
        out.flush()
        
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
        
    def run(self, stanza, cleaned_params, input_config):
        
        # Make the parameters
        interval   = cleaned_params["interval"]
        title      = cleaned_params["title"]
        url        = cleaned_params["url"]
        timeout    = self.timeout
        sourcetype = "web_ping"
        index      = cleaned_params["index"]
        source     = stanza
        
        if self.needs_another_run( input_config.checkpoint_dir, stanza, interval ):
            
            # Perform the ping
            result = WebPing.ping(url, timeout)
            
            # Send the event
            self.output_result( result, stanza, title, index=index, source=source, sourcetype=sourcetype, unbroken=True, close=True )
            
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