let currentSlide = 0;
let slides;
$(document).ready(function() {
	//显示弹出框
	 $("#requestModal").modal({
        backdrop: 'static', // Disable clicking outside the modal to close
        keyboard: false     // Disable using the keyboard to close
    });
    $("#requestModal").modal('show');


	if (window.Worker) {
		
		var $result = $("#result");
		var isDone = false;
		
		$("#uploadBtn").on("change", function(evt) {
			
			isDone = false;
			
			$result.html("");
			$("#load-progress").text("0%").attr("aria-valuenow", 0).css("width", "0%");
			$("#result_block").removeClass("hidden").addClass("show");
			
			var fileName = evt.target.files[0];
			
			// Read the file
			var reader = new FileReader();
			reader.onload = (function(theFile) {
				return function(e) {

					// Web Worker
					var worker = new Worker(workerScriptUrl);
				
					worker.addEventListener('message', function(e) {
						
						var msg = e.data;
						
						switch(msg.type) {
							case "progress-update":
								$("#load-progress").text(msg.data.toFixed(2) + "%")
									.attr("aria-valuenow", msg.data.toFixed(2))
									.css("width", msg.data.toFixed(2) + "%");
								break;
							case "slide":
								$result.append(msg.data);
								break;
							case "processMsgQueue":
								processMsgQueue(msg.data);
								break;
							case "pptx-thumb":
								$("#pptx-thumb").attr("src", "data:image/jpeg;base64," + msg.data);
								break;
							case "slideSize":
								if (localStorage) {
									localStorage.setItem("slideWidth", msg.data.width);
									localStorage.setItem("slideHeight", msg.data.height);
								} else {
									alert("Browser don't support Web Storage!");
								}
								break;
							case "globalCSS":
								$result.append("<style>" + msg.data + "</style>");
								break;
							case "ExecutionTime":
								$("#info_block").html("Execution Time: " + msg.data + " (ms)");
								isDone = true;
								worker.postMessage({
									"type": "getMsgQueue"
								});
								break;
							case "WARN":
								console.warn('Worker: ', msg.data);
								break;
							case "ERROR":
								console.error('Worker: ', msg.data);
								$("#error_block").text(msg.data);
								break;
							case "DEBUG":
								console.debug('Worker: ', msg.data);
								break;
							case "INFO":
							default:
								console.info('Worker: ', msg.data);
								//$("#info_block").html($("#info_block").html() + "<br><br>" + msg.data);
						}
						
					}, false);
					
					worker.postMessage({
						"type": "processPPTX",
						"data": e.target.result
					});
					
				}
			})(fileName);
			reader.readAsArrayBuffer(fileName);
		});
		
		$("#slideContentModel").on("show.bs.modal", function (e) {
			if (!isDone) { return; }
			$("#slideContentModel .modal-body textarea").text($result.html());
		});
		
		$("#download-btn").click(function () {
			if (!isDone) { return; }
			var cssText = "";
			$.get("css/pptx2html.css", function (data) {
				cssText = data;
			}).done(function () {
				var headHtml = "<style>" + cssText + "</style>";
				var bodyHtml = $result.html();
				var html = "<!DOCTYPE html><html><head>" + headHtml + "</head><body>" + bodyHtml + "</body></html>";
				var blob = new Blob([html], {type: "text/html;charset=utf-8"});
				saveAs(blob, "slides_p.html");
			});
		});
		
		$("#download-reveal-btn").click(function () {
			if (!isDone) { return; }
			var cssText = "";
			$.get("css/pptx2html.css", function (data) {
				cssText = data;
			}).done(function () {
				var revealPrefix = 
"<script type='text/javascript'>\
Reveal.initialize({\
	controls: true,\
	progress: true,\
	history: true,\
	center: true,\
	keyboard: true,\
	slideNumber: true,\
	\
	theme: Reveal.getQueryHash().theme,\
	transition: Reveal.getQueryHash().transition || 'default',\
	\
	dependencies: [\
		{ src: 'lib/js/classList.js', condition: function() { return !document.body.classList; } },\
		{ src: 'plugin/markdown/marked.js', condition: function() { return !!document.querySelector( '[data-markdown]' ); } },\
		{ src: 'plugin/markdown/markdown.js', condition: function() { return !!document.querySelector( '[data-markdown]' ); } },\
		{ src: 'plugin/highlight/highlight.js', async: true, callback: function() { hljs.initHighlightingOnLoad(); } },\
		{ src: 'plugin/zoom-js/zoom.js', async: true, condition: function() { return !!document.body.classList; } },\
		{ src: 'plugin/notes/notes.js', async: true, condition: function() { return !!document.body.classList; } }\
	]\
});\
</script>";
				var headHtml = "<style>" + cssText + "</style>";
				var bodyHtml = "<div id='slides' class='slides'>" + $result.html() + "</div>";
				var html = revealPrefix + headHtml + bodyHtml;
				var blob = new Blob([html], {type: "text/html;charset=utf-8"});
				saveAs(blob, "slides.html");
			});
		});
		
		$("#to-reveal-btn").click(function () {
			if (localStorage) {
				localStorage.setItem("slides", LZString.compressToUTF16($result.html()));
				window.open("./reveal/demo.html", "_blank");
			} else {
				alert("Browser don't support Web Storage!");
			}
		});

	} else {
		alert("Browser don't support Web Worker!");
	}
});

