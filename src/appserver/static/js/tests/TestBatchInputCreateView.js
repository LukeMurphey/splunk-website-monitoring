
require.config({
    paths: {
        batch_input_create_view: "../app/website_monitoring/js/views/BatchInputCreateView",
        jasmine: '//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine'
    }
});

require([
        "jquery",
        "underscore",
        "backbone",
        "batch_input_create_view",
        "splunkjs/mvc/searchmanager",
        "splunkjs/mvc/utils",
        "jasmine",
        "splunkjs/mvc/simplexml/ready!"
    ], function(
        $,
        _,
        Backbone,
        BatchInputCreateView,
        SearchManager,
        utils
    )
    {
    
	    /**
	     * The tests
	     */
	    describe("BatchInputCreateView: ", function() {
	        
	        it("creation of a title from URL", function() {
	        	var view = new BatchInputCreateView();
	            expect(view.generateTitle("http://textcritical.net")).toBe("textcritical.net");
	        });
	        
	        it("creation of a stanza from URL", function() {
	        	var view = new BatchInputCreateView();
	            expect(view.generateStanza("http://textcritical.net")).toBe("textcritical_net");
	        });
	        
	        it("parsing of URL", function() {
	        	var view = new BatchInputCreateView();
	        	var parsed = view.parseURL("http://textcritical.net");
	            expect(parsed.hostname).toBe("textcritical.net");
	        });
	    });

	}
);