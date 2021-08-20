function getMeta(metaName) {
	const metas = document.getElementsByTagName('meta');
	for (let i = 0; i < metas.length; i++) {
		if (metas[i].getAttribute('name') === metaName) {
			return metas[i].getAttribute('content');
		}
	}
	return '';
}
//var bigChat = new ChatConsumer(getMeta('client_host'),getMeta('server_host'));
let bigChat = new ChatConsumer();



(function() {

	/* Constructor starts here */
	this.BigBot = function(bigChat) {
		this.bigChat = bigChat;
		/* Create global element references starts here */
		this.botWidget = null;
		this.botWidgetPopup = null;
		this.bigBotWrapper = null;
		this.stylesheet = null;
		this.fontStyle = null;
		this.botInputText = null;
		this.audioInput = null;
		this.container = document;
		this.active = false;
		this.currentX;
		this.currentY;
		this.initialX;
		this.initialY;
		this.xOffset = 0;
		this.yOffset = 0;
		this.dragItem = null;
		this.window_open = false;
		this.greet = function() {
			alert('Hello world');
		};

		/* Create global element references ends here */

		/* Define option defaults starts here */

		var defaults = {
			selector: '#BigBot',
			widgetPosition:'BottomRight',
			chatPosition:'right',
			snapToSides:true,
			speechEnabled:true,
			speechToTextWith:'default',
			themeColor:'#3f51b5'
		}

		/* Define option defaults ends here */

		/* Create options by extending defaults with the passed in arugments starts here */
		if (arguments[1] && typeof arguments[1] === "object") {
			this.options = extendDefaults(defaults, arguments[1]);
		}
		/* Create options by extending defaults with the passed in arugments ends here */

		// new-code


	}
	/* Constructor ends here */

	/****************************** PUBLIC METHODS STARTS *****************************************/
	/* init Method starts here */

	BigBot.prototype.init = function() {
		var self = this;
		var rootStyle = document.createElement("style");
		rootStyle.innerText = ":root {--theme-color: "+this.options.themeColor+"; --bot-avatar:url(logo.png); }";
		document.head.appendChild(rootStyle);
		loadCSS(getMeta('server_host')+"/static/client/bigbot.css","bigbotCss");
		let stateCheck = setInterval(() => {
			if (document.readyState === 'complete') {
				clearInterval(stateCheck);
				buildOut.call(self);
				initializeEvents.call(self);

			}
		}, 100);

		bigChat.onTypingStatusChanged = function(context,user,isTyping){
			typingIndicator(isTyping);
		};

		bigChat.onInputSuggestionReceived = function (data) {
			var dataObj = data;
			document.getElementById('bigbot_suggestionBtn').innerHTML = getSuggestions(data);
			document.getElementById('bigbot_suggestionBtn').style.left = "0px";
			document.querySelectorAll('.suggest').forEach(item => {
				item.addEventListener('click', event => {
					var idValue = parseInt( item.id.split('suggest-')[1]);
					console.log("DATA OBJECT -",dataObj[idValue]);
					triggerUserMessages(item,"action",dataObj[idValue].value,dataObj[idValue]);
					document.getElementById('bigbot_suggestionBtn').innerHTML = "";
					document.getElementById('bigBotInput').value = "";

				});
			});
		};

		/* onDelegatesChanged starts here */



		/* onDelegatesChanged ends here */


		// bigChat.onHistoryReceived = function(messages){
		// 	document.querySelector('.bigbot_bigBotChat').innerHTML = '<div style="width: 100%;height: 150px"></div><div id="bigbot_typingIndicator2" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div><div id="bigbot_bigBotChatLast" class="bigbot_bigBotChatLast" style="width: 100%;height: 174px"></div>';
		//
		// 	if(messages.length >0){
		// 		var lastmessage = '';
		// 		for (var key of Object.keys(messages)) {
		// 			triggerBotMessages(messages[key],"",100 ,messages[key].outgoing);
		// 			lastmessage = messages[key];
		//
		// 			const mail_message = messages[key];
		// 			for(let i = 0; i < mail_message.statement.contents.length ;i++){
		// 				const node = mail_message.statement.contents[i];
		// 				if(node.node == 'big.bot.core.iframe'){
		// 					getInputPicker('iframe',{src:node.content,width:node.width,height:node.height});
		// 				}else if(node.node == 'big.bot.core.image'){
		// 					getInputPicker('image',{src:node.content});
		// 				}
		// 			}
		//
		// 		}
		//
		// 		var input_type = false;
		// 		if ('type' in lastmessage.statement.tags) {
		// 			input_type = lastmessage.statement.tags.type;
		// 			getInputPicker(input_type);
		//
		// 		} else {
		// 			input_type = '';
		// 		}
		//
		// 		//getInputPicker('datetime-local');
		//
		// 	}else{
		// 		//getWelcomeMessages();
		// 	}
		//
		// };

		/* onMessageReceived Callback starts here */

		bigChat.onLockInput = function (locked) {
			var inputElement = document.getElementById('bigBotInput');
			if(locked){
				inputElement.readOnly = true;
			}else {
				inputElement.readOnly = false;
			}
		};
		bigChat.onMessagesReceived = function (message, reset = false) {
			console.error('-window_open--',self.window_open);

			if(reset){
				document.querySelector('.bigbot_bigBotChat').innerHTML = '<div style="width: 100%;height: 150px"></div><div id="bigbot_typingIndicator2" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div><div id="bigbot_bigBotChatLast" class="bigbot_bigBotChatLast" style="width: 100%;height: 174px"></div>';
			}

			if(message.length==0)
				return;

			if(!self.window_open)
				return;

			//message.button = [{"name": "Show","action": "test"},{"name": "Fullscreen","action": "test"},{"name": "Delete","action": "test"},{"name": "Edit","action": "test"}];
			//var buttons = [];

				// buttons = [{
				// 	"body": 'create task',
				// 	"values":["create task"],
				// 	"contexts":[0]
				// },{
				// 	"body": 'Edit',
				// 	"values":[3],
				// 	"contexts":[0]
				// },{
				// 	"body": 'Contact us',
				// 	"values":[3],
				// 	"contexts":[0]
				// }];


			console.log("MESSAGE",message);



			for(let i = message.length - 1; i >= 0; i--){
				let mail_message = message[i];
				let buttons = [];
				if(mail_message.statement.contents) {
					for (let i = 0; i < mail_message.statement.contents.length; i++) {
						const node = mail_message.statement.contents[i];
						if(node.node == 'big.bot.core.actions'){
							buttons = node.data;
							break;
						}
					}
				}

				triggerBotMessages(message[i],buttons,5000,message[i].outgoing);



				if(mail_message.statement.contents) {
					for (let i = 0; i < mail_message.statement.contents.length; i++) {
						const node = mail_message.statement.contents[i];
						if (node.node == 'big.bot.core.iframe') {
							getInputPicker('iframe', {src: node.data, width: node.width, height: node.height});
						} else if (node.node == 'big.bot.core.image') {
							getInputPicker('image', {src: node.data});
						}
					}
				}
			}

			// var input_type = false;
			// if ('type' in message[0].statement.tags && message[0].statement.tags != undefined ){
			// 	input_type = message[0].statement.tags.type;
			// 	getInputPicker(input_type);
			// }
			// else{
			// 	input_type = '';
			// }

			const mail_message = message[message.length-1];


			if(mail_message.statement.contents){
				for(let i = 0; i < mail_message.statement.contents.length ;i++){
					const node = mail_message.statement.contents[i];
					 if(node.node == 'big.bot.core.delegates'){
						getInputPicker('list',{content:node.data});
					}else if(node.node == 'big.bot.core.picker.date'){
						getInputPicker('date');
					}else if(node.node == 'big.bot.core.picker.datetime'){
						getInputPicker('datetime');
					}else if(node.node == 'big.bot.core.picker.duration'){
						getInputPicker('duration');
					}else if(node.node == 'big.bot.core.oauth'){
						getInputPicker('auth_card',node);
					}else if(node.node == 'big.bot.core.state'){
						getInputPicker('specialButtons',node.data);
					}
				}
			}


			// let actions = [{
			// 	"body": 'Cancel',
			// 	"className":'cancelButton',
			// 	"values":[3],
			// 	"contexts":[0]
			// },{
			// 	"body": 'Skip',
			// 	"className":'skipButton',
			// 	"values":[false],
			// 	"contexts":[0]
			// }];
			//
			// getInputPicker('specialButtons',actions);

			// getInputPicker('iframe',{src:'http://192.168.43.155:8069/chart_hub_distro/render_demo?fullscreen=True&id=3&w=200&h=250',width:200,height:250});


			if(getSpeechStatus() == 'yes'){

				if(self.options.speechToTextWith == "aws"){

					/*
					document.getElementById('audioPlayback').load();
					document.getElementById('audioSource').src = message[i].audio;
					document.getElementById('audioPlayback').play();
					*/

					textToSpeechWithAWSPolly(message[0].statement.text);
				}else{

					setTimeout(function () {
						textToSpeech(message[0].statement.text);
					},1000);
				}
			}
			getTemplateByName("botDateBubble",{});

		};

		bigChat.onUpdateTray = function(active_channel, channels) {
			console.log('delegate ui updating.....');
			//Util.popitup('https://google.com');



			let root = document.documentElement;
			root.style.setProperty('--bot-avatar', 'url('+active_channel.image+')');
			var delegateContent = '';
			for(var i=0; i< channels.length;++i){
				let channel = channels[i];

				let ncount = bigChat.getNotificationCount(channel) == 0 ? "" : "<b class=\"avatarNoti\">%d</b>".format_string(bigChat.getNotificationCount(channel) );
				if(channel.id == active_channel.id){
					let newRow = '<span class="avatarWrapper"><img title="%s" data-id="%d" class="delegateAvatar" src="%s" width="46">%s</span>'
							.format_string(channel.name,i,channel.image,ncount);
					delegateContent +=  newRow;

				}else{
					let newRow = '<span class="avatarW"><img title="%s" data-id="%d" class="delegateAvatar" src="%s" width="46">%s</span>'
						.format_string(channel.name,i,channel.image,ncount);;
					delegateContent += newRow;
				}
			}
			let stateCheck = setInterval(() => {
				if (document.readyState === 'complete') {
					clearInterval(stateCheck);
					setTimeout(function () {
						document.getElementsByClassName('channelTab')[0].style.display = 'block';
						document.getElementById('delegateContent').innerHTML = delegateContent;
						document.querySelectorAll('.delegateAvatar').forEach(item => {
							item.addEventListener('click', event => {
								var index = item.getAttribute('data-id');
								root.style.setProperty('--bot-avatar', 'url('+channels[index].image+')');
								bigChat.onSelectChannel(channels[index]);
								//triggerUserMessages(data[index].body,"action",data[index].value,data[index],true);
							});
						});

					},600);

				}
			}, 100);




		};
		/* onMessageReceived Callback ends here */
	}
	/* init Method ends here */
	BigBot.prototype.show = function() {
		this.botWidget.classList.add('showPopup');
	}
	BigBot.prototype.hide = function() {
		this.botWidget.classList.remove('showPopup');
	}
	BigBot.prototype.closeChat = function(){
		document.querySelector('.bigbot_bigBotChat').style.left = '420px';
		document.querySelector('.bigbot_bigBotChat').innerHTML = '<div style="width: 100%;height: 150px"></div><div id="bigbot_typingIndicator2" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div><div id="bigbot_bigBotChatLast" class="bigbot_bigBotChatLast" style="width: 100%;height: 174px"></div>';
		setTimeout(function () {
			document.querySelector('.bigbot_bigBotWrapper ').style.display = 'none';
			document.getElementById('botbutton').style.display = 'block';
		},100)
	}
	BigBot.prototype.send = function(){
		removeEmoji();
		var inputElement = document.getElementById('bigBotInput');
		if(inputElement.value == "" || inputElement.value == " "){
			alert('Please enter something');
		}else{
			bigChat.sendMessage('text', inputElement.value, inputElement.value);
			// document.getElementById('gooeyWrapperAnswer').innerHTML = '<div class="answer--bubble gooeyBubble by--user default isComplete"><div class="answer-body__wrapper"><div class="answer--body update">'+inputElement.value+'</div></div></div>';
			// var tmplHtml = '<%this.templateSrc.A%>';
			// var template = templateRender(tmplHtml, {
			// 	templateSrc:{
			// 		"A" :getTemplateByName('answerBubble',{'body':inputElement.value,'delay':100,'hiddenClass':''})
			// 	}
			// });
			inputElement.value = '';

			//var list = document.getElementById("bigBotChatLast");
			// var list = document.getElementById("bigbot_typingIndicator2");
			// list.insertAdjacentHTML('beforebegin', template);
			scrollFunct('bigbot_bigBotChat',500);
			setTimeout(function () {
				document.getElementById('bigBotMic').style.display = "block";
				document.getElementById('bigbot_bigBotButton').style.display = "none";
				loadBotMessages();
				setTimeout(function () {
					scrollFunct('bigbot_bigBotChat',500);
				},1000);
			},100);
		}
	}
	BigBot.prototype.test = function() {
        let self = this;
		document.querySelector('.bigbot_bigBotWrapper').style.display = 'block';
		setTimeout(function () {
			self.window_open = true;
			var ele = document.getElementById('bigbot_bigBotChat');
			ele.style.left = "0px";
			document.getElementsByClassName('bigbot_botInputText')[0].style.right = '12px';
			document.getElementById('botbutton').style.display = 'none';
			setTimeout(function(){
				document.getElementById('gooeyWrapper').style.opacity = '1';
				document.getElementById('bigbot_emojiPicker').style.opacity = '1';
				document.getElementById('bigbot_fileAttachment').style.opacity = '1';
				loadBotMessages.call(this);
				self.bigChat.onMessagesReceived(self.bigChat.history);
				setTimeout(function () {
					scrollFunct('bigbot_bigBotChat',500);
				},500);
			},500);
		},500);


		// var sChat = new ChatConsumer(getMeta('client_host'),getMeta('server_host'));
		// sChat.onHistoryReceived = function(messages){
		// 	document.querySelector('.bigbot_bigBotChat').innerHTML = '<div style="width: 100%;height: 150px"></div><div id="bigbot_typingIndicator2" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div><div id="bigbot_bigBotChatLast" class="bigbot_bigBotChatLast" style="width: 100%;height: 174px"></div>';
		// 	if(messages.length >0){
		// 		var lastmessage = '';
		// 		for (var key of Object.keys(messages)) {
		// 			triggerBotMessages(messages[key],"",100 ,messages[key].outgoing);
		// 			lastmessage = messages[key];
		//
		// 			const mail_message = messages[key];
		// 			for(let i = 0; i < mail_message.statement.contents.length ;i++){
		// 				const node = mail_message.statement.contents[i];
		//
		// 				if(node.node == 'big.bot.core.iframe'){
		// 					getInputPicker('iframe',{src:node.content,width:node.width,height:node.height});
		// 				}else if(node.node == 'big.bot.core.image'){
		// 					getInputPicker('image',{src:node.content});
		// 				}else if(node.node == 'big.bot.core.delegates'){
		// 					getInputPicker('list',{content:node.content});
		// 				}
		// 			}
		//
		// 		}
		//
		// 		var input_type = false;
		// 		if ('type' in lastmessage.statement.tags) {
		// 			input_type = lastmessage.statement.tags.type;
		// 			getInputPicker(input_type);
		//
		// 		} else {
		// 			input_type = '';
		// 		}
		// 		//getInputPicker('iframe',{src:"https://www.youtube.com/embed/t_n0yhhuJBs",width:260,height:200});
		// 		//getInputPicker('iframe',{src:"https://www.youtube.com/embed/t_n0yhhuJBs",width:260,height:200});
		// 		//getInputPicker('iframe',{src:"https://www.youtube.com/embed/t_n0yhhuJBs",width:260,height:200});
		// 		//getInputPicker('datetime-local');
		// 	}else{
		// 		//getWelcomeMessages();
		// 	}
		// };
	};
	/****************************** PUBLIC METHODS ENDS *****************************************/

	/****************************** PRIVATE METHODS STARTS *****************************************/

	/* Utility method to extend defaults with user options starts here */
	function extendDefaults(source, properties) {
		var property;
		for (property in properties) {
			if (properties.hasOwnProperty(property)) {
				source[property] = properties[property];
			}
		}
		return source;
	}
	/* Utility method to extend defaults with user options ends here */

	/* Initialize Events starts here */
	function initializeEvents() {
		var self = this;
		this.container.addEventListener("touchstart", dragStart.bind(this), false);
		this.container.addEventListener("touchend", dragEnd.bind(this), false);
		this.container.addEventListener("touchmove", drag.bind(this), false);
		this.container.addEventListener("mousedown", dragStart.bind(this), false);
		this.container.addEventListener("mouseup", dragEnd.bind(this), false);
		this.container.addEventListener("mousemove", drag.bind(this), false);
		if(this.botWidget){
			this.botWidget.addEventListener("mouseenter", this.show.bind(this));
			this.botWidget.addEventListener("mouseleave", this.hide.bind(this));
		}
		
		document.getElementById("bigBotInput").addEventListener("blur", function(event) {

			if(hasClass(self.bigBotWrapper,"onFocus")){
				document.getElementsByClassName("bigbot_bigBotWrapper")[0].classList.remove('focus');
			}

		});
		document.getElementById('closeBigBot').addEventListener("click",this.closeChat.bind(this));
		document.getElementById("bigbotPopupButton").addEventListener("click",this.test.bind(this));
		document.getElementById("bigbot_bigBotButton").addEventListener("click",this.send.bind(this));
		document.getElementById("bigBotInput").addEventListener("keyup", function(event) {
			if(this.value){
				if (event.keyCode === 13) {
					event.preventDefault();
					document.getElementById("bigbot_bigBotButton").click();
					document.getElementById('bigBotMic').style.display = "block";

				}
				document.getElementById('bigBotMic').style.display = "none";
				document.getElementById('bigbot_bigBotButton').style.display = "block";
				document.getElementsByClassName('bigbot_suggestionBtnWrapper')[0].style.display = "block";
				bigChat.onInputTextChanged(this.value);
			}else{
				document.getElementById('bigBotMic').style.display = "block";
				document.getElementById('bigbot_bigBotButton').style.display = "none";
			}


		});
		document.querySelector('#bigBotMic').addEventListener('click',function () {
			speechToText();
		});

		document.querySelector("#bigBotInput").addEventListener("focus", function(event) {
			if(hasClass(self.bigBotWrapper,"onFocus")){
				document.getElementsByClassName("bigbot_bigBotWrapper")[0].classList.add('focus');
			}

		});

		document.querySelector('#file-input').addEventListener('change', function() {
			uploadFiles();
		});

		document.getElementsByName('bg').forEach(function(item){

			item.addEventListener('change',function(){
			if(item.value == 'on'){
				self.bigBotWrapper.classList.add("focus");
				self.bigBotWrapper.classList.remove("onFocus");


			}else if(item.value == 'focus'){
				self.bigBotWrapper.classList.remove("focus");
				self.bigBotWrapper.classList.add("onFocus");
			}else{
				self.bigBotWrapper.classList.remove("focus");
				self.bigBotWrapper.classList.remove("onFocus");
			}


			});

		});

		document.querySelector('.speechBtn').addEventListener( 'change', function() {
			if(this.checked) {
				// Checkbox is checked..
				if(self.options.speechToTextWith == 'aws') {
					removeJS("awsPolly");
				}
			} else {
				if(self.options.speechToTextWith == 'aws') {
					loadJS("https://sdk.amazonaws.com/js/aws-sdk-2.410.0.min.js", "awsPolly");
				}
				// Checkbox is not checked..
			}
		});
		document.getElementById('bigbot_fileClose').addEventListener("click",function () {
			var dropInstance = Dropzone.forElement("#dropzone");
			document.getElementById('dropzone').style.display = "none";
			dropInstance.removeAllFiles();
			dropInstance.disable();
		});
		document.getElementById('bigbot_fileAttachment').addEventListener("click",function () {
			/*
			if(document.querySelectorAll("#dropzone")[0].dropzone){
				var dropInstance = Dropzone.forElement("#dropzone");
				document.getElementById('dropzone').style.display = "block";
				dropInstance.enable();
			}else{
				var myDropzone = new Dropzone("#dropzone", { url: "/file/post"});
				document.getElementById('dropzone').style.display = "block";
			}
*/
			document.getElementById('file-input').click();

		});

		document.getElementById('bigbot_emojiPicker').addEventListener('click',function () {
			var emojiBubble = document.getElementById('emojiBubble');
			if(hasClass(emojiBubble,'show')){
				removeEmoji();
			}else{
				getEmoji();
			}
		});

		if (this.overlay) {
			this.overlay.addEventListener('click', this.close.bind(this));
		}

		var sliderItems = document.getElementById('bigbot_suggestionBtn');
		slide(sliderItems);

	}
	/* Initialize Events ends here */

	/* template Render function starts here */
	function templateRender(html, options){
		var re = /<%(.+?)%>/g,
			reExp = /(^( )?(var|if|for|else|switch|case|break|{|}|;))(.*)?/g,
			code = 'with(obj) { var r=[];\n',
			cursor = 0,
			result,
			match;
		var add = function(line, js) {
			js? (code += line.match(reExp) ? line + '\n' : 'r.push(' + line + ');\n') :
				(code += line != '' ? 'r.push("' + line.replace(/"/g, '\\"') + '");\n' : '');
			return add;
		};
		while(match = re.exec(html)) {
			add(html.slice(cursor, match.index))(match[1], true);
			cursor = match.index + match[0].length;
		}
		add(html.substr(cursor, html.length - cursor));
		code = (code + 'return r.join(""); }').replace(/[\r\t\n]/g, ' ');
		try { result = new Function('obj', code).apply(options, [options]); }
		catch(err) { console.error("'" + err.message + "'", " in \n\nCode:\n", code, "\n"); }
		return result;
	}
	/* template Render function ends here */

	/* forEach function starts here */
	function forEach  (collection, callback, scope) {
		if (Object.prototype.toString.call(collection) === '[object Object]') {
			for (var prop in collection) {
				if (Object.prototype.hasOwnProperty.call(collection, prop)) {
					callback.call(scope, collection[prop], prop, collection);
				}
			}
		} else {
			for (var i = 0, len = collection.length; i < len; i++) {
				callback.call(scope, collection[i], i, collection);
			}
		}
	}
	/* forEach function ends here */

	/* hasClass function starts here */
	function hasClass(element,selector) {
		var className = " " + selector + " ";
		if ((" " + element.className + " ").replace(/[\n\t\r]/g, " ").indexOf(className) > -1) {
			return true;
		}
		return false;
	}
	/* hasClass function ends here */

	/* scrollFunct starts here */
	function scrollFunct(selector,duration) {
		var element = document.getElementById(selector);
		var difference = element.offsetHeight - element.scrollTop;
		var perTick = (element.offsetHeight/(1000/200));
		var scrollInterval = setInterval(function(){
			if ( element.scrollTop < (element.scrollHeight - element.offsetHeight )) {
				element.scrollTop = element.scrollTop + perTick;
			}
			else {clearInterval(scrollInterval); }
		},15);
		setTimeout(function(){ clearInterval(scrollInterval); },3000)
	}
	/* scrollFunct ends here */

	/* uploadFiles function starts here */

	function uploadFiles(){
		// user has not chosen any file
		if(document.querySelector('#file-input').files.length == 0) {
			alert('Error : No file selected');
			return;
		}

		// first file that was chosen
		var file = document.querySelector('#file-input').files[0];

		// allowed types
		var mime_types = [ 'image/jpeg', 'image/png' ];

		// validate MIME type
		if(mime_types.indexOf(file.type) == -1) {
			alert('Error : Incorrect file type');
			return;
		}

		// max 2 MB size allowed
		if(file.size > 25*1024*1024) {
			alert('Error : Exceeded size 25MB');
			return;
		}

		// validation is successful
		//alert('You have chosen the file ' + file.name);

		// upload file now

		var data = new FormData();

// file selected by the user
// in case of multiple files append each of them

		var filesCount = document.querySelector('#file-input');
		for(var i=0;i<filesCount.files.length;++i){

			data.append('file', filesCount.files[i]);
		}
		var userToken = bigChat.getUserToken();
        data.append('uuid',userToken[0]);
        data.append('token',userToken[1]);

		console.log(data);
		var request = new XMLHttpRequest();
		request.open('post', getMeta('server_host')+'/consumer/file');

// upload progress event
		request.upload.addEventListener('progress', function(e) {
			var percent_complete = (e.loaded / e.total)*100;

			// Percentage of upload completed
			console.log(percent_complete);
		});

// AJAX request finished event
		request.addEventListener('load', function(e) {
			// HTTP status message
			console.log(request.status);

			// request.response will hold the response from the server
			console.log(request.response);
		});

// send POST request to server side script
		request.send(data);
	}

	/* uploadFiles function ends here */

	/* Draggable Methods start here */

	/* dragStart function starts here */
	function dragStart(e) {
		if(this.options.snapToSides) {
			document.getElementById('botbutton').style.setProperty("transition", "", "important");
		}
		if (e.type === "touchstart") {
			this.initialX = e.touches[0].clientX - this.xOffset;
			this.initialY = e.touches[0].clientY - this.yOffset;
		} else {
			this.initialX = e.clientX - this.xOffset;
			this.initialY = e.clientY - this.yOffset;
		}

		if ((e.target.parentElement.id === "bigbotWidgetPopup" || e.target.parentElement.id === "botbutton") && e.target.id !== "bigbotPopupButton") {
			this.active = true;
			this.dragItem = e.target.parentElement;
		}

	}
	/* dragStart function ends here */

	/* dragEnd function starts here */
	function dragEnd(e) {
		if (e.target.id === "bigbotWidgetPopup" || e.target.id === "botbutton") {
			document.getElementById('botbutton').classList.add("showPopup");
		}
		if (this.active) {
			var Offset = document.getElementById('botbutton').getBoundingClientRect();
			this.initialX = this.currentX;
			this.initialY = this.currentY;
			var scaleX = 0;
			var scaleY = 0;
			if(Offset.left >= window.innerWidth/2){
				document.getElementById('botbutton').classList.remove("leftBot");
				document.getElementById('botbutton').classList.add("rightBot");
				if(this.options.snapToSides){
					scaleX = 1;
					this.initialX = 0;
					this.xOffset = 0;

				}

			}else{
				document.getElementById('botbutton').classList.remove("rightBot");
				document.getElementById('botbutton').classList.add("leftBot");
				if(this.options.snapToSides) {
					scaleX = -1;
					this.initialX = -window.innerWidth + 68;
					this.xOffset = -window.innerWidth + 68;
				}
			}
			if(Offset.top >= 50){
				document.getElementById('botbutton').classList.remove("topBot");
				document.getElementById('botbutton').classList.add("bottomBot");
				scaleY = 1;
			}else{
				document.getElementById('botbutton').classList.remove("bottomBot");
				document.getElementById('botbutton').classList.add("topBot");
				scaleY = -1;
			}
			if(this.options.snapToSides) {
				document.getElementById('botbutton').style.setProperty("transition", "transform 0.5s", "important");
				setTranslate(this.initialX, this.currentY, scaleX, scaleY, '');
			}
		}
		this.active = false;
	}
	/* dragEnd function ends here */

	/* drag function starts here */
	function drag(e) {
		if (this.active) {
			e.preventDefault();
			document.getElementById('botbutton').classList.remove("showPopup");
			if (e.type === "touchmove") {
				this.currentX = e.touches[0].clientX - this.initialX;
				this.currentY = e.touches[0].clientY - this.initialY;
			} else {
				this.currentX = e.clientX - this.initialX;
				this.currentY = e.clientY - this.initialY;
			}
			var Offset = document.getElementById('botbutton').getBoundingClientRect();
			this.xOffset = this.currentX;
			this.yOffset = this.currentY;
			var scaleX = 0;
			var scaleY = 0;

			if(Offset.left >= window.innerWidth/2){
				scaleX = 1;

			}else{
				scaleX = -1;
			}
			if(Offset.top >= 50){
				scaleY = 1;
			}else{
				scaleY = -1;
			}
			setTranslate(this.currentX, this.currentY,scaleX,scaleY, '');
		}
	}
	/* drag function ends here */

	/* setTranslate function starts here */
	function setTranslate(xPos, yPos, scaleX,scaleY,el) {
		var some = document.getElementById('botbutton').style.setProperty("transform", "translate3d(" + xPos + "px, " + yPos + "px, 0) scaleX(" + scaleX + ") scaleY(" + scaleY + ") ", "important");
	}
	/* setTranslate function starts here */

	/* Draggable Methods end here */

	/* appendEmoji function starts here */
	var appendEmoji = function(){
		var content = this.innerHTML;
		document.getElementById('bigBotInput').value += ' '+content;
	}
	/* appendEmoji function ends here */

	/* removeEmoji function starts here */
	function removeEmoji() {
		document.getElementById('emojiBubble').classList.remove('show');
		document.getElementById('emojiContent').innerHTML = '';
	}
	/* removeEmoji function ends here */

	/* getEmoji function starts here*/
	function getEmoji() {
		document.getElementById('emojiBubble').classList.add('show');
		var emojis = [0x1F600, 0x1F603, 0x1F604, 0x1F601, 0x1F606, 0x1F605, 0x1F923, 0x1F602,
			0x1F642, 0x1F643, 0x1F609, 0x1F60A, 0x1F607, 0x1F970, 0x1F60D, 0x1F929,
			0x1F618, 0x1F617,0x1F61A,0x1F619,0x1F60B, 0x1F61B, 0x1F61C, 0x1F92A, 0x1F61D, 0x1F911,
			0x1F917, 0x1F92D, 0x1F92B, 0x1F914, 0x1F910, 0x1F928, 0x1F610, 0x1F611,
			0x1F636, 0x1F60F, 0x1F612, 0x1F644, 0x1F62C, 0x1F925,0x1F60C, 0x1F614, 0x1F62A, 0x1F924, 0x1F634, 0x1F637, 0x1F912, 0x1F915,0x1F922, 0x1F92E, 0x1F927, 0x1F975, 0x1F976, 0x1F974, 0x1F635, 0x1F92F,0x1F920, 0x1F973, 0x1F978, 0x1F60E];
		var html = '';
		for (var i = 0; i < emojis.length; ++i) {
			html += '<a class="emoji">' + String.fromCodePoint(emojis[i]) + '</a>';
		}
		document.getElementById('emojiContent').innerHTML = html;
		var elements = document.getElementsByClassName("emoji");
		for (var j = 0; j < elements.length; ++j) {
			elements[j].addEventListener('click', appendEmoji, false);
		}
	}
	/* getEmoji function starts here*/

	/* getTemplateByName function starts here */
	function getTemplateByName(tmpl,data){
		switch (tmpl) {
			case "botBubble":
				return '<div class="bigbot_bot--bubble chat-text isCold '+data.hiddenClass+'" data-delay="'+data.delay+'" id="message-'+Math.random()+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p>'+data.body+'</p></div></div></div>';
			case "botBubbleWithButtons":
				var buttons = '';
				var body1,body2;
				var message = data.body;
				var readMoreBtn = '';
				var avatarBadge ='';
					if(!data.data.is_human){
						avatarBadge = 'bigbot_bot--badge';
					}
				if(message.length>150){
					//body1 = message.substr(0, message.lastIndexOf(' ', 60)+1)+'<span class="ellipsis">...</span>';
					//body2 = '<span class="read-more-target">'+message.slice(message.lastIndexOf(' ', 60)+1)+'</span>';
					message = message.replace(/<\/?[^>]+(>|$)/g, ""); /* It will not escape <img> tag */
					body1 = message.substr(0, message.lastIndexOf(' ', 150)+1)+'<span class="ellipsis">...</span>';
					body2 = '<span class="read-more-target">'+message.substr(message.lastIndexOf(' ', 150)+1)+'</span>';
					readMoreBtn = '<label for="post-'+data.id+'" class="read-more-trigger"></label></div>'
				}else{
					body1 = message;
					body2='';
				}

				if(data.buttons.length>0){
					buttons = '<div class="botButtons inlineButtons">';
					for(var i=0;i<data.buttons.length;++i){
						let jstr = JSON.stringify(data.buttons[i]);
						buttons += '<a data-obj=\''+JSON.stringify(data.buttons[i])+'\' class="inlineBtn-'+data.id+' botBtnLink '+data.buttons[i].className+'">'+data.buttons[i].body+'</a>';

					}
					buttons +='</div>';
					console.log("BUTTONS - ",buttons);
				}
				return '<div class="bigbot_bot--bubble chat-text isComplete '+data.hiddenClass+'" data-delay="'+data.delay+'" id="message-'+Math.random()+'"><div id="avatar-'+data.id+'" class="bigbot_bot--avatar '+avatarBadge+'" style="--bot-avatar: url('+data.avatar+');"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text">  <input type="checkbox" class="read-more-state" id="post-'+data.id+'" /><p class="read-more-wrap">'+body1+''+body2+'</p>'+readMoreBtn+'</div>'+buttons+'</div></div>';
			case "answerBubble":
				return '<div class="answer--bubble by--user default isCold isComplete" id="some-button-'+Math.random()+'" data-delay="'+data.delay+'"><div class="answer-body__wrapper"><div class="answer--body update">'+data.body+'</div><button type="button" aria-label="Redo" class="icon--redoWrapper"><div class="redo"></div></button></div></div>';
			case "attachmentBubble":
				var attachments = '';
				for (var i=0;i<data.data.length;++i){
					attachments += '<div class="answer--bubble by--user userAttachment default isCold isComplete" id="some-button-'+Math.random()+'" data-delay="'+data.delay+'"><div class="answer-body__wrapper"><div class="answer--body update"><img src="'+data.data[i].url+'" alt="image" style="border-radius: 9px;display: block;height: auto;width: 100%"></div><button type="button" aria-label="Redo" class="icon--redoWrapper"><div class="redo"></div></button></div></div>';
				}
				return  attachments;
			case "typing":
				return '<div id="typingIndicator" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div>';
			case "botImageBubble":
				return '<div class="bigbot_bot--bubble bigbot_imageBubble chat-text isCold isHidden" data-delay="1500" id="message-'+Math.random()+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text" style="padding: 0"><img src="'+data.body+'" alt="image" style="border-radius: 9px;display: block;height: auto;width: 100%"></div></div></div>';
			case "botListView":
				return '<div class="bigbot_panel--wrapper panel--multi isHidden isCold" data-delay="'+data.delay+'"  id="message-'+Math.random()+'"><div class="bigbot_panel--main"><div class="bigbot_panel--content"><div class="bigbot_panel--options"><div class="bigbot_panel--optionsInner"><div class="panel--arrow arrow--up"><span class="arrow"></span></div><ul role="listbox" class="bigbot_panel--options__list"><li role="option" aria-selected="false" class="option " data-option-id="1519560580350" data-url=""><div class="option--text"><p>I want to know more about the product</p></div><div class="bigbot_icon--checkWrapper dark atLeft fast"><div class="bigbot_check-outline"><span></span></div> <div class="check"></div></div></li><li role="option" aria-selected="false" class="option " data-option-id="1519560573214" data-url=""><div class="option--text"><p>I want to know more about the pricing</p></div><div class="bigbot_icon--checkWrapper dark atLeft fast"><div class="bigbot_check-outline"><span></span></div><div class="check"></div></div></li><li role="option" aria-selected="false" class="option " data-option-id="1519560607787" data-url=""><div class="option--text"><p>I want to contact the QB team</p></div><div class="bigbot_icon--checkWrapper dark atLeft fast"><div class="bigbot_check-outline"><span></span></div><div class="check"></div></div></li><li role="option" aria-selected="false" class="option " data-option-id="1519560622873" data-url=""><div class="option--text"><p>My request is not listed here</p></div><div class="bigbot_icon--checkWrapper dark atLeft fast"><div class="bigbot_check-outline"><span></span></div><div class="check"></div></div></li></ul><div class="panel--arrow arrow--down"><span class="arrow"></span></div></div></div></div><div class="panel--overlay"><div class="bigbot_icon--checkWrapper fromBottom circle"><div class="check"></div></div><button type="button" aria-label="Redo" aria-hidden="true" class="icon--redoWrapper"><div class="redo"></div></button></div></div></div>';
			case "botInputBubble":
				return '<div data-function="" class="bigbot_bot--bubble '+data.type+'--bubble bigbot_inputTextBubble chat-text isCold isHidden" data-delay="'+data.delay+'" id="date-'+Math.random()+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p><input autofocus="true" class="input--text" id="'+data.type+'PickerInput" type="'+data.type+'" /> <button id="'+data.type+'PickerButton" class="input--button"><img src="'+data.src+'" /></button></p></div></div></div>';
			case "botTimeBubble":
				return '<div data-function="" class="bigbot_bot--bubble bigbot_inputTextBubble chat-text isCold isHidden" data-delay="'+data.delay+'" id="date-'+Math.random()+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p><input autofocus="true" class="input--text" id="timePickerInput" type="time" /> <button id="timePickerButton" class="input--button"></button></p></div></div></div>';
			default:
				break;
		}
	}
	/* getTemplateByName function ends here */

	/* delegateSwitch function starts here */
function delegateSwitch(selector,data){
	document.getElementById(selector).addEventListener("click",function(){
		bigChat.onSelectMessage(data);
	});

}
	/* delegateSwitch function ends here */

	/* getUIComponents function starts here */

	function getUIComponents(elements,data) {

		switch (elements) {
			case "date":
				return '<div data-function="" class="bigbot_bot--bubble date--bubble bigbot_inputTextBubble chat-text isCold isHidden" data-delay="100" id="comp-'+data.idPrefix+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p><input type="text"  id="'+data.idPrefix+'PickerInput" class="input--text js-date-picker" placeholder="YYYY-MM-DD"><button id="'+data.idPrefix+'PickerButton" class="input--button"><img src="'+getMeta('server_host')+'/static/client/img/date.svg'+'" /></button></p></div></div></div><div class="picker-container"></div>';
			case "duration":
				return '<div data-function="" class="bigbot_bot--bubble date--bubble bigbot_inputTextBubble chat-text isCold isHidden" data-delay="100" id="comp-'+data.idPrefix+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p><input type="text"  id="'+data.idPrefix+'PickerInput" class="input--text js-time-picker" placeholder="HH:mm"><button id="'+data.idPrefix+'PickerButton" class="input--button"><img src="'+getMeta('server_host')+'/static/client/img/time.svg'+'" /></button></p></div></div></div><div class="picker-container"></div>';
			case "datetime":
				return '<div data-function="" class="bigbot_bot--bubble date--bubble bigbot_inputTextBubble chat-text isCold isHidden" data-delay="100" id="comp-'+data.idPrefix+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"><p><input type="text"  id="'+data.idPrefix+'PickerInput" class="input--text js-datetime-picker" placeholder="YYYY-MM-DD HH:mm:ss"><button id="'+data.idPrefix+'PickerButton" class="input--button"><img src="'+getMeta('server_host')+'/static/client/img/datetime-local.svg'+'" /></button></p></div></div></div><div class="picker-container"></div>';
			case "image":
				return '<div class="bigbot_bot--bubble bigbot_imageBubble chat-text isCold isHidden" data-delay="1500" id="message-'+Math.random()+'"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text" style="padding: 0"><img src="'+data.src+'" alt="image" style="border-radius: 9px;display: block;height: auto;width: 100%"></div></div></div>';
			case "iframe":
				return '<div class="bigbot_bot--bubble bigbot_imageBubble chat-text isCold isHidden" data-delay="1500" id="message-'+Math.random()+'"><div class="bigbot_bot--body" style="max-width:'+Number(data.width+17)+'px"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text" style="padding: 0"><iframe src="'+data.src+'" width="'+Number(data.width+17)+'" height="'+Number(data.height + 17)+'" style="max-width: 320px;border: none;min-height: 100px;width: auto"></iframe></div></div></div>';
			case "list":
				var listContent = '';
				for(var i = 0;i < data.content.length;++i){
					listContent += '<li role="option" aria-selected="false" class="option delegateList" data-obj=\''+JSON.stringify(data.content[i])+'\' data-option-id="list-'+i+'" data-url=""><input type="hidden" class="itemHidden" value="'+data.content[i].body+'" /><div class="option--text"><p>'+data.content[i].body+'</p></div><div class="bigbot_listAvatar bigbot_icon--checkWrapper dark atLeft fast"><img src="'+data.content[i].image+'"></div></li>'
				}

				return '<div class="bigbot_panel--wrapper panel--multi isHidden isCold" data-delay="1500"  id="message-'+Math.random()+'"><div class="bigbot_panel--main"><div class="bigbot_panel--content"><div class="bigbot_panel--options"><div class="bigbot_panel--optionsInner"><div class="panel--arrow arrow--up"><span class="arrow"></span></div><ul role="listbox" class="bigbot_panel--options__list">'+listContent+'</ul><div class="panel--arrow arrow--down"><span class="arrow"></span></div></div></div></div></div></div>';

			case "auth_card":
				return '<div class="bigbot_bot--bubble bigbot_imageBubble chat-text isCold isHidden" data-delay="1500" id="message-'+Math.random()+'"><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text" style="padding: 0"><div class="authCardWrapper"><div class="authCardContent" ><h3><img src="'+data.data.icon+'" /> '+data.data.title+'</h3><p>'+data.data.description+'</p><button data-url="'+data.data.data+'" id="'+data.idPrefix+'authenticateBtn"><svg width="10px" focusable="false" data-prefix="fas" data-icon="key" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" class="svg-inline--fa fa-key fa-w-16 fa-2x"><path fill="#ffffff" d="M512 176.001C512 273.203 433.202 352 336 352c-11.22 0-22.19-1.062-32.827-3.069l-24.012 27.014A23.999 23.999 0 0 1 261.223 384H224v40c0 13.255-10.745 24-24 24h-40v40c0 13.255-10.745 24-24 24H24c-13.255 0-24-10.745-24-24v-78.059c0-6.365 2.529-12.47 7.029-16.971l161.802-161.802C163.108 213.814 160 195.271 160 176 160 78.798 238.797.001 335.999 0 433.488-.001 512 78.511 512 176.001zM336 128c0 26.51 21.49 48 48 48s48-21.49 48-48-21.49-48-48-48-48 21.49-48 48z" class=""></path></svg> Authenticate</button></div></div></div></div></div>';

			case "specialButtons":
				var buttons = '<div class="botButtons specialBtns">';
				for(var i = 0; i< data.data.length;++i){
					buttons += '<a data-obj=\''+JSON.stringify(data.data[i])+'\' class="specialButton botBtnLink '+data.data[i].className+'">'+data.data[i].body+'</a>';
				}
				buttons += '</div>';
				return buttons;
			default:
				return '';

		}
	}

	/* getUIComponents function ends here */
	function getUIFunction(type,params){
		switch (type) {
			case "date":
				loadJS(getMeta("server_host")+"/static/client/js/picker.js","");
				setTimeout(function () {
					var some = document.querySelectorAll('.js-date-picker');
					forEach(some, function (value, index, obj) {
						new Picker(value, {
							controls:true,
							format: 'YYYY-MM-DD',
							headers: true,
							container: '.picker-container',
							text: {
								title: 'Pick a Date',
							},
						});
					});
					document.getElementById(params.idPrefix+'PickerButton').addEventListener('click',function () {
						var element = document.getElementById(params.idPrefix+'PickerInput');
						triggerUserMessages(element,'date',element.value,false);
					});
				},1000);
				break;
			case "duration":
				loadJS(getMeta("server_host")+"/static/client/js/picker.js","");
				setTimeout(function () {
					var some = document.querySelectorAll('.js-time-picker');
					forEach(some, function (value, index, obj) {

						new Picker(value, {
							controls:true,
							format: 'HH:mm',
							headers: true,
							container: '.picker-container',
							text: {
								title: 'Pick a time',
							},
						});
					});



					document.getElementById(params.idPrefix+'PickerButton').addEventListener('click',function () {
						var element = document.getElementById(params.idPrefix+'PickerInput');
						var timeValue = element.value.split(':');
						var value = [parseInt(timeValue[0]),parseInt(timeValue[1])];
						triggerUserMessages(element,'duration',value,false);
					});
				},1000);
				break;
			case "datetime":
				loadJS(getMeta("server_host")+"/static/client/js/picker.js","");
				setTimeout(function () {
					new Picker(document.querySelector('.js-datetime-picker'), {
						controls:true,
						format: 'YYYY-MM-DD HH:mm:ss',
						headers: true,
						container: '.picker-container',
						text: {
							title: 'Select a Date & Time',
						},
					});
					document.getElementById(params.idPrefix+'PickerButton').addEventListener('click',function () {
						var element = document.getElementById(params.idPrefix+'PickerInput');
						triggerUserMessages(element,'datetime',element.value,false);
					});
				},1000);
				break;
			case "list":
				document.querySelectorAll('.delegateList').forEach(item => {
					item.addEventListener('click', event => {
						var obj = JSON.parse(item.getAttribute('data-obj'));
						var sss = item.childNodes.cl
						var itemChild = null;
						for (var i = 0; i < item.childNodes.length; i++) {
							if (item.childNodes[i].className == "itemHidden") {
								itemChild = item.childNodes[i];
								break;
							}
						}

						//console.log("OBJ - ",itemChild);
						//var idValue = parseInt( item.id.split('suggest-')[1]);
						//console.log("DATA OBJECT -",dataObj[idValue]);
						triggerUserMessages(itemChild,"action",obj.value,obj,true);

						//document.getElementById('suggestionBtn').innerHTML = "";
						//document.getElementById('bigBotInput').value = "";

					});
				});



				break;
			case "auth_card":
				var btn = document.getElementById(params.idPrefix+'authenticateBtn');
				var url = btn.getAttribute("data-url");
				btn.onclick = () => {
					var myWindow = window.open(url, '_blank',
						'location=yes,height=370,width=520,scrollbars=yes,status=yes');
				};
				break;
			case "specialButtons":
				document.querySelectorAll('.specialButton').forEach(item => {
					item.addEventListener('click', event => {
						var obj = JSON.parse(item.getAttribute('data-obj'));

						console.log("OBJ - ",obj);
						//var idValue = parseInt( item.id.split('suggest-')[1]);
						//console.log("DATA OBJECT -",dataObj[idValue]);
						triggerUserMessages(obj.body,"action",[],obj,true);
						document.getElementsByClassName('specialBtns')[0].remove();

						//document.getElementById('suggestionBtn').innerHTML = "";
						//document.getElementById('bigBotInput').value = "";

					});
				});
				break;
			case "inlineButtons":
		console.log('BUTTONS - - - - ',params);
				document.querySelectorAll('.inlineBtn-'+params.idPrefix).forEach(item => {
					item.addEventListener('click', event => {
						var obj = JSON.parse(item.getAttribute('data-obj'));

						console.log("OBJ - ",obj);
						//var idValue = parseInt( item.id.split('suggest-')[1]);
						//console.log("DATA OBJECT -",dataObj[idValue]);
						triggerUserMessages(obj.body,"action",[],obj,true);
						//document.getElementsByClassName('specialBtns')[0].remove();

						//document.getElementById('suggestionBtn').innerHTML = "";
						//document.getElementById('bigBotInput').value = "";

					});
				});
				break;
			default:
				return '';

		}


	}
	/* getDatePicker function starts here */

	function getInputPicker (type,data=''){
		var idPrefix = Math.random();
		var tmplHtml = '<% for(var index in this.templateSrc){%><%this.templateSrc[index]%> <%}%>';
		// var template = templateRender(tmplHtml, {
		// 	templateSrc:{
		// 		"A" :getTemplateByName('botInputBubble',{'src':'http://'+getMeta('server_host')+'/static/bigbot/img/'+type+'.svg','type':type,'delay':100,'hiddenClass':'isHidden'}),
		// 	}
		// });

		var template = templateRender(tmplHtml, {

			templateSrc:{
				"A" :getUIComponents(type,{'idPrefix':idPrefix,'src':getMeta('server_host')+'/static/bigbot/img/'+type+'.svg',data:data,content:data.content,src:data.src,width:data.width,height:data.height}),
			}
		});

		//var list = document.getElementById("bigBotChatLast");
		var list = document.getElementById("bigbot_typingIndicator2");
		list.insertAdjacentHTML('beforebegin', template);
		scrollFunct('bigbot_bigBotChat',500);
		setTimeout(function () { loadBotMessages();
			getUIFunction(type,{'idPrefix':idPrefix});

		},500);
	}

	/* getDatePicker function ends here */

	/* getTimePicker function starts here */

	function getTimePicker(){
		var tmplHtml = '<% for(var index in this.templateSrc){%><%this.templateSrc[index]%> <%}%>';
		var template = templateRender(tmplHtml, {
			templateSrc:{
				"A" :getTemplateByName('botTimeBubble',{'body':'Hello!','delay':1000,'hiddenClass':'isHidden'}),
			}
		});
		var list = document.getElementById("bigbot_bigBotChatLast");
		list.insertAdjacentHTML('beforebegin', template);
		scrollFunct('bigbot_bigBotChat',500);
		setTimeout(function () { loadBotMessages();
			setTimeout(function () {

				document.getElementById('timePickerButton').addEventListener('click',function () {
					triggerUserMessages(document.getElementById('timePickerInput'));

				});
			},500);
		},500);
	}

	/* getTimePicker function ends here */

	/* getWelcomeMessages() function starts here */

	function getWelcomeMessages() {
		var tmplHtml = '<% for(var index in this.templateSrc){%><%this.templateSrc[index]%> <%}%>';
		var template = templateRender(tmplHtml, {
			templateSrc:{
				"A" :getTemplateByName('botBubble',{'body':'Hello!','delay':1000,'hiddenClass':'isHidden'}),
				"B" :getTemplateByName('botImageBubble',{
					'body':'https://bigbot-static-public.s3-ap-southeast-1.amazonaws.com/GIFs/hello_06.gif','delay':3000,'hiddenClass':'isHidden'}),
				"D" :getTemplateByName('botBubble',{'body':'How may I help you?','delay':5000,'hiddenClass':'isHidden'})
			}
		});
		var list = document.getElementById("bigbot_typingIndicator2");
		//var list = document.getElementById("bigBotChatLast");
		list.insertAdjacentHTML('beforebegin', template);
		scrollFunct('bigbot_bigBotChat',500);
		setTimeout(function () { loadBotMessages();
		},100);
	}

	/* getWelcomeMessages() function ends here */

	/* triggerUserMessage function starts here */
	function  triggerUserMessages(element,type='text',value,data=[],silent=false) {
		var inputElement = element;
		var inputValue;
		if( typeof inputElement == 'object'){
			inputValue = inputElement.value;
		}else{
			inputValue = inputElement;
		}

		if(inputValue == "" || inputValue == " "){
			alert('Please enter something');
		}else{

			bigChat.sendMessage(type,inputValue,value,data);
			// var tmplHtml = '<%this.templateSrc.A%>';
			// var template = templateRender(tmplHtml, {
			// 	templateSrc:{
			// 		"A" :getTemplateByName('answerBubble',{'body':inputValue,'delay':100,'hiddenClass':''})
			// 	}
			// });
			// inputValue = '';
			// if( typeof inputElement == 'object') {
			// 	if(inputElement.closest('.isComplete')) {
			// 		inputElement.closest('.isComplete').remove();
			// 	}
			// }else{
			//
			// }
			//
			//
			// //var list = document.getElementById("bigBotChatLast");
			// var list = document.getElementById("bigbot_typingIndicator2");
			// list.insertAdjacentHTML('beforebegin', template);
			scrollFunct('bigbot_bigBotChat',500);
			setTimeout(function () { loadBotMessages();
				setTimeout(function () {
					scrollFunct('bigbot_bigBotChat',500);
				},1000);
			},100);
		}
	}
	/* triggerUserMessage function ends here */

	/* triggerBotMessages starts here */
	function triggerBotMessages(message,buttons="",delay=100,outgoing=false) {
		var body = message.statement.text;
		var tmplHtml = '<% if(this.outgoing == false){ %><%this.templateSrc.A%><%; }else{ if(this.attachments.length >0){ %><%this.templateSrc.C%><%; }else{ %><%this.templateSrc.B%><%;}}%>';

		var template = templateRender(tmplHtml, {
			outgoing:outgoing,
			attachments:message.attachments,
			templateSrc:{
				"A" :getTemplateByName('botBubbleWithButtons',{'avatar':message.avatar,'body':body,'id':message.id,'delay':delay,'hiddenClass':'','buttons':buttons,'data':message}),
				"B" :getTemplateByName('answerBubble',{'body':body,'delay':100,'hiddenClass':''}),
				"C":getTemplateByName('attachmentBubble',{'data':message.attachments})
			}
		});



		//var list = document.getElementById("bigBotChatLast");
		var list = document.getElementById("bigbot_typingIndicator2");
		if(list == null)
			return;
		list.insertAdjacentHTML('beforebegin', template);

		scrollFunct('bigbot_bigBotChat',500);

		setTimeout(function () { loadBotMessages();
		if(buttons.length > 0){
			getUIFunction("inlineButtons",{'idPrefix':message.id});

		}
		if(outgoing == false){
			delegateSwitch('avatar-'+message.id,message);
		}


		},100);
	}
	/* triggerBotMessages ends here */

	/* typingIndicator function starts here */

	function typingIndicator(istyping) {
		var typingIndicator = document.getElementById('bigbot_typingIndicator2');
		if (istyping) {

			typingIndicator.style.display = 'block';
			scrollFunct('bigbot_bigBotChat',500);

		}else {
			typingIndicator.style.display = 'none';
		}
	}

	/* typingIndicator function ends here */

	/* getSuggestions function starts here */
	function getSuggestions(data){
		//var funct = this.greet();
		var buttonContent = '';
		for(var i=0;i< data.length;++i){
			buttonContent += '<button id="suggest-'+i+'" class="suggest" value="'+data[i].body+'">'+data[i].body+'</button>';

		}
		return buttonContent;
	}
	/* getSuggestions function ends here */

	function sendSuggestion(element,type='action') {
		triggerUserMessages(element,type);
	}

	/* inputEvent starts here */
	function inputEvent(selc){
		var inputElement = document.getElementById('input-'+selc);
		document.getElementById('button-'+selc).addEventListener('click',function () {
			if(inputElement.value == "" || inputElement.value == " "){
				alert('Please enter something');
			}else{
				bigChat.sendMessage('text',inputElement.value,inputElement.value);
				var newItem = document.createElement("div");
				newItem.className = "answer--bubble by--user default isHidden isCold";
				newItem.id = "some-button-"+selc;
				newItem.setAttribute("data-delay",100);
				newItem.innerHTML = '<div class="answer-body__wrapper"><div class="answer--body update">'+inputElement.value+'</div><button type="button" aria-label="Redo" class="icon--redoWrapper"><div class="redo"></div></button></div>';
				var list = document.getElementById("bigbot_bigBotChatLast");
				document.getElementById('bigbot_bigBotChat').insertBefore(newItem, list);
				setTimeout(function () { loadBotMessages(); },100);
			}
		});
	}

	/* inputEvent ends here */

	/* speechToText function starts here */
	function speechToText(){
		window.SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
		let finalTranscript = '';
		let recognition = new window.SpeechRecognition();
		let inputElement = document.querySelector('#bigBotInput');
		recognition.interimResults = false;
		recognition.maxAlternatives = 10;
		recognition.continuous = false;

		recognition.onstart = (event)=> {
			document.querySelector('.waveWrapper').style.display = 'block';
			console.log('Listening');
		}
		recognition.onresult = (event) => {

			let interimTranscript = '';
			for (let i = event.resultIndex, len = event.results.length; i < len; i++) {
				let transcript = event.results[i][0].transcript;
				if (event.results[i].isFinal) {
					finalTranscript += transcript;
				} else {
					interimTranscript += transcript;
				}
			}

			inputElement.value = finalTranscript + interimTranscript;
		}
		recognition.start();
		recognition.onspeechend = (event) =>{
			console.log('speech end');
		}
		recognition.onend= (event) =>{
			document.querySelector('.waveWrapper').style.display = 'none';
			console.log('On End');
			recognition.stop();
			setTimeout(function () {
				if(inputElement.value.length >0 && inputElement.value != ' '){
					document.querySelector('#bigbot_bigBotButton').click();
				}

			}, 1000);

		}
		recognition.onsoundend = (event) => {
			document.querySelector('.waveWrapper').style.display = 'none';
			console.log('Speech End');
			recognition.stop();
			setTimeout(function () {
				if(inputElement.value.length >0 && inputElement.value != ' '){
					document.querySelector('#bigbot_bigBotButton').click();
				}

			}, 1000);

		}


	}

	/* speechToText function ends here */

	/* textToSpeechWithAWSPolly function starts here */
	function textToSpeechWithAWSPolly(text) {
		var awsRegion,awsPoolId;

		loadCredentials(getMeta('server_host')+"/api/misc/credential/", function(text2){
			var data = JSON.parse(text2);
			awsRegion = data[0].data.region;
			awsPoolId = data[0].data.IdentityPoolId;


			AWS.config.region = awsRegion;
			AWS.config.credentials = new AWS.CognitoIdentityCredentials({IdentityPoolId: awsPoolId});
			var speechParams = {
				OutputFormat: "mp3",
				SampleRate: "16000",
				Text: text,
				TextType: "text",
				VoiceId: "Matthew"
			};
			var polly = new AWS.Polly({apiVersion: '2016-06-10'});
			var signer = new AWS.Polly.Presigner(speechParams, polly);
			signer.getSynthesizeSpeechUrl(speechParams, function(error, url) {
				if (!error) {
					document.getElementById('audioPlayback').load();
					document.getElementById('audioSource').src = url;
					document.getElementById('audioPlayback').play();
				} else {
					setTimeout(function () {
						textToSpeech(text);
					},1000);
					console.log(error);
				}
			});
		});
	}
	/* textToSpeechWithAWSPolly function ends here */

	/* textToSpeechFunction starts here*/
	function textToSpeech(text) {

		var available_voices = window.speechSynthesis.getVoices();
		var english_voice = '';
		for(var i=0; i<available_voices.length; i++) {
			if(available_voices[i].lang === 'en-US') {
				english_voice = available_voices[i];
				break;
			}
		}
		if(english_voice === '')
			english_voice = available_voices[0];
		var utter = new SpeechSynthesisUtterance();
		utter.rate = 1;
		utter.pitch = 0.5;
		utter.volume = 1.0;
		utter.text = text;
		utter.voice = english_voice;
		utter.onend = function() {
			//	alert('Speech has finished');
		}
		window.speechSynthesis.speak(utter);
	}
	/* textToSpeechFunction ends here*/

	/* getSpeechStatus function starts here */
	// function getSpeechStatus(){
	// 	var ele = document.getElementsByName('speechVolume');
	// 	for(i = 0; i < ele.length; i++) {
	// 		if(ele[i].checked)
	// 			return ele[i].getAttribute('id');
	// 	}
	//
	// }
	//
	function getSpeechStatus(){
		var ele = document.querySelector('.speechBtn');
		if(ele.checked) {
			return 'no';
		} else {
			return 'yes';
		}
	}
	/* getSpeechStatus function ends here */

	/* New Slider Function starts here */

	function slide(items) {
		var posX1 = 0,
			posX2 = 0,
			posInitial,
			posFinal,
			slides = items.getElementsByClassName('suggest'),
			slidesLength = slides.length,
			slideSize = items.getElementsByClassName('suggest')[0].offsetWidth,
			firstSlide = slides[0],
			lastSlide = slides[slidesLength - 1];

		var elem = document,
			info = document.getElementById('info'),
			marker = true,
			delta,
			direction,
			interval = 50,
			counter1 = 0,
			counter2,
			counter3,
			counter4;

		// Mouse events
		items.onmousedown = dragStartN;

		// Wheel events

		items.addEventListener('wheel',wheel);

		// Touch events
		items.addEventListener('touchstart', dragStartN);
		items.addEventListener('touchend', dragEndN);
		items.addEventListener('touchmove', dragActionN);


		function dragStartN (e) {
			e = e || window.event;
			//e.preventDefault();
			posInitial = items.offsetLeft;

			if (e.type == 'touchstart') {
				posX1 = e.touches[0].clientX;
			} else {
				posX1 = e.clientX;
				document.onmouseup = dragEndN;
				document.onmousemove = dragActionN;
			}
		}

		function dragActionN (e) {
			e = e || window.event;

			if (e.type == 'touchmove') {
				posX2 = posX1 - e.touches[0].clientX;
				posX1 = e.touches[0].clientX;
			} else{
				posX2 = posX1 - e.clientX;
				posX1 = e.clientX;
				//console.log('POSX1 - ',posX1);
			}
			var lastItem = document.querySelectorAll(".suggest:nth-last-child(1)")[0];
			var lastChild = document.getElementsByClassName('suggest');
			if(lastChild.length>=3) {
				lastItem = document.querySelectorAll(".suggest:nth-last-child(3)")[0];
			}

			var buttonLeftOffset = items.offsetLeft - posX2;
			var min = 0;

			var a = document.querySelector('#bigbot_suggestionBtn').offsetWidth;
			var b = document.querySelector('.bigbot_suggestionBtnWrapper').offsetWidth;
			var max = -(a - b + 10);
			if(buttonLeftOffset <= min && buttonLeftOffset > max){
				items.style.left = (buttonLeftOffset) + "px";
				console.log(max);
			}
			console.log(items.offsetWidth +" - "+ lastItem.offsetLeft);
		}

		function dragEndN (e) {
			posFinal = items.offsetLeft;
			i = items.offsetLeft;
			document.onmouseup = null;
			document.onmousemove = null;
		}

		var i = 0;

		function wheel(e){
			var min = 0;
			var a = document.querySelector('#bigbot_suggestionBtn').offsetWidth;
			var b = document.querySelector('.bigbot_suggestionBtnWrapper').offsetWidth;
			var max = -(a - b + 10);
			counter1 += 1;
			delta = e.deltaY;
				if (delta > 0) {
					direction = 'up';
					i = Number(i) + Number(10);
					if(i <= min && i > max){
						items.style.left = i + "px";
					}
				} else {
					direction = 'down';
					i = Number(i) - Number(10);
					if(i <= min && i > max){
						items.style.left = i + "px";
					}
				}
			if (marker) {
				wheelStart(e);
			}
			return false;
		}

		function wheelStart(e){
			marker = false;
			wheelAct(e);
			counter3 = new Date();
			console.log('Start event. Direction: ' + direction);
		}

		function wheelAct(e){
			var event = e;
			counter2 = counter1;
			setTimeout(function(){
				if (counter2 == counter1) {
					wheelEnd(event);
				} else {
					wheelAct(event);
				}
			},interval);
		}
		function wheelEnd(e){
			counter4 = new Date();
			console.log('End event. Duration: ' + (counter4-counter3) + ' ms');
			marker = true;
			counter1 = 0;
			counter2 = false;
			counter3 = false;
			counter4 = false;
			i = items.offsetLeft;
			posFinal = items.offsetLeft;
		}



	}


	/* New Slider Function Ends here */

	/* slider function starts here */

	// function slide(items) {
	// 	var posX1 = 0,
	// 		posX2 = 0,
	// 		posInitial,
	// 		posFinal,
	// 		threshold = 100,
	// 		slides = items.getElementsByClassName('suggest'),
	// 		slidesLength = slides.length,
	// 		slideSize = items.getElementsByClassName('suggest')[0].offsetWidth,
	// 		firstSlide = slides[0],
	// 		lastSlide = slides[slidesLength - 1],
	// 		cloneFirst = firstSlide.cloneNode(true),
	// 		cloneLast = lastSlide.cloneNode(true),
	// 		index = 0,
	// 		allowShift = true;
	//
	// 	// Clone first and last slide
	// 	//items.appendChild(cloneFirst);
	// 	//items.insertBefore(cloneLast, firstSlide);
	// 	//	wrapper.classList.add('loaded');
	//
	// 	// Mouse events
	// 	items.onmousedown = dragStartN;
	//
	// 	// Touch events
	// 	items.addEventListener('touchstart', dragStartN);
	// 	items.addEventListener('touchend', dragEndN);
	// 	items.addEventListener('touchmove', dragActionN);
	//
	//
	// 	// Click events
	// 	//prev.addEventListener('click', function () { shiftSlide(-1) });
	// 	//next.addEventListener('click', function () { shiftSlide(1) });
	//
	// 	// Transition events
	// 	items.addEventListener('transitionend', checkIndex);
	//
	// 	function dragStartN (e) {
	// 		e = e || window.event;
	// 		//e.preventDefault();
	// 		posInitial = items.offsetLeft;
	//
	// 		if (e.type == 'touchstart') {
	// 			posX1 = e.touches[0].clientX;
	// 		} else {
	// 			posX1 = e.clientX;
	// 			document.onmouseup = dragEndN;
	// 			document.onmousemove = dragActionN;
	// 		}
	// 	}
	//
	// 	function dragActionN (e) {
	// 		e = e || window.event;
	//
	// 		if (e.type == 'touchmove') {
	// 			posX2 = posX1 - e.touches[0].clientX;
	// 			posX1 = e.touches[0].clientX;
	// 		} else {
	// 			posX2 = posX1 - e.clientX;
	// 			posX1 = e.clientX;
	// 		}
	// 		var lastItem = document.querySelectorAll(".suggest:nth-last-child(1)")[0];
	// 		var lastChild = document.getElementsByClassName('suggest');
	// 		if(lastChild.length>=3) {
	// 			lastItem = document.querySelectorAll(".suggest:nth-last-child(3)")[0];
	// 		}
	//
	// 		var buttonLeftOffset = items.offsetLeft - posX2;
	// 		var min = 0;
	// 		//var max = -(items.offsetWidth - lastItem.offsetLeft);
	// 		//var max = -(lastItem.offsetLeft);
	// 		var a = document.querySelector('#bigbot_suggestionBtn').offsetWidth;
	// 		var b = document.querySelector('.bigbot_suggestionBtnWrapper').offsetWidth;
	// 		var max = -(a - b + 10);
	// 		if(buttonLeftOffset <= min && buttonLeftOffset > max){
	// 			items.style.left = (buttonLeftOffset) + "px";
	// 			console.log(max);
	// 		}
	// 		console.log(items.offsetWidth+" - "+lastItem.offsetLeft);
	// 	}
	//
	// 	function dragEndN (e) {
	// 		posFinal = items.offsetLeft;
	// 		if (posFinal - posInitial < -threshold) {
	// 			shiftSlide(1, 'drag');
	// 		} else if (posFinal - posInitial > threshold) {
	// 			shiftSlide(-1, 'drag');
	// 		} else {
	// 			//	items.style.left = (posInitial) + "px";
	// 		}
	//
	// 		document.onmouseup = null;
	// 		document.onmousemove = null;
	// 	}
	//
	// 	function shiftSlide(dir, action) {
	// 		items.classList.add('shifting');
	//
	// 		if (allowShift) {
	// 			if (!action) { posInitial = items.offsetLeft; }
	//
	// 			if (dir == 1) {
	// 				items.style.left = (posInitial - slideSize) + "px";
	// 				index++;
	// 			} else if (dir == -1) {
	// 				items.style.left = (posInitial + slideSize) + "px";
	// 				index--;
	// 			}
	// 		};
	//
	// 		allowShift = false;
	// 	}
	//
	// 	function checkIndex (){
	// 		items.classList.remove('shifting');
	//
	// 		if (index == -1) {
	// 			items.style.left = -(slidesLength * slideSize) + "px";
	// 			index = slidesLength - 1;
	// 		}
	//
	// 		if (index == slidesLength) {
	// 			items.style.left = -(1 * slideSize) + "px";
	// 			index = 0;
	// 		}
	//
	// 		allowShift = true;
	// 	}
	// }
	/* slider function ends here */

	/* loadBotMessages starts here */
	function loadBotMessages(){

		var delay=0;var element;
		var botMessage = document.getElementsByClassName('isCold');
		forEach(botMessage, function (value, index, obj) {
			element = botMessage[index];
			var id = element.getAttribute("id");
			var elementId = document.getElementById(id);
			delay = parseInt(element.getAttribute('data-delay'));
			if(!hasClass(element,"isComplete") && hasClass(element,"isHidden")) {
				setTimeout(function () {
					elementId.classList.remove('isHidden');
					scrollFunct('bigbot_bigBotChat',1000);
					setTimeout(function () {
						elementId.classList.add("isComplete");
						scrollFunct('bigbot_bigBotChat',1000);
						if(elementId.getAttribute("data-function")!= null){
							eval(elementId.getAttribute("data-function"));
						}else{
						}
					},1000);
				},delay);

			}else{
				setTimeout(function () {
					elementId.classList.add("isComplete");
				},100);
			}
		});
		var a = document.getElementsByClassName('isComplete');
		for(var i = 0;i<a.length;++i){
			var p = document.getElementsByClassName('isComplete')[i];
			p.classList.remove('isCold');
		}
	}
	/* loadBotMessages ends here */

	/* loadCredentials function starts here */

	function loadCredentials(file, callback) {

		var rawFile = new XMLHttpRequest();
		rawFile.overrideMimeType("application/json");
		rawFile.open("GET", file, true);
		rawFile.onreadystatechange = function() {
			if (rawFile.readyState === 4 && rawFile.status == "200") {
				callback(rawFile.responseText);
			}
		}
		rawFile.send(null);
	}


	/* loadCredentials function ends here */

	/* loadJS function starts here */
	function loadJS(file,id) {
		var jsElm = document.createElement("script");
		jsElm.id = id;
		//	jsElm.type = "application/javascript";
		jsElm.src = file;
		document.body.appendChild(jsElm);
	}
	/* loadJS function ends here */

	/* loadCSS function starts here */
	function loadCSS(file,id) {
		var cssElm = document.createElement("link");
		cssElm.id = id;
		cssElm.rel = "stylesheet";
		cssElm.href = file;
		document.head.appendChild(cssElm);
	}
	/* loadCSS function ends here */

	/* removeJS function starts here */
	function removeJS(id){
		var script = document.getElementById(id);
		script.remove();
	}
	/* removeJS function ends here */

	/* Buildout Method starts here */

	function buildOut() {
		var docFrag;
		var checked = '';
		var xLeft = window.innerWidth - 84;
		var yTop = -window.innerHeight + 150 ;
		var position = '';
		var positionClass = '';
		switch (this.options.widgetPosition) {
			case "TopRight":
				position = 'transform:translate3d(0px, '+yTop+'px, 0px) scaleX(1) scaleY(1) !important';
				this.initialY = -window.innerHeight + 150;
				this.yOffset = -window.innerHeight + 150;
				positionClass = "rightBot";
				break;
			case "TopLeft":
				position = 'transform:translate3d(-'+xLeft+'px, '+yTop+'px, 0px) scaleX(-1) scaleY(1) !important';
				this.initialX = -window.innerWidth + 68;
				this.xOffset = -window.innerWidth + 68;
				this.initialY = -window.innerHeight + 150;
				this.yOffset = -window.innerHeight + 150;
				positionClass = "leftBot";
				break;
			case "BottomLeft":
				position = 'transform:translate3d(-'+xLeft+'px, 0px, 0px) scaleX(-1) scaleY(1) !important';
				this.initialX = -window.innerWidth + 68;
				this.xOffset = -window.innerWidth + 68;
				positionClass = "leftBot";
				break;
			case "BottomRight":
			default:
				position = 'transform:translate3d(0px, 0px, 0px) scaleX(1) scaleY(1) !important';
				positionClass = "rightBot";
				break;
		}

		if(this.options.speechEnabled == false){ checked = 'checked'}else{
			if(this.options.speechToTextWith == 'aws'){
				loadJS("https://sdk.amazonaws.com/js/aws-sdk-2.410.0.min.js","awsPolly");
			}
		}
		// var rootStyle = document.createElement("style");
		// rootStyle.innerText = ":root {--theme-color: "+this.options.themeColor+"; }";
		// document.head.appendChild(rootStyle);
		// this.stylesheet = document.createElement("link");
		// this.stylesheet.rel = "stylesheet";
		// this.stylesheet.href = getMeta('server_host')+"/static/bigbot/bigbot.css";
		// document.head.appendChild(this.stylesheet);
		this.fontStyle = document.createElement("link");
		this.fontStyle.rel = "stylesheet";
		this.fontStyle.href = "https://fonts.googleapis.com/css2?family=Open+Sans&display=swap";
		document.head.appendChild(this.fontStyle);
		var dropZ = document.createElement("link");
		dropZ.rel = "stylesheet";
		dropZ.href = "https://cdnjs.cloudflare.com/ajax/libs/dropzone/4.3.0/dropzone.css";
		document.head.appendChild(dropZ);
		loadJS("https://cdnjs.cloudflare.com/ajax/libs/dropzone/4.3.0/dropzone.js","drop");

		docFrag = document.createDocumentFragment();
		this.botWidget = document.createElement("div");
		this.botWidget.id = "botbutton";
		this.botWidget.className = "bigbotWidgetButton show hoverModeOn "+positionClass;
		this.botWidget.style.cssText = position;
		this.botWidgetPopup = document.createElement('div');
		this.botWidgetPopup.id = "bigbotWidgetPopup";
		this.botWidgetPopup.className = "bigbotWidgetPopup";
		this.botWidgetPopup.innerHTML = '<button class="bigbotWidgetPopup--button" id="bigbotPopupButton">Talk with Big Bot</button><a class="brandingLabel" href="https://abigbot.com?utm_source=bb_chat_widget" target="_blank" rel="noopener noreferrer">Create your own Bigbot</a>';
		this.botWidget.appendChild(this.botWidgetPopup);
		this.bigBotWrapper = document.createElement("div");
		this.bigBotWrapper.className = "bigbot_bigBotWrapper "+this.options.chatPosition;
		this.bigBotWrapper.innerHTML = '<input name="fileToUpload" type="file" id="file-input" multiple />\n' +
			'\t<div id="bigbot_bigBotChat" class="bigbot_bigBotChat"><div style="width: 100%;height: 150px"></div><div id="bigbot_typingIndicator2" class="bigbot_bot--bubble chat-text" data-delay="100"><div class="bigbot_bot--avatar"></div><div class="bigbot_bot--body"><div class="bigbot_bot--loading"><div class="bigbot_loading--dots"><div class="bigbot_dot bigbot_dot--a"></div><div class="bigbot_dot bigbot_dot--b"></div><div class="bigbot_dot bigbot_dot--c"></div></div></div><div class="bigbot_bot--text"> </div></div></div><div id="bigbot_bigBotChatLast" class="bigbot_bigBotChatLast" style="width: 100%;height: 174px"></div></div><div class="dropzone bigbot_fileAttach" id="dropzone"><span id="bigbot_fileClose" class="bigbot_fileClose">x</span></span><div class="dz-default dz-message"><p><svg width="64" height="64" focusable="false" data-prefix="fad" data-icon="photo-video" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512" class="svg-inline--fa fa-photo-video fa-w-20 fa-7x"><g class="fa-group"><path fill="currentColor" d="M608 0H160a32 32 0 0 0-32 32v96h160V64h192v320h128a32 32 0 0 0 32-32V32a32 32 0 0 0-32-32zM232 103a9 9 0 0 1-9 9h-30a9 9 0 0 1-9-9V73a9 9 0 0 1 9-9h30a9 9 0 0 1 9 9zm352 208a9 9 0 0 1-9 9h-30a9 9 0 0 1-9-9v-30a9 9 0 0 1 9-9h30a9 9 0 0 1 9 9zm0-104a9 9 0 0 1-9 9h-30a9 9 0 0 1-9-9v-30a9 9 0 0 1 9-9h30a9 9 0 0 1 9 9zm0-104a9 9 0 0 1-9 9h-30a9 9 0 0 1-9-9V73a9 9 0 0 1 9-9h30a9 9 0 0 1 9 9z" class="fa-secondary"></path><path fill="currentColor" opacity="0.8" d="M416 160H32a32 32 0 0 0-32 32v288a32 32 0 0 0 32 32h384a32 32 0 0 0 32-32V192a32 32 0 0 0-32-32zM96 224a32 32 0 1 1-32 32 32 32 0 0 1 32-32zm288 224H64v-32l64-64 32 32 128-128 96 96z" class="fa-primary"></path></g></svg></p><span>Drag & Drop files here to upload</span></div></div><footer id="footer--toolbar" class="show"><div id="toolbar--inner" class="with-poweredLabel show"><div class="bigbot_dropdown">\n' +
			'  <input type="checkbox" id="bigbot_dropdown">\n' +
			'\n' +
			'  <label class="bigbot_dropdown__face" for="bigbot_dropdown">\n' +
			'    <div class="bigbot_dropdown__arrow"></div>\n' +
			'  </label>\n' +
			'\n' +
			'  <ul class="bigbot_dropdown__items bigbot_nav"> <li class="bigbot_nav__head"> Messaging </li><li class="bigbot_nav__separator"></li><li class="bigbot_nav__item"> <a id="invite_chat_user" class="bigbot_nav__link"> <i class="bigbot_nav__link-icon fa fa-users"></i> <span class="bigbot_nav__link-text"> Chat Background</span><div class="bigbot_submenu"> <ul> <li><div class="button b2" id="bigbot_menu_switch">\n' +
			'          <label class="radioLabel" for="on_radio" id="on_label"><span>On</span></label>\n' +
			'        <input type="radio" name="bg" id="on_radio" value="on" class="menuRadio">\n' +
			'\n' +
			'          <label class="radioLabel" for="off_radio" id="off_label"><span>Off</span></label>\n' +
			'        <input type="radio" name="bg" id="off_radio" value="off" checked class="menuRadio" style="left: 25%;">\n' +
			'            <label class="radioLabel" for="focus_radio" id="focus_label"><span>OnHover</span></label>\n' +
			'        <input type="radio" name="bg" id="focus_radio" value="focus" class="menuRadio" style="left: 50%;width: 50%;">\n' +
			'        <div class="knobs">\n' +
			'          <span></span>\n' +
			'        </div>\n' +
			'        <div class="layer"></div>\n' +
			'      </div></li></ul> </div> </a> </li></ul>\n' +
			'</div><a id="powered--label" rel="noopener noreferrer" target="_blank" href="https://abigbot.com?utm_source=bb_chat_widget"><span class="powered--label__text">Create your own Bigbot</span></a><div class="button b2" id="button-18"><input '+checked+' type="checkbox" class="checkbox speechBtn"><div class="knobs"><span></span></div><div class="layer"></div></div><div id="close" title="Close"><button type="button" id="closeBigBot"><svg width="20px" height="20px" focusable="false" data-prefix="fas" data-icon="angle-right" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 512" class="svg-inline--fa fa-angle-right fa-w-8 fa-3x"><path fill="#ffffff" d="M224.3 273l-136 136c-9.4 9.4-24.6 9.4-33.9 0l-22.6-22.6c-9.4-9.4-9.4-24.6 0-33.9l96.4-96.4-96.4-96.4c-9.4-9.4-9.4-24.6 0-33.9L54.3 103c9.4-9.4 24.6-9.4 33.9 0l136 136c9.5 9.4 9.5 24.6.1 34z" class=""></path></svg></button></div></div></footer><div class="waveWrapper"><div class="loader"><svg id="wave" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 38.05"><title>Audio Wave</title><path id="Line_1" data-name="Line 1" d="M0.91,15L0.78,15A1,1,0,0,0,0,16v6a1,1,0,1,0,2,0s0,0,0,0V16a1,1,0,0,0-1-1H0.91Z"></path><path id="Line_2" data-name="Line 2" d="M6.91,9L6.78,9A1,1,0,0,0,6,10V28a1,1,0,1,0,2,0s0,0,0,0V10A1,1,0,0,0,7,9H6.91Z"></path><path id="Line_3" data-name="Line 3" d="M12.91,0L12.78,0A1,1,0,0,0,12,1V37a1,1,0,1,0,2,0s0,0,0,0V1a1,1,0,0,0-1-1H12.91Z"></path><path id="Line_4" data-name="Line 4" d="M18.91,10l-0.12,0A1,1,0,0,0,18,11V27a1,1,0,1,0,2,0s0,0,0,0V11a1,1,0,0,0-1-1H18.91Z"></path><path id="Line_5" data-name="Line 5" d="M24.91,15l-0.12,0A1,1,0,0,0,24,16v6a1,1,0,0,0,2,0s0,0,0,0V16a1,1,0,0,0-1-1H24.91Z"></path><path id="Line_6" data-name="Line 6" d="M30.91,10l-0.12,0A1,1,0,0,0,30,11V27a1,1,0,1,0,2,0s0,0,0,0V11a1,1,0,0,0-1-1H30.91Z"></path><path id="Line_7" data-name="Line 7" d="M36.91,0L36.78,0A1,1,0,0,0,36,1V37a1,1,0,1,0,2,0s0,0,0,0V1a1,1,0,0,0-1-1H36.91Z"></path><path id="Line_8" data-name="Line 8" d="M42.91,9L42.78,9A1,1,0,0,0,42,10V28a1,1,0,1,0,2,0s0,0,0,0V10a1,1,0,0,0-1-1H42.91Z"></path><path id="Line_9" data-name="Line 9" d="M48.91,15l-0.12,0A1,1,0,0,0,48,16v6a1,1,0,1,0,2,0s0,0,0,0V16a1,1,0,0,0-1-1H48.91Z"></path></svg><div class="listening"><div class="loading">Listening</div></div></div></div><div class="bigbot_suggestionBtnWrapper"><div id="bigbot_suggestionBtn" class="bigbot_suggestionBtn"><span class="suggest"></span></div></div><svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="800"><defs><filter id="goo"><feGaussianBlur in="SourceGraphic" stdDeviation="20" result="blur" /><feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -9" result="goo" /><feComposite in="SourceGraphic" in2="goo" /></filter></defs></svg><svg><filter id="goo2"><feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" /><feColorMatrix in="blur" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7" result="goo2" /><feBlend in="SourceGraphic" in2="goo2" /></filter></svg><div class="channelTab"><div><h5>Switch conversation</h5><p id="delegateContent"><span><img src="https://static.intercomassets.com/avatars/3356436/square_128/IMG_9774-1565898438.JPG?1565898438" width="52"></span><span><img src="https://static.intercomassets.com/avatars/3725384/square_128/IMG_5845-1579613391.jpg?1579613391" width="52"></span><span><img src="https://static.intercomassets.com/avatars/1336040/square_128/FullSizeRender-1503421137.jpg?1503421137" width="52"></span></p></div></div><a id="bigbot_emojiPicker"><svg width="24px" height="24px" focusable="false" data-prefix="far" data-icon="laugh" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 496 512" class="svg-inline--fa fa-laugh fa-w-16 fa-2x"><path fill="#757575" d="M248 8C111 8 0 119 0 256s111 248 248 248 248-111 248-248S385 8 248 8zm141.4 389.4c-37.8 37.8-88 58.6-141.4 58.6s-103.6-20.8-141.4-58.6S48 309.4 48 256s20.8-103.6 58.6-141.4S194.6 56 248 56s103.6 20.8 141.4 58.6S448 202.6 448 256s-20.8 103.6-58.6 141.4zM328 224c17.7 0 32-14.3 32-32s-14.3-32-32-32-32 14.3-32 32 14.3 32 32 32zm-160 0c17.7 0 32-14.3 32-32s-14.3-32-32-32-32 14.3-32 32 14.3 32 32 32zm194.4 64H133.6c-8.2 0-14.5 7-13.5 15 7.5 59.2 58.9 105 121.1 105h13.6c62.2 0 113.6-45.8 121.1-105 1-8-5.3-15-13.5-15z" class=""></path></svg></a>  <a id="bigbot_fileAttachment"><svg width="22px" height="22px" focusable="false" data-prefix="fas" data-icon="paperclip" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" class="svg-inline--fa fa-paperclip fa-w-14 fa-2x"><path fill="#757575" d="M43.246 466.142c-58.43-60.289-57.341-157.511 1.386-217.581L254.392 34c44.316-45.332 116.351-45.336 160.671 0 43.89 44.894 43.943 117.329 0 162.276L232.214 383.128c-29.855 30.537-78.633 30.111-107.982-.998-28.275-29.97-27.368-77.473 1.452-106.953l143.743-146.835c6.182-6.314 16.312-6.422 22.626-.241l22.861 22.379c6.315 6.182 6.422 16.312.241 22.626L171.427 319.927c-4.932 5.045-5.236 13.428-.648 18.292 4.372 4.634 11.245 4.711 15.688.165l182.849-186.851c19.613-20.062 19.613-52.725-.011-72.798-19.189-19.627-49.957-19.637-69.154 0L90.39 293.295c-34.763 35.56-35.299 93.12-1.191 128.313 34.01 35.093 88.985 35.137 123.058.286l172.06-175.999c6.177-6.319 16.307-6.433 22.626-.256l22.877 22.364c6.319 6.177 6.434 16.307.256 22.626l-172.06 175.998c-59.576 60.938-155.943 60.216-214.77-.485z" class=""></path></svg></a><div id="gooeyWrapper"><div id="gooeyWrapperAnswer"></div></div>';
		this.botInputText = document.createElement("div");
		this.botInputText.className = "bigbot_botInputText";
		this.botInputText.style.filter = "url(#goo)";
		this.botInputText.innerHTML = '<div id="emojiBubble" class="emojiBubble"><div id="emojiContent"></div></div> <input class="bigbot_inputText" id="bigBotInput" autocomplete="off" type="text" placeholder="Type a message"><button id="bigbot_bigBotButton" class="bigbot_inputButton"><svg xmlns="http://www.w3.org/2000/svg" class="svg-inline--fa fa-paper-plane fa-w-16" width="28" height="20" viewBox="0 0 352 512"><path fill="#757575" d="M476 3.2L12.5 270.6c-18.1 10.4-15.8 35.6 2.2 43.2L121 358.4l287.3-253.2c5.5-4.9 13.3 2.6 8.6 8.3L176 407v80.5c0 23.6 28.5 32.9 42.5 15.8L282 426l124.6 52.2c14.2 6 30.4-2.9 33-18.2l72-432C515 7.8 493.3-6.8 476 3.2z"></path></svg></button><button id="bigBotMic" class="bigbot_inputButton" style="text-align: center;"><svg xmlns="http://www.w3.org/2000/svg" version="1.1" id="Capa_1" fill="#757575" x="0px" y="0px" width="24" height="24" viewBox="0 0 352 512" class="svg-inline--fa fa-microphone fa-w-11 fa-7x"><path fill="#757575" d="M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z" class=""></path></svg></button>';

		this.audioInput = document.createElement("audio");
		this.audioInput.id = 'audioPlayback';
		this.audioInput.innerHTML = '<source id="audioSource" type="audio/mp3" src="">';
		//this.audioInput.style.display = 'none';
		this.bigBotWrapper.appendChild(this.audioInput);
		this.bigBotWrapper.appendChild(this.botInputText);

		docFrag.appendChild(this.botWidget);
		docFrag.appendChild(this.bigBotWrapper);

		document.body.appendChild(docFrag);

	}

	/* Buildout Method ends here */

	/****************************** PRIVATE METHODS ENDS *****************************************/

}());
var BigBot;
bigChat.onChannelReady = function(style, channel){
	console.error(style);
	BigBot = new BigBot(this,{snapToSides:true,speechEnabled:false,speechToTextWith:"aws",widgetPosition:"BottomRight",chatPosition:"right",
		themeColor:style.primary_color});
	BigBot.init();
};
bigChat.begin();