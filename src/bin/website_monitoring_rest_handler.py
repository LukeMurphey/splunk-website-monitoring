import splunk.admin as admin
import splunk.entity as entity
import splunk
import logging
import logging.handlers
import os
import re
import copy

class StandardFieldValidator(object):
    """
    This is the base class that should be used to for field validators.
    """
    
    def to_python(self, name, value):
        """
        Convert the field to a Python object. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """
        
        if value is None:
            raise admin.ArgValidationException("The value for the '%s' parameter cannot be none" % (name))
        
        if len( str(value).strip() ) == 0:
            raise admin.ArgValidationException("The value for the '%s' parameter cannot be empty" % (name))
        
        return value

    def to_string(self, name, value):
        """
        Convert the field to a string that can be persisted to a conf file. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """
        
        if value is None:
            return ""
        else:
            return str(value)

class BooleanFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent booleans.
    """
    
    def to_python(self, name, value):
        if value in [True, False]:
            return value

        elif str(value).strip().lower() in ["true", "1"]:
            return True

        elif str(value).strip().lower() in ["false", "0"]:
            return False
        
        raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid boolean" % ( str(value), name))

    def to_string(self, name, value):

        if value == True:
            return "1"

        elif value == False:
            return "0"
        
        return super(BooleanFieldValidator, self).to_string(name, value)
    
class IntegerFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent integers.
    """
    
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value
    
    def to_python(self, name, value):
        
        if value is None:
            return None
        
        int_value = int( str(value).strip() )
        
        # Make sure that the value is at least the minimum
        if self.min_value is not None and int_value < self.min_value:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not valid, it must be at least %s" % ( str(value), name, self.min_value))
            
        # Make sure that the value is no greater than the maximum
        if self.max_value is not None and int_value > self.max_value:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not valid, it must be not be greater than %s" % ( str(value), name, self.max_value))
        
        try:
            return int( str(value).strip() )
        except ValueError:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid integer" % ( str(value), name))

    def to_string(self, name, value):

        if value is None or len(str(value).strip()) == 0:
            return None

        else:
            return super(IntegerFieldValidator, self).to_string(name, value)
    
class FieldSetValidator():
    """
    This base class is for validating sets of fields.
    """
    
    def validate(self, name, values):
        """
        Validate the values. Should throw a ArgValidationException if the data is invalid.
        
        Arguments:
        name -- The name of the object, used for error messages
        values -- The value to convert (in a dictionary)
        """
        
        pass
    
class ListValidator(StandardFieldValidator):
    """
    Validates and converts field that represents a list (comma or colon separated).
    """
    
    LIST_SPLIT  = re.compile("[:,]*")
    
    def to_python(self, name, value):
        
        # Treat none as an empty list
        if value is None:
            return []
        
        split_list = ListValidator.LIST_SPLIT.split(value)
        
        return split_list

    def to_string(self, name, value):
        
        if value is None:
            return ""
        else:
            # Rebuild the list as comma separated list in order to normalize it
            return ",".join( value )
        
class HostFieldValidator(StandardFieldValidator):
    """
    Validates and converts host fields that represent DNS names or IP addresses.
    """
    
    def to_python(self, name, value):
        
        if value is None:
            return value
        
        elif not self.is_valid_hostname(value):
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid host name or IP" % ( str(value), name))
        
        return value
        
    def is_valid_hostname(self, hostname):
        
        ip_address_re = re.compile("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$");
        hostname_re = re.compile("^(([a-zA-Z0-9_]|[a-zA-Z0-9_][a-zA-Z0-9\-_]*[a-zA-Z0-9_])\.)*([A-Za-z0-9_]|[A-Za-z0-9_][A-Za-z0-9\-_]*[A-Za-z0-9_])$");
        
        if ip_address_re.match(hostname) or hostname_re.match(hostname):
            return True
        else:
            return False
    
class ProxyTypeFieldValidator(StandardFieldValidator):
    """
    Validates proxy types.
    """
    
    def to_python(self, name, value):
        
        if value is None:
            return None
        
        # Prepare the string so that the proxy type can be matched more reliably
        t = value.strip().lower()
        
        if t not in ["socks4", "socks5", "http", ""]:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid proxy type" % ( str(value), name))
        
        return t

def log_function_invocation(fx):
    """
    This decorator will provide a log message for when a function starts and stops.
    
    Arguments:
    fx -- The function to log the starting and stopping of
    """
    
    def wrapper(self, *args, **kwargs):
        logger.debug( "Entering: " + fx.__name__ )
        r = fx(self, *args, **kwargs)
        logger.debug( "Exited: " + fx.__name__ )
        
        return r
    return wrapper

def setup_logger(level, name, file_name, use_rotating_handler=True):
    """
    Setup a logger for the REST handler.
    
    Arguments:
    level -- The logging level to use
    name -- The name of the logger to use
    file_name -- The file name to log to
    use_rotating_handler -- Indicates whether a rotating file handler ought to be used
    """
    
    logger = logging.getLogger(name)
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    
    log_file_path = os.path.join( os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', file_name)
    
    if use_rotating_handler:
        file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=25000000, backupCount=5)
    else:
        file_handler = logging.FileHandler(log_file_path)
        
    formatter = logging.Formatter('%(asctime)s %(levelname)s ' + name + ' - %(message)s')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger

