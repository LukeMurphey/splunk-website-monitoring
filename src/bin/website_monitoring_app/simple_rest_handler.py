"""
This includes a helper class (named RestHandler) that makes implementing a custom REST handler in Splunk very easy.

This is licensed under the Apache License Version 2.0
See https://www.apache.org/licenses/LICENSE-2.0.html

To use this, you will need to:

1) Define a restmap.conf and declare the handler
2) Define the Python code of the REST handler

See below for examples.

------------------------------------------------
restmap.conf example
------------------------------------------------
Below is an example of the restmap.conf file (assumes your code is placed in
bin/my_custom_rest_handler.py):

[admin_external:my_custom_rest_handler]
handlertype = python
handlerfile = my_custom_rest_handler.py
handleractions = list,edit,_reload


------------------------------------------------
Python REST handler example
------------------------------------------------
Below is an example of the REST handler Python code.


from simple_rest_handler import RestHandler, IntegerFieldValidator, BooleanFieldValidator
import logging
import splunk.admin as admin

class MyCustomRestHandler(RestHandler):

    # Below is the name of the conf file (example.conf)
    conf_file = 'example'

    # Below are the list of parameters that are accepted
    PARAM_DEBUG = 'debug'
    PARAM_FOO = 'foo'
    PARAM_SOME_INTEGER = 'some_integer'

    # Below are the list of valid and required parameters
    valid_params = [PARAM_DEBUG, PARAM_FOO, PARAM_SOME_INTEGER]
    required_params = [PARAM_SOME_INTEGER]

    # List of fields and how they will be validated
    field_validators = {
        PARAM_DEBUG : BooleanFieldValidator(),
        PARAM_SOME_INTEGER : IntegerFieldValidator(0, 65535)
    }

    # General variables
    app_name = "my_custom_app"

    # Logger info
    logger_file_name = 'my_custom_rest_handler.log'
    logger_name = 'MyCustomRestHandler'
    logger_level = logging.INFO

# initialize the handler
if __name__ == "__main__":
    admin.init(MyCustomRestHandler, admin.CONTEXT_NONE)
"""

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

        raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid boolean" % (str(value), name))

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

        int_value = int(str(value).strip())

        # Make sure that the value is at least the minimum
        if self.min_value is not None and int_value < self.min_value:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not valid, it must be at least %s" % ( str(value), name, self.min_value))

        # Make sure that the value is no greater than the maximum
        if self.max_value is not None and int_value > self.max_value:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not valid, it must be not be greater than %s" % ( str(value), name, self.max_value))

        try:
            return int(str(value).strip())
        except ValueError:
            raise admin.ArgValidationException("The value of '%s' for the '%s' parameter is not a valid integer" % (str(value), name))

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

    LIST_SPLIT = re.compile("[:,]*")

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
            return ",".join(value)

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

def log_function_invocation(fx):
    """
    This decorator will provide a log message for when a function starts and stops.

    Arguments:
    fx -- The function to log the starting and stopping of
    """

    def wrapper(self, *args, **kwargs):

        if hasattr(self, 'logger') and self.logger is not None:
            self.logger.debug("Entering: " + fx.__name__)

        return_value = fx(self, *args, **kwargs)

        if hasattr(self, 'logger') and self.logger is not None:
            self.logger.debug("Exited: " + fx.__name__)

        return return_value
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

class IncorrectlyConfiguredException(Exception):
    """
    Represents an error in the configuration of the class.
    """
    pass

