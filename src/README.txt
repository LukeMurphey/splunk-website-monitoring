================================================
Overview
================================================

This app provides a mechanism for detecting when web applications are no longer responsive or are performing slowly.



================================================
Configuring Splunk
================================================

This app exposes a new input type that can be configured in the Splunk Manager. To configure it, create a new "Website Availability Check" input in the Manager under Data inputs.



================================================
Getting Support
================================================

Go to the following website if you need support:

     http://splunk-base.splunk.com/apps/83317/answers/

You can access the source-code and get technical details about the app at:

     https://github.com/LukeMurphey/splunk-website-monitoring



================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 0.5     | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.6     | Added a dashboard to show the history of a monitored site                                                        |
|         | Added highlighting of high response times in red on the main overview dashboard                                  |
|         | Fixed issues where the modular input failed to validate parameters correctly and log error messages              |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.7     | Added availability calculation to the status history dashboard                                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.8     | Added support for using a proxy server                                                                           |
+---------+------------------------------------------------------------------------------------------------------------------+
