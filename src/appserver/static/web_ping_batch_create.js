
//Translations for en_US
i18n_register({"plural": function(n) { return n == 1 ? 0 : 1; }, "catalog": {}});

require.config({
    paths: {
        batch_create_view: '../app/website_monitoring/js/views/BatchInputCreateView'
    }
});

require(['jquery','underscore','splunkjs/mvc', 'batch_create_view', 'splunkjs/mvc/simplexml/ready!'],
		function($, _, mvc, BatchInputCreateView){
	
    // Render the slideshow setup page
    var batchInputCreateView = new BatchInputCreateView({
        el: $('#batch-create-inputs')
    });
    
    // Render the page
    batchInputCreateView.render();
	
});