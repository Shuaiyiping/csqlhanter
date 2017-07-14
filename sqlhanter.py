#!/usr/bin/python
# -*- coding:utf-8 -*-

import time
import json
import urllib
import urllib2
import sys
import requests
import threading
from Queue import Queue
from pymongo import MongoClient
import warnings
warnings.filterwarnings("ignore")
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

que = Queue()
result_que = Queue()
count = 0
MONGO_SERVER = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'spiders'
MONGO_COLLECTION = 'urls'
db = MongoClient(MONGO_SERVER,MONGO_PORT)[MONGO_DATABASE][MONGO_COLLECTION]
mutex = threading.Lock()
result_file = open('/tmp/result','w+')

class Autoinj(threading.Thread):
    """
        sqlmapapi 接口建立和管理sqlmap任务
        by zhangh (zhanghang.org#gmail.com)
      modefied by fiht(fiht#qq.com)
    """

    def __init__(self, server='', target='', method='', data='', cookie='', referer=''):
        threading.Thread.__init__(self)
        self.server = server
        if self.server[-1] != '/':
            self.server = self.server + '/'
        # if method == "GET":
            # self.target = target + '?' + data
        # else:
            # self.target = target
        self.target = ''
        self.taskid = ''
        self.engineid = ''
        self.status = ''
        self.method = method
        self.data = data
        self.referer = referer
        self.cookie = cookie
        self.start_time = time.time()
        #print "server: %s \ttarget:%s \tmethod:%s \tdata:%s \tcookie:%s" % (self.server, self.target, self.method, self.data, self.cookie)
    #----------------------------------------------------------------------
    def get_target(self):
        """从数据库中找target,以后可以加一个用文件找的"""
        mutex.acquire()
        result = db.find_one({'Scaning':{'$exists':False}})
        if result:
            self.target = result['url']
            db.update({'url':result['url']},{'$set':{'Scaning':1}})
            print('正在检测%s'%self.target)
            mutex.release()
            return True
        else:
            # print('没法从数据库里面取出数据')
            pass
        return False
        mutex.release()
        
    def task_new(self):
        self.taskid = json.loads(requests.get(self.server + 'task/new', verify=False).text)['taskid']
        if len(self.taskid) > 0:
            return True
        return False

    def task_delete(self):
        if json.loads(requests.get(self.server + 'task/' + self.taskid + '/delete', verify=False).text)['success']:
            return True
        return False

    def scan_start(self):
        headers = {'Content-Type':'application/json'}
        url = self.server + 'scan/' + self.taskid + '/start'
        data = {'url':self.target}
        t = requests.post(url, data=json.dumps(data), headers=headers, verify=False).text
        t = json.loads(t)
        self.engineid = t['engineid']
        if len(str(self.engineid)) > 0 and t['success']:
            return True
        return False

    def scan_status(self):
        self.status = json.loads(requests.get(self.server + 'scan/' + self.taskid + '/status', verify=False).text)['status']

    def scan_data(self):
        data = json.loads(requests.get(self.server + 'scan/' + self.taskid + '/data', verify=False).text)
        return data
        # if len(self.data) == 0:
        #     print 'not injection:\t' + self.target
        # else:
        #     print '=======> injection:\t' + self.target
    
    def option_set(self):
        headers = {'Content-Type':'application/json'}
        url = self.server + 'option/' + self.taskid + '/set'
        data = {}
        if self.method == "POST":
            data["data"] = self.data
        if len(self.cookie)>1:
            data["cookie"] = self.cookie
        #print data
        data['threads'] = 10
        data['smart'] = True
        data['is-dba'] = True
        t = requests.post(url, data=json.dumps(data), headers=headers, verify=False).text
        t = json.loads(t)

    def scan_stop(self):
        json.loads(requests.get(self.server + 'scan/' + self.taskid + '/stop', verify=False).text)['success']

    def scan_kill(self):
        json.loads(requests.get(self.server + 'scan/' + self.taskid + '/kill', verify=False).text)['success']

    def start_test(self):
        # 开始任务
        #self.target=que.get()
        self.start_time = time.time()
        if not self.task_new():
            print "Error: task created failed."
            return False
        # 设置扫描参数
        self.option_set()
        # 启动扫描任务
        if not self.scan_start():
            print "Error: scan start failed."
            return False
        # 等待扫描任务
        while True:
            self.scan_status()
            if self.status == 'running':
                time.sleep(40)
            elif self.status == 'terminated':
                break
            else:
                print "unkown status"
                break
            if time.time() - self.start_time > 3000: #多于五分钟
                error = True
                print('删除一个不怎么带劲的IP:%s'%self.target)
                count += 1
                self.scan_stop()
                self.scan_kill()
                return [self.target,0]

        # 取结果
        res = self.scan_data()
        # 删任务
        self.task_delete()
        global count

        if res['data']:
            count += 1
            print "耗时:" + str(time.time() - self.start_time)
            print '已经检测%d个url'%count
            return [self.target,res['data'][1]['value'][0]['dbms']]
        else:
            count += 1
            print "耗时:" + str(time.time() - self.start_time)
            print '已经检测%d个url'%count
            return [self.target,0]

    #----------------------------------------------------------------------
    def run(self):
        """不停地找"""
        while(self.get_target()):
            try:
                result = self.start_test()
                #print('----->',result)
                if result[1]:
                    mutex.acquire()
                    db.update({'url':result[0]},{'$set':{'injection':1,'info':result[1]}})
                    print('找到一个url %s'%result[0])
                    result_file.writelines(self.target+'--->'+str(result[1]))
                    mutex.release()
                else:
                    mutex.acquire()
                    db.update({'url':result[0]},{'$set':{'injection':0}})
                    mutex.release()
            except Exception as e:
                # print e
                break
host_list = ['http://localhost:8775/','http://localhost:8776/','http://localhost:8776',
             'http://localhost:8775/',
#             'http://139.129.25.173:8775/',#,'http://139.129.25.173:8775/',
#             'http://123.206.65.93:8775/'
             ]         
#----------------------------------------------------------------------

def main():
    threads = [Autoinj(host) for i in range(50) for host in host_list] # 一个client实例一次处理10个注入点
    for thread_ in threads:
        thread_.start()

if __name__=='__main__':
    start_time = time.time()
    # for i in open('/tmp/sss').readlines():
        # #print('http://%s'%i.strip())
        # que.put(i.strip())
    main()
    #host = ['http://localhost:8775/']
    #print('一共花费时间%s,一共找到注入%s'%(time.time()-start_time,result_que.qsize()))
#if 