
(function () {
	'use strict';
	var path, slash;
	path = location.href;
		if(getOS() == "MAC") {
			slash = "/";
			path = path.substring(0, path.length - 11);
		}
		if(getOS() == "WIN") {
			slash = "/";
			path = path.substring(8, path.length - 11);
		}
		const net = require('net');
		var csInterface = new CSInterface();
		const server = net.createServer((socket) => {
		socket.on('data', (data) => {
		
		data = String(data)
		csInterface.evalScript(data, (result) => {
			if (result==""){
				socket.write("null");
			} else {
			socket.write(result);
			}
			
		});
	
		});
		});
		server.maxConnections = 2;
		
		server.listen(9888);
		setTimeout(function(){
			generateButtons();
		}, 300);
	
	
	}());
	
	
	function generateButtons(){
		var debug = 1;
		var object = undefined;
		if (debug === 1) {
			var object = {'File Save...': 'Save Version.cmd', 'File Save comment...': 'Save Extended.cmd', 'Prism settings' : 'Settings.cmd', 'Project Browser' : 'Project Browser.cmd', 'Export' : 'Export.cmd'};
		} else {
			
		var object = {'File Save...': 'SaveVersion', 'File Save comment...': 'SaveComment', 'Prism settings' : 'Settings', 'Project Browser' : 'ProjectBrowser', 'Export' : 'Export'};
		}
		
	
		var buttonHolder = document.getElementById("buttonHolder");
		var thisButton;
		var thisName;
		for (const [key, value] of Object.entries(object)){
	
			thisName = key
			thisButton = document.createElement("BUTTON");
			thisButton.innerHTML = thisName;
			thisButton.setAttribute("class", "scriptButton");
			thisButton.setAttribute("path", "A");
			thisButton.setAttribute("onclick", "buttonClick( '" + value + "' )");
			buttonHolder.appendChild(thisButton);
			// var br = document.createElement("br");
			// buttonHolder.appendChild(br);
	
	
		}
	}	
	
	
	
	function buttonClick(buttonElement){// Define the path to the .cmd file		
		const { exec } = require('child_process');
		const path = require('path');
		const cmdFilePath = CMDSDIR+"/"+buttonElement;
		
		// Execute the .cmd file
		exec(`"${cmdFilePath}"`, (error, stdout, stderr) => {
			if (error) {
				console.error(`Error executing command: ${error}`);
				return;
			}
			if (stderr) {
				console.error(`stderr: ${stderr}`);
				return;
			}
			console.log(`stdout: ${stdout}`);
		});
	}

	function getOS() {
		var userAgent = window.navigator.userAgent,
		platform = window.navigator.platform,
		macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
		windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
		os = null;
	
		if(macosPlatforms.indexOf(platform) != -1) {
			os = "MAC";
		} else if(windowsPlatforms.indexOf(platform) != -1) {
			os = "WIN";
		}
		return os;
	}