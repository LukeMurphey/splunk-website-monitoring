"""
This REST handler faciltates access to the website_monitoring.conf file.
"""

import splunk.admin as admin
import splunk.entity as entity
import splunk

import logging

import os
import sys
path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)
from modular_input.server_info import ServerInfo

from website_monitoring_app.simple_rest_handler import RestHandler, BooleanFieldValidator, \
IntegerFieldValidator, StandardFieldValidator, HostFieldValidator, log_function_invocation

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

class WebsiteMonitoringRestHandler(RestHandler):
    """
    The REST handler provides configuration management for web ping.
    """

    # Below is the name of the conf file
    conf_file = 'website_monitoring'

    # Below are the list of parameters that are accepted
    PARAM_DEBUG = 'debug'
    PARAM_PROXY_SERVER = 'proxy_server'
    PARAM_PROXY_PORT = 'proxy_port'
    PARAM_PROXY_USER = 'proxy_user'
    PARAM_PROXY_PASSWORD = 'proxy_password'
    PARAM_PROXY_TYPE = 'proxy_type'
    PARAM_PROXY_IGNORE = 'proxy_ignore'
    PARAM_THREAD_LIMIT = 'thread_limit'
    PARAM_MAX_RESPONSE_TIME = 'max_response_time'

    # Below are the list of valid and required parameters
    valid_params = [PARAM_DEBUG, PARAM_PROXY_SERVER, PARAM_PROXY_PORT, PARAM_PROXY_USER, PARAM_PROXY_PASSWORD, PARAM_PROXY_TYPE, PARAM_PROXY_IGNORE, PARAM_THREAD_LIMIT, PARAM_MAX_RESPONSE_TIME]

    # List of fields and how they will be validated
    field_validators = {
        PARAM_DEBUG : BooleanFieldValidator(),
        PARAM_PROXY_SERVER : HostFieldValidator(),
        PARAM_PROXY_PORT : IntegerFieldValidator(0, 65535),
        PARAM_PROXY_TYPE : ProxyTypeFieldValidator(),
        PARAM_PROXY_IGNORE : StandardFieldValidator(),
        PARAM_MAX_RESPONSE_TIME : IntegerFieldValidator(0, 65535),
    }

    # General variables
    app_name = "website_monitoring"

    # Logger info
    logger_file_name = 'website_monitoring_rest_handler.log'
    logger_name = 'WebsiteMonitoringRestHandler'
    logger_level = logging.INFO

    # This will indicate if we added the thread limit validator
    # This will be done in convertParams() once we have a session-key that will let us know if the
    # host is running on Splunk Cloud (in which a thread limit of 25 must be used)
    added_thread_limit_validator = False

    def convertParams(self, name, params, to_string=False):
        if not self.added_thread_limit_validator:
            # Only allow a thread limit of 25 if this is on cloud
            if ServerInfo.is_on_cloud(session_key=self.getSessionKey()):
                self.field_validators[self.PARAM_THREAD_LIMIT] = IntegerFieldValidator(1, 25)
            else:
                self.field_validators[self.PARAM_THREAD_LIMIT] = IntegerFieldValidator(1, 5000)

            self.added_thread_limit_validator = True

        # Call the super class convertParams()
        return super(WebsiteMonitoringRestHandler, self).convertParams(name, params, to_string)

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
                for key, val in settings.items():
                    if key == self.PARAM_THREAD_LIMIT and int(val) > 25 and ServerInfo.is_on_cloud(session_key=self.getSessionKey()):
                        confInfo[stanza].append(key, 25)
                    else:
                        confInfo[stanza].append(key, val)

# initialize the handler
if __name__ == "__main__":
    admin.init(WebsiteMonitoringRestHandler, admin.CONTEXT_NONE)
