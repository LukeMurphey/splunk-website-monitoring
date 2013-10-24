require(['jquery','underscore','splunkjs/mvc', '/en-US/static/app/website_monitoring/WebsiteStatusCellRenderer.js', 'splunkjs/mvc/simplexml/ready!'],
	function($, _, mvc, WebsiteStatusCellRenderer){
	
	    var statusTable = mvc.Components.get('element2');
	
	    statusTable.getVisualization(function(tableView){
	        tableView.table.addCellRenderer(new WebsiteStatusCellRenderer());
	        tableView.table.render();
	    });
	    
	}
);