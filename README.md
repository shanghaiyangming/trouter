#Trouter
项目名称：<br />
Tornado Router<br /><br />
简称：<br />
Trouter<br /><br />
功能介绍：<br /><br />
使用tornado进行路由转发控制。<br /><br />
当短时间出现大量的请求超过阈值的情况，服务会将过载部分的请求缓存在zeroMQ/Redis中，以便能缓慢的释放请求到应用服务器。
保障服务的正常运行。
<br /><br />
python trouter.py -m 1000 -a "127.0.0.1:9999" -p 8000 -t 500

参数说明：
-m --max 最大连接数，默认是10000
-a --app 后台应用服务器的地址，多个应用服务器用英文逗号分隔
-p --port 监听的端口号，默认是12345
-t --threshold 阈值，默认是500 当达到阈值的时候，自动阻塞请求不再向后转发
