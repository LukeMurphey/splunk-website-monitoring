/*
 * This view is intended to be used as a base class for form views that need to perform input validation. To use this you must:
 * 
 *  1) Make your HTML such that the inputs have a control-group with a unique class name
 *  2) Register validators for each of the fields that must be validated by calling addValidator()
 * 
 * 
 *
  		  <div class="control-group input-host-mac">
		    <label class="control-label required-input" for="inputMAC">MAC Address</label>
		    <div class="controls">
		      <input type="text" id="inputMAC" placeholder="e.g. 00:11:22:33:44:55 or 00-11-22-33-44-55">
		      <span class="help-inline"></span>
		    </div>
		  </div>
 */

define([
    "underscore",
    "backbone",
    "splunkjs/mvc",
    "jquery",
    "splunkjs/mvc/simplesplunkview",
    "util/splunkd_utils",
    "splunkjs/mvc/utils"
], function(
    _,
    Backbone,
    mvc,
    $,
    SimpleSplunkView,
    splunkd_utils,
    mvc_utils
){

    return SimpleSplunkView.extend({
        className: "ValidationView",
        
        defaults: {
            validators: []
        },

        initialize: function() {

            // Merge the provided options and the defaults
        	this.options = _.extend({}, this.defaults, this.options);
        },

        /**
         * Register a function for performing form validation.
         */
        addValidator: function(selector, value_extractor_fx, validation_fx, message){

            if(this.validators == undefined){
                this.validators = [];
            }

            this.validators.push({
                selector: selector,
                value_extractor_fx: value_extractor_fx,
                validation_fx: validation_fx,
                message: message
            })
        },

        /**
         * Perform validation and show/hide error messages accordingly.
         */
        doValidation: function(selector, value, validation_fx, message){
        	if(!validation_fx(value)){
  		  		$(selector, this.$el).addClass('error');
  		  		$(selector + ' .help-inline', this.$el).text(message);
  		  		return 1;
  		  	}
  		  	else{
  		  		this.clearValidationState(selector);
  		  		return 0;
  		  	}
        },
        
		/**
		 * Clear the validation state for the given input.
		 */
		clearValidationState: function(selector){
  		  	$(selector, this.$el).removeClass('error');
  		  	$(selector + ' .help-inline', this.$el).text('');
		},

		/**
		 * Clear the validation state for all of the forms.
		 */
		clearAllValidators: function(){
            for (var key in this.validators) {
                this.clearValidationState(key);
            }
		},

        /**
         * Determine if the form is valid.
         */
        validate: function(){
        	
        	var issues = 0;
  		  	
  		  	// Test 'em
            for (var c = 0; c < this.validators.length; c++) {
                var validator = this.validators[c];
                issues += this.doValidation(validator.selector, validator.value_extractor_fx(), validator.validation_fx, validator.message);
            }
        	
  		  	// Return the validation status
  		  	if(issues > 0){
  		  		return false;
  		  	}
  		  	else{
  		  		return true;
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
            this.renderMessageDivs();
        	$("#warning-message .message", this.$el).text(message);
        	this.unhide($("#warning-message", this.$el));
        },
        
        /**
         * Show a warning noting that something bad happened.
         */
        showInfoMessage: function(message){
            this.renderMessageDivs();
        	$("#info-message .message", this.$el).text(message);
        	this.unhide($("#info-message", this.$el));
        },

        /**
         * Render the HTML necessary for the information and warning messages to appear.
         * 
         * This will add HTML necessary to render error and information messages to the DOM. You can manually place
         * the HTML anywhere you want by copying the following in your template:
         * 
            <div style="display:none" id="warning-message">
                <div class="alert alert-error">
                    <i class="icon-alert"></i>
                    <span class="message"></span>
                </div>
            </div>
            <div style="display:none" id="info-message">
                <div class="alert alert-info">
                    <i class="icon-alert"></i>
                    <span class="message"></span>
                </div>
            </div>
         */
        renderMessageDivs: function(){
            var html = '<div style="display:none" id="warning-message">' + 
                            '<div class="alert alert-error">' +
                                '<i class="icon-alert"></i>' +
                                '<span class="message"></span>' +
                            '</div>' +
                        '</div>' + 
                        '<div style="display:none" id="info-message">' + 
                            '<div class="alert alert-info">' +
                                '<i class="icon-alert"></i>' +
                                '<span class="message"></span>' +
                            '</div>' +
                        '</div>';

            // Prepend the content if necessary
            if($('#warning_message_dialog', this.$el).length === 0){
                $(this.$el).prepend(html);
            }
                
            
        },
    });
});