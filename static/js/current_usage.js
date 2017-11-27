google.charts.load('current', {
	'packages' : [ 'gauge' ]
});

google.charts.setOnLoadCallback(init_charts);

var running = true;
var l_per_min = 0;
var start_time_l_per_min = 0;
var start_count_l_per_min = 0;

var start_time_l = 0;
var start_count_l = 0;

var seconds = 1000;
var minutes = 1000 * 60;
var price = 0;


var options_l_per_min = {
		width : 200,
		height : 200,
		redFrom : 18,
		redTo : 20,
		yellowFrom : 16,
		yellowTo : 18,
		minorTicks : 5,
		max : 20
	};

var data_l_per_min;

var chart_l_per_min;

function set_price(_price) {
	price = _price;
}


function getLiveData() {
	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, new_data);
}

// Cookie handling...
function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/sensor/current";
} 

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length,c.length);
        }
    }
    return "";
} 
// cookie handling

function init_charts() {
	
	
	// ######### l_per_min ##############
    if (getCookie("start_count_l_per_min") == "") {
    	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor='+sensor, 
    		function (jsonData) {
    			start_count_l_per_min = jsonData["data"];
    			setCookie("start_count_l_per_min", start_count_l_per_min, 1);
    		}
    	);
    	
    } else {
    	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, 
        		function (jsonData) {
    		        data = jsonData["data"];
        			if (data >= parseInt(getCookie("start_count_l_per_min"))) {
        				start_count_l_per_min = parseInt(getCookie("start_count_l_per_min"));
        			} else {
        				start_count_l_per_min = data;
        				setCookie("start_count_l_per_min", start_count_l_per_min, 1);
        			}
        		}
        	);
    	
    }
    
    // start_time_l_per_min = getCookie("start_time_l_per_min");
	
    if (getCookie("start_time_l_per_min") == "") {
    	start_time_l_per_min = Date.now();
    	setCookie("start_time_l_per_min", start_time_l_per_min, 1);
    } else {
    	start_time_l_per_min = parseInt(getCookie("start_time_l_per_min"));
    }
    // ######### l_per_min ##############
    
 // ######### liters ##############
    if (getCookie("start_count_l") == "") {
    	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, 
    		function (jsonData) {
    			start_count_l = jsonData["data"];
    			setCookie("start_count_l", start_count_l, 1);
    		}
    	);
    	
    } else {
    	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, 
        		function (jsonData) {
    		        data = jsonData["data"];
        			if (data >= parseInt(getCookie("start_count_l"))) {
        				start_count_l = parseInt(getCookie("start_count_l"));
        			} else {
        				start_count_l = data;
        				setCookie("start_count_l", start_count_l, 1);
        			}
        		}
        	);
    	
    }
    
    start_time_l = getCookie("start_time_l");
	
    if (getCookie("start_time_l") == "") {
    	start_time_l = Date.now();
    	setCookie("start_time_l", start_time_l, 1);
    } else {
    	start_time_l = parseInt(getCookie("start_time_l"));
    }
    // ######### liters ##############
    
    
	
	chart_l_per_min = new google.visualization.Gauge(document
			.getElementById('liter_per_min_div'));
	data_l_per_min = google.visualization.arrayToDataTable([
		[ 'Label', 'Value' ], [ 'L/min', 0] ]);
	
	drawChart_l_per_min();
	$("#sinceSpan_l_per_min").text(new Date(start_time_l_per_min).toLocaleTimeString());
	$("#sinceSpan_l").text(new Date(start_time_l).toLocaleTimeString());
	
	
	getLiveData();
}

function reset_l_per_min () {
	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, 
    		function (jsonData) {
    			start_count_l_per_min = jsonData["data"];
    			setCookie("start_count_l_per_min", start_count_l_per_min, 1);
    			start_time_l_per_min = Date.now();
    			setCookie("start_time_l_per_min", start_time_l_per_min, 1);
    			$("#sinceSpan_l_per_min").text(new Date(start_time_l_per_min).toLocaleTimeString());
    			data_l_per_min.setValue(0, 1, 0);
    	        chart_l_per_min.draw(data_l_per_min, options_l_per_min);
    		}
    	);
	
}

function reset_l() {
	$.getJSON($SCRIPT_ROOT + '/sensor/_get_live_data?sensor=' + sensor, 
    		function (jsonData) {
    			start_count_l = jsonData["data"];
    			setCookie("start_count_l", start_count_l, 1);
    			start_time_l = Date.now();
    			setCookie("start_time_l", start_time_l, 1);
    			$("#sinceSpan_l").text(new Date(start_time_l).toLocaleTimeString());
    			$("#zeros").text("000000");
    	        $("#liters").text("");
    	        $("#euro_sum").text("0 €");
    		}
    	);
	
}


function drawChart_l_per_min() {
	chart_l_per_min.draw(data_l_per_min, options_l_per_min);
}

function new_data(jsonData) {
	if (jsonData["status"] == "ok" && running) {
		
		data = jsonData["data"];
		// ###### l_per_min #####
		if (data - start_count_l_per_min != 0) {
			l_per_min = (data - start_count_l_per_min) / ((Date.now() - start_time_l_per_min) / minutes);
			
			data_l_per_min.setValue(0, 1, l_per_min);
	        chart_l_per_min.draw(data_l_per_min, options_l_per_min);
		}
		
		// ######## l_per_min end
		
		
		// ###### liters
		
		if (data - start_count_l != 0) {
	        
	        var zeros = "0";
	        var liters = 0;
	        
	        liters = data - start_count_l;
	        zeros = zeros.repeat(6 - liters.toString().length);
	        
	        $("#zeros").text(zeros);
	        $("#liters").text(liters);
	        
	        var preis = liters*(price/1000);
	        
	        $("#euro_sum").text(preis.toFixed(2) + " €");
	        
		}
		

		
		setTimeout(getLiveData, 1000);
	} else if (running) {
		alert("Keine Daten empfangen");
		running = false;
	} 
}