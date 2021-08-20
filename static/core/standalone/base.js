!function(a,b){"function"==typeof define&&define.amd?define([],b):"undefined"!=typeof module&&module.exports?module.exports=b():a.ReconnectingWebSocket=b()}(this,function(){function a(b,c,d){function l(a,b){var c=document.createEvent("CustomEvent");return c.initCustomEvent(a,!1,!1,b),c}var e={debug:!1,automaticOpen:!0,reconnectInterval:1e3,maxReconnectInterval:3e4,reconnectDecay:1.5,timeoutInterval:2e3};d||(d={});for(var f in e)this[f]="undefined"!=typeof d[f]?d[f]:e[f];this.url=b,this.reconnectAttempts=0,this.readyState=WebSocket.CONNECTING,this.protocol=null;var h,g=this,i=!1,j=!1,k=document.createElement("div");k.addEventListener("open",function(a){g.onopen(a)}),k.addEventListener("close",function(a){g.onclose(a)}),k.addEventListener("connecting",function(a){g.onconnecting(a)}),k.addEventListener("message",function(a){g.onmessage(a)}),k.addEventListener("error",function(a){g.onerror(a)}),this.addEventListener=k.addEventListener.bind(k),this.removeEventListener=k.removeEventListener.bind(k),this.dispatchEvent=k.dispatchEvent.bind(k),this.open=function(b){h=new WebSocket(g.url,c||[]),b||k.dispatchEvent(l("connecting")),(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","attempt-connect",g.url);var d=h,e=setTimeout(function(){(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","connection-timeout",g.url),j=!0,d.close(),j=!1},g.timeoutInterval);h.onopen=function(){clearTimeout(e),(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","onopen",g.url),g.protocol=h.protocol,g.readyState=WebSocket.OPEN,g.reconnectAttempts=0;var d=l("open");d.isReconnect=b,b=!1,k.dispatchEvent(d)},h.onclose=function(c){if(clearTimeout(e),h=null,i)g.readyState=WebSocket.CLOSED,k.dispatchEvent(l("close"));else{g.readyState=WebSocket.CONNECTING;var d=l("connecting");d.code=c.code,d.reason=c.reason,d.wasClean=c.wasClean,k.dispatchEvent(d),b||j||((g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","onclose",g.url),k.dispatchEvent(l("close")));var e=g.reconnectInterval*Math.pow(g.reconnectDecay,g.reconnectAttempts);setTimeout(function(){g.reconnectAttempts++,g.open(!0)},e>g.maxReconnectInterval?g.maxReconnectInterval:e)}},h.onmessage=function(b){(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","onmessage",g.url,b.data);var c=l("message");c.data=b.data,k.dispatchEvent(c)},h.onerror=function(b){(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","onerror",g.url,b),k.dispatchEvent(l("error"))}},1==this.automaticOpen&&this.open(!1),this.send=function(b){if(h)return(g.debug||a.debugAll)&&console.debug("ReconnectingWebSocket","send",g.url,b),h.send(b);throw"INVALID_STATE_ERR : Pausing to reconnect websocket"},this.close=function(a,b){"undefined"==typeof a&&(a=1e3),i=!0,h&&h.close(a,b)},this.refresh=function(){h&&h.close()}}return a.prototype.onopen=function(){},a.prototype.onclose=function(){},a.prototype.onconnecting=function(){},a.prototype.onmessage=function(){},a.prototype.onerror=function(){},a.debugAll=!1,a.CONNECTING=WebSocket.CONNECTING,a.OPEN=WebSocket.OPEN,a.CLOSING=WebSocket.CLOSING,a.CLOSED=WebSocket.CLOSED,a});

String.prototype.format_string = function () {
    let a = this;
    let b;
    for (b in arguments) {
        a = a.replace(/%[a-z]/, arguments[b]);
    }
    return a;
};

class BigUtil {
    static getUUID() {
        return (`${1e7}-${1e3}-${4e3}-${8e3}-${1e11}`).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    static popitup(url) {
        let newWindow =window.open(url,'Bigbot OAuth','height=200,width=150');
        if (window.focus) {
            newWindow.focus()
        }
        return false;
    }

    static dictToURI(dict) {
        const str = [];
        for (var p in dict)
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(dict[p]));
        return str.join("&");
    }

