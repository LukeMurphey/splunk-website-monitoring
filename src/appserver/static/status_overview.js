require.config({
    paths: {
    	website_status_cell_renderer: '../app/website_monitoring/WebsiteStatusCellRenderer',
    	info_message_view: '../app/website_monitoring/js/views/InfoMessageView'
    }
});

require(['jquery','underscore','splunkjs/mvc', 'website_status_cell_renderer', 'info_message_view', 'splunkjs/mvc/searchmanager', 'splunkjs/mvc/simplexml/ready!'],
	function($, _, mvc, WebsiteStatusCellRenderer, InfoMessageView, SearchManager){
	
		// Setup the cell renderer
	    var statusTable = mvc.Components.get('element1');
	
	    statusTable.getVisualization(function(tableView){
	        tableView.table.addCellRenderer(new WebsiteStatusCellRenderer());
	        tableView.table.render();
	    });
	    

	    // Make the search that will determine if website monitoring inputs exist
	    var hasInputSearch = new SearchManager({
	        "id": "webping-inputs-search",
	        "earliest_time": "-48h@h",
	        "latest_time": "now",
	        "search":'| rest /services/data/inputs/web_ping | append [search sourcetype="web_ping" | head 1] | stats count',
	        "cancelOnUnload": true,
	        "autostart": false,
	        "app": '',
	        "auto_cancel": 90,
	        "preview": false
	    }, {tokens: false});
	
	    var infoMessageView = new InfoMessageView({
	    	search_manager: hasInputSearch,
	    	message: 'Create an input to monitor a website. <a target="_blank" href="../../manager/website_monitoring/adddata/selectsource?input_type=web_ping&modinput=1&input_mode=1">Create a website monitoring input now.</a>',
	    	eval_function: function(searchResults){ return searchResults.rows[0][0] === "0" }
	    });
	    
	}
);