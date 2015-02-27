#Trouter
项目名称：<br />
Tornado Router<br />
简称：<br />
Trouter<br />
功能介绍：<br />
使用tornado进行路由转发控制。<br />
当短时间出现大量的请求超过阈值的情况，服务会将过载部分的请求缓存在zeroMQ/Redis中，以便能缓慢的释放请求到应用服务器。
保障服务的正常运行。