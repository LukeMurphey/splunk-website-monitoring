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

     https://answers.splunk.com/app/questions/1493.html

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

----------------------------------------------------------------------------------------------

Q: Can I allow non-admin users to make and edit inputs?

A: Yes, just assign users the "edit_modinput_web_ping" capability. You will likely want to give them the "list_inputs"capability too.



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
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.1.1   | Fixed issue where proxy servers with underscores were not allowed                                                |
|         | Website monitoring REST handler logs are now source-typed correctly                                              |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.1.2   | The dialog that tells users how to setup an input is now hidden if an input exists                               |
|         | Failure to load checkpoint data due to corruption is now handled more gracefully                                 |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.1.3   | Fixed reference to Insteon app code                                                                              |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.2.0   | Added capability "edit_modinput_web_ping" which can be assigned to allow non-admins to make inputs               |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.2.1   | Added capability "edit_modinput_web_ping" to admin and power users                                               |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.3     | Added support for Server Name Indication (SNI); only works on Splunk installs with Python 2.7.9+                 |
|         | Added support for client SSL certificate authentication                                                          |
|         | Fixed issue where multiple log entries were being created for the same event                                     |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.3.1   | Added more rows to the list of items on the Status Overview dashboard                                            |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.3.2   | Disabling server SSL certificate verification which is incorrectly failing on valid certificates at times        |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.4.0   | Adding HTTP authentication support                                                                               |
|         | Added improved modular input UI                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.5.0   | Added ability to specify the user-agent string                                                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.5.1   | Updated connection error message to make it more clear how to troubleshoot the problem                           |
|         | Eliminating error message regarding InsecureRequestWarning                                                       |
|         | Fixed error that can happen when attempting to determine authentication type                                     |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.6     | Added page to create multiple inputs (batch creation)                                                            |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.6.1   | Fixed issue where the input could fail when attempting to determine the authentication type                      |
|         | Made input more resilient to errors (restarts upon errors)                                                       |
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.6.2   | Message indicating that authentication method could not be determined is now a warning                           |
|         | Splunkd connection exceptions are more gracefully handled when attempting to determine proxy configuration       |
|         | Fixed issue where the message indicating that no inputs existed could sometimes be shown more than once          |
|         | Fixed issue where the message indicating that no inputs existed would show when inputs did exist (on other hosts)|
|---------|------------------------------------------------------------------------------------------------------------------|
| 1.6.3   | Fixed issue where batch created inputs were made in the search app as opposed to the Website Monitoring app      |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0     | Input now uses a multi-threaded model supporting a vastly higher number of inputs                                |
|         | Added health monitoring dashboards                                                                               |
|         | Fixed issue where sometimes the status was left blank when a connection to a website failed                      |
|         | Updated the Status History dashboard with new single value widgets                                               |
|         | Fixed incorrect link to answers in README                                                                        |
|         | Improved handling of connection errors on Windows                                                                |
+---------+------------------------------------------------------------------------------------------------------------------+

