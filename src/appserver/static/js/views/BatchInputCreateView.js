
require.config({
    paths: {
        "text": "../app/website_monitoring/js/lib/text",
        "bootstrap-tags-input": "../app/website_monitoring/js/lib/bootstrap-tagsinput.min"
    },
    shim: {
        'bootstrap-tags-input': {
        	deps: ['jquery']
        }
    }
});

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
	"util/splunkd_utils",
	"models/SplunkDBase",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
	"models/services/server/ServerInfo",
    'text!../app/website_monitoring/js/templates/BatchInputCreateView.html',
    "bootstrap-tags-input",
    "splunk.util",
    "css!../app/website_monitoring/css/BatchInputCreateView.css",
    "css!../app/website_monitoring/js/lib/bootstrap-tagsinput.css"
], function(
    _,
    Backbone,
    mvc,
	splunkd_utils,
	SplunkDBaseModel,
    $,
    SimpleSplunkView,
	ServerInfo,
    Template
){
    var SHCInfo = SplunkDBaseModel.extend({
		url: '/en-US/splunkd/services/shcluster/status',
		//urlRoot: "shcluster",
		//id: 'status',
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

    // Define the custom view class
    var BatchInputCreateView = SimpleSplunkView.extend({
        className: "BatchInputCreateView",
        
        defaults: {
        	
        },
        
        events: {
        	"click .create-inputs" : "doCreateInputs",
        	"click .stop-creating-inputs" : "stopCreateInputs"
        },
        
        initialize: function() {
        	this.options = _.extend({}, this.defaults, this.options);
        	
        	//this.some_option = this.options.some_option;
        	
        	// These are internal variables
        	this.processing_queue = [];
        	this.processed_queue = [];
        	this.unprocessed_queue = [];
        	this.interval = null;
        	this.index = null;
        	this.dont_duplicate = true;
        	this.stop_processing = false;
        	this.capabilities = null;
        	this.inputs = null;
        	this.existing_input_names = [];
			this.is_on_cloud = null;
        	
        	this.getExistingInputs();
        },
        
        /**
         * Parses a URL into chunks. See https://gist.github.com/jlong/2428561
         */
        parseURL: function(url){
        	var parser = document.createElement('a');
        	parser.href = url;

        	/*
        	parser.protocol; // => "http:"
        	parser.hostname; // => "example.com"
        	parser.port;     // => "3000"
        	parser.pathname; // => "/pathname/"
        	parser.search;   // => "?search=test"
        	parser.hash;     // => "#hash"
        	parser.host;     // => "example.com:3000"
        	*/
        	
        	return parser;
        },
        
        /**
         * Generate a suggested title from the URL.
         */
        generateTitle: function(url){
        	var parsed = this.parseURL(url);
        	return parsed.hostname;
        },
        
        /**
         * Generate a suggested stanza from the URL.
         */
        generateStanza: function(url, existing_stanzas){
        	
        	// Set a default value for the existing_stanzas argument
        	if( typeof existing_stanzas == 'undefined' || existing_stanzas === null){
        		existing_stanzas = [];
        	}
        	
        	// If we have no existing stanzas, then just make up a name and go with it
        	if(existing_stanzas.length === 0){
        		var parsed = this.parseURL(url);
            	return parsed.hostname.replace(/[-.]/g, "_");
        	}
        	
        	var parsed = this.parseURL(url);
        	var stanza_base = parsed.hostname.replace(/[-.]/g, "_");
        	var possible_stanza = stanza_base;
        	var stanza_suffix_offset = 0;
        	var collision_found = false;
        	
        	while(true){
        		
        		collision_found = false;
        		
        		// See if we have a collision
            	for(var c = 0; c < existing_stanzas.length; c++){
            		if(existing_stanzas[c] === possible_stanza){
            			collision_found = true;
            			break;
            		}
            	}
        		
            	// Stop if we don't have a collision
            	if(!collision_found){
            		return possible_stanza;
            	}
            	
            	// We have a collision, continue
            	else{
            		stanza_suffix_offset = stanza_suffix_offset + 1;
            		possible_stanza = stanza_base + "_" + stanza_suffix_offset;
            	}
        		    		
        	}
        	
        },
        
        /**
         * Create an input
         */
        createInput: function(url, interval, index, name, title){
        	
        	// Get a promise ready
        	var promise = jQuery.Deferred();
        	
        	// Set a default value for the arguments
        	if( typeof name == 'undefined' ){
        		name = null;
        	}
        	
        	if( typeof title == 'undefined' ){
        		title = null;
        	}
        	
        	if( typeof index == 'undefined' ){
        		index = null;
        	}
        	
        	// Populate defaults for the arguments
        	if(name === null){
        		name = this.generateStanza(url, this.existing_input_names);
        	}
        	
        	if(title === null){
        		title = this.generateTitle(url);
        	}
        	
        	// Make the data that will be posted to the server
        	var data = {
        		"url": url,
        		"interval": interval,
        		"name": name,
        		"title": title,
        	};
        	
        	if(index !== null){
        		data["index"] = index;
        	}
        	
        	// Perform the call
        	$.ajax({
        			url: splunkd_utils.fullpath("/servicesNS/" + Splunk.util.getConfigValue("USERNAME") +  "/website_monitoring/data/inputs/web_ping"),
        			data: data,
        			type: 'POST',
        			
        			// On success
        			success: function(data) {
        				console.info('Input created');
        				
        				// Remember that we processed this one
        				this.processed_queue.push(url);
        				
        				// Make sure that we add the name so that we can detect duplicated names
        				this.existing_input_names.push(name);
        				
        			}.bind(this),
        		  
        			// On complete
        			complete: function(jqXHR, textStatus){
        				
        				// Handle cases where the input already existing or the user did not have permissions
        				if( jqXHR.status == 403){
        					console.info('Inadequate permissions');
        					this.showWarningMessage("You do not have permission to make inputs");
        				}
        				else if( jqXHR.status == 409){
        					console.info('Input already exists, skipping this one');
        				}
        				
        				promise.resolve();
        			  
        			}.bind(this),
        		  
        			// On error
        			error: function(jqXHR, textStatus, errorThrown){
        				
        				// These responses indicate that the user doesn't have permission of the input already exists
        				if( jqXHR.status != 403 && jqXHR.status != 409 ){
        					console.info('Input creation failed');
        				}
    					
    					// Remember that we couldn't process this on
    					this.unprocessed_queue.push(url);
    					
        			}.bind(this)
        	});
        	
        	return promise;
        },
        
        /**
         * Keep on processing the inputs in the queue.
         */
        createNextInput: function(){
        	
        	// Stop if we are asked to
        	if(this.stop_processing){
        		return;
        	}
        	
        	// Update the progress bar
        	var progress = 100 * ((this.processed_queue.length + this.unprocessed_queue.length) / (this.processing_queue.length + this.processed_queue.length + this.unprocessed_queue.length));
        	$(".bar", this.$el).css("width", progress + "%");
        	
        	// Stop if we are done
        	if(this.processing_queue.length === 0){
        		
				if(this.processed_queue.length > 0){
					// Show a message noting that we are done
					this.showInfoMessage("Done creating the inputs (" + this.processed_queue.length + " created)");
				}
        		
        		var extra_message = "";
        		
        		if(this.dont_duplicate){
        			extra_message = " (duplicates are being skipped)";
        		}
        		
        		if(this.unprocessed_queue.length === 1){
        			this.showWarningMessage("1 input was not created" + extra_message);
        		}
        		else if(this.unprocessed_queue.length > 0){
        			this.showWarningMessage("" + this.unprocessed_queue.length + " inputs were not created" + extra_message);
        		}
        		
        		// Hide the dialog
        		$("#progress-modal", this.$el).modal('hide');
        		
        		// Clear the inputs we successfully created
				for(var c = 0; c < this.processed_queue.length; c++){
					$("#urls", this.$el).tagsinput('remove', this.processed_queue[c]);
				}
        	}
        	
        	// Otherwise, keep going
        	else{
        		
        		// Get the next entry
        		var url = this.processing_queue.pop();
        		
        		// Make sure this URL doesn't already exist, skip it if necessary
        		if(this.dont_duplicate && this.isAlreadyMonitored(url)){
        			$("#urls", this.$el).tagsinput('remove', url);
        			this.unprocessed_queue.push(url);
        			console.info("Skipping creation of an input that already existed for " + url);
        			this.createNextInput();
        		}

				// Don't allow creation of non-HTTPS inputs on Splunk cloud
				else if(this.is_on_cloud && url.startsWith("http://")){
					this.unprocessed_queue.push(url);
        			console.info("Skipping creation of an input that doesn't use HTTPS " + url);
        			this.createNextInput();
				}
        		
        		// Create the input
        		else{
                	// Process the next input
                    $.when(this.createInput(url, this.interval, this.index)).done(function(){
                    	this.createNextInput();
              		}.bind(this));
        		}

        		
        	}
        },
        
        /**
         * Validate the inputs.
         */
        validate: function(){
        	
        	var issues = 0;
        	
        	// Validate the URLs
        	if($("#urls", this.$el).tagsinput('items').length === 0){
        		issues = issues + 1;
        		$(".control-group.urls", this.$el).addClass("error");
        		$(".control-group.urls .help-inline", this.$el).show();
        	}
        	else{
        		$(".control-group.urls", this.$el).removeClass("error");
        		$(".control-group.urls .help-inline", this.$el).hide();
        	}
        	
        	// Validate the interval
        	if(!this.isValidInterval($("#interval", this.$el).val())){
        		issues = issues + 1;
        		$(".control-group.interval", this.$el).addClass("error");
        		$(".control-group.interval .help-inline", this.$el).show();
        	}
        	else{
           		$(".control-group.interval", this.$el).removeClass("error");
        		$(".control-group.interval .help-inline", this.$el).hide();
        	}
        	
        	return issues === 0;
        },
        
        /**
         * Returns true if the item is a valid interval.
         */
        isValidInterval: function(interval){
        	
        	var re = /^\s*([0-9]+([.][0-9]+)?)\s*([dhms])?\s*$/gi;
        	
        	if(re.exec(interval)){
        		return true;
        	}
        	else{
        		return false;
        	}
        },
        
        /**
         * Ensure that the tag is a valid URL.
         */
        validateURL: function(event) {
        	
        	// Add the protocol if it is missing
        	if(event.item.indexOf("http://") !== 0 && event.item.indexOf("https://") !== 0){
        		
        		// Add the protocol since the user just left that part out
				if(this.is_on_cloud){
					$("#urls").tagsinput('add', "https://" + event.item);
				}
        		else{
					$("#urls").tagsinput('add', "http://" + event.item);
				}

        		event.cancel = true;
        		
        	}

			// Don't allow a non-HTTPS site to be entered on Splunk cloud
			else if(event.item.indexOf("http://") === 0 && this.is_on_cloud){
				this.showWarningMessage("Websites must use encryption (HTTPS) to be monitored on Splunk Cloud");
				event.cancel = true;
			}
        },
        
        /**
         * Stop creating the inputs.
         */
        stopCreateInputs: function(){
        	this.stop_processing = true;
        },
        
        /**
         * Create the inputs based on the inputs.
         */
        doCreateInputs: function(){
        	
        	if(this.validate()){
            	
            	this.hideMessages();
            	
            	this.processed_queue = [];
            	this.unprocessed_queue = [];
            	this.processing_queue = $("#urls", this.$el).tagsinput('items');
            	this.interval = $("#interval", this.$el).val();
            	this.dont_duplicate = $(".dont-duplicate", this.$el).is(':checked');
            	//this.index = $("#index", this.$el).val();
            	
            	// Open the progress dialog
            	this.stop_processing = false;
            	$("#progress-modal", this.$el).modal();
            	
            	// Start the process
            	this.createNextInput();
        	}
        	
        },
        
        /**
         * Hide the given item while retaining the display value
         */
        hide: function(selector){
        	selector.css("display", "none");
        	selector.addClass("hide");
        },
        
        /**
         * Un-hide the given item.
         * 
         * Note: this removes all custom styles applied directly to the element.
         */
        unhide: function(selector){
        	selector.removeClass("hide");
        	selector.removeAttr("style");
        },
        
        /**
         * Hide the messages.
         */
        hideMessages: function(){
        	this.hideWarningMessage();
        	this.hideInfoMessage();
        },
        
        /**
         * Hide the warning message.
         */
        hideWarningMessage: function(){
        	this.hide($("#warning-message", this.$el));
        },
        
        /**
         * Hide the informational message
         */
        hideInfoMessage: function(){
        	this.hide($("#info-message", this.$el));
        },
        
        /**
         * Show a warning noting that something bad happened.
         */
        showWarningMessage: function(message){
        	$("#warning-message > .message", this.$el).text(message);
        	this.unhide($("#warning-message", this.$el));
        },
        
        /**
         * Show a warning noting that something bad happened.
         */
        showInfoMessage: function(message){
        	$("#info-message > .message", this.$el).text(message);
        	this.unhide($("#info-message", this.$el));
        },
        
        /**
         * Determine if the user has the given capability.
         */
        hasCapability: function(capability){

        	var uri = Splunk.util.make_url("/splunkd/__raw/services/authentication/current-context?output_mode=json");

        	if( this.capabilities === null ){

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

            return $.inArray(capability, this.capabilities) >= 0;

        },
        
        /**
         * Determine if the given URL is already monitored.
         */
        isAlreadyMonitored: function(url){
        	
        	for(var c = 0; c < this.inputs.length; c++){
        		
        		if(this.inputs[c].content.url === url){
        			return true;
        		}
        		
        	}
        	
        	return false;
        },
        
        /**
         * Get a list of the existing inputs.
         */
        getExistingInputs: function(){

        	var uri = splunkd_utils.fullpath("/servicesNS/nobody/search/data/inputs/web_ping?output_mode=json");

	        // Fire off the request
        	jQuery.ajax({
        		url:     uri,
        		type:    'GET',
        		async:   false,
        		success: function(result) {
        			
        			if(result !== undefined){
        				this.inputs = result.entry;
        			}
        			
        			// Populate a list of the existing input names
        			this.existing_input_names = [];
        			
                	for(var c = 0; c < this.inputs.length; c++){
                		this.existing_input_names.push(this.inputs[c]["name"]);
                	}

        		}.bind(this)
        	});

        },
		
		/**
		 * Get the SHC information.
		 */
		getSHCInfo: function(){
			// Get a promise ready
			var promise = jQuery.Deferred();

			new SHCInfo().fetch({
				url: splunkd_utils.fullpath('/en-US/splunkd/services/shcluster/status'),
				success: function (model, response, options) {
					this.shc_info = model;
					promise.resolve(model);
				},
                error: function(response, textStatus, errorThrown){
					this.shc_info = null;

                    /*
                     * Handle the case where the host isn't SHC.
                     */
        			if((textStatus.status > 400 && textStatus.status < 500) || textStatus.status === 503){ 
						promise.resolve(null);
					}
					else{
						promise.reject();
					}
				}
			});

			return promise;
		},

        /**
         * Render the view.
         */
        render: function () {
        	
			if(this.is_on_cloud === null){
				this.server_info = new ServerInfo();
			}
			
			$.when(
				// Get the SHC info
				this.getSHCInfo(),

				// Get the server-info
				new ServerInfo().fetch()
			)
			.done(function(shc_info, model){
				// Determine if the host is on cloud
				if(model[0].entry[0].content.instance_type){
					this.is_on_cloud = model[0].entry[0].content.instance_type === 'cloud';
				}
				else{
					this.is_on_cloud = false;
				}

				// Below is the list of capabilities required
				var capabilities_required = ['edit_modinput_web_ping', 'list_inputs'];
				
				// Find out which capabilities are missing
				var capabilities_missing = [];
				
				// Check each one
				for(var c = 0; c < capabilities_required.length; c++){
					if(!this.hasCapability(capabilities_required[c])){
						capabilities_missing.push(capabilities_required[c]);
					}
				}

				// Render the view
				this.$el.html(_.template(Template, {
					'has_permission' : capabilities_missing.length === 0,
					'capabilities_missing' : capabilities_missing,
					'is_shc' : shc_info !== null,
					'is_on_cloud' : this.is_on_cloud
				}));
				
				// Render the URL as tags
				$("#urls").tagsinput('items');
				
				$("#urls").on('beforeItemAdd', this.validateURL.bind(this));
			}.bind(this));
        }
    });
    
    return BatchInputCreateView;
});