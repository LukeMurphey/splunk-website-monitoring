require.config({
    paths: {
        custom_setup: "../app/website_monitoring/js/views/AppSetupView"
    }
});

require([
         "jquery",
         "custom_setup",
         "splunkjs/mvc/simplexml/ready!"
     ], function(
         $,
         AppSetupView
     )
     {
         
         var appSetupView = new AppSetupView({
        	 el: $('#setupView')
         });
         
         appSetupView.render();
     }
);