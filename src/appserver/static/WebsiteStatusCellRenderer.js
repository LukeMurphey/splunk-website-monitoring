define(['jquery', 'underscore', 'splunkjs/mvc', 'views/shared/results_table/renderers/BaseCellRenderer'], function($, _, mvc, BaseCellRenderer) {
    
    var WebsiteStatusCellRenderer = BaseCellRenderer.extend({
    	 canRender: function(cell) {
    		 return ($.inArray(cell.field, ["title", "response", "response_time", "average"]) >= 0); // Add "url" to this list to render the favicon
		 },
		 
		 render: function($td, cell) {
			 
			 // Add the class so that the CSS can style the content
			 $td.addClass(cell.field);
			 
			 var icon = null;
			 
			 // Handle the response
			 if(cell.field == "response"){
				 
			 	// Parse out the response code and whether the content matches from the response
				parsed_values = /([0-9]+)([ ](.*))?/i.exec(cell.value);
			 
				// Handle the response code if it was an integer that could be parsed
				if(parsed_values !== null){
					response = parsed_values[1];
					has_expected_string = parsed_values[3];

					// Reformat the cell value
					cell.value = response;

					if(has_expected_string === "true"){
						cell.value += " (content matches)";
						$td.addClass("contentmatch");
					}
					else if(has_expected_string === "false"){
						cell.value += " (content doesn't match)";
						$td.addClass("contentnonmatch");
					}

					// Assign the classes based on the response code
					var int_value = parseInt(response, 10);
					
					if(int_value >= 400){
						$td.addClass("failure");
						icon = 'alert';
					}
					else if(has_expected_string === "false"){
						$td.addClass("failure");
						icon = 'alert';
					}
					else if(int_value >= 100){
						$td.addClass("success");
						icon = 'check';
					}
					else{
						$td.addClass("failure");
						icon = 'alert';
					}
				}
				// Otherwise, handle this as a string that represents an error state
				// e.g. "Connection timed out"
				else{
					$td.addClass("failure");
					icon = 'alert';
				}
				
			 }
			 
			 // Handle the response_time and average fields
			 else if(cell.field == "response_time" || cell.field == "average"){
				 
				 var float_value = parseFloat(cell.value, 10);
				 
				 if( float_value >= 1000 ){
					 $td.addClass("failure");
					 icon = 'alert';
				 }
				 else{
					 $td.addClass("success");
					 
					 var percent = 0;
					 
					 if(float_value <= 100){
						 percent = 0;
					 }else if(float_value <= 250){
						 percent = 25;
					 }
					 else if(float_value <= 500){
						 percent = 50;
					 }
					 else if(float_value <= 750){
						 percent = 75;
					 }
					 else if(float_value <= 1000){
						 percent = 100;
					 }
					 else{
						 percent = null;
					 }
					 
					 if(percent !== null){
						 /*
					     $td.html(_.template('<img class="performance_icon" height="12" width="12" src="/static/app/website_monitoring/img/<%- percent %>.png" /> <%- value %>', {
				            	value: cell.value,
				            	percent: percent
				         }));
					     */
					     $td.html(_.template('<i class="stopwatch-icon-<%- percent %>" /> <%- value %>', {
				            	value: cell.value,
				            	percent: percent
				         }));
					     
					     $td.addClass("response-" + percent);
					     
					     return;
					 }

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
				 $td.html(cell.value);
			 }
		 }
	});
    
    return WebsiteStatusCellRenderer;
});