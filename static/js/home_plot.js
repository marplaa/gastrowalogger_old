$(document).ready(function() {
	getData();

});


function getData() {

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
}

function drawChart(jsonData) {

	if (jsonData["status"] == "ok") {
		sensor = jsonData["sensor"]
		data = jsonData["data"];
		labels = jsonData["labels"];
		
		var ctx = document.getElementById(sensor["id"] + '_chart_div').getContext('2d');
		ctx.heigth = 500;
		
		$('#' + sensor["id"] + '_chart_heading').text(jsonData["heading"]); 

		var chart = new Chart(
				ctx,
				{
					// The type of chart we want to create
					type : 'bar',

					// The data for our dataset
					data : {
						labels : labels,
						datasets : [ {
							label : "consumption",
							backgroundColor : icon_mapping[sensor.type]["color"],
							borderColor : icon_mapping[sensor.type]["color"],
							data : data,
						} ]
					},

					// Configuration options go here
					options : {
						maintainAspectRatio: false,
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
							enabled : true
						}
					}
				});

	}

}