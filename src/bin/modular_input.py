import logging
from logging import handlers
from xml.dom.minidom import Document
import traceback
import xml.dom
import xml.sax.saxutils
import sys
import re
import time
import os
import hashlib
import json
from urlparse import urlparse

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

def setup_logger():
    """
    Setup a logger.
    """
    
    logger = logging.getLogger('python_modular_input')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)
    
    file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'python_modular_input.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Make a logger unless it already exists
try:
    logger
except NameError:
    logger = setup_logger()

class FieldValidationException(Exception):
    pass

class Field(object):
    """
    This is the base class that should be used to for field validators. Sub-class this and override to_python if you need custom validation.
    """
    
    DATA_TYPE_STRING = 'string'
    DATA_TYPE_NUMBER = 'number'
    DATA_TYPE_BOOLEAN = 'boolean'
    
    def get_data_type(self):
        """
        Get the type of the field.
        """
        
        return Field.DATA_TYPE_STRING 
    
    def __init__(self, name, title, description, none_allowed=False, empty_allowed=True, required_on_create=None, required_on_edit=None):
        """
        Create the field.
        
        Arguments:
        name -- Set the name of the field (e.g. "database_server")
        title -- Set the human readable title (e.g. "Database server")
        description -- Set the human readable description of the field (e.g. "The IP or domain name of the database server")
        none_allowed -- Is a value of none allowed?
        empty_allowed -- Is an empty string allowed?
        required_on_create -- Is this field required when creating?
        required_on_edit -- Is this field required when editing?
        """
        
        # Try to set required_on_create and required_on_edit to sane defaults if not defined
        if required_on_create is None and none_allowed:
            required_on_create = False
        elif required_on_create is None and not none_allowed:
            required_on_create = True
                
        if required_on_edit is None and required_on_create is not None:
            required_on_edit = required_on_create
        
        if name is None:
            raise ValueError("The name parameter cannot be none")

        if len(name.strip()) == 0:
            raise ValueError("The name parameter cannot be empty")
        
        if title is None:
            raise ValueError("The title parameter cannot be none")

        if len(title.strip()) == 0:
            raise ValueError("The title parameter cannot be empty")
        
        if description is None:
            raise ValueError("The description parameter cannot be none")

        if len(description.strip()) == 0:
            raise ValueError("The description parameter cannot be empty")
        
        self.name = name
        self.title = title
        self.description = description
        
        self.none_allowed = none_allowed
        self.empty_allowed = empty_allowed
        self.required_on_create = required_on_create
        self.required_on_edit = required_on_edit
    
    def to_python(self, value):
        """
        Convert the field to a Python object. Should throw a FieldValidationException if the data is invalid.
        
        Arguments:
        value -- The value to convert
        """
        
        if not self.none_allowed and value is None:
            raise FieldValidationException("The value for the '%s' parameter cannot be empty" % (self.name))
         
        if not self.empty_allowed and len(str(value).strip()) == 0:
            raise FieldValidationException("The value for the '%s' parameter cannot be empty" % (self.name))
        
        return value

    def to_string(self, value):
        """
        Convert the field to a string value that can be returned. Should throw a FieldValidationException if the data is invalid.
        
        Arguments:
        value -- The value to convert
        """
        
        return str(value)


class BooleanField(Field):
    
    def to_python(self, value):
        Field.to_python(self, value)
        
        if value in [True, False]:
            return value

        elif str(value).strip().lower() in ["true", "1"]:
            return True

        elif str(value).strip().lower() in ["false", "0"]:
            return False
        
        raise FieldValidationException("The value of '%s' for the '%s' parameter is not a valid boolean" % (str(value), self.name))

    def to_string(self, value):

        if value == True:
            return "1"

        elif value == False:
            return "0"
        
        return str(value)
    
    def get_data_type(self):
        return Field.DATA_TYPE_BOOLEAN
    
    
class ListField(Field):
    
    def to_python(self, value):
        
        Field.to_python(self, value)
        
        if value is not None:
            return value.split(",")
        else:
            return []
    
    def to_string(self, value):

        if value is not None:
            return ",".join(value)
        
        return ""
    
    
class RegexField(Field):
    
    def to_python(self, value):
        
        Field.to_python(self, value)
        
        if value is not None:
            try:
                return re.compile(value)
            except Exception as e:
                raise FieldValidationException(str(e))
        else:
            return None
    
    def to_string(self, value):

        if value is not None:
            return value.pattern
        
        return ""


