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
			unit : jsonData["unit"],
			long_labels : jsonData["long_labels"],
			notes : jsonData["notes"],
			datasets : [ {
				label : "dataset",
				borderColor : jsonData["bg"],
				backgroundColor : icon_mapping[sensors[sensor].type]["color"],
				borderWidth: 3,
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
					title : function(tooltipItem, data) {
						return (data.long_labels[tooltipItem[0].index]);
					},
					label : function(tooltipItem, data) {
						return (" " + tooltipItem.yLabel + " " + data.unit);
					},
					afterBody : function(tooltipItem, data) {
						return (data.notes[tooltipItem[0].index]);
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
		chart.data.datasets[0].borderColor = jsonData["bg"];
		chart.data.long_labels = jsonData["long_labels"]
		chart.data.labels = jsonData["labels"];
		chart.data.notes = jsonData["notes"];
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