    static isEmpty(ob) {
        for (var i in ob) {
            return false;
        }
        return true;
    }

    static isEmptyDictionary(data){
        return Object.keys(data).length === 0;
    }

    static log(message) {
        console.log(message);
    }

    static error(message) {
        console.error(message);
    }

    static debug(title, message) {
        console.debug(title, message);
    }

    static warn(title, message) {
        console.warn(title, message);
    }

    static info(message) {
        console.info(message);
    }

    static getHttpHostAddress() {
        return 'http://192.168.1.6:8000';
        // return 'https://console.bigitsystems.com';
        //real
        const location = window.location;
        return location.protocol + '//' + location.host;
    }

    static getWSHostAddress() {
        return 'ws://192.168.1.49:8000';
        //return 'wss://console.bigitsystems.com';
        //real
        const location = window.location;
        let protocol = location.protocol == 'https:' ? 'wss://' : 'ws://';
        return protocol + location.host;
    }

    static getMetaContent(metaName) {
        const metas = document.getElementsByTagName('meta');
        for (let i = 0; i < metas.length; i++) {
            if (metas[i].getAttribute('name') === metaName) {
                return metas[i].getAttribute('content');
            }
        }
        return '';
    }

}

class Requests{

    constructor(host='') {
        this.host = host;
    }

    put(endpoint='', params = [], headers = {}, in_body = false) {
        return this.post(endpoint,params,headers,in_body,'PUT')
    }

    delete(endpoint='', params = [], headers = {}, in_body = false) {
        return this.post(endpoint,params,headers,in_body,'DELETE')
    }

    post(endpoint='', params = [], headers = {}, in_body = false, http_method = 'POST') {
        const self = this;
        return new Promise(function (resolve, reject) {
            const http = new XMLHttpRequest();
            const url = self.host+endpoint;
            http.open(http_method, url, true);
            http.onload = function () {
                if(http.status === 200){
                    //const contentType = http.getResponseHeader("Content-Type");
                    try {
                        resolve(JSON.parse(http.responseText));
                    }catch (e){
                        resolve(http.responseText);
                    }
                }else {
                    reject(http);
                }
            };
            http.onerror = function () {
                reject(http);
            };
            Object.keys(headers).forEach(function(key) {
                http.setRequestHeader(key, headers[key]);
            });
            if(in_body){
                http.setRequestHeader('Content-type', 'application/json');
                http.send(JSON.stringify(params))
            }else {
                http.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
                http.send(self.dictToURI(params));
            }
        });
    }

    get(endpoint='', params = [], headers = {}) {
        const self = this;
        return new Promise(function (resolve, reject) {
            const http = new XMLHttpRequest();
            const url = self.host+endpoint;
            http.open('GET', url, true);
            http.onload = function () {
                if(http.status === 200){
                    //const contentType = http.getResponseHeader("Content-Type");
                    try {
                        resolve(JSON.parse(http.responseText));
                    }catch (e){
                        resolve(http.responseText);
                    }
                }else {
                    reject(http);
                }
            };
            http.onerror = function () {
                reject(http);
            };
            Object.keys(headers).forEach(function(key) {
                http.setRequestHeader(key, headers[key]);
            });
            http.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            http.send(self.dictToURI(params));
        });
    }

    dictToURI(dict) {
        const str = [];
        for (var p in dict)
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(dict[p]));
        return str.join("&");
    }

}

class CookieManager {

    constructor() {
        this.prefix = '';
    }

    setCookie(cname, cvalue, days = 365) {
        var d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        document.cookie = this.prefix + cname + "=" + cvalue + ";" + expires + ";";
    }

    getCookie(cname) {
        var name = this.prefix + cname + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }

    getIntCookie(cname){
        let val = this.getCookie(cname);
        if(val)
            return parseInt(val);
        return 0;
    }

    hasCookie(cname) {
        var user = this.getCookie(cname);
        if (user != "") {
            return true;
        } else {
            return false;
        }
    }

