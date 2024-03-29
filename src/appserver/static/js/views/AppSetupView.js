require.config({
    paths: {
        text: "../app/website_monitoring/js/lib/text",
        setup_view: '../app/website_monitoring/js/views/SetupView'
    }
});

define([
    "underscore",
    "jquery",
    "models/SplunkDBase",
    "setup_view",
    "text!../app/website_monitoring/js/templates/AppSetupView.html",
    "css!../app/website_monitoring/css/AppSetupView.css"
], function(
    _,
    $,
    SplunkDBaseModel,
    SetupView,
    Template
){
    var WEBSITE_MONITORING_APP_CONFIG_URL = '/en-US/splunkd/__raw/servicesNS/nobody/website_monitoring/app_config/website_monitoring/';
    var WEBSITE_MONITORING_APP_CONFIG_DEFAULT_STANZA_URL = WEBSITE_MONITORING_APP_CONFIG_URL + 'default';

    var WebsiteMonitoringConfiguration = SplunkDBaseModel.extend({
        url: WEBSITE_MONITORING_APP_CONFIG_URL,
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

    return SetupView.extend({
        className: "AppSetupView",

        events: {
            "click #save-config" : "saveConfig"
        },

        defaults: {
            "secure_storage_realm" : "website_monitoring_app_proxy",
            "secure_storage_username" : "IN_CONF_FILE"
        },

        formProperties: {
            'proxyServer' : '.proxy-address input',
            'proxyUser' : '.proxy-user input',
            'proxyIgnore' : '.proxy-ignore input',
            'proxyServerPort' : '.proxy-port input',
            'threadLimit' : '.thread-limit input',
            'proxyPassword' : '.proxy-password input',
            'proxyPasswordConfirmation' : '.proxy-password-confirm input',
            'proxyType' : '.proxy-type select',
            'responseLength': '.response-length input'
        },

        initialize: function() {
        	this.options = _.extend({}, this.defaults, this.options);
            SetupView.prototype.initialize.apply(this, [this.options]);

            this.setupValidators();

            this.website_monitoring_configuration = null;
            this.secure_storage_stanza = this.makeStorageEndpointStanza(this.options.secure_storage_username, this.options.secure_storage_realm);

            this.is_on_cloud = null;
            this.server_info = null;
        },

        updateModel: function(){

            if(this.is_on_cloud){
                this.website_monitoring_configuration.entry.content.set({
                    name: 'default',
                    
                    proxy_server: 'proxy_server',
                    proxy_port: '',
                    proxy_type: 'http',
                    proxy_ignore: '',

                    proxy_user: 'user',
                    proxy_password: '',

                    thread_limit: this.getThreadLimit(),

                    max_response_body_length: this.getResponseLength()
                }, {
                    silent: true
                });
            }
            else{
                this.website_monitoring_configuration.entry.content.set({
                    name: 'default',
                    
                    proxy_server: this.getProxyServer(),
                    proxy_port: this.getProxyServerPort(),
                    proxy_type: this.getProxyType(),
                    proxy_ignore: this.getProxyIgnore(),

                    proxy_user: this.getProxyUser(),
                    proxy_password: '', //This will be stored in secure storage

                    thread_limit: this.getThreadLimit(),

                    max_response_body_length: this.getResponseLength()
                }, {
                    silent: true
                });
            }
        },

        savePassword: function(){
            var password = this.getProxyPassword();

            // Delete the secured password if the password was cleared
            if(password.length === 0){
                return this.deleteEncryptedCredential(this.secure_storage_stanza, true);
            }
            // Otherwise, update it
            else{
                return this.saveEncryptedCredential(this.options.secure_storage_username, password, this.options.secure_storage_realm);
            }
        },

        saveConfig: function(){
            
            if(!this.userHasAdminAllObjects()){
                alert("You don't have permission to edit this app");
            }
            else if(this.validate()){
                // Update the model with the latest info so that we can save it
                this.updateModel();

                this.showFormInProgress(true);

                $.when(
                    this.website_monitoring_configuration.save({}, {
                        'url' : WEBSITE_MONITORING_APP_CONFIG_DEFAULT_STANZA_URL
                    }),
                    this.savePassword()
                )
                // If successful, show a success message
                .then(
                    function(){
                        this.showInfoMessage("Configuration successfully saved");

                        this.showFormInProgress(false);
                        this.redirectIfNecessary("status_overview");
                        
                    }.bind(this)
                )
                // Otherwise, show a failure message
                .fail(function (response) {
                    this.showFormInProgress(false);

                    if (response.responseJSON && response.responseJSON.messages && response.responseJSON.messages.length > 0 && response.responseJSON.messages[0].text) {
                        this.showWarningMessage("Configuration could not be saved: " + response.responseJSON.messages[0].text);
                    } else {
                        this.showWarningMessage("Configuration could not be saved");
                    }
                }.bind(this));
                
                // Set the app as configured
                this.setConfigured();

            }

            return false;
        },
        
        /**
         * Sets the controls as enabled or disabled.
         */
        setControlsEnabled: function(enabled){

            if(enabled === undefined){
                enabled = true;
            }

            $('input,select', this.el).prop('disabled', !enabled);

        },

        /**
         * Make the form as in progress.
         */
        showFormInProgress: function(inProgress){
            $('.btn-primary').prop('disabled', inProgress);
            this.setControlsEnabled(!inProgress);

            if(inProgress){
                $('.btn-primary').text("Saving Configuration...");
            }
            else{
                $('.btn-primary').text("Save Configuration");
            }
        },

        /**
         * Fetch the app configuration data.
         */
        fetchAppConfiguration: function(){
            this.website_monitoring_configuration = new WebsiteMonitoringConfiguration();

            this.setControlsEnabled(false);

            // Get a promise ready
            var promise = jQuery.Deferred();

            this.website_monitoring_configuration.fetch({
                url: WEBSITE_MONITORING_APP_CONFIG_DEFAULT_STANZA_URL,
                id: 'default',
                success: function (model, response, options) {
                    console.info("Successfully retrieved the default website_monitoring configuration");
                    this.setProxyServer(model.entry.content.attributes.proxy_server);
                    this.setProxyServerPort(model.entry.content.attributes.proxy_port);
                    this.setProxyType(model.entry.content.attributes.proxy_type);
                    this.setProxyIgnore(model.entry.content.attributes.proxy_ignore);

                    this.setThreadLimit(model.entry.content.attributes.thread_limit);
                    this.setResponseLength(model.entry.content.attributes.max_response_body_length);

                    this.setProxyUser(model.entry.content.attributes.proxy_user);
                    this.setProxyPassword(model.entry.content.attributes.proxy_password);
                    this.setProxyPasswordConfirmation(model.entry.content.attributes.proxy_password);

                    promise.resolve(response);
                }.bind(this),
                error: function(response, textStatus, errorThrown){

                    /*
                     * Handle the case where the default stanza doesn't exist. Cloud rules don't
                     * allow default stanzas so we have to put defaults in code.
                     */
        			if(textStatus.status === 404){ 
                        console.info("Default website_monitoring configuration doesn't exist yet");
                        // Set to the default values
                        this.setProxyServer("");
                        this.setProxyServerPort("");
                        this.setProxyType("http");
                        this.setProxyIgnore("");
    
                        this.setThreadLimit("200");
                        this.setResponseLength("1000");
    
                        this.setProxyUser("");
                        this.setProxyPassword("");
                        this.setProxyPasswordConfirmation("");

                        // Start with a new configuration since one doesn't exist yet
                        this.website_monitoring_configuration = new WebsiteMonitoringConfiguration({
                            user: 'nobody',
                            app: 'website_monitoring'
                        });

                        promise.resolve(response);
        			}
                    else{
                        console.warn("Unsuccessfully retrieved the default website_monitoring configuration");
                        promise.reject();
                    }
                }.bind(this)
            });

            return promise;
        },

        render: function () {

            $.when(
                this.isOnCloud()
            )
            .then(function(is_on_cloud){

                if(this.userHasAdminAllObjects()){

                    // Render the view
                    this.$el.html(_.template(Template, {
                        'has_permission' : this.userHasAdminAllObjects(),
                        'is_on_cloud' : is_on_cloud
                    }));

                    // Start the process of loading the app configuration if necessary
                    if(this.website_monitoring_configuration === null){

                        this.setControlsEnabled(false);

                        $.when(
                            this.fetchAppConfiguration(),
                            this.getEncryptedCredential(this.secure_storage_stanza, true)
                        )
                        // If successful, then load the credential
                        .then(
                            function(a, credential){

                                if(credential){
                                    this.setProxyPassword(credential.entry.content.attributes.clear_password);
                                    this.setProxyPasswordConfirmation(credential.entry.content.attributes.clear_password);
                                }

                                this.setControlsEnabled(true);
                            }.bind(this)
                        );

                    }

                }
                else{
                    this.$el.html("Sorry, you don't have permission to perform setup");
                }
            }.bind(this));
        },

        /**
         * Below is a list of validators for the form fields.
         */
        isValidPort: function(value){
            var port = parseInt(value, 10); 

            if(value === ''){
                return true;
            }
            else if(isNaN(port)){
                return false;
            }
            else if(port < 1 || port > 65535){
                return false;
            }
            else{
                return true;
            }
        },

        isValidThreadLimit: function(value){
            var threads = parseInt(value, 10); 

            if(isNaN(threads)){
                return false;
            }
            else if(threads < 1){
                return false;
            }
            else{
                return true;
            }
        },

        isValidResponseLength: function(value){
            var lengths = parseInt(value,10);

            if(isNaN(lengths)) {
                return false;
            }
            else if(lengths < -1 || lengths > 1048576){
                return false;
            }
            else{
                return true;
            }
        },

        matchesPassword: function(value){
            var originalPassword = this.getProxyPassword();

            if(originalPassword !== value){
                return false;
            }
            else{
                return true;
            }
        },

        isValidServer: function(value){

            var domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$/gm;
            var ipRegex = /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g;

            if(value === ''){
                return true;
            }
            else if(domainRegex.exec(value) || ipRegex.exec(value)){
                return true;
            }
            else{
                return false;
            }
        },

        /**
         * Setup the validators so that we can detect bad input
         */
        setupValidators: function(){
            // Note: the getters are defined by the SetupView which creates the setters and getters from formProperties
            this.addValidator('.proxy-address', this.getProxyServer.bind(this), this.isValidServer, "Must be a valid domain name or IP address");
            this.addValidator('.proxy-port', this.getProxyServerPort.bind(this), this.isValidPort, "Must be a valid port number");
            this.addValidator('.thread-limit', this.getThreadLimit.bind(this), this.isValidThreadLimit, "Must be an integer greater than 0");
            this.addValidator('.response-length', this.getResponseLength.bind(this), this.isValidResponseLength, "Must be an integer greather than -1 and less than 104876");
            this.addValidator('.proxy-password-confirm', this.getProxyPasswordConfirmation.bind(this), this.matchesPassword.bind(this), "Must match the password");
        },
    });
});