import unittest
import sys
import os
import re
import time
import shutil
import tempfile
import threading
from StringIO import StringIO
import errno
import HTMLTestRunner

sys.path.append(os.path.join("..", "src", "bin"))

from web_ping import URLField, DurationField, WebPing, NTLMAuthenticationValueException
from modular_input import Field, FieldValidationException
from website_monitoring_rest_handler import HostFieldValidator
from website_monitoring_app import requests

from unit_test_web_server import UnitTestWithWebServer, skipIfNoServer
from test_proxy_server import get_server as get_proxy_server

def skipIfNoProxyServer(func):
    def _decorator(self, *args, **kwargs):

        if not hasattr(self, 'proxy_address') or self.proxy_address is None:
            self.skipTest("No proxy address defined, proxy based test will not run")
            return

        elif not hasattr(self, 'proxy_port') or self.proxy_port is None:
            self.skipTest("No proxy port defined, proxy based test will not run")
            return

        elif not hasattr(self, 'proxy_type') or self.proxy_type is None:
            self.skipTest("No proxy type defined, proxy based test will not run")
            return
        else:
            return func(self, *args, **kwargs)

    return _decorator

class WebsiteMonitoringAppTest(unittest.TestCase):

    DEFAULT_TEST_PROXY_SERVER_PORT = 21080
    warned_about_no_proxyd = False
    proxyd = None
    proxy_address = None
    proxy_port = None
    proxy_type = None
    config_loaded = False

    def toInt(self, str_int):
        if str_int is None:
            return None
        else:
            return int(str_int)

    def loadConfig(self, properties_file=None):

        # Stop if we already loaded the configuration
        if WebsiteMonitoringAppTest.config_loaded:
            return

        # Load the port from the environment if possible. This might be get overridden by the local.properties file.
        WebsiteMonitoringAppTest.proxy_port = int(os.environ.get("TEST_PROXY_SERVER_PORT", WebsiteMonitoringAppTest.DEFAULT_TEST_PROXY_SERVER_PORT))

        fp = None

        if properties_file is None:
            properties_file = os.path.join("..", "local.properties")

            try:
                fp = open(properties_file)
            except IOError:
                pass

        if fp is not None:
            regex = re.compile("(?P<key>[^=]+)[=](?P<value>.*)")

            settings = {}

            for l in fp.readlines():
                r = regex.search(l)

                if r is not None:
                    d = r.groupdict()
                    settings[d["key"]] = d["value"]

            # Load the parameters from the 
            WebsiteMonitoringAppTest.proxy_address = settings.get("value.test.proxy.address", WebsiteMonitoringAppTest.proxy_address)
            WebsiteMonitoringAppTest.proxy_port = self.toInt(settings.get("value.test.proxy.port", WebsiteMonitoringAppTest.proxy_port))
            WebsiteMonitoringAppTest.proxy_type = settings.get("value.test.proxy.type", None)

        # If no proxy was defined, use the internal proxy server for testing
        if WebsiteMonitoringAppTest.proxyd is None and WebsiteMonitoringAppTest.proxy_address is None:

            WebsiteMonitoringAppTest.proxy_address = "127.0.0.1"
            WebsiteMonitoringAppTest.proxy_port = WebsiteMonitoringAppTest.proxy_port
            WebsiteMonitoringAppTest.proxy_type = "http"

            WebsiteMonitoringAppTest.proxyd = get_proxy_server(WebsiteMonitoringAppTest.proxy_port)

            def start_server(proxyd):
                proxyd.serve_forever()

            t = threading.Thread(target=start_server, args = (WebsiteMonitoringAppTest.proxyd,))
            t.daemon = True
            t.start()

        # Note that we loaded the config already so that we don't try it again.
        WebsiteMonitoringAppTest.config_loaded = True

    def setUp(self):
        self.loadConfig()

class TestHostFieldValidator(unittest.TestCase):

    def test_underscore_allowed(self):
        # http://lukemurphey.net/issues/1002
        # http://answers.splunk.com/answers/233571/website-monitoring-is-not-working-with-proxy-setup.html

        validator = HostFieldValidator()

        self.assertTrue(validator.is_valid_hostname("my_proxy.localhost.com"))

class TestURLField(unittest.TestCase):

    def test_url_field_valid(self):
        url_field = URLField("test_url_field_valid", "title", "this is a test")

        self.assertEqual(url_field.to_python("http://google.com").geturl(), "http://google.com")
        self.assertEqual(url_field.to_python("http://google.com/with/path").geturl(), "http://google.com/with/path")
        self.assertEqual(url_field.to_python("http://google.com:8080/with/port").geturl(), "http://google.com:8080/with/port")

    def test_url_field_invalid(self):
        url_field = URLField("test_url_field_invalid", "title", "this is a test")

        self.assertRaises(FieldValidationException, lambda: url_field.to_python("hxxp://google.com"))
        self.assertRaises(FieldValidationException, lambda: url_field.to_python("http://"))
        self.assertRaises(FieldValidationException, lambda: url_field.to_python("google.com"))