    removeCookie(cname) {
        this.setCookie(cname,"");
    }
}


class RPCRequest {

    constructor(host) {
        this.host = host;
        // this.cm = new CookieManager();
        console.log('RPC Request.');
    }

    onReady(request) {

    }

    env(model) {
        return new ModelRequest(this, model);
    }

    execute(endpoint, params) {
        let auth_params = {
            access_id: false,
            access_token: false,
        };
        let post_params = Object.assign({}, auth_params, params);
        const uri = BigUtil.dictToURI({
            json: JSON.stringify(post_params),
        });
        let url = this.host + endpoint;

        return new Promise(function (resolve, reject) {
            const http = new XMLHttpRequest();
            http.open('POST', url, true);
            http.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            http.onload = function () {
                resolve(JSON.parse(http.responseText));
            };
            http.onerror = function () {
                reject('Unable to complete.');
            };
            http.send(uri);
            BigUtil.info("Fetching endpoint %s".format_string(url))
        });
    }

}

class FormRequest {

    constructor(request, model) {
        this.request = request;
        this.model = model;
    }

    onDataReceived(data){

    }

    submit(action){

    }

    save(form_data){

    }


}

class ModelRequest {

    constructor(request, model) {
        this.request = request;
        this.model = model;
        this.endpoint = '/rpc/object';
    }

    read(ids, fields = []) {
        return this.call('write', [ids, {fields: fields}]);
    }

    search_read(filter, fields = [], limit = 0, offset = 0, sort = ['id', 'asc']) {
        return this.call('search_read', [filter, {fields: fields, limit: limit, offset: offset, sort: sort}]);
    }

    create(values) {
        return this.call('write', [values]);
    }

    write(id, values) {
        return this.call('write', [id, values]);
    }

    unlink(ids) {
        return this.call('unlink', [ids]);
    }

    call(method, args) {
        let data = {
            method: method,
            model: this.model,
            params: args
        };
        return this.request.execute(this.endpoint, data);
    }

}

class TreeRequest {

    constructor(request) {
        this.request = request;
    }

    setContent(content) {
        this.filter = content.filter;
        this.sort = content.sort;
        this.limit = content.limit;
        this.offset = content.offset;
        this.count = content.count;
        this.model = content.model;
        this.fields = content.fields;
        this.heads = content.heads;
    }

    getDataSummary() {
        if (this.count == 0)
            return "%d-%d/%d".format_string(0, 0, 0);
        else if (this.offset + this.limit <= this.count)
            return "%d-%d/%d".format_string(this.offset + 1, this.offset + this.limit, this.count);
        else
            return "%d-%d/%d".format_string(this.offset + 1, this.count, this.count);
    }

    fetch() {
        console.log('fetching....');
        let self = this;
        this.request.env(this.model)
            .search_read(this.filter, this.fields, this.limit, this.offset, this.sort)
            .then(function (data) {
                console.log(data);
                self.count = data.count;
                self.onPageFetched(data.result);
            }).catch(function (e) {
            console.error(e);
        });
    }

    getDisplayValue(head, row) {
        let val = row[head[0]];
        if (Array.isArray(val) && val.length == 2)
            return val[1];
        if (!val)
            return "Undefined";
        return val;
    }

    onPageFetched(rows) {

    }

    next() {
        if (this.hasNext()) {
            this.offset = this.offset + this.limit;
            this.fetch();
        }
    }

    previous() {
        if (this.hasPrevious()) {
            this.offset = this.offset - this.limit;
            this.fetch();
        }
    }

    hasNext() {
        return (this.offset + this.limit) < this.count;
    }

    hasPrevious() {
        return (this.offset - this.limit) >= 0;
    }

    delete(ids) {
        let self = this;
        this.request.env(this.model)
            .unlink(ids)
            .then(function (data) {
                if ((self.offset - ids.length) >= 0)
                    self.offset = self.offset - ids.length;
                else
                    self.offset = 0;
                self.fetch();
            }).catch(function (e) {
            console.error(e);
        });
    }


}

class ApiManager {

    constructor() {

    }

