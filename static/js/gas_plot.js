/*google.charts.load('current', {
	packages : [ 'corechart', 'bar' ]
});*/

google.charts.load('current', {'packages':['bar']});
google.charts.setOnLoadCallback(drawTitleSubtitle);

var options = {
	height : 500,
	legend: {position: 'none'},
	chart : {
		title : 'Gasverbrauch'
	},
	colors: ['#ff6600', '#ffab91']
};

var data;
var material;

function drawTitleSubtitle() {
	
	material = new google.charts.Bar(document.getElementById('chart_div'));

	$.ajax({
        type: 'POST',
        url: '/gas/_get_chart',
        data: $("#settings").serialize(),
        success: newData,
    });

	//var jsonData = $.ajax({
	//	url : "",
	//	dataType : "json",
	//	async : false
	//}).responseText;

	// Create our data table out of JSON data loaded from server.
	
}

function requestNewData() {
	$.ajax({
        type: 'POST',
        url: '/gas/_get_chart',
        data: $( "#settings" ).serialize(),
        success: newData,
    });
	$("#loading_icon").fadeIn();
}

function newData(jsonData) {
	data = new google.visualization.DataTable(jsonData);

	// Instantiate and draw our chart, passing in some options.

	
	material.draw(data, options);
	$("#loading_icon").fadeOut();
}