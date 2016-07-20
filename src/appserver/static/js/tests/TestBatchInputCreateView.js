
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
	        
	        it("creation of a stanza from URL with list of existing stanzas", function() {
	        	var view = new BatchInputCreateView();
	            
	            expect(view.generateStanza("http://textcritical.net", ["textcritical_net", "textcritical_net_1"])).toBe("textcritical_net_2");
	        });
	        
	        it("parsing of URL", function() {
	        	var view = new BatchInputCreateView();
	        	var parsed = view.parseURL("http://textcritical.net");
	            expect(parsed.hostname).toBe("textcritical.net");
	        });
	        
	        it("validation of valid URL", function() {
	        	var view = new BatchInputCreateView();
	            
	            expect(view.isValidURL("http://textcritical.net")).toBe(true);
	        });
	        
	        it("validation of valid URL (with https)", function() {
	        	var view = new BatchInputCreateView();
	            
	            expect(view.isValidURL("https://textcritical.net")).toBe(true);
	        });
	        
	        it("validation of url missing protocol", function() {
	        	var view = new BatchInputCreateView();
	        	
	            expect(view.isValidURL("textcritical.net")).toBe(false);
	        });
	        
	        it("validation of url with implied protocol", function() {
	        	var view = new BatchInputCreateView();
	        	
	            expect(view.isValidURL("//textcritical.net")).toBe(false);
	        });
	        
	        it("validation of interval", function() {
	        	var view = new BatchInputCreateView();
	            
	            expect(view.isValidInterval("2h")).toBe(true);
	        });
	        
	    });

	}
);