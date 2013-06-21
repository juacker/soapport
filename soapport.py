#!/usr/bin/env python
#encoding: utf-8

'''
SOAP client

@author: Juan Cañete <juan.canete@panel.es>
@date: 2013/05/16
'''

import argparse
import uuid
import urllib2
import os,sys
import datetime
import json
import re
from multiprocessing import Pool

XML_TEMPLATE_DIR='./srv'
XML_MAPPINGS_DIR='./srv'
XML_INFO_DIR='./srv'
XML_TEMPLATES={}
XML_MAPPINGS={}
XML_INFO={}
FIELD_SEPARATOR='|'

def request_service(url,data,headers):
    init=datetime.datetime.now()
    req=urllib2.Request(url,data,headers)
    try:
        response=urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        response=e
    end=datetime.datetime.now()
    stime=end-init
    print init.strftime('%Y-%m-%d %H:%M:%S')+'|',
    print end.strftime('%Y-%m-%d %H:%M:%S')+'|',
    print str(stime.seconds)+'.'+str(stime.microseconds)+'|',
    print str(response.code)+'|',
    print str(headers['SOAPAction']),
    if response.code == 500:
        return False
    else:
        return True


def get_requestinfo(xmlstring,info):
    if not XML_INFO.has_key(info):
        xmlinfofile=os.path.join(XML_INFO_DIR,info+'.info')
        try:
            XML_INFO[info]=json.loads(open(xmlinfofile).read().split('\n')[0])
        except IOError:
            print 'Error opening XML Info File for service: '+info
            return None
    uri=XML_INFO[info]['__URI__']
    service=XML_INFO[info]['__SERVICENAME__']
    xmllen=len(xmlstring)
    headers={'Content-Type': 'text/xml;charset=UTF-8','SOAPAction': service,'Content-Length': xmllen}
    return uri,headers

def get_xmlTradstring(xmlfile):
    try:
        xmlstr=open(xmlfile).read()
    except Exception as e:
        print 'Error: opening xml file: '+str(e)
        sys.exit()
    message_id=str(uuid.uuid4())
    xmlstr=xmlstr.replace('__MESSAGEID__',message_id)
    return xmlstr
    
def get_xmlstr_g(file=None,reg=None):
    def get_xmlfromreg(reg):
        r_fields=reg.split(FIELD_SEPARATOR)
        if r_fields is None:
            return None
        service=r_fields[0]
        if not XML_TEMPLATES.has_key(service):
            xmltplfile=os.path.join(XML_TEMPLATE_DIR,service+'.tpl')
            try:
                XML_TEMPLATES[service]=open(xmltplfile).read()
            except IOError:
                print 'Error opening XML Template file for service: '+service
                return None
        if not XML_MAPPINGS.has_key(service):
            xmlmapfile=os.path.join(XML_MAPPINGS_DIR,service+'.map')
            try:
                XML_MAPPINGS[service]=json.loads(open(xmlmapfile).read().split('\n')[0])
            except IOError:
                print 'Error opening XML Mappings file for service: '+service
                return None
            except ValueError as e:
                print 'Error processing XML Mappings file for service: '+service+' '+str(e)
                return None
        try:
            xmlstr=XML_TEMPLATES[service]
            for param,position in XML_MAPPINGS[service].iteritems():
                xmlstr=xmlstr.replace(param,r_fields[position])
            xmlstr=xmlstr.replace('__MESSAGEID__',str(uuid.uuid4()))
        except IndexError:
            print 'Error replacing service XML template'
            return None
        else:
            return xmlstr
    if reg:
        xmlstr=get_xmlfromreg(reg)
        if xmlstr:
            yield xmlstr,reg
    elif file:
        for line in file:
            reg=line.split('\n')[0]
            xmlstr=get_xmlfromreg(reg)
            if xmlstr:
                yield xmlstr,reg

def parallel_request(request):
    url,data,headers,reg=request
    request_service(url,data,headers)
    print reg.split('\n')[0].split(FIELD_SEPARATOR)[1:]

        

def main():
    parser = argparse.ArgumentParser(description='SOAP Motherfucker client')
    parser.add_argument('-s','--server', required=True,help='S2T server/IP')
    parser.add_argument('-p','--port', required=True, type=int,help='S2T server port')
    parser.add_argument('-f','--file',  type=argparse.FileType('r'), help='File containing request values')
    parser.add_argument('-r','--request', help='Individual request parameters')
    parser.add_argument('-c','--concurrency',type=int,default=10,help='Concurrency level')
    args = parser.parse_args()
    server=args.server
    port=args.port
    concurrency=args.concurrency
    if (args.file and args.request) or (not args.file and not args.request):
        parser.print_help()
        sys.exit('Error: Need to determine either --file or --request parameter')
    p=Pool(concurrency)
    requests=[]
    for xmlstr,reg in get_xmlstr_g(file=args.file,reg=args.request):
        uri,headers=get_requestinfo(xmlstr,reg.split(FIELD_SEPARATOR)[0])
        url='http://'+server+':'+str(port)+uri
        requests.append((url,xmlstr,headers,reg))
    xs=p.map(parallel_request,requests)

if __name__=='__main__':
    main()
