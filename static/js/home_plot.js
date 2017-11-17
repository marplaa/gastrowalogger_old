$(document).ready(function() {
	getData();

});


function getData() {

	// $.get({
	// type : 'GET',
	// url : '/sensor/_get_sensors',
	// success : function (data) {sensors = data},
	// });

//	$.get("/sensor/_get_sensors", function(data) {
//		sensors = data;
//	});

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

	// $.ajax({
	// type : 'POST',
	// url : '/charts/_get_chart?sensor=',
	// data : {
	// from_date : from_date,
	// from_time : "00:00",
	// to_date : to_date,
	// to_time : "00:00",
	// resolution : "86400"
	// },
	// success : drawChart,
	// });
	//
	// $.ajax({
	// type : 'POST',
	// url : '/water/_get_verbrauch',
	// data : {
	// von_date : from_date,
	// von_uhr : "00:00",
	// bis_date : to_date,
	// bis_uhr : "00:00",
	// aufloesung : "86400"
	// },
	// success : drawWaterChart,
	// });

}

function drawChart(jsonData) {

	if (jsonData["status"] == "ok") {
		sensor = jsonData["sensor"]
		data = jsonData["data"];
		labels = jsonData["labels"];
		
		var ctx = document.getElementById(sensor["id"] + '_chart_div').getContext('2d');

		var chart = new Chart(
				ctx,
				{
					// The type of chart we want to create
					type : 'bar',

					// The data for our dataset
					data : {
						labels : labels,
						datasets : [ {
							label : "My First dataset",
							backgroundColor : icon_mapping[sensor.type]["color"],
							borderColor : icon_mapping[sensor.type]["color"],
							data : data,
						} ]
					},

					// Configuration options go here
					options : {
						legend : {
							display : false
						},
						scales : {
							yAxes : [ {
								ticks : {
									beginAtZero : true,
								}
							} ]
						},
						tooltips : {
							callbacks : {
								afterFooter : function(tooltipItem, chart) {
									return ("<br><br>" + tooltipItem[0].xLabel);
								}
							}
						}
					}
				});


		// Instantiate and draw our chart, passing in some options.

	}

}