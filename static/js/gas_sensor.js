var _labels = [];
var _data = [];
var highThresArray = [];
var lowThresArray = [];
var running = false;
var ctx = document.getElementById("myChart");
var myChart;
var impulseCount = 0;

function set_thresholds(lowThres, highThres) {
	for (var i = 0; i < 100; i++) {
		highThresArray[i] = highThres;
		lowThresArray[i] = lowThres;
	}
	myChart.update();
	$("#lowThresInput").val(lowThres);
	$("#highThresInput").val(highThres);
}

function setSettings(data) {
	set_thresholds(data["lowThres"], data["highThres"])
	populate_fields(data);
}

function sendSettings() {
	$.ajax({
        type: 'POST',
        url: $SCRIPT_ROOT + '/gas/_set_settings',
        data: $( "#settingsForm" ).serialize(),
        success: function(response) {loadSettings(); },
    });
}

function _init(settings) {
	
	for (var i = 0; i < 100; i++) {
		_labels.push("" + i);
		_data.push(0);
		highThresArray[i] = settings["highThres"];
		lowThresArray[i] = settings["lowThres"];
	}
	
	myChart = new Chart(ctx, {
		type: 'line',
		data: {
			labels: _labels,
			datasets: [{
				label: 'value',
				data: _data,
				fill: false,
				borderColor: "#444",
				pointBackgroundColor: "#999",
				pointBorderColor:"#444"
			},
			{
				label: 'highThres',
				data: highThresArray,
				fill: false,
				borderColor: "#A22",
				pointBackgroundColor: "#A11",
				pointBorderColor:"#A11"
			},
			{
				label: 'lowThres',
				data: lowThresArray,
				fill: false,
				borderColor: "#2A2",
				pointBackgroundColor: "#1A1",
				pointBorderColor:"#1A1"
			}]
		},
		options: {
			scales: {
				yAxes: [{
					ticks: {
						max: 1024,
						min: 0,
						beginAtZero:true,
						stepSize: 100
					}
				}],
				xAxes: [{
					display: false
				}]
			},
			responsive: true,
			animation: false,
			tooltips: {
				enabled: false
			},
			legend: [{
				display: false
			}]
		}
	})
	
	$("#button1").click(function (){running=!running; request_Data(); $('#button1').toggleClass('btn-danger btn-success'); if (running) {$("#button1").text("Stop");} else {$("#button1").text("Start");}});
	$("#updateThres").click(function (){var formData = $("#settingsForm").serialize();  console.log(formData);});
	$("#invert").prop( "checked", settings["invert"]);
	

	
}

function populate_fields(settings) {
	$("#lowThresInput").val(settings["lowThres"]);
	$("#hysteresisInput").val(settings["hysteresis"]);
	$("#hysteresisInputAuto").val(settings["hysteresis"]);
	$("#highThresInput").val(settings["highThres"]);
	$("#invert").prop( "checked", settings["invert"]);
	$("#minIdleLengthInput").val(settings["min_idle_length"]);
	$("#minImpulseLengthInput").val(settings["min_impulse_length"]);
	$("#intervalInput").val(settings["interval"]);
	$("#maxFailsInput").val(settings["max_fails"]);
	
	$("#lowThresLegend").text(settings["lowThres"]);
	$("#highThresLegend").text(settings["highThres"]);
	
	$("#impulseBadge").val(settings["count"]);
	
}

function loadDefaults() {
	$.getJSON($SCRIPT_ROOT + '/gas/_load_defaults', setSettings);
	
}

function loadSettings() {
	$.getJSON($SCRIPT_ROOT + '/gas/_get_settings', setSettings);
	
}

function new_data(data) {
	if (data != -1 && running) {
		_data.shift();
		_data.push(data["value"]);
		myChart.update();
		
		$("#valueLegend").text(data["value"]);
		$("#lowThresLegend").text(data["lowThres"]);
		$("#highThresLegend").text(data["highThres"]);
		$("#impulsesBadge").text(data["count"]);
		
		if (impulseCount < data["count"]) {
			$("#impulsesBadge").effect( "highlight", {color:"#F55"}, 1000 );
		}
		impulseCount = data["count"];
		
		setTimeout(request_Data, 60);
	} else if (running) {
		timer.pause();
		alert("Keine Daten empfangen");
		running = false;
		$("#button1").text("Start");
		$('#button1').toggleClass('btn-danger btn-success');
	} 
}

function new_thresholds(data) {
	set_thresholds(data["lowThres"], data["highThres"]);
	myChart.update();
}

function request_Data() {
	$.getJSON($SCRIPT_ROOT + '/gas/_get_calibration_data', new_data);
}



