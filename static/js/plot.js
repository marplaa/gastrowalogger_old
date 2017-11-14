/*google.charts.load('current', {
	packages : [ 'corechart', 'bar' ]
});*/

google.charts.load('current', {
	'packages' : [ 'bar' ]
});
//google.charts.setOnLoadCallback(drawChart);

var sensor;
var options;

function setSensor(_sensor) {
	sensor = _sensor;
	google.charts.setOnLoadCallback(drawChart);

	options = {
		height : 700,
		legend : {
			position : 'none'
		},
		chart : {
			title : sensors[sensor].alias
		},
		colors : [icon_mapping[sensors[sensor].type]["color"], icon_mapping[sensors[sensor].type]["color"] ]
	};
}

var data;
var material;

function drawChart() {

	material = new google.charts.Bar(document.getElementById('chart_div'));

	$.ajax({
		type : 'POST',
		url : '/charts/_get_chart?sensor=' + sensor,
		data : $("#settings").serialize(),
		success : newData,
	});

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
		data = new google.visualization.DataTable(jsonData);

		// Instantiate and draw our chart, passing in some options.

		material.draw(data, options);
		$("#loading_icon").fadeOut();
	} else {
		$("#loading_icon").fadeOut();
		alertPopupColor(jsonData["error_msg"], "Notice", "#abc");
	}

}



