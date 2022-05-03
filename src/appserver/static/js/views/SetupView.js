/*
 * This view is intended to be used as a base class for simpleXML setup views. This class is
 * intended to make creation of a setup view easier by:
 * 
 *   1) Providing a mechanism for setting the app as configured so that users aren't redirected through setup again.
 *   2) Providing a means for permission checking so that you can ensure that the user has admin_all_objects
 * 
 * To use this class, you will need to do the following:
 * 
 *   1) Make your view class sub-class "SetupView" (the class providing in this file)
 *   2) Call this classes initialize() function in your classes initialize() function.
 *   3) Call setConfigured() when your class completes setup. This will mark the app as configured.
 * 
 * 
 * 
 * Below is a short example of of the use of this class:
 
require.config({
    paths: {
        setup_view: '../app/my_custom_app/js/views/SetupView'
    }
});

define([
    "underscore",
    "backbone",
    "jquery",
    "setup_view",
], function(
    _,
    Backbone,
    $,
    SetupView
){

    return SetupView.extend({
        className: "MyCustomAppSetupView",

        events: {
            "click #save-config" : "saveConfig"
        },
        
        defaults: {
        	app_name: "my_custom_app"
        },

        initialize: function() {
        	this.options = _.extend({}, this.defaults, this.options);
            SetupView.prototype.initialize.apply(this, [this.options]);
        },

        saveConfig: function(){
            if(this.userHasAdminAllObjects()){
                this.setConfigured();
            }
            else{
                alert("You don't have permission to edit this app");
            }
        },
        
        render: function () {
            this.$el.html('<a href="#" class="btn btn-primary" id="save-config">Save Configuration</a>');
        }
    });
});
 */

