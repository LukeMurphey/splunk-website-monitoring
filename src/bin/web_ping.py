"""
This module defines the Website Monitoring web_ping modular input.
"""

import os
import sys

path_to_mod_input_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modular_input.zip')
sys.path.insert(0, path_to_mod_input_lib)
from modular_input import Field, ModularInput, URLField, DurationField
from modular_input.shortcuts import forgive_splunkd_outages
from modular_input.secure_password import get_secure_password
from splunk.models.field import Field as ModelField
from splunk.models.field import IntField as ModelIntField
import splunk

import re
import hashlib
import time
import json
import threading
import logging
import urllib

import socket
from website_monitoring_app import socks
from website_monitoring_app import requests
from website_monitoring_app.requests_ntlm import HttpNtlmAuth

# Disable the SSL certificate warning
# http://lukemurphey.net/issues/1390
# We don't support SSL certicate checking at this point because I haven't found a good way to
# include the SSL cert libraries into a Splunk app.
from website_monitoring_app.requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class NTLMAuthenticationValueException(Exception):
    """
    This class is used to communicate that the NTLM authentication information is invalid.
    """
    pass

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
        self.msecs = self.secs * 1000 # millisecs

class WebPing(ModularInput):
    """
    The web ping modular input connects to a website to determine if the site is operational and
    tracks the time it takes to respond.
    """

    PARSE_URL_RE = re.compile(r"http[s]?[:]//(.*)", re.IGNORECASE)

    HTTP_AUTH_BASIC = 'basic'
    HTTP_AUTH_DIGEST = 'digest'
    HTTP_AUTH_NTLM = 'ntlm'
    HTTP_AUTH_NEGOTIATE = 'negotiate'
    HTTP_AUTH_NONE = None

    DEFAULT_THREAD_LIMIT = 200

    # The following define which secure password entry to use for the proxy
    PROXY_PASSWORD_REALM = 'website_monitoring_app_proxy'
    PROXY_PASSWORD_USERNAME = 'IN_CONF_FILE'

    # This stores the default app config information
    default_app_config = None

    class Result(object):
        """
        The results object designates the results of connecting to a website.
        """

        def __init__(self, request_time, response_code, timed_out, url, response_size=None,
                     response_md5=None, response_sha224=None, has_expected_string=None):

            self.request_time = request_time
            self.response_code = response_code
            self.timed_out = timed_out
            self.url = url
            self.response_size = response_size
            self.response_md5 = response_md5
            self.response_sha224 = response_sha224
            self.has_expected_string = has_expected_string

    def __init__(self, timeout=30, thread_limit=None):

        scheme_args = {'title': "Website Availability Check",
                       'description': "Connects to a website in order to obtain performance statistics",
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "true"}

        args = [
                Field("title", "Title", "A short description (typically just the domain name)", empty_allowed=False),
                URLField("url", "URL", "The URL to connect to (must be be either HTTP or HTTPS protocol)", empty_allowed=False, require_https_on_cloud=True),
                DurationField("interval", "Interval", "The interval defining how often to perform the check; can include time units (e.g. 15m for 15 minutes, 8h for 8 hours)", empty_allowed=False),
                Field("configuration", "Configuration", "Defines a specific proxy configuration to use (in website_monitoring.spec) if not using the default; only used if you want to have multiple proxy servers", none_allowed=True, empty_allowed=True),
                Field("client_certificate", "Client Certificate Path", "Defines the path to the client certificate (if the website requires client SSL authentication)", none_allowed=True, empty_allowed=True),
                Field("client_certificate_key", "Client Certificate Key Path", "Defines the path to the client certificate key (necessary of the key is in a separate file from the certificate)", none_allowed=True, empty_allowed=True),
                Field("username", "Username", "The username to use for authenticating (only HTTP authentication supported)", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False),
                Field("password", "Password", "The password to use for authenticating (only HTTP authentication supported)", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False),
                Field("user_agent", "User Agent", "The user-agent to use when communicating with the server", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False),
                Field("should_contain_string", "String match", "A string that should be present in the content", none_allowed=True, empty_allowed=True, required_on_create=False, required_on_edit=False)
        ]

        ModularInput.__init__(self, scheme_args, args, logger_name='web_availability_modular_input', logger_level=logging.DEBUG)

        if timeout > 0:
            self.timeout = timeout
        else:
            self.timeout = 30

        if thread_limit is None:
            self.thread_limit = WebPing.DEFAULT_THREAD_LIMIT
        else:
            self.thread_limit = thread_limit

        self.threads = {}

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
        proxy_type_processed = proxy_type.strip().lower()

        if proxy_type_processed == "socks4":
            return socks.PROXY_TYPE_SOCKS4
        elif proxy_type_processed == "socks5":
            return socks.PROXY_TYPE_SOCKS5
        elif proxy_type_processed == "http":
            return socks.PROXY_TYPE_HTTP
        elif proxy_type_processed == "":
            return None
        else:
            if logger:
                logger.warn("Proxy type is not recognized: %s", proxy_type)
            return None

    @classmethod
    def determine_auth_type(cls, url, proxies=None, timeout=None, cert=None, logger=None):
        """
        Determine the authentication type that is appropriate to authenticate to the given
        web-server.

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
            http = requests.get(url.geturl(), proxies=proxies, timeout=timeout, cert=cert,
                                verify=False)

            # Find the authentication header irrespective of case
            auth_header_value = None

            for header, value in http.headers.items():
                if header.lower() == 'www-authenticate':
                    auth_header_value = value
                    break

            # Determine if the authentication header is present and use it to determine the
            # authentication type
            if auth_header_value is not None:

                # Handle the pesky cases where a comma separated value is provided in the header
                # for NTLM negotiation (like "negotiate, ntlm")
                if 'ntlm' in auth_header_value.lower():
                    return cls.HTTP_AUTH_NTLM

                # Otherwise, check the HTTP header for the authentication header
                m = re.search('^([a-zA-Z0-9]+)', auth_header_value)
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
            try:
                return HttpNtlmAuth(username, password)
            except ValueError as e:
                raise NTLMAuthenticationValueException(e)

        # Basic authentication
        elif auth_type == cls.HTTP_AUTH_BASIC:
            return requests.auth.HTTPBasicAuth(username, password)

        # Unknown authentication type
        else:

            if logger:
                logger.warn('Unknown type of authentication requested, auth_type=%s', auth_type)

            return (username, password)

    @classmethod
    def is_fips_mode(cls):
        """
        Determine if the app is running in FIPS mode. This means that weaker hash algorithms need to
        be disabled. Attempting to use these weaker hash algorithms will cause OpenSSL to to crash,
        taking down the entire Python process.
        """

        is_fips = os.environ.get('SPLUNK_FIPS', None)

        if is_fips is not None and is_fips.strip().lower() in ['1', 'true']:
            return True
        else:
            return False

    @classmethod
    def isExceptionForTimeout(cls, exception):
        """
        Determines if the given exception is due to a timeout

        Argument:
        exception -- The exception
        """

        if exception.args is not None and len(exception.args) > 0 and hasattr(exception.args[0], 'reason') and hasattr(exception.args[0].reason, 'errno') and exception.args[0].reason.errno in [60, 61, 10060, 10061, 100]:
            return True

        else:
            # Check the stacktrace to see if any of the exception indicate that the issue is a timeout
            count = 0

            while exception is not None and count < 10:
                # Try to parse out the errno from the message since the errno is oftentimes
                # unavailable in the exception chain
                if re.match(".*((\[Errno ((60)|(61)|(10060)|(10061))\])|(timed out)).*", str(exception)):
                    return True

                # See if the exception has a reason code indicating a connection failure
                if hasattr(exception, 'errno') and exception.errno in [60, 61, 10060, 10061, 110]:
                    return True

                # Get the next exception
                if hasattr(exception, 'args') and exception.args is not None and len(exception.args) > 0 and isinstance(exception.args[0], Exception):
                    exception = exception.args[0]
                elif hasattr(exception, 'reason') and exception.reason is not None:
                    exception = exception.reason
                else:
                    exception = None

                count = count + 1

        return False

    @classmethod
    def ping(cls, url, username=None, password=None, timeout=30, proxy_type=None,
             proxy_server=None, proxy_port=None, proxy_user=None, proxy_password=None, proxy_ignore=None,
             client_certificate=None, client_certificate_key=None, user_agent=None,
             logger=None, should_contain_string=None):
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
        proxy_ignore -- The list of domains to not use the proxy server for.
        client_certificate -- The path to the client certificate to use.
        client_certificate_key -- The path to the client key to use.
        user_agent -- The string to use for the user-agent
        logger -- The logger object to use for logging
        should_contain_string -- A string that is expected in the response
        """

        if logger:
            logger.info('Performing ping, url="%s"', url.geturl())
    
        # Disable the use of the proxy variables
        if proxy_ignore is not None:
            os.environ['NO_PROXY'] = proxy_ignore

        if logger:
            logger.debug('Proxies discovered from the environment, proxies="%r"', urllib.getproxies())

        # Determine which type of proxy is to be used (if any)
        resolved_proxy_type = cls.resolve_proxy_type(proxy_type, logger=logger)

        # Set should_contain_string to none if it is blank since this means it really doesn't have
        # a value
        if should_contain_string is not None and len(should_contain_string.strip()) == 0:
            should_contain_string = None

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
                socks.setdefaultproxy(resolved_proxy_type, proxy_server, int(proxy_port))
                socket.socket = socks.socksocket
                if logger:
                    logger.debug("Using socks proxy server=%s, port=%s", proxy_server, proxy_port)

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

        if logger and cert is not None:
            logger.debug("Using client certificate %s", cert)

        request_time = 0
        response_code = 0
        response_md5 = None
        response_sha224 = None
        timed_out = False
        response_size = None
        has_expected_string = None

        # Setup the headers as necessary
        headers = {}

        if user_agent is not None:
            if logger:
                logger.debug("Setting user-agent=%s", user_agent)

            headers['User-Agent'] = user_agent

        # Make an auth object if necessary
        auth = None
        auth_type = None

        if username is not None and password is not None:

            # Determine the auth type
            auth_type = cls.determine_auth_type(url, proxies=proxies, timeout=timeout, cert=cert,
                                                logger=logger)

            # Don't allow the use of NTLM on a host in FIPS mode since NTLM uses MD4 which is a
            # weak algorithm
            if auth_type == cls.HTTP_AUTH_NTLM and cls.is_fips_mode():

                if logger:
                    logger.warn("Authentication type was automatically identified but will not be used since it uses a weak hash algorithm which is not allowed on this host since it is running in FIPS mode; auth_type=%s", auth_type)

                auth_type = cls.HTTP_AUTH_NONE

            # The authentication type could not be determined. However, we know that
            # authentication is required since a username and password was provided.
            # Default to HTTP basic authentication.
            elif auth_type == cls.HTTP_AUTH_NONE:
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
                if not cls.is_fips_mode():
                    response_md5 = hashlib.md5(http.text).hexdigest()

                response_sha224 = hashlib.sha224(http.text).hexdigest()

                # Determine if the expected string is in the content
                if should_contain_string is not None:
                    has_expected_string = should_contain_string in http.text

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
                logger.error("An SSL exception was thrown when executing a web request against url=%s: " + str(e), url.geturl())

        except requests.exceptions.ConnectionError as e:
            timed_out = WebPing.isExceptionForTimeout(e)

            if not timed_out and logger:
                logger.exception("A connection exception was thrown when executing a web request against url=%s, this can happen if the domain name, IP address is invalid or if network connectivity is down or blocked by a firewall; see help_url=http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Troubleshooting", url.geturl())

        except socks.GeneralProxyError:
            # This may be thrown if the user configured the proxy settings incorrectly
            if logger:
                logger.exception("An error occurred when attempting to communicate with the proxy for url=%s", url.geturl())

        except Exception as e:
            if logger:
                logger.exception("A general exception was thrown when executing a web request for url=%s", url.geturl())

        # Finally, return the result
        return cls.Result(request_time, response_code, timed_out, url.geturl(), response_size, response_md5, response_sha224, has_expected_string)

    def output_result(self, result, stanza, title, index=None, source=None, sourcetype=None,
                      host=None,unbroken=True, close=True, proxy_server=None, proxy_port=None,
                      proxy_user=None, proxy_type=None, out=sys.stdout):
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

        # Add the variable noting if the expected string was present
        if result.has_expected_string is not None:
            data['has_expected_string'] = str(result.has_expected_string).lower()

        return self.output_event(data, stanza, index=index, host=host, source=source,
                                 sourcetype=sourcetype, unbroken=unbroken, close=close, out=out)

    @classmethod
    def get_file_path(cls, checkpoint_dir, stanza):
        """
        Get the path to the checkpoint file. Note that the checkpoint directory is using MD5 for
        legacy purposes (since old versions of the app used MD5). This isn't a significant issue
        since MD5 isn't be used for security purposes here but merely to make sure that file has no
        special characters.

        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        """

        if cls.is_fips_mode():
            return os.path.join(checkpoint_dir, hashlib.sha224(stanza).hexdigest() + ".json")
        else:
            return os.path.join(checkpoint_dir, hashlib.md5(stanza).hexdigest() + ".json")

    def save_checkpoint(self, checkpoint_dir, stanza, last_run):
        """
        Save the checkpoint state.

        Arguments:
        checkpoint_dir -- The directory where checkpoints ought to be saved
        stanza -- The stanza of the input being used
        last_run -- The time when the analysis was last performed
        """

        self.save_checkpoint_data(checkpoint_dir, stanza, {'last_run' : last_run})

    @forgive_splunkd_outages
    def get_app_config(self, session_key, stanza="default"):
        """
        Get the app configuration.

        Arguments:
        session_key -- The session key to use when connecting to the REST API
        stanza -- The stanza to get the proxy information from (defaults to "default")
        """

        # If the stanza is empty, then just use the default
        if stanza is None or stanza.strip() == "":
            stanza = "default"

        # Start off with a default list of settings
        website_monitoring_config = {
            'proxy_type' : 'http',
            'proxy_server' : '',
            'proxy_port' : '',
            'proxy_user': '',
            'proxy_password' : '',
            'thread_limit' : 200,
            'proxy_ignore' : None,
        }

        # Get the proxy configuration
        try: 
            server_response, server_content = splunk.rest.simpleRequest('/servicesNS/nobody/website_monitoring/admin/website_monitoring/' + stanza + '?output_mode=json', sessionKey=session_key)

            if server_response['status'] != '200':
                raise Exception("Could not get the website_monitoring configuration")

            app_content = json.loads(server_content)
            self.logger.debug("Loaded config is %r", app_content)
            website_monitoring_config.update(app_content['entry'][0]['content'])

            # Convert the thread limit to an integer
            try:
                website_monitoring_config['thread_limit'] = int(website_monitoring_config['thread_limit'])
            except ValueError:
                self.logger.error("The value for the thread limit is invalid and will be ignored (will use a limit of 200), value=%s", website_monitoring_config['thread_limit'])
                website_monitoring_config['thread_limit'] = 200

            self.logger.debug("App config information loaded, stanza=%s", stanza)

        except splunk.ResourceNotFound:
            self.logger.info('Unable to find the app configuration for the specified configuration stanza=%s, error="not found"', stanza)
        except splunk.SplunkdConnectionException:
            self.logger.error('Unable to find the app configuration for the specified configuration stanza=%s error="splunkd connection error", see url=http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Troubleshooting', stanza)
            raise

        return website_monitoring_config

    @forgive_splunkd_outages
    def get_proxy_config(self, session_key, stanza="default"):
        """
        Get the proxy configuration

        This returns the following in a list:
            # proxy type
            # proxy server
            # proxy port
            # proxy user
            # proxy ignore list

        Arguments:
        session_key -- The session key to use when connecting to the REST API
        stanza -- The stanza to get the proxy information from (defaults to "default")
        """

        # Don't allow the use of a proxy server on Splunk Cloud since this could
        # allow unencrypted communication. Cloud shouldn't need the use of a proxy anyways.
        # Some do use the app to test proxies but they should use an on-prem forwarder
        # instead.
        if self.is_on_cloud(session_key):
            return "http", None, None, None, None, None

        # If the stanza is empty, then just use the default
        if stanza is None or stanza.strip() == "":
            stanza = "default"

        # Get the proxy configuration
        website_monitoring_config = self.get_app_config(session_key, stanza)

        # Get the proxy password from secure storage (if it exists)
        secure_password = get_secure_password(realm=WebPing.PROXY_PASSWORD_REALM,
                                              username=WebPing.PROXY_PASSWORD_USERNAME,
                                              session_key=session_key)

        if secure_password is not None:
            proxy_password = secure_password['content']['clear_password']
            self.logger.debug("Loaded the proxy password from secure storage")
        elif website_monitoring_config is not None:
            proxy_password = website_monitoring_config['proxy_password']
        else:
            proxy_password = None

        if website_monitoring_config is not None:
            return website_monitoring_config['proxy_type'], website_monitoring_config['proxy_server'], \
                website_monitoring_config['proxy_port'], website_monitoring_config['proxy_user'], \
                proxy_password, website_monitoring_config['proxy_ignore']
        else:
            return 'http', '', '', '', proxy_password, None

    def run(self, stanza, cleaned_params, input_config):

        # Make the parameters
        interval = cleaned_params["interval"]
        title = cleaned_params["title"]
        url = cleaned_params["url"]
        client_certificate = cleaned_params.get("client_certificate", None)
        client_certificate_key = cleaned_params.get("client_certificate_key", None)
        username = cleaned_params.get("username", None)
        password = cleaned_params.get("password", None)
        timeout = self.timeout
        sourcetype = cleaned_params.get("sourcetype", "web_ping")
        host = cleaned_params.get("host", None)
        index = cleaned_params.get("index", "default")
        conf_stanza = cleaned_params.get("configuration", None)
        user_agent = cleaned_params.get("user_agent", None)
        should_contain_string = cleaned_params.get("should_contain_string", None)
        source = stanza

        # Load the thread_limit if necessary
        # This should only be necessary once in the processes lifetime
        if self.default_app_config is None:

            # Get the default app config
            self.default_app_config = self.get_app_config(input_config.session_key)
            self.logger.debug("Default config is %r", self.default_app_config)

            # Get the limit from the app config
            loaded_thread_limit = self.default_app_config['thread_limit']

            # Ensure that the thread limit is valid
            if loaded_thread_limit is not None and loaded_thread_limit > 0:
                self.thread_limit = loaded_thread_limit
                self.logger.debug("Thread limit successfully loaded, thread_limit=%r",
                                  loaded_thread_limit)

            # Warn that the thread limit is invalid
            else:
                self.logger.warn("The thread limit is invalid and will be ignored, thread_limit=%r", loaded_thread_limit)

        # Clean up old threads
        for thread_stanza in self.threads.keys():

            # Keep track of the number of removed threads so that we can make sure to emit a log
            # message noting the number of threads
            removed_threads = 0

            # IF the thread isn't alive, prune it
            if not self.threads[thread_stanza].isAlive():
                removed_threads = removed_threads + 1
                self.logger.debug("Removing inactive thread for stanza=%s, thread_count=%i", thread_stanza, len(self.threads))
                del self.threads[thread_stanza]

            # If we removed threads, note the updated count in the logs so that it can be tracked
            if removed_threads > 0:
                self.logger.info("Removed inactive threads, thread_count=%i, removed_thread_count=%i", len(self.threads), removed_threads)

        # Stop if we have a running thread
        if stanza in self.threads:
            self.logger.debug("No need to execute this stanza since a thread already running for stanza=%s", stanza)

        # Determines if the input needs another run
        elif self.needs_another_run(input_config.checkpoint_dir, stanza, interval):

            # Get the secure password if necessary
            if username is not None:
                secure_password = get_secure_password(realm=stanza, session_key=input_config.session_key)

                if secure_password is not None:
                    password = secure_password['content']['clear_password']
                    self.logger.debug("Successfully loaded the secure password for input=%s", stanza)

            def run_ping():

                # Get the proxy configuration
                try:
                    proxy_type, proxy_server, proxy_port, proxy_user, proxy_password, proxy_ignore = \
                    self.get_proxy_config(input_config.session_key, conf_stanza)
                except splunk.ResourceNotFound:
                    self.logger.error("The proxy configuration could not be loaded (was not found). The execution will be skipped for this input with stanza=%s", stanza)
                    return
                except splunk.SplunkdConnectionException:
                    self.logger.error("The proxy configuration could not be loaded (Splunkd connection exception). The execution will be skipped for this input with stanza=%s, see url=http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Troubleshooting", stanza)
                    return
                except:
                    self.logger.exception("Exception generated when attempting to get the proxy configuration stanza=%s, see url=http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Troubleshooting", stanza)
                    return

                # Perform the ping
                try:
                    result = WebPing.ping(url, username, password, timeout, proxy_type,
                                          proxy_server, proxy_port, proxy_user, proxy_password,
                                          proxy_ignore, client_certificate, client_certificate_key, user_agent,
                                          logger=self.logger, should_contain_string=should_contain_string)
                except NTLMAuthenticationValueException as e:
                    self.logger.warn('NTLM authentication failed due to configuration issue stanza=%s, message="%s"', stanza, str(e))

                with self.lock:

                    # Send the event
                    self.output_result(result, stanza, title, host=host, index=index, source=source,
                                    sourcetype=sourcetype, unbroken=True, close=True,
                                    proxy_server=proxy_server, proxy_port=proxy_port,
                                    proxy_user=proxy_user, proxy_type=proxy_type)

                    # Get the time that the input last ran
                    last_ran = self.last_ran(input_config.checkpoint_dir, stanza)

                    # Save the checkpoint so that we remember when we last ran the input
                    self.save_checkpoint(input_config.checkpoint_dir, stanza,
                                         self.get_non_deviated_last_run(last_ran, interval, stanza))

            # Don't scan the URL if the URL is unencrypted and the host is on Cloud
            if self.is_on_cloud(input_config.session_key) and not url.scheme == "https":
                self.logger.warn("The URL will not be scanned because the host is running on Splunk Cloud and the URL isn't using encryption, url=%s", url.geturl())

            # Don't scan the URL if the host is SHC and 
            elif self.is_on_cloud(input_config.session_key) and not url.scheme == "https":
                self.logger.warn("The URL will not be scanned because the host is running on Splunk Cloud and the URL isn't using encryption, url=%s", url.geturl())

            # If this is not running in multi-threading mode, then run it now in the main thread
            elif self.thread_limit <= 1:
                run_ping()

            # If the number of threads is at or above the limit, then wait until the number of
            # threads comes down
            elif len(self.threads) >= self.thread_limit:
                self.logger.warn("Thread limit has been reached and thus this execution will be skipped for stanza=%s, thread_count=%i", stanza, len(self.threads))

            # Execute the input as a separate thread
            else:

                # Start a thread
                t = threading.Thread(name='web_ping:' + stanza, target=run_ping)
                self.threads[stanza] = t
                t.start()

                self.logger.info("Added thread to the queue for stanza=%s, thread_count=%i", stanza, len(self.threads))

if __name__ == '__main__':

    web_ping = None

    try:
        web_ping = WebPing()
        web_ping.execute()
        sys.exit(0)
    except Exception as e:

        # This logs general exceptions that would have been unhandled otherwise (such as coding
        # errors)
        if web_ping is not None and web_ping.logger is not None:
            web_ping.logger.exception("Unhandled exception was caught, this may be due to a defect in the script")
        else:
            raise e
