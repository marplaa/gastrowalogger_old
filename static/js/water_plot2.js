google.charts.load('current', {
	packages : [ 'corechart', 'bar' ]
});
google.charts.setOnLoadCallback(drawTitleSubtitle);

var options = {
	height : 500,
	legend: {position: 'none'},
	explorer: {axis: 'horizontal'},
	hAxis: {
        gridlines: {
           count:-1,
           units: {
               days: {format: ['dd.MM.yy']},
               hours: {format: ['hh:mm']},
           }
        },
        minorGridlines: {
            units: {
              hours: {format: ['hh:mm']},
              minutes: {format: ['mm']}
            }
          }
    },
	
	chart : {
		title : 'Wasserverbrauch'
	}
};




var data;
var material;

function drawTitleSubtitle() {
	
	material = new google.visualization.ColumnChart(document.getElementById('chart_div'));

	$.ajax({
        type: 'POST',
        url: '/water/_get_verbrauch',
        data: $("#settings").serialize(),
        success: newData,
    });

	// var jsonData = $.ajax({
	// url : "",
	// dataType : "json",
	// async : false
	// }).responseText;

	// Create our data table out of JSON data loaded from server.
	
}

function requestNewData() {
	$.ajax({
        type: 'POST',
        url: '/water/_get_verbrauch',
        data: $( "#settings" ).serialize(),
        success: newData,
    });
}

function newData(jsonData) {
	data = new google.visualization.DataTable(jsonData);

	// Instantiate and draw our chart, passing in some options.

	
	material.draw(data, options);
}