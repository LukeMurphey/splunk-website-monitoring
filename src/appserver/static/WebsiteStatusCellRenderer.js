define(['jquery', 'underscore', 'splunkjs/mvc', 'views/shared/results_table/renderers/BaseCellRenderer'], function($, _, mvc, BaseCellRenderer) {
    
    var WebsiteStatusCellRenderer = BaseCellRenderer.extend({
    	 canRender: function(cell) {
    		 return ($.inArray(cell.field, ["title", "response_code", "response_time", "average"]) >= 0); // Add "url" to this list to render the favicon
		 },
		 
		 render: function($td, cell) {
			 
			 // Add the class so that the CSS can style the content
			 $td.addClass(cell.field);
			 
			 var icon = "";
			 
			 // Handle the response_code
			 if( cell.field == "response_code" ){
				 
				 var int_value = parseInt(cell.value, 10);
				 
				 if( int_value >= 400 ){
					 $td.addClass("failure");
					 icon = 'alert';
				 }
				 else if( int_value >= 100 ){
					 $td.addClass("success");
					 icon = 'check';
				 }
				 else{
					 $td.addClass("failure");
					 icon = 'alert';
				 }
				
			 }
			 
			 // Handle the response_time and average fields
			 else if( cell.field == "response_time" ||  cell.field == "average" ){
				 
				 var float_value = parseFloat(cell.value, 10);
				 
				 if( float_value >= 1000 ){
					 $td.addClass("failure");
				 }
				 else{
					 $td.addClass("success");
				 }
				 
			 }
			 
			 else if(cell.field == "url" ){
				 
				 // Parse the URL
				 var getLocation = function(href) {
					    var l = document.createElement("a");
					    l.href = href;
					    return l;
			     };
				 
			     $td.html(_.template('<img height="16" width="16" src="http://www.google.com/s2/favicons?domain=<%- domain %>" /> <%- value %>', {
		            	value: cell.value,
		            	domain: getLocation(cell.value).hostname
		         }));
			     
			     return;
			 }
			 
			 // Render the cell
			 if( icon != null ){
				 $td.html(_.template('<i class="icon-<%- icon %>"> </i><%- value %>', {
		            	value: cell.value,
		                icon: icon
		         }));
			 }
			 else{
				 $td.html( cell.value );
			 }
		 }
	});
    
    return WebsiteStatusCellRenderer;
});