// PPT背景文本框监听
 document.addEventListener('input', function (event) {
        if (event.target.id !== 'userRequest') return;
        autoExpand(event.target);
    }, false);

    function autoExpand(field) {
        // Reset field height
        field.style.height = 'inherit';

        // Get the computed styles for the element
        var computed = window.getComputedStyle(field);

        // Calculate the height
        var height = parseInt(computed.getPropertyValue('border-top-width'), 10)
                     + parseInt(computed.getPropertyValue('padding-top'), 10)
                     + field.scrollHeight
                     + parseInt(computed.getPropertyValue('padding-bottom'), 10)
                     + parseInt(computed.getPropertyValue('border-bottom-width'), 10);

        field.style.height = height + 'px';
    }

// 弹出框提交
function submitRequest() {
	 var userRequest = $("#userRequest").val();
    // Save the user request in local storage
	localStorage.setItem("userRequest", userRequest);

	$("#requestModal").modal('hide');
	$("#mainContent").show();
}


var currentAudio = null; // This will hold the currently playing audio element
// 声音播放
document.addEventListener('click', function(event) {
  if (event.target.classList.contains('play-sound')) {
    var button = event.target;
    var index = button.getAttribute('data-text-index');
    var textbox = document.querySelector('.chatgpt-textbox[data-text-index="' + index + '"]');
    var textContent = textbox.innerText || textbox.textContent;
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

    // Disable the button
    button.disabled = true;
    button.textContent = 'Loading...'; // Optional: Update button text

    fetch('/post/ppt2speech/play', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ text: textContent ,slideIndex: index})
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.blob();
    })
    .then(blob => {
		  // If there's currently playing audio, pause it and set current time to 0
		  if (currentAudio) {
			currentAudio.pause();
			currentAudio.currentTime = 0;
		  }

		  // Create a new audio element for the new audio
		  var url = window.URL.createObjectURL(blob);
		  currentAudio = new Audio(url);
		  currentAudio.play();

		  // Optional: Update button text to 'Play Sound'
		  button.textContent = 'Play Sound';

		  // Optional: Reset the button text when the audio ends
		  currentAudio.onended = function() {
			button.textContent = 'Play Sound';
		  };
		})
    .catch(error => {
      console.error('Error:', error);
      button.textContent = 'Play Sound'; // Optional: Reset button text if there's an error
    })
    .finally(() => {
      // Re-enable the button
      button.disabled = false;
    });
  }
});


function showSlide(index) {
  var slides = document.querySelectorAll('.slide');
  var textboxes = document.querySelectorAll('.chatgpt-textbox');
  var buttons = document.querySelectorAll('.slide-content');
    // 保存当前幻灯片的内容
  var currentTextbox = document.querySelector('.chatgpt-textbox[data-text-index="' + currentSlide + '"]');
  if (currentTextbox && currentTextbox.innerHTML !== '生成中...') {
    localStorage.setItem('editable-content-' + currentSlide, currentTextbox.innerHTML);
  }

  if (index >= 0 && index < slides.length) {
    // Hide all slides and textboxes
    slides.forEach(function(slide) { slide.style.display = 'none'; });
    textboxes.forEach(function(textbox) { textbox.style.display = 'none'; });
	buttons.forEach(function(buttons) { buttons.style.display = 'none'; });

    // Show the selected slide and its textbox
    slides[index].style.display = 'block';
    textboxes[index].style.display = 'block'; // Make sure the index matches between slides and textboxes
	buttons[index].style.display = 'block';

    // Load the content from local storage if it exists
    const savedContent = localStorage.getItem('editable-content-' + index);
    const textbox = document.querySelector('.chatgpt-textbox[data-text-index="' + index + '"]');

    if (savedContent && savedContent !== '生成中...') {
      textbox.innerHTML = savedContent;
    } else {
      // No saved content or it's still generating, fetch new content from backend
      textbox.innerHTML = '生成中...'; // Display "Generating..." message
      fetchContentFromBackend(index, textbox); // Call function to fetch content from backend
    }

  } else {
    console.error('Slide or Textbox ' + index + ' does not exist.');
  }
}

