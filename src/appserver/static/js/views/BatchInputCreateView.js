
require.config({
    paths: {
        text: "../app/website_monitoring/js/lib/text"
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
    "css!../app/website_monitoring/css/BatchInputCreateView.css"
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
        	"click .create-inputs" : "doCreateInputs"
        },
        
        initialize: function() {
        	this.options = _.extend({}, this.defaults, this.options);
        	
        	//this.some_option = this.options.some_option;
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
        generateStanza: function(url){
        	var parsed = this.parseURL(url);
        	return parsed.hostname.replace(/[-.]/g, "_");
        },
        
        /**
         * Create an input
         */
        createInput: function(){

        	// Make the data that will be posted to the server
        	var data = {
        		"url": "http://test.lukemurphey.net",
        		"interval": "2h",
        		"name": "test_js",
        		"title": "Test from JS!",
        	};
        	
        	// Perform the call
        	$.ajax({
        			//url: splunkd_utils.fullpath("data/inputs/web_ping/_new"),
        			url: splunkd_utils.fullpath("/servicesNS/admin/search/data/inputs/web_ping"),
        			data: data,
        			type: 'POST',
        			
        			// On success, populate the table
        			success: function(data) {
        				console.info('Input created');
        			  
        			}.bind(this),
        		  
        			// Handle cases where the input already existing could not be found or the user did not have permissions
        			complete: function(jqXHR, textStatus){
        				if( jqXHR.status == 403){
        					console.info('Inadequate permissions');
        					this.showWarningMessage("You do not have permission to make inputs");
        				}
        				else if( jqXHR.status == 409){
        					console.info('Input already exists, skipping this one');
        				}
        			  
        			}.bind(this),
        		  
        			// Handle errors
        			error: function(jqXHR, textStatus, errorThrown){
        				if( jqXHR.status != 403 && jqXHR.status != 409 ){
        					console.info('Input creation failed');
        					this.showWarningMessage("The input could not be created");
        				}
        			}.bind(this)
        	});
        },
        
        /**
         * Create the inputs based on the inputs.
         */
        doCreateInputs: function(){
        	this.createInput();
        },
        
        /**
         * Display a warning message
         */
        showWarningMessage: function(message){
        	
        },
        
        render: function () {
        	
        	this.$el.html(_.template(Template, {
        		//'some_option' : some_option
        	}));
        	
        }
    });
    
    return BatchInputCreateView;
});