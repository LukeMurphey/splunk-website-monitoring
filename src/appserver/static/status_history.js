require.config({
    paths: {
    	website_status_cell_renderer: '../app/website_monitoring/WebsiteStatusCellRenderer'
    }
});


require(['jquery','underscore','splunkjs/mvc', 'website_status_cell_renderer', 'splunkjs/mvc/simplexml/ready!'],
	function($, _, mvc, WebsiteStatusCellRenderer){
		
	   var statusTable = mvc.Components.get('element6');

	   statusTable.getVisualization(function(tableView){
	        tableView.table.addCellRenderer(new WebsiteStatusCellRenderer());
	        tableView.table.render();
	   });
		
	}
);