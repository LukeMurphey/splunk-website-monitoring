[web_ping://default]
* Configure an input for determining the status of a web site

url = <value>
* The URL to be checked

interval = <value>
* Indicates how often to perform the ping

title = <value>
* A title of the URL

configuration = <value>
* Indicates which stanza in website_monitoring.conf to get the configuration information from (optional)

client_certificate = <value>
* Defines the path to a client SSL certificate (for client SSL authentication)

client_certificate_key = <value>
* Defines the path to the client certificate key (necessary if the key is in a separate file from the certificate)

username = <value>
* Defines the username to use for authenticating (only HTTP authentication supported)

password = <value>
* DEPRECATED: the password should be stored in the secure password storage system
* Defines the password to use for authenticating (only HTTP authentication supported)

user_agent = <value>
* Defines the user-agent string used by the HTTP client

should_contain_string = <value>
* Defines a string that ought to be included in the response content
* If the content isn't included then the content will be considered wrong
