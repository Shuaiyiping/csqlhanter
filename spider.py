#!/usr/bin/env python
#-*- coding: utf-8 -*-

from multiprocessing import Process
from multiprocessing import Pool
from HTMLParser import HTMLParser,HTMLParseError
import asyncore, asynchat, socket, threading
from Queue import Queue
import subprocess, os, sys, getopt, logging
import string, re
import random,time
import requests
from urlparse import urljoin
import urlparse
import hashlib
from functions import is_similar_url
from configs import randomUserAgent
from pymongo import MongoClient

queue = Queue()

MONGO_SERVER = '127.0.0.1'
MONGO_PORT = 27017
MONGO_DATABASE = 'spiders'
MONGO_COLLECTION = 'urls'
db = MongoClient(MONGO_SERVER,MONGO_PORT)[MONGO_DATABASE][MONGO_COLLECTION]

class MyHTMLParser(HTMLParser):
	urls = []
	def __init__(self, cur_url):
		HTMLParser.__init__(self)
		self._cur_url = cur_url
		self._re_urls = set()

	def _get_last_path(self, url):
		if url[-1:] == '/':
			return url
		try:
			up = urlparse.urlparse(url)
			new_url = up.netloc + up.path
			last_index = new_url[::-1].find('/')
			ret_url = new_url[:len(new_url)-last_index]
			return up.scheme + "://" + ret_url
		except Exception, e:
			return url

	def _URL(self, value):
		if value.startswith("http://"):
			return value
		elif value.startswith("/") or value.startswith('./'):
			ret = urljoin(self._get_last_path(self._cur_url), value.strip('.'))
			return ret
		elif value.startswith(urlparse.urlparse(self._cur_url).netloc):
			return "http://" + ret
		else:
			ret = urljoin(self._get_last_path(self._cur_url), value)
			return ret

	def handle_starttag(self, tag, attrs):
		# Only parse the 'anchor' tag.
		URL_TAGS = ('a', 'img', 'link', 'script', 'iframe', 'frame', 'from', 'object')
		URL_ATTR = ('href', 'src', 'data', 'action')
		if tag in URL_TAGS:
			# Check the list of defined attributes.
			for name, value in attrs:
				# If href is defined, print it.
				if name in URL_ATTR:
					#print name, "=", value
					if value and (value.find('javascript') == -1) and not value.startswith("#"):
						url = self._URL(value)
						if url:
							self._re_urls.add(url)

	# 获取满足URL形式的数据，如：文本或者标签以外的URL
	def handle_data(self, data):
		re_urls = set()
		URL_RE = re.compile('((http|https)://([\w:@\-\./]*?)[^ \n\r\t"\'<>]\s*)', re.U|re.I)
		for url in re.findall(URL_RE, data):
			try:
				url = self._URL(url[0])
			except ValueError:
				pass
			else:
				re_urls.add(url)

		def find_relactive(data):
			res = set()
			# 如index.php或index.php?aid=1&bid=2这样的相对url
			regex = '([/]{0,1}\w+.(asp|html|php|jsp|aspx|htm)(\?([\w%]*=[\w%]*)(&([\w%]*=[\w%]*))*){0,1})'
			relative_regex = re.compile(regex, re.U|re.I)
			for match_tuple in relative_regex.findall(data):
				match_str = match_tuple[0]
				url = urljoin(self._get_last_path(self._cur_url),match_str)
				res.add(url)
			return res

		re_urls.update(find_relactive(data))
		self._re_urls.update(re_urls)

	def gethref(self):
		return list(self._re_urls)


