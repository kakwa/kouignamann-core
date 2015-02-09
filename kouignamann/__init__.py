# -*- coding: utf-8 -*-

import os
import sys
import re
import yaml
from kouignamann.pyyamlwrapper import loadNoDump
from kouignamann.errors import RelationError, DumplicatedKey
from mako.template import Template

categories = ['partitionings','virtual-ips','hosts','hardwares', 'general']

class YamlLoad:

    def mergeNoCollision(self, d1, d2):
        merged = {}
        for d in [ d1, d2 ]:
            for k, v in d.items ():
                if k not in merged:
                    merged [k] = v
                else:
                    raise DumplicatedKey(k, self.subDir)
        return merged

    def load(self):
        ymlDir = os.path.join(self.inventory_dir, self.subDir)
        ymlFiles = []
        inv = {}
        for (dirpath, dirnames, filenames) in os.walk(ymlDir):
            def dirAppend(yml):
                return os.path.join(dirpath, yml)
            ymlFiles.extend(map(dirAppend,filenames))
        for ymlFile in ymlFiles:
            stream = open(ymlFile, 'r')
            try:
                content = loadNoDump(stream)
            except DumplicatedKey as e:
                raise DumplicatedKey(e.host, self.subDir)
            inv = self.mergeNoCollision(inv, content)
        return inv
        
class Partitionings(YamlLoad):
    def __init__(self, inventory_dir):
        self.subDir = 'partitionings'
        self.inventory_dir = inventory_dir

class VirtualIps(YamlLoad):
    def __init__(self, inventory_dir):
        self.subDir = 'virtual-ips'
        self.inventory_dir = inventory_dir

class Hosts(YamlLoad):
    def __init__(self, inventory_dir):
        self.subDir = 'hosts'
        self.inventory_dir = inventory_dir

class Hardwares(YamlLoad):
    def __init__(self, inventory_dir):
        self.subDir = 'hardwares'
        self.inventory_dir = inventory_dir

class General(YamlLoad):
    def __init__(self, inventory_dir):
        self.subDir = 'general'
        self.inventory_dir = inventory_dir

class Inventory:
    def __init__(self, inventory_dir):
        self.hostsObj          = Hosts(inventory_dir)
        self.generalObj        = General(inventory_dir)
        self.hardwaresObj      = Hardwares(inventory_dir)
        self.virtualipsObj     = VirtualIps(inventory_dir)
        self.partitioningsObj  = Partitionings(inventory_dir)
        self.load()

    def checkRelation(self, hosts, subinv, key):
        for host in hosts:
            if not hosts[host][key] in subinv:
                raise RelationError(host, key)
            else:
                hosts[host][key] = subinv[hosts[host][key]]

    def getPartition(self, host):
        return self.partitionings[self.hosts[host]['partitioning']]

    def getHardware(self, host):
        return self.partitionings[self.hosts[host]['hardware']]

    def _search(self, data, filters):
        if type(data) is list:
            for item in data:
                if self._search(item, filters):
                    return True
        elif type(data) is dict:
            for key in data:
                if key in filters and re.match(filters[key], data[key]):
                    return True
                elif type(data[key]) is list or type(data[key]) is dict:
                    if self._search(data[key], filters):
                        return True
        else:
            return False

    def search(self, filters, node=None):
        matchHost = {}
        if node is None:
            for host in self.hosts:
                if self._search(self.hosts[host], filters):
                    matchHost[host]=self.hosts[host]
        else:
            if self._search(self.hosts[node], filters):
                matchHost[node]=self.hosts[node]
        return matchHost

    def _select(self, data, fields):
        ret = []
        if type(data) is list:
            ret = []
            for item in data:
                tmp = self._select(item, fields)
                if tmp:
                    ret.append(tmp)
        elif type(data) is dict:
            ret = {}
            for key in data:
                if key in fields:
                    ret[key] = data[key]
                else:
                    tmp = self._select(data[key], fields)
                    if tmp:
                        ret[key] = tmp
        return ret

    def select(self, data, fields, node=None):
        matchHost = {}
        if node is None:
            for host in data:
                tmp = self._select(data[host], fields)
                if tmp:
                    matchHost[host]=tmp
        else:
            tmp = self._select(data[node], fields)
            if tmp:
                matchHost[node]=tmp
        return matchHost

    def format(self, document):
        return yaml.dump(document, default_flow_style=False)

    def templateRender(self, template, pattern='${host.hostname}', node=None, mode='byhost'):
        mytemplate = Template(filename=template)
        fileNameTemplate = Template(pattern)
        if mode == 'byhost':
            result = {}
            if node is None:
                for host in self.hosts:
                    fileName=fileNameTemplate(general=self.general, \
                            host=self.hosts[host], virtualIps=self.virtualIps)
                    result[fileName]=mytemplate.render(general=self.general, \
                            host=self.hosts[host],  virtualIps=self.virtualIps)
            else:
                if self._search(self.hosts[node], filters):
                    fileName=fileNameTemplate(general=self.general, \
                            host=self.hosts[node], virtualIps=self.virtualIps)
                    result[fileName]=mytemplate.render(general=self.general, \
                            host=self.hosts[node])
        elif mode == 'global':
            fileName=fileNameTemplate(general=self.general, \
                    host=self.hosts, virtualIps=self.virtualIps)
            result=mytemplate.render(general=self.general, hosts=self.hosts, \
                    virtualIps=self.virtualIps)
        return result


                    
    def load(self):
        tmp_hosts          = self.hostsObj.load()
        tmp_general        = self.generalObj.load()
        tmp_hardwares      = self.hardwaresObj.load()
        tmp_virtualips     = self.virtualipsObj.load()
        tmp_partitionings  = self.partitioningsObj.load()
        self.checkRelation(tmp_hosts, tmp_hardwares, 'hardware')
        self.checkRelation(tmp_hosts, tmp_partitionings, 'partitioning')
        self.hosts         = tmp_hosts
        self.general       = tmp_general
        self.hardwares     = tmp_hardwares
        self.virtualips    = tmp_virtualips
        self.partitionings = tmp_partitionings

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