    get(host, endpoint, queryParams) {
        return this.execute(host, endpoint, 'GET', queryParams, false);
    }

    post(host, endpoint, queryParams, formData) {
        return this.execute(host, endpoint, 'POST', queryParams, formData);
    }

    post_body(host, endpoint, queryParams, bodyData) {
        return this.execute(host, endpoint, 'POST', queryParams, bodyData, true);
    }

    get_body(host, endpoint, queryParams, bodyData) {
        return this.execute(host, endpoint, 'GET', queryParams, bodyData, true);
    }

    execute(host, endpoint, method, queryParams, formData, withBody=false) {
        let url = host + endpoint;
        // add query params if not empty
        if (!BigUtil.isEmptyDictionary(queryParams))
            url = url + '?' + BigUtil.dictToURI(queryParams);

        return new Promise(function (resolve, reject) {
            const http = new XMLHttpRequest();
            http.open(method, url, true);
            if(!withBody)
                http.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
            else
                http.setRequestHeader("Content-Type", "application/json");
            http.onload = function () {
                if (http.status == 200) {
                    resolve(http.responseText);
                } else {
                    BigUtil.error(http.responseText);
                    reject(http.status);
                }
            };
            http.onerror = function () {
                reject('Unable to complete.');
            };
            if (formData){
                if(!withBody)
                    http.send(BigUtil.dictToURI(formData));
                else
                    http.send(JSON.stringify(formData))
            }
            else{
                if(!withBody)
                    http.send();
                else
                    http.send(JSON.stringify(formData));
            }
            //BigUtil.info("%s : %s".format_string(method, url))
        });
    }
}

class JsonRPC {

    constructor(host) {
        this.host = host
    }

    execute(endpoint, method, params, id = null) {
        let self = this;
        let url = self.host + endpoint;
        let body = {
            "jsonrpc": "2.0",
            "method": method,
            "id": id,
            "params": params,
        };
        return new Promise(function (resolve, reject) {
            const http = new XMLHttpRequest();
            http.open('POST', url, true);
            http.setRequestHeader("Content-Type", "application/json");
            http.onload = function () {
                if (http.status == 200) {
                    let result = JSON.parse(http.responseText);
                    resolve(result.result);
                } else {
                    BigUtil.error(http.responseText);
                    reject(http.status);
                }
            };
            http.onerror = function () {
                reject('Unable to complete.');
            };
            http.send(JSON.stringify(body));
        });
    }

}

class ChatConsumer {

    constructor() {
        this.ccdn = 'https://console.bigitsystems.com'
        //this.client_host = BigUtil.getMetaContent('client_host');
        this.server_host = BigUtil.getMetaContent('server_host');
        this.api = new ApiManager();
        this.cm = new CookieManager();
        this.jsonrpc = new JsonRPC(this.server_host);
        this.channels = [];
        this.history = [];
        this.enable_websocket = true;
        this.active_channel= null;
        this.style = {
            primary_color:"#2980b9"
        };
        this.holder = {};
        this.notification = {};

    }

    initializeWebsocket(uuid,token) {

        const self = this;
        let loc = null;
        if(this.server_host === '')
            loc = new URL(window.location);
        else
            loc = new URL(this.server_host);

        let protocol =  loc.protocol  == 'http:' ? 'ws://' : 'wss://';
        let url = protocol+loc.host+'?uuid='+uuid+'&token='+token;

        console.log("Websocket opening: ", url);

        this.socket = new ReconnectingWebSocket(url);

        this.socket.onopen = function (e) {
            console.log("Websocket connected!");
        };
        this.socket.onclose = function (e) {
            console.log("Websocket closed!");
        };
        this.socket.onerror = function (e) {
            console.error(e);
        };
        this.socket.onmessage = function (e) {
            console.warn("onMessageSocket");
            const object = JSON.parse(e.data);
            if(object.event == 'message'){
                // if(!self.isInChannels(object.channel)){
                //     self.channels.push(object.channel);
                //     self.onUpdateTray(self.active_channel, self.channels);
                // }
                self.channels = object.channels;
                self.onUpdateTray(object.channel, self.channels);
                if(object.channel.id == self.active_channel.id){
                    self.onMessagesReceived([object.message]);
                }else {
                    self.onNotificationReceived(object.channel, object.message);
                }
            }else if(object.event == 'channel'){
                console.error(object);
                if(!self.isInChannels(object.channel)){
                    self.channels.push(object.channel);
                }
                self.active_channel = object.channel;
                self.history = object.history;
                self.onUpdateTray(self.active_channel, self.channels);
                self.onMessagesReceived(object.history,true);
            }else if(object.event == 'revoke'){
                self.cm.setCookie('uuid', object.uuid);
                self.cm.setCookie('token', object.token);
                window.location.reload();
            }
            self.onInputTextChanged();
        };
    }

