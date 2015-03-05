<?php
sleep(1);
var_dump($_GET);
var_dump($_POST);
echo "hello world!";
$fp = fopen(__DIR__.'/visit.log','a+');
fwrite($fp,$_SERVER['REQUEST_URI']."\r\n");
fclose($fp);
