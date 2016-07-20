
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
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    'text!../app/website_monitoring/js/templates/BatchInputCreateView.html',
    "bootstrap-tags-input",
    "css!../app/website_monitoring/css/BatchInputCreateView.css",
    "css!../app/website_monitoring/js/lib/bootstrap-tagsinput.css"
], function(
    _,
    Backbone,
    mvc,
    splunkd_utils,
    $,
    SimpleSplunkView,
    Template
){
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
        		name = this.generateStanza(url);
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
        			url: splunkd_utils.fullpath("/servicesNS/admin/search/data/inputs/web_ping"),
        			data: data,
        			type: 'POST',
        			
        			// On success
        			success: function(data) {
        				console.info('Input created');
        				
        				// Remember that we processed this one
        				this.processed_queue.push(url);
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
        		
        		// Show a message noting that we are done
        		this.showInfoMessage("Done creating the inputs (" + this.processed_queue.length + " created)");
        		
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
        		
            	// Get a list of users to show from which to load the context
                $.when(this.createInput(url, this.interval, this.index)).done(function(){
                	this.createNextInput();
          		}.bind(this));
        		
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
         * Returns true if the item is a valid URL.
         */
        isValidURL: function(url){
        	var regex = new RegExp("^(http[s]?:\\/\\/(www\\.)?|ftp:\\/\\/(www\\.)?|www\\.){1}([0-9A-Za-z-\\.@:%_\+~#=]+)+((\\.[a-zA-Z]{2,3})+)(/(.)*)?(\\?(.)*)?");
        	
        	return regex.test(url);
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
        	if(!this.isValidURL(event.item)){
        		
        		// Try adding the protocol to see if the user just left that part out.
        		if(this.isValidURL("http://" + event.item)){
        			$("#urls").tagsinput('add', "http://" + event.item);
        		}
        		
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
            	this.processing_queue = $("#urls", this.$el).tagsinput('items');
            	this.interval = $("#interval", this.$el).val();
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
         * Render the view.
         */
        render: function () {
        	
        	this.$el.html(_.template(Template, {
        		//'some_option' : some_option
        	}));
        	
        	// Render the URL as tags
        	$("#urls").tagsinput('items');
        	
        	$("#urls").on('beforeItemAdd', this.validateURL.bind(this));
        }
    });
    
    return BatchInputCreateView;
});