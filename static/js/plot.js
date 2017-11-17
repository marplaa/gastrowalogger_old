var sensor;

$(document).ready(function() {
	$.ajax({
		type : 'POST',
		url : '/charts/_get_chart?sensor=' + sensor,
		data : $("#settings").serialize(),
		success : drawChart,
	});

});

function setSensor(_sensor) {
	sensor = _sensor;
}

var chart;
var labels;
var data;
var ctx = document.getElementById('myChart').getContext('2d');

function drawChart(jsonData) {

	data = jsonData["data"];
	labels = jsonData["labels"];

	chart = new Chart(ctx, {
		// The type of chart we want to create
		type : 'bar',

		// The data for our dataset
		data : {
			labels : labels,
			datasets : [ {
				label : "My First dataset",
				backgroundColor : icon_mapping[sensors[sensor].type]["color"],
				borderColor : icon_mapping[sensors[sensor].type]["color"],
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
			tooltips: {
	            callbacks: {
	            	afterFooter : function(tooltipItem, chart) {
	            		return("<br><br>" + tooltipItem[0].xLabel);
	            	}
	            }
			}
		}
	});
	document.getElementById("myChart").onclick = function(evt) {
		var element = chart.getElementAtEvent(evt)[0]
		var clickedElementindex = element["_index"];

		// get specific label by index
		alert(chart.data.labels[clickedElementindex]);
	}

}

function requestNewData() {
	$.ajax({
		type : 'POST',
		url : '/charts/_get_chart?sensor=' + sensor,
		data : $("#settings").serialize(),
		success : newData,
	});
	$("#loading_icon").fadeIn();
}

function newData(jsonData) {
	if (jsonData["status"] == "ok") {

		chart.data.datasets[0].data = jsonData["data"];
		chart.data.labels = jsonData["labels"];
		chart.update();
		// Instantiate and draw our chart, passing in some options.

		$("#loading_icon").fadeOut();
	} else {
		$("#loading_icon").fadeOut();
		alertPopupColor(jsonData["error_msg"], "Notice", "#abc");
	}

}

function clickHandler(evt) {
	var item = myChart.getElementAtEvent(evt)[0];

	if (item) {
		var label = myChart.data.labels[firstPoint._index];
		var value = myChart.data.datasets[firstPoint._datasetIndex].data[firstPoint._index];
	}
}
