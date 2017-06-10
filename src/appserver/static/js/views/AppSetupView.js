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

        getProxyUser: function(){
            return $('.proxy-user input', this.$el).val();
        },

        getServerPort: function(){
            return $('.proxy-port input', this.$el).val();
        },

        isInteger: function(value){
            if(isNaN(parseInt(value, 10))){
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
            this.addValidator('.proxy-port', this.getServerPort.bind(this), this.isInteger, "Port must be a valid integer");
        },
    });
});