class TestDurationField(unittest.TestCase):

    def test_duration_valid(self):
        duration_field = DurationField("test_duration_valid", "title", "this is a test")

        self.assertEqual(duration_field.to_python("1m"), 60)
        self.assertEqual(duration_field.to_python("5m"), 300)
        self.assertEqual(duration_field.to_python("5 minute"), 300)
        self.assertEqual(duration_field.to_python("5"), 5)
        self.assertEqual(duration_field.to_python("5h"), 18000)
        self.assertEqual(duration_field.to_python("2d"), 172800)
        self.assertEqual(duration_field.to_python("2w"), 86400 * 7 * 2)

    def test_url_field_invalid(self):
        duration_field = DurationField("test_url_field_invalid", "title", "this is a test")

        self.assertRaises(FieldValidationException, lambda: duration_field.to_python("1 treefrog"))
        self.assertRaises(FieldValidationException, lambda: duration_field.to_python("minute"))

def skipIfNoServer(func):
    def _decorator(self, *args, **kwargs):
        if self.httpd is None:
            # Don't run the test if the server is not running
            self.skipTest("The web-server is not running")
        else:
            return func(self, *args, **kwargs)

    return _decorator

class TestWebPing(WebsiteMonitoringAppTest, UnitTestWithWebServer):

    def setUp(self):

        super(TestWebPing, self).setUp()

        self.tmp_dir = tempfile.mkdtemp(prefix="TestWebPing")
        #os.makedirs(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_get_file_path(self):
        self.assertEquals(WebPing.get_file_path("/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping", "web_ping://TextCritical.com"), "/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping" + os.sep + "35163af7282b92013f810b2b4822d7df.json")

    def test_ping(self):

        url_field = URLField("test_ping", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"), timeout=3)

        self.assertEquals(result.response_code, 200)
        self.assertGreater(result.request_time, 0)

    def test_ping_super_long_url(self):
        # https://answers.splunk.com/answers/488784/why-my-website-monitoring-only-check-1-time.html

        url_field = URLField("test_ping", "title", "this is a test")

        #result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page?s=superloooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong"), timeout=3)
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page_superlooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooong"), timeout=3)

        self.assertEquals(result.response_code, 200)
        self.assertGreater(result.request_time, 0)

    def test_ping_non_existent_domain(self):
        # https://answers.splunk.com/answers/337070/website-monitoring-app-setup.html#answer-338487

        url_field = URLField("test_ping_non_existent_domain", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("http://xyz"), timeout=3)

        self.assertEquals(result.response_code, 0)
        self.assertEquals(result.request_time, 0)

    def test_ping_timeout(self):
        url_field = URLField("test_ping_timeout", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("https://192.168.30.23/"), timeout=3)

        self.assertEquals(result.timed_out, True)

    def test_is_exception_for_timeout(self):
        try:
            r = requests.get('https://192.168.30.23/')
        except requests.exceptions.ConnectionError as e:

            if not WebPing.isExceptionForTimeout(e):
                print e
            self.assertTrue(WebPing.isExceptionForTimeout(e))

    def test_save_checkpoint(self):
        web_ping = WebPing()
        web_ping.save_checkpoint(self.tmp_dir, "web_ping://TextCritical.com", 100)
        self.assertEquals(web_ping.last_ran(self.tmp_dir, "web_ping://TextCritical.com"), 100)

    def test_is_expired(self):
        self.assertFalse(WebPing.is_expired(time.time(), 30))
        self.assertTrue(WebPing.is_expired(time.time() - 31, 30))

    def get_test_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    def test_needs_another_run(self):

        # Test case where file does not exist
        self.assertTrue(WebPing.needs_another_run("/Users/lmurphey/Applications/splunk/var/lib/splunk/modinputs/web_ping", "web_ping://DoesNotExist", 60))

        # Test an interval right at the earlier edge
        self.assertFalse(WebPing.needs_another_run(os.path.join(self.get_test_dir(), "configs"), "web_ping://TextCritical.com", 60, 1365486765))

        # Test an interval at the later edge
        self.assertFalse(WebPing.needs_another_run(os.path.join(self.get_test_dir(), "configs"), "web_ping://TextCritical.com", 10, 1365486775))

        # Test interval beyond later edge
        self.assertTrue(WebPing.needs_another_run(os.path.join(self.get_test_dir(), "configs"), "web_ping://TextCritical.com", 10, 1365486776))
        
    def test_output_result(self):
        web_ping = WebPing(timeout=3)

        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"), timeout=3)

        out = StringIO()

        web_ping.output_result(result, "stanza", "title", unbroken=True, close=True, out=out)

        self.assertTrue(out.getvalue().find("response_code=200") >= 0)

    def test_output_result_unavailable(self):
        web_ping = WebPing(timeout=3)

        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://192.168.30.23/"), timeout=3)

        out = StringIO()

        web_ping.output_result(result, "stanza", "title", unbroken=True, close=True, out=out)

        self.assertTrue(out.getvalue().find("timed_out=True") >= 0)

    def test_bad_checkpoint(self):

        web_ping = WebPing()

        # Make sure the call does return the expected error (is attempting to load the data data)
        with self.assertRaises(ValueError):
            web_ping.get_checkpoint_data(os.path.join(self.get_test_dir(), "configs"), throw_errors=True)
        
        # Make sure the test returns None
        data = web_ping.get_checkpoint_data(os.path.join(self.get_test_dir(), "configs", "web_ping://TextCritical.net"))

        self.assertEqual(data, None)

    @skipIfNoServer
    def test_hash(self):

        url_field = URLField("test_ping", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"), timeout=3)

        self.assertEquals(result.response_code, 200)

        self.assertEquals(result.response_md5, '1f6c14189070f50c4c06ada640c14850') # This is 1f6c14189070f50c4c06ada640c14850 on disk
        self.assertEquals(result.response_sha224, 'deaf4c0062539c98b4e957712efcee6d42832fed2d803c2bbf984b23')

    def test_missing_servername(self):
        """
        Some web-servers require that the "Host" be included on SSL connections when the server is hosting multiple domains on the same IP.

        Without the host header, the server is unable to determine which certificate to provide and thus closes the connection.

        http://lukemurphey.net/issues/1035
        """

        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("https://lukemurphey.net"), timeout=3)

        self.assertEquals(result.response_code, 200)

    @skipIfNoProxyServer
    def test_ping_over_proxy(self):

        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://textcritical.com"), timeout=3, proxy_type=self.proxy_type, proxy_server=self.proxy_address, proxy_port=self.proxy_port)

        self.assertEquals(result.response_code, 200)

    @skipIfNoServer
    def test_ping_with_basic_authentication(self):

        # Try with valid authentication
        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port)), timeout=3, username="admin", password="changeme")

        self.assertEquals(result.response_code, 200)

        self.assertEquals(result.response_md5, '1f6c14189070f50c4c06ada640c14850') # This is 1f6c14189070f50c4c06ada640c14850 on disk
        self.assertEquals(result.response_sha224, 'deaf4c0062539c98b4e957712efcee6d42832fed2d803c2bbf984b23')

        # Verify that bad authentication fails
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port)), timeout=3, username="admin", password="wrongpassword")

        self.assertEquals(result.response_code, 401)
        self.assertGreater(result.request_time, 0)

    def test_ping_with_digest_authentication(self):

        # Try with valid authentication
        url_field = URLField( "test_ping", "title", "this is a test")
        result = WebPing.ping( url_field.to_python("http://httpbin.org/digest-auth/auth/user/passwd"), timeout=3, username="user", password="passwd")

        self.assertEquals(result.response_code, 200)

    @skipIfNoServer
    def test_ping_with_ntlm_authentication(self):

        # Try with valid authentication
        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/ntlm_auth"), timeout=3, username="user\\domain", password="passwd")

        self.assertEquals(result.response_code, 200)

    @skipIfNoServer
    def test_ping_with_ntlm_negotiate_authentication(self):

        # Try with valid authentication
        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/ntlm_auth_negotiate"), timeout=3, username="user\\domain", password="passwd")

        self.assertEquals(result.response_code, 200)

    def test_ping_with_ntlm_authentication_missing_domain(self):

        # Try with missing domain
        url_field = URLField( "test_ping", "title", "this is a test")
        self.assertRaises(NTLMAuthenticationValueException, lambda: WebPing.ping( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/ntlm_auth"), timeout=3, username="user", password="passwd"))

    @skipIfNoServer
    def test_ping_with_basic_authentication_optional(self):

        # Try with valid authentication
        url_field = URLField("test_ping", "title", "this is a test")
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/optional_auth"), timeout=3, username="admin", password="changeme")

        self.assertEquals(result.response_code, 203)

        # Verify that no authentication still works
        result = WebPing.ping( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/optional_auth"), timeout=3)

        self.assertEquals(result.response_code, 202)
        self.assertGreater(result.request_time, 0)

    @skipIfNoServer
    def test_determine_auth_method_basic(self):

        # Try with basic auth
        url_field = URLField( "test_ping", "title", "this is a test")
        auth_type = WebPing.determine_auth_type( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port)))

        self.assertEquals(auth_type, WebPing.HTTP_AUTH_BASIC)

    def test_determine_auth_method_digest(self):

        # Try with digest auth
        url_field = URLField( "test_ping", "title", "this is a test")
        auth_type = WebPing.determine_auth_type( url_field.to_python("http://httpbin.org/digest-auth/auth/user/passwd"))

        self.assertEquals(auth_type, WebPing.HTTP_AUTH_DIGEST)

    @skipIfNoServer
    def test_determine_auth_method_ntlm(self):

        # Try with digest auth
        url_field = URLField( "test_ping", "title", "this is a test")
        auth_type = WebPing.determine_auth_type( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/ntlm_auth"))

        self.assertEquals(auth_type, WebPing.HTTP_AUTH_NTLM)

    @skipIfNoServer
    def test_determine_auth_method_ntlm_comma_header(self):

        # Try with digest auth
        url_field = URLField( "test_ping", "title", "this is a test")
        auth_type = WebPing.determine_auth_type( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/ntlm_auth_negotiate"))

        self.assertEquals(auth_type, WebPing.HTTP_AUTH_NTLM)

    @skipIfNoServer
    def test_determine_auth_method_none(self):

        # Try with digest auth
        url_field = URLField( "test_ping", "title", "this is a test")
        auth_type = WebPing.determine_auth_type( url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"))

        self.assertEquals(auth_type, WebPing.HTTP_AUTH_NONE)

    @skipIfNoServer
    def test_custom_user_agent(self):
        """
        http://lukemurphey.net/issues/1341
        """

        url_field = URLField("test_ping", "title", "this is a test")

        # Make sure that the server is validating the user-agent by returning 200 when the user-agent doesn't match
        # This just validates that the test case works
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/user_agent_check"), user_agent="USER_AGENT_CHECK_DOESNT_MATCH", timeout=3)
        self.assertEquals(result.response_code, 200)

        # Make sure that the server is validating the user-agent which returns 201 when the user-agent matches "USER_AGENT_CHECK"
        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/user_agent_check"), user_agent="USER_AGENT_CHECK", timeout=3)
        self.assertEquals(result.response_code, 201)

    @skipIfNoServer
    def test_should_contain_string(self):

        url_field = URLField("test_ping", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"), timeout=3, should_contain_string="<h1>My First Heading</h1>")

        self.assertEquals(result.response_code, 200)

        self.assertEquals(result.response_md5, '1f6c14189070f50c4c06ada640c14850') # This is 1f6c14189070f50c4c06ada640c14850 on disk
        self.assertEquals(result.response_sha224, 'deaf4c0062539c98b4e957712efcee6d42832fed2d803c2bbf984b23')
        self.assertEquals(result.has_expected_string, True)

    @skipIfNoServer
    def test_should_contain_string_no_match(self):

        url_field = URLField("test_ping", "title", "this is a test")

        result = WebPing.ping(url_field.to_python("http://127.0.0.1:" + str(self.web_server_port) + "/test_page"), timeout=3, should_contain_string="<h1>Should not Match!</h1>")

        self.assertEquals(result.response_code, 200)

        self.assertEquals(result.response_md5, '1f6c14189070f50c4c06ada640c14850') # This is 1f6c14189070f50c4c06ada640c14850 on disk
        self.assertEquals(result.response_sha224, 'deaf4c0062539c98b4e957712efcee6d42832fed2d803c2bbf984b23')
        self.assertEquals(result.has_expected_string, False)

class TestOnCloud(unittest.TestCase):
    
    def setUp(self):
        super(TestOnCloud, self).setUp()

        # Configure an instance of the class to test
        self.web_ping = WebPing()

        # Force the class to act like it is on cloud
        self.web_ping.is_on_cloud = self.fake_is_on_cloud

    def fake_is_on_cloud(self, session_key):
        return True

    def test_get_proxy_config(self):
        # See https://lukemurphey.net/issues/2445
        self.web_ping.is_on_cloud = self.fake_is_on_cloud
        self.web_ping.get_proxy_config('a session key')
        self.assertEquals(self.web_ping.get_proxy_config('a session key'), ("http", None, None, None, None, None))

if __name__ == '__main__':
    try:
        report_path = os.path.join('..', os.environ.get('TEST_OUTPUT', 'tmp/test_report.html'))

        # Make the test directory
        try:
            os.makedirs(os.path.dirname(report_path))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

        with open(report_path, 'w') as report_file:
            test_runner = HTMLTestRunner.HTMLTestRunner(
                stream=report_file
            )
            unittest.main(testRunner=test_runner)
    finally:
        if WebsiteMonitoringAppTest.proxyd is not None:
            WebsiteMonitoringAppTest.proxyd.shutdown()
