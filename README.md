# csqlhanter

## 简介
csqlhanter是基于爬虫的sql批量检测工具，spider.py负责爬虫和去重，支持多域名爬扫。sqlhanter.py是基于sqlmapapi的多线程sql扫描工具。

## 用法
url.txt填入要扫描的url或者域名，运行spider.py自动爬扫，爬到的url会存到mongodb中，然后运行sqlhanter就自动进行sql注入扫描了。