class RestHandler(admin.MConfigHandler):
    """
    The REST handler provides a framework for making a REST endpoint.
    """

    # Below is the name of the conf file
    conf_file = None

    # Below are the list of valid and required parameters
    valid_params = []
    required_params = []

    # These are parameters that are not persisted to the conf files; these are used within the REST handler only
    unsaved_params = []

    # List of fields and how they will be validated
    # Note: if a field does not have a validator, it will be passed through without validation
    field_validators = {}

    # This field designates the fields that the REST handler ought to allow fields with similar values using dot syntax (value.1, value.2, etc).
    # For these fields, instances containing what looks like the dot syntax will use the validator based on the item without the dot syntax.
    # Thus, the field "value.1.name" will be validated by whatever item validates "value.name".
    multi_fields = []
    multi_field_re = re.compile("(?P<prefix>.*)[.][0-9]+(?P<suffix>.*)")

    # These are validators that work across several fields and need to occur on the cleaned set of fields
    general_validators = []

    # The app name variable
    app_name = None

    # The logger configuration
    logger_file_name = 'rest_handler.log'
    logger_name = 'RestHandler'
    logger_level = logging.INFO

    # This is the internal reference to the logger class
    _logger = None

    @property
    def logger(self):
        """
        Get the logger to use.
        """

        # Initialize the logger if necessary
        if self._logger is None:

            file_name = self.logger_file_name

            # Add the file extension if necessary
            if not file_name.endswith('.log'):
                file_name = file_name + '.log'

            self._logger = setup_logger(self.logger_level, self.logger_name, file_name)

        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

    def isProperlyInitialized(self):
        """
        Return true if all of the required parameters are properly set.
        """
        try:
            self.checkIfProperlyInitialized()
            return True
        except IncorrectlyConfiguredException:
            return False

    def checkIfProperlyInitialized(self):
        """
        Make sure that all of the required parameters are properly set.
        """

        if self.app_name is None:
            raise IncorrectlyConfiguredException("The app_name property must be defined")

        if self.conf_file is None:
            raise IncorrectlyConfiguredException("The conf_file property must be defined")

        if self.valid_params is None:
            raise IncorrectlyConfiguredException("The valid_params property must be defined")
        elif len(self.valid_params) == 0:
            raise IncorrectlyConfiguredException("The valid_params property must have at least one entry")

        if self.logger_name is None:
            raise IncorrectlyConfiguredException("The logger_name property must be defined")

    def setup(self):
        """
        Setup the required and optional arguments
        """
        self.logger.debug("Setup called for action=%r", self.requestedAction)

        try:
            self.checkIfProperlyInitialized()
        except IncorrectlyConfiguredException as exception_raised:
            self.logger.error('The REST handler is improperly configured: ' + str(exception_raised))

        # Set the required parameters
        for arg in self.required_params:
            self.supportedArgs.addReqArg(arg)

        # Set up the valid parameters
        for arg in self.valid_params:
            if arg not in self.required_params:
                self.supportedArgs.addOptArg(arg)

    def removeMultiFieldSpecifier(self, name):
        """
        Remove the multi-field specifier if the field is supposed to be support mulitple instances using the dot syntax (value.1, value.2, etc).

        Arguments:
        name -- The name of the field.
        """

        # Stop if we don't have any multi-fields
        if self.multi_fields is None:
            return name

        m = self.multi_field_re.match(name)

        if m and m.groups()[0] in self.multi_fields:
            self.logger.debug("removeMultiFieldSpecifier: " + name + " to " + m.groups()[0] + m.groups()[1])
            return m.groups()[0] + m.groups()[1]
        else:
            return name

    def convertParams(self, name, params, to_string=False):
        """
        Convert so that they can be saved to the conf files and validate the parameters.

        Arguments:
        name -- The name of the stanza being processed (used for exception messages)
        params -- The dictionary containing the parameter values
        to_string -- If true, a dictionary containing strings is returned; otherwise, the objects are converted to the Python equivalents
        """

        new_params = {}

        for key, value in params.items():

            validator = self.field_validators.get(self.removeMultiFieldSpecifier(key))

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
        confDict = self.readConf(self.conf_file)

        # Set the settings
        if confDict != None:
            for stanza, settings in confDict.items():

                # DEFINE DEFAULT PARAMETERS HERE

                for key, val in settings.items():
                    confInfo[stanza].append(key, val)

                    # ADD CODE HERE to get your parameters

    @log_function_invocation
    def handleReload(self):
        """
        Reload the list of configuration options.
        """

        # Refresh the configuration (handles disk based updates)
        entity.refreshEntities('properties/' + self.conf_file, sessionKey=self.getSessionKey())

    def clearValue(self, d, name):
        """
        Set the value of in the dictionary to none

        Arguments:
        d -- The dictionary to modify
        name -- The name of the variable to clear (set to none)
        """

        if name in d:
            d[name] = None

    def saveConf(self, settings, name, confInfo, existing_settings=None):
        """
        Save the given configuration to the conf file.

        Arguments:
        settings -- A dictionary with the settings to write out
        name -- The stanze name of the conf file to write out
        confInfo -- The confInfo 
        existing_settings -- The existing settings of the previous conf entry (if it exists). This is used to determine which values to be cleared.
        """

        # Check the configuration settings
        cleaned_params = self.checkConf(settings, name, confInfo, existing_settings=existing_settings)

        # Get the validated parameters
        validated_params = self.convertParams(name, cleaned_params, True)

        # Clear out the given parameters if blank so that it can be removed if the user wishes (note that values of none are ignored by Splunk)
        clearable_params = []

        for p in clearable_params:
            if p in validated_params and validated_params[p] is None:
                validated_params[p] = ""

        # Write out the updated conf
        self.writeConf(self.conf_file, name, validated_params)

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
            confDict = self.readConf(self.conf_file)

            # Get the settings for the given stanza
            is_found = False

            if name is not None:
                for stanza, settings in confDict.items():
                    if stanza == name:
                        is_found = True

                         # In case, we need to view the old settings
                        existing_settings = copy.copy(settings)

                        break # Got the settings object we were looking for

            # Stop if we could not find the name
            if not is_found:
                raise admin.NotFoundException("A stanza for the given name '%s' could not be found" % (name))

            # Get the settings that are being set
            new_settings = {}

            for key in args.data:
                new_settings[key] = args[key][0]

            # Create the resulting configuration that would be persisted if the settings provided are applied
            settings.update(new_settings)

            # Save the configuraiton
            self.saveConf(new_settings, name, confInfo, existing_settings)

        except admin.NotFoundException, e:
            raise e
        except Exception, e:
            self.logger.exception("Exception generated while performing edit")

            raise e

    @log_function_invocation
    def handleCreate(self, confInfo):
        """
        Handles creation of configuration options

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """

        try:

            name = self.callerArgs.id
            args = self.callerArgs

            self.logger.info("Creating a new entry for stanza=%r", name)

            # Load the existing configuration
            confDict = self.readConf(self.conf_file)

            # Make sure the entry doesn't exist already
            if name is not None:
                for stanza, settings in confDict.items():
                    if stanza == name:
                        is_found = True

                        raise splunk.admin.ArgValidationException('Entry exists already')

            # Get the settings that are being set
            new_settings = {}

            for key in args.data:
                new_settings[key] = args[key][0]

            # Save the configuration
            self.saveConf(new_settings, name, confInfo)

            # Make sure Splunk reloads the changes
            self.handleReload()

        except Exception, e:
            self.logger.exception("Exception generated while performing creation of new entry")

            raise e

    def checkConf(self, settings, stanza=None, confInfo=None, onlyCheckProvidedFields=False, existing_settings=None):
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
                elif key in self.valid_params and key not in self.unsaved_params:
                    confInfo[stanza].append(key, val)

        # Below is a list of the required fields. The entries in this list will be removed as they
        # are observed. An empty list at the end of the config check indicates that all necessary
        # fields where provided.
        required_fields = self.required_params[:]

        # Check each of the settings
        for key, val in settings.items():

            # Remove the field from the list of required fields
            try:
                required_fields.remove(key)
            except ValueError:
                pass # Field not available, probably because it is not required

        # Stop if not all of the required parameters are not provided
        if onlyCheckProvidedFields == False and len(required_fields) > 0: #stanza != "default" and
            raise admin.ArgValidationException("The following fields must be defined in the configuration but were not: " + ",".join(required_fields))

        # Clean up and validate the parameters
        cleaned_params = self.convertParams(stanza, settings, False)

        # Run the general validators
        for validator in self.general_validators:
            validator.validate(stanza, cleaned_params, existing_settings)

        # Remove the parameters that are not intended to be saved
        for to_remove in self.unsaved_params:
            if to_remove in cleaned_params:
                del cleaned_params[to_remove]

        # Return the cleaned parameters
        return cleaned_params

    @staticmethod
    def stringToIntegerOrDefault(str_value, default_value=None):
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