class IntegerField(Field):
    
    def to_python(self, value):
        
        Field.to_python(self, value)
        
        if value is not None:
            try:
                return int(value)
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None
    
    def to_string(self, value):

        if value is not None:
            return str(value)
        
        return ""
    
    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER
    
    
class FloatField(Field):
    
    def to_python(self, value):
        
        Field.to_python(self, value)
        
        if value is not None:
            try:
                return float(value)
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None
    
    def to_string(self, value):

        if value is not None:
            return str(value)
        
        return ""
    
    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER

    
class RangeField(Field):

    def __init__(self, name, title, description, low, high, none_allowed=False, empty_allowed=True):
        super(RangeField, self).__init__(name, title, description, none_allowed=False, empty_allowed=True)
        self.low = low
        self.high = high
    
    def to_python(self, value):
        
        Field.to_python(self, value)
        
        if value is not None:
            try:
                tmp = int(value)
                return tmp >= self.low and tmp <= self.high
            except ValueError as e:
                raise FieldValidationException(str(e))
        else:
            return None
    
    def to_string(self, value):

        if value is not None:
            return str(value)
        
        return ""
    
    def get_data_type(self):
        return Field.DATA_TYPE_NUMBER

class URLField(Field):
    """
    Represents a URL. The URL is converted to a Python object that was created via urlparse.
    """
    
    @classmethod
    def parse_url(cls, value, name):
        parsed_value = urlparse(value)
        
        if parsed_value.hostname is None or len(parsed_value.hostname) <= 0:
            raise FieldValidationException("The value of '%s' for the '%s' parameter does not contain a host name" % (str(value), name))
        
        if parsed_value.scheme not in ["http", "https"]:
            raise FieldValidationException("The value of '%s' for the '%s' parameter does not contain a valid protocol (only http and https are supported)" % (str(value), name))
    
        return parsed_value
    
    def to_python(self, value):
        Field.to_python(self, value)
        
        return URLField.parse_url(value.strip(), self.name)
    
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

class ModularInputConfig():
    
    def __init__(self, server_host, server_uri, session_key, checkpoint_dir, configuration):
        self.server_host = server_host
        self.server_uri = server_uri
        self.session_key = session_key
        self.checkpoint_dir = checkpoint_dir
        self.configuration = configuration
        
    def __str__(self):
        attrs = ['server_host', 'server_uri', 'session_key', 'checkpoint_dir', 'configuration']
        return str({attr: str(getattr(self, attr)) for attr in attrs})
    
    @staticmethod
    def get_text(node, default=None):
        """
        Get the value of the text in the first node under the given node.
        
        Arguments:
        node -- The node that should have a text node under it.
        default -- The default text that ought to be returned if no text node could be found (defaults to none).
        """
        
        if node and node.firstChild and node.firstChild.nodeType == node.firstChild.TEXT_NODE:
            return node.firstChild.data
        else:
            return default
    
    @staticmethod
    def get_config_from_xml(config_str_xml):
        """
        Get the config from the given XML and return a ModularInputConfig instance.
        
        Arguments:
        config_str_xml -- A string of XML that represents the configuration provided by Splunk.
        """
        
        # Here are the parameters we are going to fill out
        server_host = None
        server_uri = None
        session_key = None
        checkpoint_dir = None
        configuration = {}
        
        # Parse the document
        doc = xml.dom.minidom.parseString(config_str_xml)
        root = doc.documentElement
        
        # Get the server_host
        server_host_node = root.getElementsByTagName("server_host")[0] 
        server_host = ModularInputConfig.get_text(server_host_node)
        
        # Get the server_uri
        server_uri_node = root.getElementsByTagName("server_uri")[0] 
        server_uri = ModularInputConfig.get_text(server_uri_node)
        
        # Get the session_key
        session_key_node = root.getElementsByTagName("session_key")[0] 
        session_key = ModularInputConfig.get_text(session_key_node)
        
        # Get the checkpoint directory
        checkpoint_node = root.getElementsByTagName("checkpoint_dir")[0] 
        checkpoint_dir = ModularInputConfig.get_text(checkpoint_node)
        
        # Parse the config
        conf_node = root.getElementsByTagName("configuration")[0]
        
        if conf_node:
            
            for stanza in conf_node.getElementsByTagName("stanza"):
                config = {}
                
                if stanza:
                    stanza_name = stanza.getAttribute("name")
                    
                    if stanza_name:
                        config["name"] = stanza_name
    
                        params = stanza.getElementsByTagName("param")
                        
                        for param in params:
                            param_name = param.getAttribute("name")
                            
                            config[param_name] = ModularInputConfig.get_text(param)
                            
                    configuration[stanza_name] = config

        return ModularInputConfig(server_host, server_uri, session_key, checkpoint_dir, configuration)


