================================================
Overview
================================================

This app provides a mechanism for detecting when web applications are no longer responsive or are performing slowly.



================================================
Configuring Splunk
================================================

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Once the app is installed, you can use the app by configuring a new input:
  1. Navigate to "Settings » Data Inputs" at the menu at the top of Splunk's user interface.
  2. Click "Website Availability Check"
  3. Click "New" to make a new instance of an input

Alternatively, you can use the batch creation UI to make several inputs:
  1. Open the "Website Monitoring" app from the main launcher.
  2. Open the "Create Inputs" view from the app navigation
  3. Enter the URLs you would like to monitor and press save to creates



================================================
Getting Support
================================================

Go to the following website if you need support:

     https://answers.splunk.com/app/questions/1493.html

You can access the source-code and get technical details about the app at:

     https://github.com/LukeMurphey/splunk-website-monitoring



================================================
Third Party Dependencies
================================================

See the following for a list of the third-party dependencies included in this app: https://lukemurphey.net/projects/splunk-website-monitoring/wiki/Dependencies/11



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

A: Yes, just assign users the "edit_modinput_web_ping" and "edit_tcp" capabilities. You will likely want to give them the "list_inputs"capability too.

----------------------------------------------------------------------------------------------

Q: How do I prevent users from making inputs on a Search Head Cluster?

A: Remove the "edit_modinput_web_ping" capability from all roles when you are using the app in a Search Head Cluster to prevent people from making inputs on a cluster.



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
|         | Improved styling of the Status Overview dashboard                                                                |
|         | Changed the batch creation page to be no longer be considered a dashboard                                        |
|         | New app icon                                                                                                     |
|         | Replaced rest call on the Status Overview dashboard with a lookup                                                |
|         | Fixed NTLM authentication and improved detection of the authentication that the server supports                  |
|         | Improved messaging regarding the execution gaps and splunkd connection exception messages                        |
|         | Improved appearance of the Status Overview table                                                                 |
|         | Fixed intermittent Javascript error on the Status Overview dashboard                                             |
|         | Made the Status Overview page more responsive (works better on iPads)                                            |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.1   | Styling enhancements to the Status Overview dashboard (font icons, cell background colors, etc.)                 |
|         | Fixed issue where the NTLM authentication didn't work on some Splunk installations                               |
|         | Added the search views to the nav                                                                                |
|         | Improving the capability checking on the batch input creation page                                               |
|         | Fixed issues on the batch input creation page that prevent people with permissions from making inputs            |
|         | Updated the app icon to improve appearance on the main apps page in Splunk                                       |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.0.2   | Fixed broken link for app configuration                                                                          |
|         | Replaced deprecated SimpleXML attributes                                                                         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.1     | Number of executing threads can now be customized                                                                |
|         | Connection failure log messages now include the related URL                                                      |
|         | Status Overview now aggregates by source, not url                                                                |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.1.1   | Fixed btool error due to "thread_limit" not being defined                                                        |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.2     | Added ability to modify what is considered a failure (response time threshold and response codes)                |
|         | Fixed issue preventing message from didn't appearing on the Status Overview page noting no inputs exist          |
|         | Improved compatibility with Splunk 6.6                                                                           |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.3     | Added new simple XML setup page                                                                                  |
|         | Passwords are now stored using Splunk's secure storage                                                           |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.4     | Updating dependencies to newer versions                                                                          |
|         | Added restrictions necessary to gain Cloud certification                                                         |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.4.1   | Disabled the use of a proxy on Splunk Cloud since this is unnecessary on Cloud                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.5     | Added the ability to alert when the response of a web-page doesn't include particular content                    |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.6     | Fixed issue where the macro for a definition of a failure wouldn't match the friendly name in UI                 |
|         | Made REST calls more resilient to transient Splunkd connection errors                                            |
|         | Added the ability to define the indexes to search by default (see the macro "website_monitoring_search_index")   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.6.1   | Fixed issue where the alert search didn't provide information on some outages                                    |
|         | Fixed Status Overview dashboard which didn't include all errors when "Include only failures" was selected        |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.6.2   | Connection failures now include a lot more detail which makes debugging easier                                   |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.0   | Added an Executive Summary dashboard                                                                             |
|         | You can no longer make inputs on an SHC (since they need to be on a forwarder)                                   |
|         | Inputs on an SHC environment no longer run unless on the SHC captain                                             |
|         | Fixed the drilldown from "Status Overview" to "Status History" which failed to carry over some arguments         |
|         | Apps should now be self-installable on Splunk Cloud                                                              |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.1   | Fixed issue where NTLM log message did not work                                                                  |
|         | Fixed issue where the did not work when using the developer license of Splunk                                    |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.2   | Fixed issue where timeouts where not detected as unavailability                                                  |
|         | Fixed issue where the executive summary page didn't use the failure definition macro                             |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.3   | Fixed issue where only the first 30 passwords could be accessed                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.4   | Added ability to define a list of hosts to ignore the proxy for                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|
| 2.7.5   | Fixed error on Splunk Cloud                                                                                      |
|         | Removed requirement of 'edit_tcp' capability                                                                     |
+---------+------------------------------------------------------------------------------------------------------------------+

