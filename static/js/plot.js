var sensor;

$( document ).ready(function() {
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
	    type: 'bar',

	    // The data for our dataset
	    data: {
	        labels: labels,
	        datasets: [{
	            label: "My First dataset",
	            backgroundColor: icon_mapping[sensors[sensor].type]["color"],
	            borderColor: icon_mapping[sensors[sensor].type]["color"],
	            data: data,
	        }]
	    },

	    // Configuration options go here
	    options: {
	    	legend: {
				display: false
			},
			scales: {
				yAxes: [{
					ticks: {
						beginAtZero:true,
					}
				}]
			}
	    }
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

// The select handler. Call the chart's getSelection() method
function selectHandler() {
  var selectedItem = material.getSelection()[0];
  if (selectedItem) {
    var value = data.getValue(selectedItem.row, 0);
    alert('The user selected ' + value);
  }
}