require.config({
    paths: {
        "ValidationView": "../app/website_monitoring/js/views/ValidationView"
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "models/SplunkDBase",
    "collections/SplunkDsBase",
    "ValidationView",
    "util/splunkd_utils",
    "models/services/server/ServerInfo",
    "splunkjs/mvc/utils"
], function(
    _,
    Backbone,
    mvc,
    $,
    SplunkDBaseModel,
    SplunkDsBaseCollection,
    ValidationView,
    splunkd_utils,
	ServerInfo,
    mvc_utils
){

	var AppConfig = SplunkDBaseModel.extend({
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

    var EncryptedCredential = SplunkDBaseModel.extend({
        url: "storage/passwords",
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

	var EncryptedCredentials = SplunkDsBaseCollection.extend({
	    url: "storage/passwords",
        model: EncryptedCredential,
	    initialize: function() {
	      SplunkDsBaseCollection.prototype.initialize.apply(this, arguments);
	    }
	});

    return ValidationView.extend({
        className: "SetupView",
        
        defaults: {
        	app_name: null
        },

        /**
         * Override this in order to have the class make setters and getters for you.
         * 
         * Consider this example:
         * 
         *    formProperties: {
         *        'proxyServer' : '.proxy-address input'
         *     }
         * 
         * This would cause two functions to be created:
         * 
         *     * setProxyServer(newValue)
         *     * getProxyServer()
         * 
         * The functions will call $('.proxy-address input', this.$el).val() to set or get the value accordingly.
         */
        formProperties: {
            // 'proxyServer' : '.proxy-address input'
        },

        initialize: function() {

            // Merge the provided options and the defaults
        	this.options = _.extend({}, this.defaults, this.options);
            ValidationView.prototype.initialize.apply(this, [this.options]);
        	
        	// Get the app name
        	this.app_name = this.options.app_name;

            // This indicates if the app was configured
            this.is_app_configured = null;

            this.app_config = null;
            this.encrypted_credential = null;

            this.capabilities = null;
            this.is_using_free_license = $C.SPLUNKD_FREE_LICENSE;

            // Start the process of the getting the app.conf settings
            this.getAppConfig();
            this.getInputStanza();

            // This stores a list of existing credentials
            this.credentials = null;

            this.setupProperties();
        },

        isOnCloud: function(){

            // Initialize the the is_on_cloud variable if necessary
            if(typeof this.is_on_cloud === "undefined"){
                this.is_on_cloud = null;
            }
            
            // Get a promise ready
            var promise = jQuery.Deferred();

            // If we already loaded the cloud status, then return it
			if(this.is_on_cloud !== null){
				promise.resolve(this.is_on_cloud);
            }

            // Fetch the cloud status
            new ServerInfo().fetch().done(function(model){

				if(model.entry[0].content.instance_type){
					this.is_on_cloud = model.entry[0].content.instance_type === 'cloud';
				}
				else{
					this.is_on_cloud = false;
                }

                promise.resolve(this.is_on_cloud);
            });

            return promise;

        },

        /**
         * Get the app configuration.
         */
        getAppConfig: function(){

            // Use the current app if the app name is not defined
            if(this.app_name === null || this.app_name === undefined){
                this.app_name = mvc_utils.getCurrentApp();
            }

	        this.app_config = new AppConfig();
	        	
            this.app_config.fetch({
                url: splunkd_utils.fullpath('/servicesNS/nobody/system/apps/local/' + this.app_name),
                success: function (model, response, options) {
                    console.info("Successfully retrieved the app configuration");
                    this.is_app_configured = model.entry.associated.content.attributes.configured;
                }.bind(this),
                error: function () {
                    console.warn("Unable to retrieve the app configuration");
                }.bind(this)
            });
        },

        /**
         * Get the app configuration.
         */
        getInputStanza: function(){

            // Use the current app if the app name is not defined
            if(this.input_stanza === null || this.input_stanza === undefined){
                return;
            }

	        this.default_input_stanza = new AppConfig();
	        	
            this.default_input_stanza.fetch({
                url: splunkd_utils.fullpath('/servicesNS/nobody/system/admin/conf-inputs/' + this.app_name),
                success: function (model, response, options) {
                    console.info("Successfully retrieved the default input stanza configuration");
                    this.default_input = model.entry.associated.content.attributes;
                }.bind(this),
                error: function () {
                    console.warn("Unable to retrieve the default input stanza configuration");
                }.bind(this)
            });
        },

        /**
         * Escape the colons. This is necessary for secure password stanzas.
         */
        escapeColons: function(str){
            return str.replace(":", "\\:");
        },

        /**
         * Make the stanza name for a entry in the storage/passwords endpoint from the username and realm.
         */
        makeStorageEndpointStanza: function(username, realm){

            if(this.isEmpty(realm)){
                realm = "";
            }

            return this.escapeColons(realm) + ":" + this.escapeColons(username) + ":";
        },

        /**
         * Capitolize the first letter of the string.
         */
        capitolizeFirstLetter: function (string){
            return string.charAt(0).toUpperCase() + string.slice(1);
        },

        /**
         * Setup a property that allows the given attribute to be.
         */
        setupProperty: function(propertyName, selector){

            var setterName = 'set' + this.capitolizeFirstLetter(propertyName);
            var getterName = 'get' + this.capitolizeFirstLetter(propertyName);

            if(this[setterName] === undefined){
                this[setterName] = function(value){
                    $(selector, this.$el).val(value);
                };
            }

            if(this[getterName] === undefined){
                this[getterName] = function(value){
                    return $(selector, this.$el).val();
                };
            }
        },

        /**
         * Register properties for all of the properties.
         */
        setupProperties: function(){
            for(var name in this.formProperties){
                this.setupProperty(name, this.formProperties[name]);
            }
        },

        /**
         * Get the encrypted credential by realm.
         */
        getEncryptedCredentialByRealm: function(realm, returnAll){

            if(typeof returnAll === "undefined"){
                returnAll = false;
            }
    
            // Get a promise ready
            var promise = jQuery.Deferred();

            // Get the credentials
        	credentials = new EncryptedCredentials();
        	
            credentials.fetch({
                success: function (credentials) {
                    console.info("Successfully retrieved the list of credentials");

                    // Find the credential(s) with the realm
                    var credentialModels = credentials.models[c].filter(function (entry) {
                        return credentials.models[c].entry.content.attributes.realm === realm;
                    });

                    // Return all of them if requested
                    if (returnAll) {
                        promise.resolve(credentialModels);
                    }

                    // Return the first if they only wanted one
                    else if (credentialModels.length > 0) {
                        promise.resolve(credentialModels[0]);
                    }

                    // We found none, return null
                    else {
                        promise.resolve(null);
                    }
                },
                error: function () {
                    console.error("Unable to fetch the credential");
                    promise.reject();
                }
            });

            return promise;
        },

        /**
         * Get the encrypted credential.
         */
        getEncryptedCredential: function(stanza, ignoreNotFound){

            if(typeof ignoreNotFound === "undefined"){
                ignoreNotFound = false;
            }

            // Get a promise ready
        	var promise = jQuery.Deferred();

            // Make an instance to fetch into
	        this.encrypted_credential = new EncryptedCredential();

            // Fetch it
            this.encrypted_credential.fetch({
                url: splunkd_utils.fullpath('/services/storage/passwords/' + encodeURIComponent(stanza)),
                success: function (model, response, options) {
                    console.info("Successfully retrieved the encrypted credential");
                    promise.resolve(model);
                }.bind(this),
                error: function () {
                    if(ignoreNotFound){
                        promise.resolve(null);
                    }
                    else{
                        console.warn("Unable to retrieve the encrypted credential");
                        promise.reject();
                    }
                }.bind(this)
            });

            // Return the promise so that the caller can respond
            return promise;
        },

        /**
         * This is called when a credential was successfully saved.
         */
        credentialSuccessfullySaved: function(created_new_entry){
            // Fill this in when sub-classing
        },

        /**
         * Get the name of the app to use for saving entries to.
         */
        getAppName: function(){
            if(this.app_name === null){
                return mvc_utils.getCurrentApp();
            }
            else{
                return this.app_name;
            }
        },

        /**
         * Return true if the input is undefined, null or is blank.
         */
        isEmpty: function(value, allowBlanks){

            // Assign a default for allowBlanks
            if(typeof allowBlanks == "undefined"){
                allowBlanks = false;
            }

            // Test the value
            if(typeof value == "undefined"){
                return true;
            }

            else if(value === null){
                return true;
            }

            else if(value === "" && !allowBlanks){
                return true;
            }

            return false;
        },

        /**
         * Delete the encrypted credential. This will create a new encrypted credential if it doesn't exist.
         * 
         * If it does exist, it will modify the existing credential.
         */
        deleteEncryptedCredential: function(stanza, ignoreNotFound){

            if(typeof ignoreNotFound === "undefined"){
                ignoreNotFound = false;
            }

            // Get a promise ready
            var promise = jQuery.Deferred();

            // See if the credential already exists and delete.
            $.when(this.getEncryptedCredential(stanza)).done(

                // Delete the entry
                function(credentialModel){
                    credentialModel.destroy().done(function(){
                        promise.resolve();
                    }.bind(this));
                }.bind(this)
            )
            .fail(
                function(){
                    if(ignoreNotFound){
                        promise.resolve();
                    }
                    else{
                        promise.reject();
                    }
                }.bind(this)
            );

            return promise;

        },

        /**
         * Save the encrypted credential. This will create a new encrypted credential if it doesn't exist.
         * 
         * If it does exist, it will modify the existing credential.
         */
        saveEncryptedCredential: function(username, password, realm){

            // Get a promise ready
            var promise = jQuery.Deferred();

            // Verify the username
            if(this.isEmpty(username)){
                alert("The username field cannot be empty");
                promise.reject("The username field cannot be empty");
                return promise;
            }

            // Verify the password
            if(this.isEmpty(password, true)){
                alert("The password field cannot be empty");
                promise.reject("The password field cannot be empty");
                return promise;
            }

            // Create a reference to the stanza name so that we can find if a credential already exists
            var stanza = this.makeStorageEndpointStanza(username, realm);
    
            // See if the credential already exists and edit it instead.
            $.when(this.getEncryptedCredential(stanza)).done(

                // Save changes to the existing credential
                function(credentialModel){

                    // Save changes to the existing entry
                    $.when(this.postEncryptedCredential(credentialModel, username, password, realm)).done(function(){
                        // Run the function that happens when a credential was saved
                        this.credentialSuccessfullySaved(false);
                        promise.resolve();
                    }.bind(this));

                    
                }.bind(this)
            )
            .fail(
                function(){

                    // Make a new credential instance
                    credentialModel = new EncryptedCredential({
                        user: 'nobody',
                        app: this.getAppName()
                    });

                    // Save it
                    $.when(this.postEncryptedCredential(credentialModel, username, password, realm)).done(function(){
                        // Run the function that happens when a credential was saved
                        this.credentialSuccessfullySaved(true);
                        promise.resolve();
                    }.bind(this));
    
                }.bind(this)
            );

            return promise;

        },

        /**
         * Save the encrypted credential.
         */
        postEncryptedCredential: function(credentialModel, username, password, realm){

            // Get a promise ready
        	var promise = jQuery.Deferred();

            // Use the current app if the app name is not defined
            if(this.app_name === null){
                this.app_name = mvc_utils.getCurrentApp();
            }

            // Modify the model
            credentialModel.entry.content.set({
                name: username,
                password: password,
                username: username,
                realm: realm
            }, {
                silent: true
            });

            // Kick off the request to edit the entry
            var saveResponse = credentialModel.save();

            // Wire up a response to tell the user if this was a success
            if (saveResponse) {

                // If successful, show a success message
                saveResponse.done(function(model, response, options){
                    console.info("Credential was successfully saved");

                    promise.resolve(model, response, options);
                }.bind(this))

                // Otherwise, show a failure message
                .fail(function(response){
                    console.warn("Credential was not successfully updated");

                    promise.reject(response);
                }.bind(this));
            }

            // Return the promise
            return promise;
        },

        /**
         * Redirect users to the given view if the user was redirected to setup. This is useful for
         * cases where the user was directed to perform setup because the app was not yet
         * configured. This reproduces the same behavior as the original setup page does.
         */
        redirectIfNecessary: function(viewToRedirectTo){
            if(Splunk.util.getParameter("redirect_to_custom_setup") === "1"){
                document.location = viewToRedirectTo;
            }
        },

        /**
         * Save the app config to note that it is now configured.
         */
        setConfigured: function(){

            // Not necessary to set the app as configured since it is already configured
            if(this.is_app_configured){
                console.info("App is already set as configured; no need to update it");
                return;
            }

            // Modify the model
            this.app_config.entry.content.set({
                configured: true
            }, {
                silent: true
            });

            // Kick off the request to edit the entry
            var saveResponse = this.app_config.save();

            // Wire up a response to tell the user if this was a success
            if (saveResponse) {

                // If successful, show a success message
                saveResponse.done(function(model, response, options){
                    console.info("App configuration was successfully updated");
                }.bind(this))

                // Otherwise, show a failure message
                .fail(function(response){
                    console.warn("App configuration was not successfully updated");
                }.bind(this));
            }

        },

        /**
         * Determine if the user has the given capability.
         */
        hasCapability: function(capability){

        	var uri = Splunk.util.make_url("/splunkd/__raw/services/authentication/current-context?output_mode=json");

        	if(this.capabilities === null){

	            // Fire off the request
	            jQuery.ajax({
	            	url:     uri,
	                type:    'GET',
	                async:   false,
	                success: function(result) {

	                	if(result !== undefined){
	                		this.capabilities = result.entry[0].content.capabilities;
	                	}

	                }.bind(this)
	            });
        	}

			// Determine if the user should be considered as having access
			if(this.is_using_free_license){
				return true;
			}
			else{
				return $.inArray(capability, this.capabilities) >= 0;
			}

        },

        /**
         * Return true if the user has 'admin_all_objects'.
         */
        userHasAdminAllObjects: function(){
            return this.hasCapability('admin_all_objects');
        }
    });
});