"""
This class provides a base class for search commands that handles much of the Splunk-to-Python
interaction necessary for making a search command.

This is licensed under the Apache License Version 2.0
See https://www.apache.org/licenses/LICENSE-2.0.html

To make a search command, you will need to:
 1) Sub-class the search command (see below for an example)
 2) Declare your search command in commands.conf

See below for a basic example of a class that sub-classes SearchCommand:



from search_command import SearchCommand
import sys

class Echo(SearchCommand):

    def __init__(self, what_to_echo="Hello World"):

        # Save the parameters
        self.what_to_echo = what_to_echo

         # Initialize the class
        SearchCommand.__init__( self, run_in_preview=True, logger_name='echo_search_command')

    def handle_results(self, results, session_key, in_preview):
        self.output_results([{'echo' : self.what_to_echo}])

if __name__ == '__main__':
    try:
        Echo.execute()
        sys.exit(0)
    except Exception as e:
        print e
"""

import splunk.Intersplunk
import sys
import logging
from logging import handlers

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class SearchCommand(object):
    """
    A base class for implementing a search command.
    """

    # List of valid parameters
    PARAM_RUN_IN_PREVIEW = "run_in_preview"
    PARAM_DEBUG = "debug"

    VALID_PARAMS = [PARAM_RUN_IN_PREVIEW, PARAM_DEBUG]

    def __init__(self, run_in_preview=False, logger_name='python_search_command', log_level=logging.INFO, run_only_in_preview=False):
        """
        Constructs an instance of the search command.

        Arguments:
        run_in_preview -- Indicates whether the search command should run in preview mode
        logger_name -- The logger name to append to the logger
        log_level -- The log level to use for the logger
        run_only_in_preview -- Run the command only in preview
        """

        self.run_in_preview = run_in_preview
        self.run_only_in_preview = run_only_in_preview

        # Check and save the logger name
        self._logger = None

        if logger_name is None or len(logger_name) == 0:
            raise Exception("Logger name cannot be empty")

        self.logger_name = logger_name
        self.log_level = log_level
        # self.logger.info("args" + str(args))

    @property
    def logger(self):
        """
        A property that returns the logger.
        """

        # Make a logger unless it already exists
        if self._logger is not None:
            return self._logger

        logger = logging.getLogger(self.logger_name)

         # Prevent the log messages from being duplicated in the python.log file:
        logger.propagate = False
        logger.setLevel(self.log_level)

        file_handler = handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', self.logger_name + '.log']), maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        self._logger = logger
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    @classmethod
    def parse_argument(cls, argument):
        """
        Parses an argument in the form of name=value and returns the name and value as two arguments

        Arguments:
        argument -- The argument that should be split into a name/value pair (i.e. name=value)
        """

        # Find the character that splits the name from the value (returns -1 if it cannot be found)
        splitter = argument.find('=')

        # If no equal-sign was found then initialize the value to None
        if splitter < 0:
            name = None
            value = argument

        # If a splitter was found, then parse the value
        else:
            name = argument[0:splitter]
            value = argument[splitter+1:len(argument)]

        # Return the results
        return name, value

    @classmethod
    def get_arguments(cls):
        """
        Get the arguments as args and kwargs so that they can be processed into a constructor call
        to a search command.
        """

        kwargs = {}
        args = []

        # Iterate through the arguments and initialize the corresponding argument
        if len(sys.argv) > 1:

            # Iterate through each argument
            for argument in sys.argv[1:]:

                # Parse the argument
                name, value = cls.parse_argument(argument)

                # If the argument has no value then it was an unnamed argument. Put it in the
                # arguments array
                if name is None:
                    args.append(value)

                else:
                    # Put the argument in a dictionary
                    kwargs[name] = value

        return args, kwargs

    @classmethod
    def make_instance(cls):
        """
        Produce an instance of the search command with arguments from the command-line.
        """

        args, kwargs = cls.get_arguments()
        return cls(*args, **kwargs)

    @classmethod
    def execute(cls):
        """
        Initialize an instance and run it.
        """

        try:

            instance = cls.make_instance()
            instance.run()

        except Exception as exception:
            splunk.Intersplunk.parseError(str(exception))
            # self.logger.exception("Search command threw an exception")

    def run(self, results=None):
        """
        Run the search command.
        """

        try:

            # Get the results from Splunk (unless results were provided)
            if results is None:
                results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
                session_key = settings.get('sessionKey', None)

                # Don't write out the events in preview mode
                in_preview = settings.get('preview', '0') in [1, '1']

                # If run_in_preview is undefined, then just continue
                if self.run_in_preview is None:
                    pass

                # Don't do anything if the command is supposed to run only in preview but the
                # results are not preview results
                elif self.run_only_in_preview and not in_preview:

                    # Don't run in non-preview mode since we already processed the events in
                    # preview mode
                    if len(results) > 0:
                        self.logger.info( "Search command is set to run only in preview, ignoring %d results provided in non-preview mode" % (len(results)))

                    return None

                # Don't do anything if the command is NOT supposed to run in preview but the
                # results are previewed results
                elif not self.run_in_preview and in_preview:
                    return None

            else:
                settings = None

            # Execute the search command
            self.handle_results(results, session_key, in_preview)

        except Exception as exception:
            splunk.Intersplunk.parseError(str(exception))
            self.logger.exception("Search command threw an exception")

    def output_results(self, results):
        """
        Output results to Splunk.

        Arguments:
        results -- An array of dictionaries of fields/values to send to Splunk.
        """

        splunk.Intersplunk.outputResults(results)

    def handle_results(self, results, session_key, in_preview):
        """
        This function needs to be overridden.

        Arguments:
        results -- The results from Splunk to process
        session_key -- The session key to use for connecting to Splunk
        in_preview -- Whether the search is running in preview
        """

        raise Exception("handle_results needs to be implemented")
