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
FAQ
================================================

Q: How do I enable the use of a proxy server?

A: To use a proxy server, re-run the app setup page and enter the information for a proxy server.

----------------------------------------------------------------------------------------------

Q: Can I use different proxy servers for different sites?

A: Yes, see http://lukemurphey.net/projects/splunk-website-monitoring/wiki/Using_multiple_proxies



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
|         | Updated the app to work better on Splunk 6.0                                                                     |
|---------|------------------------------------------------------------------------------------------------------------------|
| 0.9     | Added support for custom root endpoints                                                                          |
|         | Fixed issue where the searches defaulted to searching all-time                                                   |
|         | Added site changes dashboard                                                                                     |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0     | Added support for using multiple proxy servers                                                                   |
|         | Added logging of the proxy server used when the ping was performed                                               |
|         | Fixed issue where the titles of ping requests contained spaces were not shown in the interface correctly         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.1   | Fixed issue where the proxy configuration option was set as required                                             |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.2   | Status overview page now automatically starts the search                                                         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.3   | Fixed issue where setting and then clearing the sourcetype or index caused an error                              |
|         | Updated icon to work with Splunk 6.2                                                                             |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.4   | Fixed issue where setting the host field on the config page did not cause it to be included in the events        |
|         | Fixed issue where the input would not stay on the interval because it included processing time in the interval   |
|         | Fixed issue where the modular input logs were not sourcetyped correctly                                          |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.0.5   | Fixed issue where inputs might not have worked correctly                                                         |
|         | Enhanced logging for when interval gap is too large and when checkpoint file could not be found                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.1     | Added ability to filter out disabled or removed inputs from the status overview page                             |
+---------+------------------------------------------------------------------------------------------------------------------+
