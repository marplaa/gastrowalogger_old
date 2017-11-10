/*google.charts.load('current', {
	packages : [ 'corechart', 'bar' ]
});*/

google.charts.load('current', {
	'packages' : [ 'bar' ]
});
google.charts.setOnLoadCallback(getData);




var options = {
	water : {
		height : 300,
		legend : {
			position : 'none'
		},
		chart : {
			title : 'Wasserverbrauch der letzten 7 Tage'
		},
		colors : [ icon_mapping["water"]["color"], icon_mapping["water"]["color"] ]
	},
	gas: {
		height : 300,
		legend : {
			position : 'none'
		},
		chart : {
			title : 'Gasverbrauch der letzten 7 Tage'
		},
		colors : [ icon_mapping["gas"]["color"], icon_mapping["gas"]["color"] ]
	},
	power: {
		height : 300,
		legend : {
			position : 'none'
		},
		chart : {
			title : 'Stromverbrauch der letzten 7 Tage'
		},
		colors : [ icon_mapping["power"]["color"], icon_mapping["power"]["color"] ]
	}
};

var data;
var material;

function getData() {
	
//	$.get({
//		type : 'GET',
//		url : '/sensor/_get_sensors',
//		success : function (data) {sensors = data},
//	});
	
	$.get( "/sensor/_get_sensors", function( data ) {
		sensors = data;
		});

	var today = Date.today();
	var week_ago = Date.today().add(-6).days();
	var from_date = week_ago.toString('dd.MM.yyyy');
	var to_date = today.toString('dd.MM.yyyy');
	
	for (sensor in sensors) {
		$.ajax({
			type : 'POST',
			url : '/charts/_get_chart?sensor=' + sensor,
			data : {
				from_date : from_date,
				from_time : "00:00",
				to_date : to_date,
				to_time : "23:59",
				resolution : "86400"
			},
			success : drawChart,
		});
	}

//	$.ajax({
//		type : 'POST',
//		url : '/charts/_get_chart?sensor=',
//		data : {
//			from_date : from_date,
//			from_time : "00:00",
//			to_date : to_date,
//			to_time : "00:00",
//			resolution : "86400"
//		},
//		success : drawChart,
//	});
//
//	$.ajax({
//		type : 'POST',
//		url : '/water/_get_verbrauch',
//		data : {
//			von_date : from_date,
//			von_uhr : "00:00",
//			bis_date : to_date,
//			bis_uhr : "00:00",
//			aufloesung : "86400"
//		},
//		success : drawWaterChart,
//	});

}

function drawChart(jsonData) {
	
	if (jsonData["status"] == "ok") {
		sensor = jsonData["sensor"]
		material = new google.charts.Bar(document.getElementById(sensor["id"]
				+ '_chart_div'));

		data = new google.visualization.DataTable(jsonData);

		// Instantiate and draw our chart, passing in some options.

		material.draw(data, options[sensor["type"]]);
	}
	
	
}