    isInChannels(channel){
        const self = this;
        for(let i=0;i<self.channels.length;i++){
            if(channel.id == self.channels[i].id)
                return true;
        }
        return false;
    }

    begin() {
        const self = this;
        if(this.cm.hasCookie('uuid') && this.cm.hasCookie('token')){
            const uuid = this.cm.getCookie('uuid');
            const token = this.cm.getCookie('token');
            BigUtil.info("Cache token already present.");
            BigUtil.info('Checking if exiting token is valid or not...')
            const params = [uuid,token];
            this.jsonrpc.execute('/jsonrpc/consumer', 'authenticate' , params).then(function (data) {
                BigUtil.info("Exiting user token is valid.");
                self.initChat(uuid,token);
            }).catch(function (status) {
                BigUtil.info("Token Present But Not Valid");
                BigUtil.info("Removing old token...");
                self.cm.removeCookie('uuid');
                self.cm.removeCookie('token');
                BigUtil.info("Generating New Token....");
                self.getToken();
            });
        }else {
            BigUtil.info("Token Not Present. Generating New....");
            self.getToken();
        }
    }

    getToken() {
        const self = this;
        const params = [false, false, 'Visitor'];
        self.jsonrpc.execute('/jsonrpc/standalone', 'create_public_standalone' , params).then(function (result) {
            BigUtil.info("New Token Generated successfully !!!");
            BigUtil.info(result);
            self.cm.setCookie('uuid', result.uuid);
            self.cm.setCookie('token', result.token);
            BigUtil.info("Token saved to cookies.");
            self.initChat(result.uuid, result.token);
        }).catch(function (e) {
        });
    }

    openLoginWindow(){
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const uri = BigUtil.dictToURI({
            uuid:uuid,
            token:token,
        })
        const url = self.server_host+'/stack/login?'+uri;
        window.open(url, '_blank', 'location=yes,height=420,width=460,scrollbars=yes,status=yes');
    }

    initChat(uuid, token){
        const self = this;
        const params = [uuid,token];
        self.jsonrpc.execute('/jsonrpc/consumer', 'get_style' , params).then(function (stylesheet) {
            self.style = stylesheet;
            self.jsonrpc.execute('/jsonrpc/consumer', 'get_active_channel' , params).then(function (active_channel) {
                BigUtil.info("Active channel info received.");
                self.active_channel = active_channel;
                let params = [uuid, token, active_channel.channel_uuid];
                self.jsonrpc.execute('/jsonrpc/consumer', 'get_messages' , params).then(function (history) {
                    BigUtil.info("Active channel history received.");
                    self.history = history;
                    self.onChannelReady(self.style, active_channel);
                    self.onMessagesReceived(history);
                    self.getChannels(uuid, token);
                    console.error(history);
                }).catch(function (e) {
                });
            }).catch(function (e) {
            });
        }).catch(function (e) {
        });
    }

    getChannels(uuid, token){
        const self = this;
        const params = [uuid,token];
        self.jsonrpc.execute('/jsonrpc/consumer', 'get_channels' , params).then(function (channels) {
            BigUtil.info("All channels information received.");
            self.channels = channels;
            self.onUpdateTray(self.active_channel,channels);
            if(self.enable_websocket)
                self.initializeWebsocket(uuid,token);
        }).catch(function (e) {
        });
    }

