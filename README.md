#Trouter
##项目名称：<br />
Tornado Router<br /><br />
##简称：
Trouter<br /><br />
##功能介绍：
网站已经上线，代码已经写好，忽然远超过预想的流量来了！怎么办？<br /><br />
重新编码？NND，怎么可能来得及？<br /><br />
加服务器？NND，现买哪里来得及？<br /><br />
就是有那么一种网站，95%的时间是空闲的，5%的时间负载远超过处理能力。<br /><br />
如何能够有效的分流请求？<br /><br />
我们考虑了三种情况：<br /><br />
1. 切换成异步接收模式，别人虐我千百遍，我待他人如初恋！不管你来多少请求，我们都接纳，但是后台慢慢处理。适合比如投票类的应用。<br /><br />
2. 同步异步混合。同一个URL，同一个API，同一个行为。但是不同的参数或者不同的提交内容，区分处理。比如微信服务器推送过来的信息。对于用户消息提问，当然要及时回复；但是对于一些系统事件，能进列队不？后台慢慢处理好不好？答案是可以！<br /><br />
3. 我的同步业务不能影响噢~ 没问题！<br /><br />
__无需修改任何代码，对程序员完全透明！！！__<br /><br />
这就是我们的trouter的作用!
<br /><br />
##启动命令示例：
python trouter.py --conn=1000 --apps=127.0.0.1:9999 --port=8000 --threshold=5 --sync_threshold=4  --enable_zmq=1 --zmq_device=tcp://127.0.0.1:55555
<br /><br />
##参数说明：<br /><br />
__conn__ 最大连接数，默认是5000<br /><br />
__apps__ 后台应用服务器的地址，多个应用服务器用英文逗号分隔<br /><br />
__port__ 监听的端口号，默认是12345<br /><br />
__threshold__ 阈值，默认是500 当达到阈值的时候，自动阻塞请求不再向后转发<br /><br />
__sync_threshold__ 同步请求阈值，默认300 保证在转发中有300个用于同步转发<br /><br />
__logging__ 错误等级，默认是info 可选参数debug|info|warning|error|none<br /><br />
__enable_zmq__ 是否开启zmq存储请求，默认是0 设置大于0的整数，表示开启<br /><br />
__zmq_device__ zeroMQ设备地址，例如：tcp://127.0.0.1:55555<br /><br />
__security_device__ zeroMQ security device 设备地址，例如：tcp://127.0.0.1:55557<br /><br />

#0mq工作设置
启动zeromq/device.py 默认监听55555 55556端口<br /><br />

#http client worker设置
启动zeromq/worker.py 根据你后台应用服务器的处理能力，启动相应数量的实例<br /><br />

#没有队列怎么办？
采用队列可以提高性能，但是没有？也可以工作！启动enable_zmq不设置即可，默认是0噢~<br /><br />
同样是实现上面的全部功能，只是性能……确实要差一点，没办法你懂的，处理的太多trouter也会累的嘛！

##Nginx转发设置：
upstream test {<br /><br />
    proxy_set_header \_\_NODELAY\_\_  1;<br /><br />
    server 192.168.56.1:8000;<br /><br />
    server 192.168.56.1:8000;<br /><br />
}<br /><br />

location / {<br /><br />
    root   html;<br /><br />
    index  index.html index.htm;<br /><br />
    proxy_set_header Host $host;<br /><br />
    proxy_set_header X-Real-IP  $remote_addr;<br /><br />
    proxy_set_header \_\_NODELAY\_\_  1;<br /><br />
    proxy_pass http://test;<br /><br />
}
<br /><br />

\_\_NODELAY\_\_表示直接返回成功{"ok":1},无延迟返回，后续将根据应用服务器的量平缓处理<br /><br />
\_\_BLACKLIST\_\_表示直接返回503 跟着要过滤的内容多个关键词用英文逗号分隔，支持中英文<br /><br />
\_\_ASYNCLIST\_\_表示对于包含给定关键词的内容（多个关键词用英文逗号分隔），切换到异步模式处理，并直接返回成功{"ok":1},无延迟返回<br /><br />
\_\_ASYNC_RESULT\_\_定义异步操作的返回结果，默认值是{"ok":1}，建议urlencode编码