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
启动命令示例：
python trouter.py --conn=1000 --apps=127.0.0.1:9999 --port=8000 --threshold=5 --sync_threshold=4
<br /><br />
参数说明：<br /><br />
__conn__ 最大连接数，默认是5000<br /><br />
__apps__ 后台应用服务器的地址，多个应用服务器用英文逗号分隔<br /><br />
__port__ 监听的端口号，默认是12345<br /><br />
__threshold__ 阈值，默认是500 当达到阈值的时候，自动阻塞请求不再向后转发<br /><br />
__sync_threshold__ 同步请求阈值，默认300 保证在转发中有300个用于同步转发<br /><br />
__logging__ 错误等级，默认是info 可选参数debug|info|warning|error|none<br /><br />

Nginx转发设置：
<br /><br />
接受参数方式
<br /><br />
upstream test {<br /><br />
    proxy_set_header \_\_NODELAY\_\_  1;<br /><br />
    server 192.168.56.1:8000;<br /><br />
    server 192.168.56.1:8000;<br /><br />
}
<br /><br />

\_\_NODELAY\_\_表示直接返回成功{"ok":1},无延迟返回，后续将根据应用服务器的量平缓处理<br /><br />
\_\_BLACKLIST\_\_表示直接返回503 跟着要过滤的内容多个关键词用英文逗号分隔，支持中英文<br /><br />
\_\_ASYNCLIST\_\_表示对于包含给定关键词的内容（多个关键词用英文逗号分隔），切换到异步模式处理，并直接返回成功{"ok":1},无延迟返回<br /><br />
\_\_ASYNC_RESULT\_\_定义异步操作的返回结果，默认值是{"ok":1}，建议urlencode编码