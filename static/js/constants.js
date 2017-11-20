//var icon_mapping = {
//	water : {
//		icon : "raindrop",
//		color : "#0099ff"
//	},
//	gas : {
//		icon : "flame",
//		color : "#ff6600"
//	},
//	power : {
//		icon : "flash",
//		color : "#ffcc00"
//	},
//};


function alertPopupColor(message, heading, color) {
	$("#alert-modal-header").text(heading);
	$("#alert-modal-message").text(message);
	$("#alert-modal .modal-body").css("background-color", color);
	$("#alert-modal").modal();
}

function alertPopup(message, heading) {
	alertPopupColor(message, heading, "#FFF")
}