    getChatHistory(channel) {
        BigUtil.info('Looking for channel history');
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const params = [uuid,token, channel.channel_uuid];
        self.jsonrpc.execute('/jsonrpc/consumer', 'get_messages' , params).then(function (history) {
            BigUtil.info("Selected Channel history received.");
            self.history = history;
            self.onMessagesReceived(history);
        }).catch(function (e) {
        });
    }

    // new calls

    onInputTextChanged(query = "") {
        BigUtil.info('Looking for suggestion...');
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const params = [uuid,token, self.active_channel.channel_uuid,query];
        self.jsonrpc.execute('/jsonrpc/consumer', 'get_suggestions' , params).then(function (suggestions) {
            BigUtil.info("New Suggestions received.");
            self.onInputSuggestionReceived(suggestions);
        }).catch(function (e) {

        });
    }


    sendMessage(type, body, value, object= false) {
        BigUtil.info('Sending message...');
        BigUtil.log(type);
        BigUtil.log(body);
        BigUtil.log(value);
        BigUtil.log(object);
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const channel_uuid = self.active_channel.channel_uuid;
        let message = {
            "body": body,
            "values":[value],
            "contexts":[0]
        };
        if(object)
            message = object;
        const params = [uuid, token, message];
        self.onTypingStatusChanged("thinking",false,true);
        self.onLockInput(true);
        self.onInputSuggestionReceived([]);
        self.jsonrpc.execute('/jsonrpc/consumer', 'post_message' , params).then(function (responses) {
            self.onTypingStatusChanged("thinking",false,false);
            self.onInputTextChanged();
            self.onLockInput(false);
            //self.onMessagesReceived(responses);
        }).catch(function (e) {
            self.onTypingStatusChanged("thinking",false,false);
            self.onInputTextChanged();
            self.onLockInput(false);
        });
    }

    getUserToken(){
        const self = this;
        return [self.cm.getCookie('uuid'), self.cm.getCookie('token')]
    }

    onSelectChannel(channel){
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const params = [uuid, token, channel.channel_uuid];
        self.jsonrpc.execute('/jsonrpc/consumer', 'set_active_channel' , params).then(function (history) {
            //self.active_channel = channel;
            //self.onUpdateTray(self.active_channel, self.channels);
            //self.onMessagesReceived(history, true);
            self.clearNotification(channel);
        }).catch(function (e) {
        });
    }

    onSelectMessage(message){
        const self = this;
        const uuid = self.cm.getCookie('uuid');
        const token = self.cm.getCookie('token');
        const params = [uuid, token, message.message_id];
        self.jsonrpc.execute('/jsonrpc/consumer', 'open_sender_channel' , params).then(function (history) {
            //self.active_channel = channel;
            //self.onUpdateTray(self.active_channel, self.channels);
            //self.onMessagesReceived(history, true);
            self.clearNotification(channel);
        }).catch(function (e) {
        });
    }



    // new call backs

    onChannelReady(style, channel) {
        console.log(channel);
    }

    onUpdateTray(active_channel, channels) {
        console.log(channels);
    }

    onInputSuggestionReceived(suggestions) {
        console.log(suggestions);
    }

    onMessagesReceived(messages, reset=false) {
        console.log(messages);
    }

    onTypingStatusChanged(context, user, is_typing) {

    }

    onLockInput(locked) {

    }

    onNotificationReceived(channel,message) {
       if(this.notification.hasOwnProperty(channel.channel_uuid)){
           this.notification[channel.channel_uuid] = this.notification[channel.channel_uuid] + 1;
       }else {
           this.notification[channel.channel_uuid] = 1;
       }
       this.onUpdateTray(this.active_channel, this.channels);
    }

    clearNotification(channel){
        if(this.notification.hasOwnProperty(channel.channel_uuid)){
            this.notification[channel.channel_uuid] = 0;
        }else {
            this.notification[channel.channel_uuid] = 0;
        }
        this.onUpdateTray(this.active_channel, this.channels);
    }

    getNotificationCount(channel){
        if(this.notification.hasOwnProperty(channel.channel_uuid)){
            return this.notification[channel.channel_uuid]
        }
        return 0;
    }

}


