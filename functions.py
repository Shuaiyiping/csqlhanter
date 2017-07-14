#!/usr/bin/env python
#coding=utf8

import urlparse

class urlinfo:
	def __init__(self, url):
		self.url = url
		self.up = urlparse.urlparse(url)
	def get_protocal(self):
		return self.up.scheme
	def get_host(self):
		return self.up.netloc.split(":")[0]
	def get_port(self):
		try:
			port = self.up.netloc.split(":")[1]
		except Exception, e:
			port = None
		return port
	def get_path(self):
		return self.up.path
	def get_keys(self):
		ret_keys = []
		if self.up.query:
			qarr = self.up.query.split('&')
			for item in qarr:
				key, val = item.split("=")
				ret_keys.append(key)
			return ret_keys

		return []

def _is_contain_list(lista, listb):
	if not isinstance(lista, list) or not isinstance(listb, list):
		return False
	a_len = len(lista)
	b_len = len(listb)
	if a_len != b_len:
		return False
	if a_len >= b_len:
		temp = lista
		lista = listb
		listb = temp

	# 判断两个list是否相似或者包含
	count = 0
	for item in lista:
		if item in listb:
			count += 1
	if count == a_len and count <= b_len:
		return True
	else:
		return False

def _is_similar_url(urla, urlb):
	# 获取协议
	urla = urlinfo(urla)
	urlb = urlinfo(urlb)
	protocala = urla.get_protocal()
	protocalb = urla.get_protocal()
	# 获取host
	hosta = urla.get_host()
	hostb = urlb.get_host()
	# 获取端口
	porta = urla.get_port()
	portb = urlb.get_port()
	# 获取路径
	patha = urla.get_path()
	pathb = urlb.get_path()
	# 获取参数list
	keya = urla.get_keys()
	keyb = urlb.get_keys()
	if protocala == protocalb and hosta == hostb and porta == portb and patha == pathb and _is_contain_list(keya, keyb):
		return True
	return False

def is_similar_url(url, urllist):
	if not isinstance(url, str) or not isinstance(urllist, list):
		return False
	for item in urllist:
		if _is_similar_url(url, item):
			return True
	return False

def main():
	url = "http://qq.com/a/b/c?key=fuck&key2=test"
	urllist = ["http://qq.com/a/b/c?key=fef&key2=afaf"]
	print is_similar_url(url, urllist)

if __name__ == '__main__':
	main()