# Setup the handler
logger = setup_logger(logging.DEBUG, "WebsiteMonitoringRestHandler", "website_monitoring_rest_handler.log")

class WebsiteMonitoringRestHandler(admin.MConfigHandler):
    """
    The REST handler provides configuration management for web ping.
    """
    
    # Below is the name of the conf file
    CONF_FILE = 'website_monitoring'
    
    # Below are the list of parameters that are accepted
    PARAM_DEBUG            = 'debug'
    PARAM_PROXY_SERVER     = 'proxy_server'
    PARAM_PROXY_PORT       = 'proxy_port'
    PARAM_PROXY_USER       = 'proxy_user'
    PARAM_PROXY_PASSWORD   = 'proxy_password'
    PARAM_PROXY_TYPE       = 'proxy_type'
    
    # Below are the list of valid and required parameters
    VALID_PARAMS           = [ PARAM_DEBUG, PARAM_PROXY_SERVER, PARAM_PROXY_PORT, PARAM_PROXY_USER, PARAM_PROXY_PASSWORD, PARAM_PROXY_TYPE ]
    
    REQUIRED_PARAMS        = []
    
    # These are parameters that are not persisted to the conf files; these are used within the REST handler only
    UNSAVED_PARAMS         = [  ]
    
    # List of fields and how they will be validated
    FIELD_VALIDATORS = {
        PARAM_DEBUG            : BooleanFieldValidator(),
        PARAM_PROXY_SERVER     : HostFieldValidator(),
        PARAM_PROXY_PORT       : IntegerFieldValidator(0, 65535),
        PARAM_PROXY_TYPE       : ProxyTypeFieldValidator()
        
    }
    
    # This field designates the fields that the REST handler ought to allow fields with similar values using dot syntax (value.1, value.2, etc).
    # For these fields, instances containing what looks like the dot syntax will use the validator based on the item without the dot syntax.
    # Thus, the field "value.1.name" will be validated by whatever item validates "value.name".
    MULTI_FIELDS = [ ]
    MULTI_FIELD_RE = re.compile("(?P<prefix>.*)[.][0-9]+(?P<suffix>.*)")
    
    # These are validators that work across several fields and need to occur on the cleaned set of fields
    GENERAL_VALIDATORS = [ ]
    
    # General variables
    APP_NAME         = "website_monitoring"
    
    def setup(self):
        """
        Setup the required and optional arguments
        """
        
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:
            
            # Set the required parameters
            for arg in self.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
            
            # Set up the valid parameters
            for arg in self.VALID_PARAMS:
                if arg not in self.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)
    
    @classmethod
    def removeMultiFieldSpecifier(cls, name):
        """
        Remove the multi-field specifier if the field is supposed to be support mulitple instances using the dot syntax (value.1, value.2, etc).
        
        Arguments:
        name -- The name of the field.
        """
        
        # Stop if we don't have any multi-fields
        if cls.MULTI_FIELDS is None:
            return name
        
        m = cls.MULTI_FIELD_RE.match(name)
        
        if m and m.groups()[0] in cls.MULTI_FIELDS:
            logger.debug("removeMultiFieldSpecifier: " + name + " to " + m.groups()[0] + m.groups()[1])
            return m.groups()[0] + m.groups()[1]
        else:
            return name
    
    @classmethod
    def convertParams(cls, name, params, to_string=False):
        """
        Convert so that they can be saved to the conf files and validate the parameters.
        
        Arguments:
        name -- The name of the stanza being processed (used for exception messages)
        params -- The dictionary containing the parameter values
        to_string -- If true, a dictionary containing strings is returned; otherwise, the objects are converted to the Python equivalents
        """
        
        new_params = {}
        
        for key, value in params.items():
            
            validator = cls.FIELD_VALIDATORS.get( cls.removeMultiFieldSpecifier(key) )

            if validator is not None:
                if to_string:
                    new_params[key] = validator.to_string(key, value)
                else:
                    new_params[key] = validator.to_python(key, value)
            else:
                new_params[key] = value

        return new_params

    @log_function_invocation
    def handleList(self, confInfo):
        """
        Provide the list of configuration options.
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        # Read the current settings from the conf file
        confDict = self.readConf(self.CONF_FILE)
        
        # Set the settings
        if None != confDict:
            for stanza, settings in confDict.items():
                
                for key, val in settings.items():
                    
                    if val is None:
                        confInfo[stanza].append(key, "")
                    else:
                        confInfo[stanza].append(key, val)
                    
                    
    @log_function_invocation 
    def handleReload(self, confInfo):
        """
        Reload the list of configuration options.
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        # Refresh the configuration (handles disk based updates)
        entity.refreshEntities('properties/' + self.CONF_FILE, sessionKey=self.getSessionKey())
        
    def clearValue(self, d, name):
        """
        Set the value of in the dictionary to none
        
        Arguments:
        d -- The dictionary to modify
        name -- The name of the variable to clear (set to none)
        """
        
        if name in d:
            d[name] = None         
    
    @log_function_invocation
    def handleEdit(self, confInfo):
        """
        Handles edits to the configuration options
        
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        
        try:
                
            name = self.callerArgs.id
            args = self.callerArgs
            
            # Load the existing configuration
            confDict = self.readConf(self.CONF_FILE)
            
            # Get the settings for the given stanza
            is_found = False
            
            if name is not None:
                for stanza, settings in confDict.items():
                    if stanza == name:
                        is_found = True
                        existing_settings = copy.copy(settings) # In case, we need to view the old settings
                        break # Got the settings object we were looking for
            
            # Stop if we could not find the name  
            if not is_found:
                raise admin.NotFoundException("A stanza for the given name '%s' could not be found" % (name) )
            
            # Get the settings that are being set
            new_settings = {}
            
            for key in args.data:
                new_settings[key] = args[key][0]
            
            # Create the resulting configuration that would be persisted if the settings provided are applied
            settings.update( new_settings )
            
            # Check the configuration settings
            cleaned_params = self.checkConf(new_settings, name, confInfo, existing_settings=existing_settings)
            
            # Get the validated parameters
            validated_params = self.convertParams( name, cleaned_params, True )
            
            # Clear out the given parameters if blank so that it can be removed if the user wishes (note that values of none are ignored by Splunk)
            clearable_params = [ self.PARAM_PROXY_SERVER, self.PARAM_PROXY_PORT, self.PARAM_PROXY_USER, self.PARAM_PROXY_PASSWORD ]
            
            for p in clearable_params:
                if p in validated_params and validated_params[p] is None:
                    validated_params[p] = ""
            
            # Write out the updated conf
            self.writeConf(self.CONF_FILE, name, validated_params )
            
        except admin.NotFoundException, e:
            raise e
        except Exception, e:
            logger.exception("Exception generated while performing edit")
            
            raise e
        
    @classmethod
    def checkConf(cls, settings, stanza=None, confInfo=None, onlyCheckProvidedFields=False, existing_settings=None):
        """
        Checks the settings and raises an exception if the configuration is invalid.
        
        Arguments:
        settings -- The settings dictionary the represents the configuration to be checked
        stanza -- The name of the stanza being checked
        confInfo -- The confinfo object that was received into the REST handler
        onlyCheckProvidedFields -- Indicates if we ought to assume that this is only part of the fields and thus should not alert if some necessary fields are missing
        existing_settings -- The existing settings before the current changes are applied
        """

        # Add all of the configuration items to the confInfo object so that the REST endpoint lists them (even if they are wrong)
        # We want them all to be listed so that the users can see what the current value is (and hopefully will notice that it is wrong)
        for key, val in settings.items():
        
            # Add the value to the configuration info
            if stanza is not None and confInfo is not None:
            
                # Handle the EAI:ACLs differently than the normal values
                if key == 'eai:acl':
                    confInfo[stanza].setMetadata(key, val)
                elif key in cls.VALID_PARAMS and key not in cls.UNSAVED_PARAMS:
                    confInfo[stanza].append(key, val)

        # Below is a list of the required fields. The entries in this list will be removed as they
        # are observed. An empty list at the end of the config check indicates that all necessary
        # fields where provided.
        required_fields = cls.REQUIRED_PARAMS[:]
        
        # Check each of the settings
        for key, val in settings.items():
            
            # Remove the field from the list of required fields
            try:
                required_fields.remove(key)
            except ValueError:
                pass # Field not available, probably because it is not required
        
        # Stop if not all of the required parameters are not provided
        if onlyCheckProvidedFields == False and len(required_fields) > 0: #stanza != "default" and 
            raise admin.ArgValidationException("The following fields must be defined in the configuration but were not: " + ",".join(required_fields) )
        
        # Clean up and validate the parameters
        cleaned_params = cls.convertParams(stanza, settings, False)
        
        # Run the general validators
        for validator in cls.GENERAL_VALIDATORS:
            validator.validate( stanza, cleaned_params, existing_settings )
        
        # Remove the parameters that are not intended to be saved
        for to_remove in cls.UNSAVED_PARAMS:
            if to_remove in cleaned_params:
                del cleaned_params[to_remove]
        
        # Return the cleaned parameters    
        return cleaned_params
        
    @staticmethod
    def stringToIntegerOrDefault( str_value, default_value=None ):
        """
        Converts the given string to an integer or returns none if it is not a valid integer.
        
        Arguments:
        str_value -- A string value of the integer to be converted.
        default_value -- The value to be used if the string is not an integer.
        """
        
        # If the value is none, then don't try to convert it
        if str_value is None:
            return default_value
        
        # Try to convert the string to an integer
        try:
            return int(str(str_value).strip())
        except ValueError:
            # Return none if the value could not be converted
            return default_value
      
# initialize the handler
if __name__ == "__main__":
    admin.init(WebsiteMonitoringRestHandler, admin.CONTEXT_NONE)
