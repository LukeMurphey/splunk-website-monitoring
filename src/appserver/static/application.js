
if( Splunk.Module.SimpleResultsTable ){
	Splunk.Module.SimpleResultsTable = $.klass(Splunk.Module.SimpleResultsTable, {
	
	    renderResults: function($super, htmlFragment) {
	        $super(htmlFragment);
	        
	        if (this.getInferredEntityName()=="events") {
	            this.renderedCount = $("tr", this.container).length - 1;
	        }
	        
	        $.each( $('.simpleResultsTable td'), function(index, value) {
	        	$(this).attr('data-value', $(this).text() );
	        });
	    }
	});
}