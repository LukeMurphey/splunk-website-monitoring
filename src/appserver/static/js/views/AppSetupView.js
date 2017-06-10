require.config({
    paths: {
        text: "../app/website_monitoring/js/lib/text",
        setup_view: '../app/website_monitoring/js/views/SetupView'
    }
});

define([
    "underscore",
    "jquery",
    "setup_view",
    "text!../app/website_monitoring/js/templates/AppSetupView.html",
], function(
    _,
    $,
    SetupView,
    Template
){

    return SetupView.extend({
        className: "AppSetupView",

        events: {
            "click #save-config" : "saveConfig"
        },

        initialize: function() {
        	this.options = _.extend({}, this.defaults, this.options);
            SetupView.prototype.initialize.apply(this, [this.options]);

            this.setupValidators();
        },

        saveConfig: function(){
            if(!this.userHasAdminAllObjects()){
                alert("You don't have permission to edit this app");
            }
            else if(this.validate()){
                this.setConfigured();
            }
        },
        
        render: function () {
            if(this.userHasAdminAllObjects()){

                // Render the view
                this.$el.html(_.template(Template, {
                    'has_permission' : this.userHasAdminAllObjects()
                }));

                //this.$el.html('This is my custom setup page <br /><br /><a href="#" class="btn btn-primary" id="save-config">Save Configuration</a>');
            }
            else{
                this.$el.html("Sorry, you don't have permission to perform setup");
            }
        },

        /**
         * Below is a list of accessors for the form fields.
         */
        getProxyUser: function(){
            return $('.proxy-user input', this.$el).val();
        },

        getServerPort: function(){
            return $('.proxy-port input', this.$el).val();
        },

        getThreadLimit: function(){
            return $('.thread-limit input', this.$el).val();
        },

        getProxyPassword: function(){
            return $('.proxy-password input', this.$el).val();
        },

        getProxyPasswordConfirmation: function(){
            return $('.proxy-password-confirm input', this.$el).val();
        },

        /**
         * Below is a list of validators for the form fields.
         */
        isValidPort: function(value){
            var port = parseInt(value, 10); 

            if(isNaN(port)){
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

        matchesPassword: function(value){
            var originalPassword = this.getProxyPassword();

            if(originalPassword !== value){
                return false;
            }
            else{
                return true;
            }
        },

        /**
         * Setup the validators so that we can detect bad input
         */
        setupValidators: function(){
            this.addValidator('.proxy-port', this.getServerPort.bind(this), this.isValidPort, "Must be a valid port number");
            this.addValidator('.thread-limit', this.getThreadLimit.bind(this), this.isValidThreadLimit, "Must be an integer greater than 0");
            this.addValidator('.proxy-password-confirm', this.getProxyPasswordConfirmation.bind(this), this.matchesPassword.bind(this), "Must match the password");
        },
    });
});