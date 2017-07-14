#!/usr/bin/env python

from_name_kb = {
'mbscanner':['username', 'user', 'userid', 'nickname', 'name'],
'abc123456':['password', 'pass', 'pwd'],
'test@163.com':['email', 'mail', 'usermail'],
'13800000000':['mobile'],
'just test':['content', 'text', 'query', 'search', 'data', 'comment'],
'www.test.com':['domain'],
'http://www.test.com':['link', 'url', 'website']
}

def smart_fill(varialbe_name):
	varialbe_name = varialbe_name.lower()
	flag = False
	for filled_value, varialbe_name_list in from_name_kb.items():
		for varialbe_name_db in varialbe_name_list:
			if varialbe_name_db == varialbe_name:
				flag = True
				return filled_value

	if not flag:
		msg = '[smart fill] Failed to find a value for parameter with name "%s"' %varialbe_name 
		return 'UNKNOW'

if __name__ == "__main__":
	print "username=%s" % smart_fill("username")