function fetchContentFromBackend(slideIndex, textboxElement) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    let userRequest = localStorage.getItem("userRequest"); // Retrieve user request from local storage

	 // Check if userRequest is empty or not set, and assign default value if necessary
    if (!userRequest) {
        userRequest = '普通中文演讲';
    }

    // Make a request to the backend endpoint
    fetch('/post/ppt2speech/save', {
        method: 'POST',
        credentials: 'include', // If you're including credentials like cookies
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken // Function to get the CSRF token
        },
        body: JSON.stringify({
            slideIndex: slideIndex,
            userRequest: userRequest // Send user request along with slide index
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Assuming the backend returns an object with a 'content' key
        if (data.content) {
            textboxElement.innerHTML = data.content;
            localStorage.setItem('editable-content-' + slideIndex, data.content); // Update local storage
        }
    })
    .catch(error => {
        console.error('Failed to fetch content:', error);
        textboxElement.innerHTML = '内容加载失败'; // Display "Content loading failed" message
    });
}


// Navigation event listeners
// Assuming you have buttons or some other elements for navigation
document.getElementById('next-slide').addEventListener('click', () => {
    var slides = document.querySelectorAll('.slide');
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
});

document.getElementById('prev-slide').addEventListener('click', () => {
    var slides = document.querySelectorAll('.slide');
    currentSlide = (currentSlide - 1 + slides.length) % slides.length;
    showSlide(currentSlide);
});

// 禁用所有按钮
function toggleButtonsDisabled(disabled) {
  document.querySelectorAll('button').forEach(function(button) {
    button.disabled = disabled;
  });
}

// PPT上传
document.addEventListener('DOMContentLoaded', function () {

  document.getElementById('uploadBtn').addEventListener('change', function (evt) {
	  	// Clear all local storage
  	localStorage.clear();
	// Disable all buttons during the upload
  	toggleButtonsDisabled(true);

    var file = evt.target.files[0];
    var formData = new FormData();
    formData.append('file', file);

    var uploadNotification = document.getElementById('uploadNotification');
    uploadNotification.textContent = 'Uploading...';
    uploadNotification.className = 'alert';
    uploadNotification.classList.remove('hidden');
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

    fetch('/post/ppt2speech/save', { // Ensure you include the trailing slash
      method: 'POST',
      body: formData,
      credentials: 'include',
      headers: {
         'X-CSRFToken': csrfToken
      },
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok ' + response.statusText);
      }
      return response.json();
    })
    .then(data => {
      uploadNotification.className = 'alert alert-success';
      uploadNotification.textContent = data.message;

      // Update the textboxes with the new content
      if (data.pages) {
        Object.keys(data.pages).forEach(pageIndex => {
          var pageContent = data.pages[pageIndex];
          var textbox = document.querySelector('.chatgpt-textbox[data-text-index="' + pageIndex.replace('page_', '') + '"]');
          if (textbox) {
            textbox.innerHTML = pageContent;
          }
        });
      }
    })
    .catch(error => {
      uploadNotification.className = 'alert alert-danger';
      uploadNotification.textContent = 'Upload failed: ' + error.message;
    })
    .finally(() => {
      // Optional: Remove loading indication
		 toggleButtonsDisabled(false);
		 document.getElementById('submitBtn').disabled = false;
    });
  });
});



function processMsgQueue(queue) {
	for (var i=0; i<queue.length; i++) {
		processSingleMsg(queue[i].data);
	}
}

function processSingleMsg(d) {
	
	var chartID = d.chartID;
	var chartType = d.chartType;
	var chartData = d.chartData;

	var data =  [];
	
	var chart = null;
	switch (chartType) {
		case "lineChart":
			data = chartData;
			chart = nv.models.lineChart()
						.useInteractiveGuideline(true);
			chart.xAxis.tickFormat(function(d) { return chartData[0].xlabels[d] || d; });
			break;
		case "barChart":
			data = chartData;
			chart = nv.models.multiBarChart();
			chart.xAxis.tickFormat(function(d) { return chartData[0].xlabels[d] || d; });
			break;
		case "pieChart":
		case "pie3DChart":
			data = chartData[0].values;
			chart = nv.models.pieChart();
			break;
		case "areaChart":
			data = chartData;
			chart = nv.models.stackedAreaChart()
						.clipEdge(true)
						.useInteractiveGuideline(true);
			chart.xAxis.tickFormat(function(d) { return chartData[0].xlabels[d] || d; });
			break;
		case "scatterChart":
			
			for (var i=0; i<chartData.length; i++) {
				var arr = [];
				for (var j=0; j<chartData[i].length; j++) {
					arr.push({x: j, y: chartData[i][j]});
				}
				data.push({key: 'data' + (i + 1), values: arr});
			}
			
			//data = chartData;
			chart = nv.models.scatterChart()
						.showDistX(true)
						.showDistY(true)
						.color(d3.scale.category10().range());
			chart.xAxis.axisLabel('X').tickFormat(d3.format('.02f'));
			chart.yAxis.axisLabel('Y').tickFormat(d3.format('.02f'));
			break;
		default:
	}
	
	if (chart !== null) {
		
		d3.select("#" + chartID)
			.append("svg")
			.datum(data)
			.transition().duration(500)
			.call(chart);
		
		nv.utils.windowResize(chart.update);
		
	}
	
}