class ModularInput():
    
    # These arguments cover the standard fields that are always supplied
    standard_args = [
                Field("name", "Stanza name", "The name of the stanza for this modular input", empty_allowed=True),
                Field("stanza", "Stanza name", "The name of the stanza for this modular input", empty_allowed=True),
                Field("source", "Source", "The source for events created by this modular input", empty_allowed=True),
                Field("sourcetype", "Stanza name", "The name of the stanza for this modular input", empty_allowed=True, none_allowed=True),
                Field("index", "Index", "The index that data should be sent to", empty_allowed=True, none_allowed=True),
                Field("host", "Host", "The host that is running the input", empty_allowed=True),
                BooleanField("disabled", "Disabled", "Whether the modular input is disabled or not", empty_allowed=True)
                ]

    def _is_valid_param(self, name, val):
        '''Raise an error if the parameter is None or empty.'''
        if val is None:
            raise ValueError("The {0} parameter cannot be none".format(name))

        if len(val.strip()) == 0:
            raise ValueError("The {0} parameter cannot be empty".format(name))
        
        return val
    
    def _create_formatter_textnode(self, xmldoc, nodename, value):
        '''Shortcut for creating a formatter textnode.
        
        Arguments:
        xmldoc - A Document object.
        nodename - A string name for the node.
        '''
        node = xmldoc.createElement(nodename)
        text = xmldoc.createTextNode(str(value))
        node.appendChild(text)
        
        return node
                
    def _create_document(self):
        '''Create the document for sending XML streaming events.'''

        doc = Document()
        
        # Create the <stream> base element
        stream = doc.createElement('stream')
        doc.appendChild(stream)

        return doc
    
    def _create_event(self, doc, params, stanza, unbroken=False, close=True):
        '''Create an event for XML streaming output.
        
        Arguments:
        doc - a Document object.
        params - a dictionary of attributes for the event.
        stanza_name - the stanza
        '''

        # Create the <event> base element
        event = doc.createElement('event')
        
        # Indicate if this event is to be unbroken (meaning a </done> tag will 
        # need to be added by a future event.
        if unbroken:
            event.setAttribute('unbroken', '1')
        
        # Indicate if this script is single-instance mode or not.
        if self.streaming_mode == 'true':
            event.setAttribute('stanza', stanza)

        # Define the possible elements
        valid_elements = ['host', 'index', 'source', 'sourcetype', 'time', 'data']
        
        # Append the valid child elements. Invalid elements will be dropped.
        for element in filter(lambda x: x in valid_elements, params.keys()):
            event.appendChild(self._create_formatter_textnode(doc, element, params[element]))
            
        if close:
            event.appendChild(doc.createElement('done'))
        
        return event
    
    def _print_event(self, doc, event):
        '''Adds an event to XML streaming output.'''

        # Get the stream from the document.
        stream = doc.firstChild
        
        # Append the event.
        stream.appendChild(event)

        # Return the content as a string WITHOUT the XML header; remove the
        # child object so the next event can be returned and reuse the same
        # Document object.
        output = doc.documentElement.toxml()
        
        stream.removeChild(event)
        
        return output
        
    def _add_events(self, doc, events):
        '''Adds a set of events to XML streaming output.'''

        # Get the stream from the document.
        stream = doc.firstChild
        
        # Add the <event> node.
        for event in events:
            stream.appendChild(event)

        # Return the content as a string WITHOUT the XML header.
        return doc.documentElement.toxml()
    
    def escape_spaces(self, s):
        """
        If the string contains spaces, then add double quotes around the string. This is useful when outputting fields and values to Splunk since a space will cause Splunk to not recognize the entire value.
        
        Arguments:
        s -- A string to escape.
        """
        
        # Make sure the input is a string
        if s is not None:
            s = str(s)
        
        if s is not None and " " in s:
            return '"' + s + '"'
        
        else:
            return s
    
    def create_event_string(self, data_dict, stanza, sourcetype, source, index, host=None, unbroken=False, close=False ):
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
        data_str = ''
        
        for k, v in data_dict.items():
            
            # If the value is a list, then write out each matching value with the same name (as mv)
            if isinstance(v, list) and not isinstance(v, basestring):
                values = v
            else:
                values = [v]
            
            k_escaped = self.escape_spaces(k)
            
            # Write out each value
            for v in values:
                v_escaped = self.escape_spaces(v)
                
                
                if len(data_str) > 0:
                    data_str += ' '
                
                data_str += '%s=%s' % (k_escaped, v_escaped)
        
        # Make the event
        event_dict = {'stanza': stanza,
                      'data' : data_str}
        
        if index is not None:
            event_dict['index'] = index
            
        if sourcetype is not None:
            event_dict['sourcetype'] = sourcetype
            
        if source is not None:
            event_dict['source'] = source
            
        if host is not None:
            event_dict['host'] = host
        
        event = self._create_event(self.document, 
                                   params=event_dict,
                                   stanza=stanza,
                                   unbroken=False,
                                   close=False)
        
        # If using unbroken events, the last event must have been 
        # added with a "</done>" tag.
        return self._print_event(self.document, event)
        
    def output_event(self, data_dict, stanza, index=None, sourcetype=None, source=None, host=None, unbroken=False, close=False, out=sys.stdout ):
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
        host -- The host
        """
        
        output = self.create_event_string(data_dict, stanza, sourcetype, source, index, host, unbroken, close)
        
        out.write(output)
        out.flush()
    
    def __init__(self, scheme_args, args=None, sleep_interval=5):
        """
        Set up the modular input.
        
        Arguments:
        title -- The title of the modular input (e.g. "Database Connector")
        description -- A description of the input (e.g. "Get data from a database")
        args -- A list of Field instances for validating the arguments
        sleep_interval -- How often to sleep between runs
        """
        
        # Setup defaults
        default_scheme_args = {
                               "use_external_validation" : "true",
                               "streaming_mode" : "xml",
                               "use_single_instance" : "true"
        }
        
        scheme_args = dict(default_scheme_args.items() + scheme_args.items())
        
        # Set the scheme arguments.
        for arg in scheme_args:
            setattr(self, arg, self._is_valid_param(arg, scheme_args.get(arg)))
                
        if args is None:
            self.args = []
        else:
            self.args = args[:]
            
        if sleep_interval > 0:
            self.sleep_interval = sleep_interval
        else:
            self.sleep_interval = 5
            
        # Create the document used for sending events to Splunk through
        self.document = self._create_document()
                    
    def addArg(self, arg):
        """
        Add a given argument to the list of arguments.
        
        Arguments:
        arg -- An instance of Field that represents an argument.
        """
        
        if self.args is None:
            self.args = []
            
        self.args.append(arg)
    
    def usage(self, out=sys.stdout):
        """
        Print a usage statement.
        
        Arguments:
        out -- The stream to write the message to (defaults to standard output)
        """
        
        out.write("usage: %s [--scheme|--validate-arguments]")
    
    def do_scheme(self, out=sys.stdout):
        """
        Get the scheme and write it out to standard output.
        
        Arguments:
        out -- The stream to write the message to (defaults to standard output)
        """
        
        logger.info("Modular input: scheme requested")
        out.write(self.get_scheme())
        
        return True
        
    def get_scheme(self):
        """
        Get the scheme of the inputs parameters and return as a string.
        """
        
        # Create the XML document
        doc = Document()
        
        # Create the <scheme> base element
        element_scheme = doc.createElement("scheme")
        doc.appendChild(element_scheme)
        
        # Create the title element
        element_title = doc.createElement("title")
        element_scheme.appendChild(element_title)
        
        element_title_text = doc.createTextNode(self.title)
        element_title.appendChild(element_title_text)
        
        # Create the description element
        element_desc = doc.createElement("description")
        element_scheme.appendChild(element_desc)
        
        element_desc_text = doc.createTextNode(self.description)
        element_desc.appendChild(element_desc_text)
        
        # Create the use_external_validation element
        element_external_validation = doc.createElement("use_external_validation")
        element_scheme.appendChild(element_external_validation)
        
        element_external_validation_text = doc.createTextNode(self.use_external_validation)
        element_external_validation.appendChild(element_external_validation_text)
        
        # Create the streaming_mode element
        element_streaming_mode = doc.createElement("streaming_mode")
        element_scheme.appendChild(element_streaming_mode)
        
        element_streaming_mode_text = doc.createTextNode(self.streaming_mode)
        element_streaming_mode.appendChild(element_streaming_mode_text)

        # Create the use_single_instance element
        element_use_single_instance = doc.createElement("use_single_instance")
        element_scheme.appendChild(element_use_single_instance)
        
        element_use_single_instance_text = doc.createTextNode(self.use_single_instance)
        element_use_single_instance.appendChild(element_use_single_instance_text)
        
        # Create the elements to stored args element
        element_endpoint = doc.createElement("endpoint")
        element_scheme.appendChild(element_endpoint)
        
        element_args = doc.createElement("args")
        element_endpoint.appendChild(element_args)
        
        # Create the argument elements
        self.add_xml_args(doc, element_args)
        
        # Return the content as a string
        return doc.toxml()
        
    def add_xml_args(self, doc, element_args):
        """
        Add the arguments to the XML scheme.
        
        Arguments:
        doc -- The XML document
        element_args -- The element that should be the parent of the arg elements that will be added.
        """
        
        for arg in self.args:
            element_arg = doc.createElement("arg")
            element_arg.setAttribute("name", arg.name)
            
            element_args.appendChild(element_arg)
            
            # Create the title element
            element_title = doc.createElement("title")
            element_arg.appendChild(element_title)
            
            element_title_text = doc.createTextNode(arg.title)
            element_title.appendChild(element_title_text)
            
            # Create the description element
            element_desc = doc.createElement("description")
            element_arg.appendChild(element_desc)
            
            element_desc_text = doc.createTextNode(arg.description)
            element_desc.appendChild(element_desc_text)
            
            # Create the data_type element
            element_data_type = doc.createElement("data_type")
            element_arg.appendChild(element_data_type)
            
            element_data_type_text = doc.createTextNode(arg.get_data_type())
            element_data_type.appendChild(element_data_type_text)
            
            # Create the required_on_create element
            element_required_on_create = doc.createElement("required_on_create")
            element_arg.appendChild(element_required_on_create)
            
            element_required_on_create_text = doc.createTextNode("true" if arg.required_on_create else "false")
            element_required_on_create.appendChild(element_required_on_create_text)

            # Create the required_on_save element
            element_required_on_edit = doc.createElement("required_on_edit")
            element_arg.appendChild(element_required_on_edit)
            
            element_required_on_edit_text = doc.createTextNode("true" if arg.required_on_edit else "false")
            element_required_on_edit.appendChild(element_required_on_edit_text)
        
    def do_validation(self, in_stream=sys.stdin):
        """
        Get the validation data from standard input and attempt to validate it. Returns true if the arguments validated, false otherwise.
        
        Arguments:
        in_stream -- The stream to get the input from (defaults to standard input)
        """
        
        data = self.get_validation_data()
        
        try:
            self.validate_parameters(None, data)
            return True
        except FieldValidationException as e:
            self.print_error(str(e))
            return False
            
    def validate(self, arguments):
        """
        Validate the argument dictionary where each key is a stanza.
        
        Arguments:
        arguments -- The arguments as an dictionary where the key is the stanza and the value is a dictionary of the values.
        """
        
        # Check each stanza
        for stanza, parameters in arguments.items():
            self.validate_parameters(stanza, parameters)
        return True
            
    def validate_parameters(self, stanza, parameters):
        """
        Validate the parameter set for a stanza and returns a dictionary of cleaner parameters.
        
        Arguments:
        stanza -- The stanza name
        parameters -- The list of parameters
        """
        
        cleaned_params = {}
        
        # Append the arguments list such that the standard fields that Splunk provides are included
        all_args = {}
        
        for a in self.standard_args:
            all_args[a.name] = a
        
        for a in self.args:
            all_args[a.name] = a
        
        # Convert and check the parameters
        for name, value in parameters.items():
            
            # If the argument was found, then validate and convert it
            if name in all_args:
                cleaned_params[name] = all_args[name].to_python(value)
                
            # Throw an exception if the argument could not be found
            else:
                raise FieldValidationException("The parameter '%s' is not a valid argument" % (name))
            
        return cleaned_params
            
    def print_error(self, error, out=sys.stdout):
        """
        Prints the given error message to standard output.
        
        Arguments:
        error -- The message to be printed
        out -- The stream to write the message to (defaults to standard output)
        """
        
        out.write("<error><message>%s</message></error>" % error)
    
    def read_config(self, in_stream=sys.stdin):
        """
        Read the config from standard input and return the configuration.
        
        in_stream -- The stream to get the input from (defaults to standard input)
        """
        
        config_str_xml = in_stream.read()
        
        return ModularInputConfig.get_config_from_xml(config_str_xml)            
    
    def run(self, stanza, cleaned_params):
        """
        Run the input using the arguments provided.
        
        Arguments:
        stanza -- The name of the stanza
        cleaned_params -- The arguments following validation and conversion to Python objects.
        """
        
        raise Exception("Run function was not implemented")
    
    @classmethod
    def is_expired( cls, last_run, interval, cur_time=None ):
        """
        Indicates if the last run time is expired based on the value of the last_run parameter.
        
        Arguments:
        last_run -- The time that the analysis was last done
        interval -- The interval that the analysis ought to be done (as an integer)
        cur_time -- The current time (will be automatically determined if not provided)
        """
        
        if cur_time is None:
            cur_time = time.time()
        
        if last_run is None:
            return True
        elif (last_run + interval) < cur_time:
            return True
        else:
            return False
    
    @classmethod
    def last_ran( cls, checkpoint_dir, stanza ):
        """
        Determines the date that the analysis was last performed for the given input (denoted by the stanza name).
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        checkpoint_dict = cls.get_checkpoint_data(checkpoint_dir, stanza)
        
        if checkpoint_dict is None or 'last_run' not in checkpoint_dict:
            return None
        else:
            return checkpoint_dict['last_run']
    
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
    def get_file_path(cls, checkpoint_dir, stanza):
        """
        Get the path to the checkpoint file.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """
        
        return os.path.join( checkpoint_dir, hashlib.sha224(stanza).hexdigest() + ".json" )
    
    @classmethod
    def get_checkpoint_data(cls, checkpoint_dir, stanza="(undefined)", throw_errors=False):
        """
        Gets the checkpoint for this input (if it exists)
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        throw_errors -- If false, then None will be returned if the data could not be loaded
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza) )
            checkpoint_dict = json.load(fp)
            
            return checkpoint_dict
        
        except IOError:
            if throw_errors:
                raise
            else:
                return None
        
        finally:
            if fp is not None:
                fp.close()
             
    @classmethod
    def get_non_deviated_last_run(cls, last_ran, interval, stanza):
        """
        This method will return a last_run time that doesn't carry over the processing time.
        If you used the current time and the script took 5 seconds to run, then next run will actually be 5 seconds after it should have been.
        
        Basically, it computes when the interval _should_ have executed so that the input runs on the correct frequency.
        
        Arguments:
        interval -- The execution interval
        last_ran -- When the input last ran (Unix epoch).
        stanza -- The stanza that this is for
        """
        
        # If this is the first run, then set it to the current time
        if last_ran is None:
            return time.time()
        
        # We don't want the input to interval to slide by including the processing time in the interval. In other words, if the interval is 60 and it takes 5 seconds to process,
        # then we don't just want to set the last_run to now because then the interval would actually be 65 seconds. So, let's assume that the processing time was 0 and we are
        # right on time. If we assume this, then we would have ran at last_run + interval exactly. 
        # There is a potential problem with this though. We'll deal with that in a bit.
        last_ran_derived = last_ran + interval
                
        # There is a one problem with correcting the last run to the previous time plus the interval. If the input failed to run for a long time, then we might keep creating a
        # last_run that is in the past and thus, keep executing the input until we finally come to the current time. I would rather just skip the ones in the past and start back
        # over. That is what we will do.
        if last_ran_derived < (time.time() - interval):
            # The last run isn't within one interval of the current time. That means we either ran too long and missed a subsequent run or we just weren't running for a long-time.
            # To catch up, we'll set it to the current time
            last_ran_derived = time.time()
            
            logger.info("Previous run was too far in the past (gap=%r) and thus some executions of the input have been missed (stanza=%s)", last_ran_derived-last_ran, stanza)
            
        #logger.info("Calculated non-deviated last_ran=%r from previous_last_ran=%r", last_ran_derived, last_ran)
        return last_ran_derived
             
    @classmethod   
    def save_checkpoint_data(cls, checkpoint_dir, stanza, data):
        """
        Save the checkpoint state.
        
        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        data -- A dictionary with the data to save
        """
        
        fp = None
        
        try:
            fp = open( cls.get_file_path(checkpoint_dir, stanza), 'w' )
            
            json.dump(data, fp)
            
        except Exception:
            logger.exception("Failed to save checkpoint directory") 
            
        finally:
            if fp is not None:
                fp.close()
    
    def do_shutdown(self):
        """
        This function is called when the modular input should shut down.
        """
        
        pass
    
    def do_run(self, in_stream=sys.stdin, log_exception_and_continue=False):
        """
        Read the config from standard input and return the configuration.
        
        in_stream -- The stream to get the input from (defaults to standard input)
        log_exception_and_continue -- If true, exceptions will not be thrown for invalid configurations and instead the stanza will be skipped.
        """
        
        # Run the modular import
        input_config = self.read_config(in_stream)
                
        while True:
                                
            # If Splunk is no longer the parent process, then it has shut down and this input needs to terminate
            if hasattr(os, 'getppid') and os.getppid() == 1:
                logging.warn("Modular input is no longer running under Splunk; script will now exit")
                self.do_shutdown()
                sys.exit(2)
            
            # Initialize the document that will be used to output the results
            self.document = self._create_document()
            
            for stanza, conf in input_config.configuration.items():
                        
                try:
                    cleaned_params = self.validate_parameters(stanza, conf)
                    self.run(stanza, 
                        cleaned_params,
                        input_config)
                except FieldValidationException as e:
                    if log_exception_and_continue:
                        logger.error("The input stanza '%s' is invalid: %s" % (stanza, str(e)))
                    else:
                        raise e
                    
            # Sleep for a bit
            try:
                time.sleep(self.sleep_interval)
            except IOError:
                pass #Exceptions such as KeyboardInterrupt and IOError can be thrown in order to interrupt sleep calls
                
    def get_validation_data(self, in_stream=sys.stdin):
        """
        Get the validation data from standard input
        
        Arguments:
        in_stream -- The stream to get the input from (defaults to standard input)
        """
        
        val_data = {}
    
        # Read everything from stdin
        val_str = in_stream.read()
    
        # Parse the validation XML
        doc = xml.dom.minidom.parseString(val_str)
        root = doc.documentElement
    
        item_node = root.getElementsByTagName("item")[0]
        if item_node:
    
            name = item_node.getAttribute("name")
            val_data["stanza"] = name
    
            params_node = item_node.getElementsByTagName("param")
            
            for param in params_node:
                name = param.getAttribute("name")
                
                if name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                    val_data[name] = param.firstChild.data
    
        return val_data
    
    def validate_parameters_from_cli(self, argument_array=None):
        """
        Load the arguments from the given array (or from the command-line) and validate them.
        
        Arguments:
        argument_array -- An array of arguments (will get them from the command-line arguments if none)
        """
        
        # Get the arguments from the sys.argv if not provided
        if argument_array is None:
            argument_array = sys.argv[1:]
        
        # This is the list of parameters we will generate
        parameters = {}
        
        for i in range(0, len(self.args)):
            arg = self.args[i]
            
            if i < len(argument_array):
                parameters[arg.name] = argument_array[i]
            else:
                parameters[arg.name] = None
        
        # Now that we have simulated the parameters, go ahead and test them
        self.validate_parameters("unnamed", parameters)
    
    def execute(self, in_stream=sys.stdin, out_stream=sys.stdout):
        """
        Get the arguments that were provided from the command-line and execute the script.
        
        Arguments:
        in_stream -- The stream to get the input from (defaults to standard input)
        out_stream -- The stream to write the output to (defaults to standard output)
        """
        
        try:
            logger.info("Execute called")
            
            if len(sys.argv) > 1:
                if sys.argv[1] == "--scheme":
                    self.do_scheme(out_stream)
                    
                elif sys.argv[1] == "--validate-arguments":
                    logger.info("Modular input: validate arguments called")
                    
                    # Exit with a code of -1 if validation failed
                    if self.do_validation() == False:
                        sys.exit(-1)
                    
                else:
                    self.usage(out_stream)
            else:
                
                # Run the modular input
                self.do_run(in_stream, log_exception_and_continue=True)
                
            logger.info("Execution completed successfully")
            
        except Exception as e:
            
            logger.error("Execution failed: %s", ( traceback.format_exc() ))
            
            # Make sure to grab any exceptions so that we can print a valid error message
            self.print_error(str(e), out_stream)