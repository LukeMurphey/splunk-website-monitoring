// Test authors:
// You only need to include this file and then declare your tests scripts in a tests.json file in /appserver/static/js/tests/tests.json
//
// The file should look something like this:
//
//    {
//            "test_es_general_settings_view": "../app/SplunkEnterpriseSecuritySuite/js/tests/TestESGeneralSettingsView",
//            "test_timeline_entry_modal_view": "../app/SplunkEnterpriseSecuritySuite/js/tests/TestTimelineEntryModalView",
//            "test_timeline_view": "../app/SplunkEnterpriseSecuritySuite/js/tests/TestTimelineView"
//    }
//

// A list of apps that are enabled for Jasmine tests

var apps = [
    'website_monitoring',
]

/**
 * Run tests as defined in the test_script_paths associative array.
 */
function runTests(test_script_paths){
    
    // Define the require paths with the Jasmine dependencies
    var paths = {
            jasmine: '//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine',
            jasmine_html: '//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine-html'
        };

    // Merge in the test scripts
    for (var test_script in test_script_paths) { paths[test_script] = test_script_paths[test_script]; }

    // Configure require
    require.config({
        paths: paths,
        shim: {
            'jasmine_html': {
                deps: ['jasmine', 'jquery']
            }
        }
    });

    // Make the require dependencies
    var dependencies = ['jquery',
                        'underscore',
                        'backbone',
                        'jasmine',
                        'jasmine_html'];

    // Add the test scripts so that they get loaded
    for(test_script in test_script_paths){
        dependencies.push(test_script);
    }

    // Add the ready call
    dependencies.push('splunkjs/mvc/simplexml/ready!');

    // Let's do this thing...
    require(dependencies, function($, _, Backbone)
         {
        
            function addStylesheet( filename ){
            
                // For Internet Explorer, use createStyleSheet since adding a stylesheet using a link tag will not be recognized
                // (http://stackoverflow.com/questions/1184950/dynamically-loading-css-stylesheet-doesnt-work-on-ie)
                if( document.createStyleSheet ){
                    document.createStyleSheet(filename);
                }
                // For everyone else
                else{
                    var link = $('<link>');
                    link.attr({type: 'text/css',rel: 'stylesheet', href: filename});
                    $('head').append( link );
                }
            }
            
             addStylesheet('//cdnjs.cloudflare.com/ajax/libs/jasmine/1.3.1/jasmine.css');
             
             // Setup jasmine for execution    
             (function() {
                
                // Configure the environment
                var jasmineEnv = jasmine.getEnv();
                jasmineEnv.updateInterval = 250;
                  
                // Use the HTML reporter for displaying the results
                var htmlReporter = new jasmine.HtmlReporter();
                jasmineEnv.addReporter(htmlReporter);
                
                jasmineEnv.specFilter = function(spec) {
                    return htmlReporter.specFilter(spec);
                };
                
                var currentWindowOnload = window.onload;
                window.onload = function() {
                  if (currentWindowOnload) {
                    currentWindowOnload();
                  }
            
                  // Add the version number
                  //document.querySelector('.version').innerHTML = jasmineEnv.versionString();
                  //execJasmine();
                };
            
                function execJasmine() {
                    
                  $('.shared-footer').hide();
                
                  jasmineEnv.execute();
                }
                
                // Hide the view content
                $('#dashboard').hide();
                
                // Reset the body margin because it looks ugly
                $('body').css('margin', '0px');
                
                // Start Jasmine in a bit
                setTimeout(execJasmine, 5000);
                
              })();

         }
    );
}

/**
 * Load the collection of tests for the given app.
 **/
function loadSuitesForApp(app){
    var promise = $.Deferred();    
    var uri = Splunk.util.make_url('static/app/' + app + '/js/tests/tests.json');
    
    jQuery.ajax({
        url:     uri,
        type:    'GET',
        cache: false,
        success: function(result) {
            if(result === undefined){
                promise.reject(result);
            } else if (typeof result === 'string') {
                result = JSON.parse(result);
                promise.resolve(result);
            } else if (typeof result === 'object') {
                promise.resolve(result);
            } else {
                promise.reject(result);
            }
        },
        error: function(result) {
            promise.reject(result);
        },
    });
    return promise;
}

/**
 * Start the tests for the app that this file resides in.
 */
function startTests(){
    require(['splunkjs/mvc/utils'], function (SplunkUtil) {
        var suites = apps.map(loadSuitesForApp);

        // wait till all collections have been loaded
        $.when.apply($, suites).done(function() {
            var suite = arguments
            // merge tests
            var tests = {};
            $.each(suite, function(idx) {
                $.extend(tests, suite[idx]);
            }.bind(tests).bind(suite));
            // run tests
            runTests(tests);
        })
    })();
}

// Now, lets start the tests
startTests();   
