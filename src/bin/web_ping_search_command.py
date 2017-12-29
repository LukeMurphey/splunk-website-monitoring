"""
This module provides a Splunk search command that performs a web-ping.
"""

from website_monitoring_app.search_command import SearchCommand
from web_ping import WebPing
from modular_input import URLField

class WebPingSearchCommand(SearchCommand):
    """
    This search command provides a Splunk interface for doing a web-ping.
    """

    def __init__(self, url=None, expected_string=None):
        SearchCommand.__init__(self, run_in_preview=False, logger_name="webping_search_command")

        self.url = url
        self.expected_string = expected_string

        self.logger.info("Web-ping running against url=%s", url)

    def handle_results(self, results, session_key, in_preview):

        # FYI: we ignore results since this is a generating command

        # Make sure that the url field was provided
        if self.url is None:
            self.logger.warn("No url was provided")
            return

        # Parse the URL
        url_field = URLField('name','title','description')
        url_parsed = url_field.to_python(self.url)

        # Do the web-ping
        result = WebPing.ping(url_parsed, logger=self.logger, should_contain_string=self.expected_string)

        # Prep the result dictionary
        data = {
            'response_code': result.response_code if result.response_code > 0 else '',
            'total_time': round(result.request_time, 2) if result.request_time > 0 else '',
            'timed_out': result.timed_out,
            'url': result.url
        }

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

        # Output the results
        self.output_results([data])

if __name__ == '__main__':
    WebPingSearchCommand.execute()
