var sensors;
var table = document.getElementById("sensor-table");

var socket = io.connect('http://homeserver.fritz.box:5000');

socket.on('connect', function() {
	// socket.emit('my event', {data: 'I\'m connected!'});
});

socket.on('new_progress', function(data) {
	$("#progressbar").attr('aria-valuenow', Math.round(data * 100))
	$("#progressbar").text(Math.round(data * 100) + " %");
	$("#progressbar").width(Math.round(data * 100) + "%");
	if (data == 1) {
		$("#progressbar").text("Finished!");
		setTimeout(function() {
			$("#progressbar-container").slideUp();
			$("#progressbar").attr('aria-valuenow', 0)
			$("#progressbar").text("0 %");
			$("#progressbar").width("0%");
		}, 2000);
	}

});

socket.on('discovered', function(data) {
	newData(data);
});

var buttons = {
	active : {
		css_class : "btn btn-success",
		html : "<span class=\"glyphicon glyphicon-play\" aria-hidden=\"true\"></span> active"
	},
	inactive : {
		css_class : "btn btn-default",
		html : "<span class=\"glyphicon glyphicon-play\" aria-hidden=\"true\"></span> activate"
	}
}



document.onload = load_sensors();

function load_sensors() {
	$.ajax({
		type : 'GET',
		url : '/sensors/_get_sensors',
		success : newData,
	});
}

function discover_sensors() {

	$("#progressbar-container").slideDown();
	socket.emit('discover_addresses', {
		data : $("#addresses-list").val()
	});

	// $.ajax({
	// type : 'POST',
	// url : '/sensors/_discover',
	// data : $("#addresses").serialize(),
	// success : newData,
	// });

}

function toggle_sensor_status(name) {
	$.ajax({
		type : 'POST',
		url : '/sensors/_toggle_status',
		success : sensorStatusChanged,
		data : {
			sensor : name
		},
	});
}

function deactivate_sensor(name) {

}

function sensorStatusChanged(data) {
	if (data != null) {
		// success
		$("#button_" + data["id"])
				.attr("class", buttons[data["status"]].css_class)
				.html( buttons[data["status"]].html);
		//
	}
}

function newData(jsonData) {

	sensors = jsonData;

	$("#test-div").text(JSON.stringify(jsonData) + Object.keys(jsonData));
	var num_rows = table.rows.length;

	for (j = 1; j < num_rows; j++) {
		table.deleteRow(1);

	}

	var i = 1;

	for (sensor in jsonData) {
		


		// Create an empty <tr> element and add it to the 1st position of
		// the table:
		var row = table.insertRow(i);

		// Insert new cells (<td> elements) at the 1st and 2nd position of
		// the "new"
		// <tr> element:
		var type_cell = row.insertCell(0);
		var name_cell = row.insertCell(1);
		var address_cell = row.insertCell(2);
		var id_cell = row.insertCell(3);
		var label_cell = row.insertCell(4);
		var activate_cell = row.insertCell(5);

		// Add some text to the new cells:
		type_cell.innerHTML = '<span class="flaticon-'
				+ icon_mapping[jsonData[sensor].type]["icon"]
				+ '" style="color: '
				+ icon_mapping[jsonData[sensor].type]["color"] + ';"></span>';
		name_cell.innerHTML = '<a href="/sensor/sensor?sensor=' + sensor + '">'
				+ sensor + '</a>';
		address_cell.innerHTML = jsonData[sensor].address;
		address_cell.className += " hidden-xs";
		id_cell.innerHTML = jsonData[sensor].id;
		id_cell.className += " hidden-xs";
		label_cell.innerHTML = jsonData[sensor].label;
		label_cell.className += " hidden-xs";
		activate_cell.innerHTML = "<button style='width: 100%;' id='button_"
				+ jsonData[sensor].id
				+ "' class='" + buttons[jsonData[sensor].status].css_class + "' onclick='toggle_sensor_status(\""
				+ sensor
				+ "\")'>" + buttons[jsonData[sensor].status].html + "</button>";
		activate_cell.className += " text-right";

		i++;

	}

}