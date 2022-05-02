define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
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
    TextInput,
    DropdownInput,
    mvc_utils,
    splunkd_utils
) {

    return SimpleSplunkView.extend({
        className: "WebsiteFailureEditorView",
        apps: null,
        RESPONSE_TIME_THRESHOLD: "response_time_threshold",
        RESPONSE_TIME_THRESHOLD_WARNING: "response_time_threshold_warning",
        RESPONSE_RESPONSE_CODES_TO_ALERT_ON: "response_codes_to_alert_on",
        
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
        },

        /**
         * Load the macros into the form
         */
        loadMacrosIntoForm: function(){

            // Get the 'error' threshold macro
            if(mvc.Components.getInstance("response-threshold-input") !== null){
                mvc.Components.getInstance("response-threshold-input").val(this.response_time_macro.content.definition);
            }

            /*
            // Get the 'warning' threshold macro
            if(mvc.Components.getInstance("response-threshold-input-warning") !== null){
                mvc.Components.getInstance("response-threshold-input-warning").val(this.response_time_warning_macro.content.definition);
            }
            */

            // Get the response code macro
            if(mvc.Components.getInstance("response-code-input") !== null){
                mvc.Components.getInstance("response-code-input").val(this.response_code_macro.content.definition);
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
            var promise = jQuery.Deferred(); // Remove??

            // Use the current app if the app name is not defined
            if(this.app_name === null || this.app_name === undefined){
                this.app_name = mvc_utils.getCurrentApp();
            }

            fetch(splunkd_utils.fullpath('/servicesNS/nobody/' + this.app_name + '/data/macros/' + macro_name + '?output_mode=json'))
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    promise.resolve(data.entry[0]);
                });
        

            return promise;
        },

        /**
         * set the macro.
         */
        setMacroDefinition: function(macro_name, definition){

            // https://community.splunk.com/t5/Getting-Data-In/get-session-key-for-included-javascript-app-with-logged-in-user/m-p/328448
            // https://community.splunk.com/t5/Monitoring-Splunk/POST-to-splunkd-raw-endpoint-returns-CSRF-validation-failed/m-p/418415
            var sessionKey = document.cookie.match(/splunkweb_csrf_token_8000=(\d+)/)[1];

            var searchParams = new URLSearchParams();
            searchParams.append("definition", definition);

            // Modify the macro
            fetch(
                splunkd_utils.fullpath('/servicesNS/nobody/' + this.app_name + '/data/macros/' + macro_name + '?output_mode=json'),
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Splunk-Form-Key': sessionKey,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: searchParams.toString()
                }
                )
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    promise.resolve(data.entry[0]);
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
        	
        	return  '<div style="display:none" id="warning_message_dialog">' + 
                        '<div class="alert alert-error">' +
	                        '<i class="icon-alert"></i>' +
	                        '<span id="warning_message"></span>' +
	                    '</div>' +
                    '</div>' + 
                    '<div style="display:none" id="success_message_dialog">' + 
                        '<div class="alert alert-info">' +
	                        '<i class="icon-alert"></i>' +
	                        '<span id="success_message"></span>' +
	                    '</div>' +
                    '</div>' + 
        			'<span id="settings_form">' + 
                    '<div>You define what you want to consider an outage below. ' +
                    'These settings will also apply to the ' +
                    '<a class="external" target="external" href="alert?s=%2FservicesNS%2Fnobody%2Fwebsite_monitoring%2Fsaved%2Fsearches%2FWebsite%2520Performance%2520Problem">alert search</a> that provides notifications of outages.' +
                    '</div>' +
        			'<div style="margin-bottom: 16px"></div>' +
        			'<div class="input" id="response-threshold-input">' +
                		'<label>Error Response Time Threshold (in milliseconds)</label>' +
                    '</div>' +
        			'<div style="margin-top: 24px" class="input" id="response-code-input">' +
                		'<label>Response Codes Considered Failures</label>' +
                	'</div>' + 
                	'</span>';
        
        },

        /**
         * Show a success message.
         */
        showSuccessMessage: function(message){
            this.hideMessage();
        	$('#success_message_dialog', this.$el).show();
        	$('#success_message', this.$el).text(message);
        },

        /**
         * Show a failure message.
         */
        showFailureMessage: function(message){
            this.hideMessage();
        	$('#warning_message_dialog', this.$el).show();
        	$('#warning_message', this.$el).text(message);
        },
        
        /**
         * Hide the message.
         */
        hideMessage: function(){
        	$('#success_message_dialog', this.$el).hide();
            $('#warning_message_dialog', this.$el).hide();
        },

        /**
         * Validate the inputs.
         */
        validate: function(){
        	
        	var message = this.getValidationMessage();

            if(message === true){
                // Everything looks good.
                this.hideMessage();
            }
            else{
                this.showFailureMessage(message);
            }
        },

        /**
         * Validate the inputs and retrieve a string describing the problems if any exist. 
         */
        getValidationMessage: function(){
        	
        	var issues = 0;

        	// Validate the 'error' threshold
        	if( !/([0-9])+$/gi.test( mvc.Components.getInstance("response-threshold-input").val())){
        		return "The threshold is not valid (must be a integer greater than zero)";
        	}
            
            /*
        	// Validate the 'warning' threshold
        	if( !/([0-9])+$/gi.test( mvc.Components.getInstance("response-threshold-input-warning").val())){
        		return "The threshold is not valid (must be a integer greater than zero)";
            }
            */
        	
        	return issues === 0;
        },

        /**
         * Start the process
         */
        startRendering: function(){

            var deferreds = [this.getMacro(this.RESPONSE_TIME_THRESHOLD), this.getMacro(this.RESPONSE_TIME_THRESHOLD_WARNING), this.getMacro(this.RESPONSE_RESPONSE_CODES_TO_ALERT_ON)];

            $.when.apply($, deferreds).done(function(response_time_macro, response_time_warning_macro, response_code_macro) {
                this.response_code_macro = response_code_macro;
                this.response_time_macro = response_time_macro;
				this.response_time_warning_macro = response_time_warning_macro;

                this.completeRender();
            }.bind(this));
        },

        render: function() {

            // Start the process of rendering
            this.startRendering();
        },

        /**
         * Render the view
         */
        completeRender: function() {
            
        	// Stop if the view was already rendered
        	if(!this.already_rendered){
	        	
                if(this.response_time_macro.acl.can_write && this.response_time_warning_macro.acl.can_write && this.response_code_macro.acl.can_write){

                    var html = '<a id="open-settings-modal" href="#">Modify the definition of a failure</a>';
                    
                    // Render the modal version of the form
                    html = html + this.getModalTemplate("Failure Definition", this.getInputTemplate());
                    
                    // Set the HTML
                    this.$el.html(html);
                    
                    // Make the 'error' threshold widget
                    var response_threshold_input = new TextInput({
                        "id": "response-threshold-input",
                        "searchWhenChanged": false,
                        "el": $('#response-threshold-input', this.$el)
                    }, {tokens: false}).render();

                    response_threshold_input.on("change", function(newValue) {
                        this.validate();
                    }.bind(this));
                    
                    /*
                    // Make the 'warning' threshold widget
                    var response_threshold_input_warning = new TextInput({
                        "id": "response-threshold-input-warning",
                        "searchWhenChanged": false,
                        "el": $('#response-threshold-input-warning', this.$el)
                    }, {tokens: false}).render();

                    response_threshold_input_warning.on("change", function(newValue) {
                        this.validate();
                    }.bind(this));
                    */
                    
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
                    // response_threshold_input_warning.onInputReady = function(){}

                    // Load the macro values into the widgets
                    this.loadMacrosIntoForm();
                }

                // User doesn't have the ability to write to the macros
                else{
                    // Set the HTML
                    this.$el.html("");
                }
	            
                // Note that we rendered the page
	        	this.already_rendered = true;

        	}
        	
            return this;
        },
        
        /**
         * Handle the click to open the modal.
         */
        clickOpenModal: function(){
            this.showModal();
        },

        /**
         * Show the form as a dialog
         */
        showModal: function(){
        	this.render();
            this.hideMessage();
        	$("#threshold-modal", this.$el).modal();
        },
        
        /**
         * Change the UI to show that the dialog is saving.
         */
        showSaving: function(isSaving){
        	
        	if(typeof isSaving === 'undefined'){
        		isSaving = true;
        	}
        	
        	if(isSaving){
        		$('#save', this.$el).prop('disabled', false);
            	$('#save', this.$e).addClass('disabled');
        	}
        	else{
        		$('#save', this.$el).removeProp('disabled');
            	$('#save', this.$e).removeClass('disabled');
        	}
        },
        
        /**
         * Save the annotation
         */
        save: function() {
        	
        	this.showSaving();

            // .then(this.saveMacroModel(this.RESPONSE_TIME_THRESHOLD_WARNING, mvc.Components.getInstance("response-threshold-input-warning").val()))
            $.when(this.setMacroDefinition(this.RESPONSE_TIME_THRESHOLD, mvc.Components.getInstance("response-threshold-input").val()))
            .then(this.setMacroDefinition(this.RESPONSE_RESPONSE_CODES_TO_ALERT_ON, mvc.Components.getInstance("response-code-input").val()))
            .done(function(){
                this.showSaving(false);
                $("#threshold-modal", this.$el).modal('hide');
            }.bind(this))
            .fail(function(){
                this.showSaving(false);
                this.showFailureMessage("Configuration could not be changed");
            }.bind(this));

        },
        

    });
});