# Copyright (C) 2013 Luke Murphey. All Rights Reserved.
#
# This file contains all possible options for an website_monitoring.conf file.  Use this file to  
# configure how the website_monitoring app functions.
#
# To learn more about configuration files (including precedence) please see the documentation 
# located at http://docs.splunk.com/Documentation/latest/Admin/Aboutconfigurationfiles

#****************************************************************************** 
# These options must be set under an [default] entry to apply to all inputs
# Otherwise, the stanza name must be associated with the individual input.
#****************************************************************************** 
proxy_server = <string>
    * Defines the proxy server that will be used.
    * Examples: "1.2.3.4", "proxy.acme.com"

proxy_port = <int>
    * Defines the port that the proxy server is on
    * Example: 8080
    
proxy_user = <string>
    * Defines the user account to use (leave blank to use no authentication)
    * Examples: johndoe
    
proxy_password = <string>
    * Defines the user account to use (leave blank to use no authentication)
    * Examples: 0p3n_sesame
    
proxy_type = <string>
    * Defines the protocol used by the proxy server
    * Must be one of: socks4, socks5, http

thread_limit = <int>
    * Defines the maximum number of threads that the input will create
    * Example: 200