define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "models/SplunkDBase",
    "collections/SplunkDsBase",
    "splunkjs/mvc/simpleform/input/text",
    "splunkjs/mvc/simpleform/input/dropdown",
    "splunkjs/mvc/utils",
    "util/splunkd_utils",
], function(
    _,
    Backbone,
    mvc,
    $,
    SimpleSplunkView,
    SplunkDBaseModel,
    SplunkDsBaseCollection,
    TextInput,
    DropdownInput,
    mvc_utils,
    splunkd_utils
) { 
    
    var Macro = SplunkDBaseModel.extend({
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

    var Macros = SplunkDsBaseCollection.extend({
        url: "/admin/macros?count=-1",
	    initialize: function() {
	    	SplunkDBaseModel.prototype.initialize.apply(this, arguments);
	    }
	});

    return SimpleSplunkView.extend({
        className: "WebsiteFailureEditorView",
        apps: null,
        
        /**
         * Setup the defaults
         */
        defaults: {

        },
        
        /**
         * Initialize the class
         */
        initialize: function() {
        	
            // Apply the defaults
            this.options = _.extend({}, this.defaults, this.options);
            options = this.options || {};

            this.already_rendered = false;

            // Keep the macros references around
            this.response_time_macro = null;
            this.response_code_macro = null;

            // Start getting the macros
            this.loadMacros();
        },

        loadMacros: function(){

            // Get the threshold macro
            if(this.response_time_macro === null){
                $.when(this.getMacro("response_time_threshold")).done(function(model){
                    this.response_time_macro = model;

                    // Set the input if it is initialized
                    if(mvc.Components.getInstance("response-threshold-input") !== null){
                        mvc.Components.getInstance("response-threshold-input").val(this.response_time_macro.entry.content.attributes.definition);
                    }

                }.bind(this));
            }
            else{
                // Set the input if it is initialized
                if(mvc.Components.getInstance("response-threshold-input") !== null){
                    mvc.Components.getInstance("response-threshold-input").val(this.response_time_macro.entry.content.attributes.definition);
                }
            }

            if(this.response_code_macro === null){
                $.when(this.getMacro("response_codes_to_alert_on")).done(function(model){
                    this.response_code_macro = model;

                    // Set the input if it is initialized
                    if(mvc.Components.getInstance("response-code-input") !== null){
                        mvc.Components.getInstance("response-code-input").val(this.response_code_macro.entry.content.attributes.definition);
                    }
                }.bind(this));
            }
            else{
                // Set the input if it is initialized
                if(mvc.Components.getInstance("response-code-input") !== null){
                    mvc.Components.getInstance("response-code-input").val(this.response_code_macro.entry.content.attributes.definition);
                }
            }
        },
        
        /**
         * Setup event handlers
         */
        events: {
            "click #save": "save",
            "click #open-settings-modal": "clickOpenModal"
        },
        
        /**
         * Get the given macro.
         */
        getMacro: function(macro_name){

            // Get a promise ready
            var promise = jQuery.Deferred();

            // Use the current app if the app name is not defined
            if(this.app_name === null || this.app_name === undefined){
                this.app_name = mvc_utils.getCurrentApp();
            }

	        macro = new Macro();
	        	
            macro.fetch({
                url: splunkd_utils.fullpath('/servicesNS/nobody/' + this.app_name + '/admin/macros/' + macro_name),
                success: function (model, response, options) {
                    console.info("Successfully retrieved the macro");

                    // Resolve with the macro we found
                    promise.resolve(model);

                }.bind(this),
                error: function () {

                    // Reject the promise
                    promise.reject();

                    console.warn("Unable to retrieve the macro");
                }.bind(this)
            });

            return promise;
        },

        /**
         * set the macro.
         */
        setMacroDefinition: function(macro_name, definition){

            // Get the macro
            $.when(this.getMacro(macro_name)).then(function(macro_model){

                // Modify the macro
                macro_model.entry.content.set({
                    definition: definition
                }, {
                    silent: true
                });

                return macro_model.save();
            }).done(function(){
                debugger;
            });
        },

        /**
         * Save the macro.
         */
        saveMacroModel: function(macro_model, definition){

            // Modify the model
            macro_model.entry.content.set({
                definition: definition
            }, {
                silent: true
            });

            // Kick off the request to edit the entry
            return macro_model.save();

        },

        /**
         * Get the controls that are necessary for the non-modal form.
         */
        getControls: function(){
        	return '<div class="controls" style="margin-top: 12px"><a href="#" class="btn btn-primary" id="save" style="display: inline;">Save</a></div>';
        },
        
        /**
         * Get the template for a modal
         */
        getModalTemplate: function(title, body){
        	
        	return '<div tabindex="-1" id="threshold-modal" class="modal fade in hide">' +
					    '<div class="modal-header">' +
					        '<button type="button" class="close btn-dialog-close" data-dismiss="modal">x</button>' +
					        '<h3 class="text-dialog-title">' + title + '</h3>' +
					    '</div>' +
					    '<div class="modal-body form form-horizontal modal-body-scrolling">' +
					    	body +
					    '</div>' +
					    '<div class="modal-footer">' +
					        '<a href="#" class="btn btn-dialog-cancel" data-dismiss="modal" style="display: inline;">Close</a>' +
					        '<a href="#" class="btn btn-primary" id="save" style="display: inline;">Save</a>' +
					   ' </div>' +
					'</div>'
        },
        
        /**
         * Make a template snippet for holding an input.
         */
        makeInputTemplate: function(label, id, helpblock){
        	
        	return '<div id="' + id + '-control-group" class="control-group">' +
                	'	<label class="control-label">' + label + '</label>' +
                	'		<div class="controls">' + 
    	            '			<div style="display: inline-block;" class="input" id="' + id + '" />' +
    	            '			<span class="hide help-inline"></span>' + 
    	            '			<span class="help-block"> ' + helpblock + '</span>' +
    	            '		</div>' +
    	            '</div>';
        	
        },
        
        /**
         * Get the input template.
         */
        getInputTemplate: function(){
        	
        	return  '<div id="message_dialog"></div>' + 
        			'<span id="settings_form">' + 
                    '<div>You define what you want to consider an outage below.' +
                    'These settings will also apply to the ' +
                    '<a href="alert?s=%2FservicesNS%2Fnobody%2Fwebsite_monitoring%2Fsaved%2Fsearches%2FWebsite%2520Performance%2520Problem">alert search</a> that provides notifications of outages.' +
                    '</div>' +
        			'<div style="margin-bottom: 32px">.</div>' +
        			'<div class="input" id="response-threshold-input">' +
                		'<label>Response Time Threshold (in milliseconds)</label>' +
                    '</div>' +
        			'<div style="margin-top: 32px" class="input" id="response-code-input">' +
                		'<label>Response Codes Considered Failures</label>' +
                	'</div>' + 
                	'</span>';
        
        },

        /**
         * Validate the inputs.
         */
        validate: function(){
        	
        	var issues = 0;

        	// Validate the threshold
        	if( !/([0-9])+$/gi.test( mvc.Components.getInstance("response-threshold-input").val())){
        		return "The threshold is not valid (must be a integer greater than zero)";
        	}
        	
        	return issues === 0;
        },
        

        /**
         * Render the view
         */
        render: function() {
            
        	// Stop if the view was already rendered
        	if(!this.already_rendered){
	        	
	        	var html = '<a id="open-settings-modal" href="#">Edit failure definition</a>';
	        	
	        	// Render the modal version of the form
	        	html = html + this.getModalTemplate("Failure Definition", this.getInputTemplate());
	        	
	        	// Set the HTML
	        	this.$el.html(html);
	        	
	        	// Make the threshold widget
	        	var response_threshold_input = new TextInput({
	                "id": "response-threshold-input",
	                "searchWhenChanged": false,
	                "el": $('#response-threshold-input', this.$el)
	            }, {tokens: false}).render();

	        	response_threshold_input.on("change", function(newValue) {
	            	this.validate();
	            }.bind(this));
                
                // Make the response code widget
	        	var response_code_input = new DropdownInput({
	                "id": "response-code-input",
	                "searchWhenChanged": false,
	                "el": $('#response-code-input', this.$el),
                    "choices": [
                        {
                            'label': '400 and 500 response codes',
                            'value': 'response_code>=400'
        		        },
                        {
                            'label': '500 response codes',
                            'value': 'response_code>=500'
        		        },
                        {
                            'label': '400 and 500 response codes, but not 404',
                            'value': '(response_code>=400 AND response_code!=404)'
        		        },
                        {
                            'label': '300, 400 and 500 response codes',
                            'value': 'response_code>=300'
        		        }
                    ]
	            }, {tokens: false}).render();

                // This prevents a JS error in Core Splunk
                response_code_input.onInputReady = function(){}
                response_threshold_input.onInputReady = function(){}
	            
                // Note that we rendered the page
	        	this.already_rendered = true;

                this.loadMacros();
        	}
        	
            return this;
        },
        
        /**
         * Handle the click to open the modal.
         */
        clickOpenModal: function(){
            this.showModal(1000, 12);
        },

        /**
         * Show the form as a dialog
         */
        showModal: function(response_threshold, response_codes){
        	this.response_threshold = response_threshold;
        	this.response_codes = response_codes;
        	
        	this.show_modal = true;
        	
        	this.render();
        	$("#threshold-modal", this.$el).modal();
        },
        
        /**
         * Change the UI to show that the dialog is saving.
         */
        showSaving: function(isSaving){
        	
        	if(typeof isSaving === 'undefined'){
        		isSaving = true;
        	}
        	
        	if( isSaving ){
        		$('#save', this.$el).prop('disabled', false);
            	$('#save', this.$e).addClass('disabled');
        	}
        	else{
        		$('#save', this.$el).prop('disabled', true);
            	$('#save', this.$e).removeClass('disabled');
        	}
        },
        
        /**
         * Change the UI to show that the dialog is loading.
         */
        showLoading: function(isLoading){
        	
        	if( typeof isLoading === 'undefined'){
        		isLoading = true;
        	}
        	
        	$('#save', this.$el).prop('disabled', isLoading);
        	
        	if( isLoading ){
        		$('#save', this.$e).addClass('disabled');
        	}
        	else{
        		$('#save', this.$e).removeClass('disabled');
        	}
        },
        
        /**
         * Save the annotation
         */
        save: function() {
        	
        	this.showSaving();

            $.when(this.saveMacroModel(this.response_time_macro, mvc.Components.getInstance("response-threshold-input").val()))
            .then(this.saveMacroModel(this.response_code_macro, mvc.Components.getInstance("response-code-input").val()))
            .done(function(){
                this.showSaving(false);
            }.bind(this));

        },
        

    });
});