class Spider():
	logfile = '/tmp/spider.log'
	isdebug = True
	depths = 0
	max_links = 0
	link	= []
	unlink	= []
	secondDomain = ''
	
	referer 	= ''
	useragent 	= 'mb spider'
	domain		= r''
	baseurl		= r''
	
	skip	= []
	ignore	= []
	black_ext = ['ico', 'jpg', 'gif', 'js', 'png', 'bmp', 'css', 'zip', 'rar', 'ttf', 'jpeg', 'swf', 'svg']
	
	threadname = ''
	def __init__(self, threadname = None):
		logging.basicConfig(level=logging.NOTSET,
			format='%(asctime)s %(levelname)-8s %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S',
			filename=self.logfile,
			filemode='a')
		self.logging = logging.getLogger()
		if threadname:
			self.threadname = '|'+threadname
	def setDebug(self,isdebug):
		self.isdebug = isdebug
		self.logging.debug('Enable Debug')
	def setDomain(self, tmp):
		if tmp:
			self.domain = tmp
	def setReferer(self,tmp):
		if tmp:
			self.referer = tmp
	def setUseragent(self,tmp):
		if tmp:
			self.useragent = tmp
	def setBaseUrl(self,tmp):
		if tmp:
			self.baseurl = tmp
	def setSecondDomain(self):
		up = urlparse.urlparse(self.domain)
		domain = up.netloc
		tmpArr = domain.split('.')
		if tmpArr:
			self.secondDomain = '.'.join(tmpArr[-2:])
	def md5_16(self, url):
		return hashlib.md5(url).hexdigest()[8:-8]
	def get_ext(self, url):
		up = urlparse.urlparse(url)
		path = up.path
		if path:
			last_name = path.split('/')[-1]
			ext = last_name.split('.')[-1]
			if ext in self.black_ext:
				return False
		return True
	def ufilter(self,url):
		if (url not in self.link) and self.get_ext(url) and not is_similar_url(url, self.link):
			self.link.append(url)
			return url
		# else:
		# 	if url not in self.skip:
		# 		self.skip.append(url)
		# 		self.logging.warning('Skip ' + url)	
		# 	return None
		
		# if url[0:1] == '/':
		# 	return self.baseurl + url
		# elif url.find('http://') == -1:
		# 	return self.baseurl +'/'+ url
		# else:
		# 	if url.find(self.secondDomain) == -1:
		# 		if url not in self.ignore:
		# 			self.logging.warning('Ignore ' + url)
		# 			self.ignore.append(url)
		# 		return None

		return None

	def working(self, url):
		self.max_links = self.max_links + 1
		# 最大的链接数
		if self.max_links > 256:
			return 

		# 遍历的层数
		# if self.depths > 10:
		# 	return
		#if self.isdebug:
		#	self.logging.debug('>>>' + str(self.depths))
      			
		if url == None:
			return

		try:
			lines = []
			parser = MyHTMLParser(url)
			headers = {'User-Agent':randomUserAgent(), 'Referer':self.referer}
			response = requests.get(url, timeout=5, headers=headers)
			status 	= response.status_code
			reason 	= response.reason
			headers = response.headers
			
			log = str(status)+' '+reason+' '+url+ ' ('+ str(self.depths)+self.threadname+') '
			
			if self.isdebug:
				print log

			if 'text/html' in headers['Content-Type']:
				if status == 200:
					body = response.content
					parser.feed(body)
					lines = parser.gethref()
					self.logging.info(log)
				elif status == 302:
					self.unlink.append(url)
					self.logging.critical(log)
				else:
					self.logging.warning(log)

				response.close()
							
				if lines:
					self.depths += 1
					self.referer = random.choice(list(lines))
					for line in lines:
						if isinstance(line, str):
							if self.secondDomain in urlparse.urlparse(line).netloc:
								line = self.ufilter(line)
								if line != None and urlparse.urlparse(line).query != '':
									db.insert({'url':line})
								if line != None:
									self.working(line)

			else:
				self.logging.warning(log + ' ' + headers['Content-Type'])
				response.close()
		except socket.timeout as e:
			self.logging.error(str(e) +' '+ url)
		except requests.exceptions.ConnectionError as e:			
			self.logging.critical(str(e) +' '+ url)
		except requests.exceptions.InvalidURL as e:
			if self.isdebug:
				print str(e) +' '+url + ' - ' + url 
			self.logging.critical(str(e) +' '+ url)
		except requests.exceptions.HTTPError as e:
			self.logging.critical(str(e) +' '+ url)		
		except HTMLParseError as e:
			self.logging.error(str(e) +' '+ url)
			if self.isdebug:
				print str(e) +' '+ url
		except UnicodeDecodeError as e:
			self.logging.critical(str(e) +' '+ url)
		except ValueError as e:
			if self.isdebug:
				print str(e) +' '+ url	
		except Exception, e:
			if self.isdebug:
				print str(e) +' '+ url
		else:
			self.logging.error(url)
		#finally:
			#self.depths = self.depths - 1
			#pass

class ThreadSpider(threading.Thread):
	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.queue = queue

		self.spider = Spider()
		self.spider.setDebug(False)
		
	def run(self):
		while True:
			#grabs host from queue
			host = self.queue.get()
			self.spider.setDomain(host)
			self.spider.setSecondDomain()
			self.spider.working(host)

			#signals to queue job is done
			self.queue.task_done()

def Multithreading(hosts):
	if not hosts:
		return
	workers	= 5
	for i in range(workers):
		t = ThreadSpider(queue)
		t.setDaemon(True)
		t.start()

	#populate queue with data   
	for host in hosts:
		queue.put(host)

	#wait on the queue until everything has been processed     
	queue.join()

def test(url):
	spider = Spider()
	spider.setDebug(True)
	spider.working(url)
	print url

def daemon(isdaemon):
	if isdaemon :
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	
def main():
	daemon(isdaemon = False)
	hosts = []
	with open('urls.txt', 'r') as f:
		for line in f.readlines():
			hosts.append(line.strip())
	Multithreading(hosts)
	# try:
	# 	start = time.time()
	# 	spider = Spider()
	# 	spider.setDebug(True)
	# 	up = urlparse.urlparse(url)
	# 	domain = up.domain
	# 	spider.setDomain(doamin)
	# 	spider.setBaseUrl(url)
	# 	spider.working(url)
	# 	print "Elapsed Time: %s" % (time.time() - start)
	# except RuntimeError as e:
	# 	print e

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print "Crtl+C Pressed. Shutting down."
