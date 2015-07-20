define([
        "underscore",
        "backbone",
        "splunkjs/mvc",
        "jquery",
        "splunkjs/mvc/simplesplunkview",
        "splunkjs/mvc/searchmanager",
        "splunkjs/mvc/utils"
        ], function(
        		_,
        		Backbone,
        		mvc,
        		$,
        		SimpleSplunkView,
        		SearchManager,
        		utils
        ) { 
	// Define the custom view class
	var InfoMessageView = SimpleSplunkView.extend({
		className: "AnnotateEventView",
		apps: null,

		/**
		 * Setup the defaults
		 */
		defaults: {
			message_el: "#dashboard > .fieldset",
			search_manager: null,
			message: null,
			eval_function: null,
			show_if_results: false,
			show_if_no_results: true
		},

		/**
		 * Initialize the class
		 */
		 initialize: function() {

			 // Apply the defaults
			 this.options = _.extend({}, this.defaults, this.options);

			 options = this.options || {};
			 
			 this.message_el = $(options.message_el);
			 this.search_manager = options.search_manager;
			 this.message = options.message;
			 this.show_if_no_results = options.show_if_no_results;
			 this.show_if_results = options.show_if_results;
			 this.eval_function = options.eval_function;
			 
			 this.setupSearch();
		 },
		 
		 /**
		  * Show a message
		  */
		 showMessage: function(message){
			 
			 var content = '<div style="' +
			    'margin-top: 0px;' +
		    	'margin-bottom: -10px;">' +
		 		'	<div class="alert alert-warning">' +
		        '    	<i class="icon-alert"></i>' +
		                     message +
		        '   </div>' +
		        '</div>';
			 
			 this.message_el.append(content);
			 
		 },

	        /**
	         * Start the process of running the search for.
	         */
	        setupSearch: function(){
	        	
	        	if( !this.search_manager || !this.message ){
	        		return;
	        	}
	            
	            this.search_manager.on("search:done", function() {
	                console.log("Info message search completed");
	            }.bind(this));
	            
	            // Process the results
	            var searchResults = this.search_manager.data("results");
	            
	            searchResults.on("data", function() {
	            	
	            	var rows_count = searchResults.data().rows.length;
	            	
	            	if(this.eval_function && this.eval_function(searchResults.data())){
	            		this.showMessage(this.message);
	            	}
	            	else if( this.show_if_results && rows_count > 0){
	            		this.showMessage(this.message);
	            	}
	            	
	            }.bind(this));
	            
	            this.search_manager.startSearch();
	        }


	});

	return InfoMessageView;
});
