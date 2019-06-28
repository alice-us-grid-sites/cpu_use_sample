#!/usr/bin/env python

"""

basic structure I use to build simple packages

"""

import sys
if sys.version[0:3] < '2.6':
    print "Python version 2.6 or greater required (found: %s)." % \
        sys.version[0:5]
    sys.exit(-1)

import math, os, pprint, re, shlex, shutil, socket, stat, time
from shutil import copyfile
from datetime import datetime
from signal import alarm, signal, SIGALRM, SIGKILL, SIGTERM
from subprocess import Popen, PIPE, STDOUT
import argparse
from ConfigParser import RawConfigParser
from process_commands import process_commands
import json

#---- Gobal defaults ---- Can be overwritten with commandline arguments 

SOME_TEXT="this is a test"
TIME_TO_NOTIFY = 10
NFINAL=5
CATKEYS = ['R.0','R.25','R.50','R.75','S.0','S.25','S.50','S.75','D.0','D.25','D.50','D.75']
DATAKEYS=['count','pcpu','pmem']
AVALS=[75.0,50.0,25.0,0.0]
UNAME='rjporter'
PNAME='root'

#----------------------------------------

class my_app:
    """ application class """

    def __init__(self, args):
        self.args = args
        self.username = args.username
        self.procname = args.procname
        self.nfinal = args.nfinal
        self.nloop = 0
        self.catkeys = CATKEYS
        self.datakeys = DATAKEYS
        self.avals = AVALS
        self.data_dict={}
        for key in self.catkeys:
            self.data_dict[key] = {}
        self.proc_c = process_commands(args.verbosity)
        self.zerodata()


#---
    def zerodata(self):
        for key in self.catkeys:
            for dkey in self.datakeys:
                self.data_dict[key][dkey]=0
        usercpu = 0.0
        nl=[int(self.data_dict[k]['count']) for k in self.catkeys]
        self.proc_c.log("%d %.2f %d %d %d %d %d %d %d " % (self.nloop,usercpu, nl[0],nl[1],nl[2],nl[3],nl[4],nl[5],nl[6]), 1)

#------------------------
    def _unixT(self):
        return int(time.mktime((datetime.now()).timetuple()))

#-------------------------
    def eval_command(self):

        cmd = "top -b -d1 -n1"
        s, o, e = self.proc_c.comm(cmd)
        if s == 0:
            flist = o.splitlines()
            for aline in flist:
                yield aline


    def output(self,usercpu):


        total_aeff = 0.0
        aeff = 0.0
        total_njobs = 0.0
        self.proc_c.log("will print output %.2f" % (usercpu),1)
        for key in self.catkeys:
            nval=float(self.data_dict[key]['count'])
            if nval > 0.0:
             #   self.data_dict[key]['pcpu']/=nval
             #   self.data_dict[key]['pmem']/=nval
                total_njobs += nval
                total_aeff += self.data_dict[key]['pcpu']

       # self.proc_c.log("seff=%.2f ntot=%.2f" % (total_aeff, total_njobs), 0)
        if total_njobs > 0.0:
            aeff = total_aeff/total_njobs
        nl=[int(self.data_dict[k]['count']) for k in self.catkeys]
        self.proc_c.log("%d %.2f %.2f %d %d %d %d %d %d %d %d %d %d %d %d" % (self.nloop,usercpu,aeff, nl[0],nl[1],nl[2],nl[3],nl[4],nl[5],nl[6],nl[7],nl[8],nl[9],nl[10],nl[11]), 0)
        self.zerodata()
#
#        self.proc_c.log("%d %.2f %d %d %d %d %d %d %d %d %d %d %d %d " % (self.nloop,usercpu,[self.data_dict[k]['count'] for k in self.catkeys]), 0)


#-------------------------
    def fill_element(self, ary):
        if self.username in ary[1] and self.procname in ary[11]:
            if ('R' not in ary[7]) and ('S' not in ary[7]) and  ('D' not in ary[7]):
                return
            cpu =float(ary[8])
            for val in self.avals:
                if cpu >= val:
                    sval = str(int(val))
                    key='.'.join([ary[7],sval])
                    self.proc_c.log('Key = %s' % (key),2)
                    self.data_dict[key]['count']+=1
                    self.data_dict[key]['pcpu']+= float(ary[8])
                    self.data_dict[key]['pmem']+= float(ary[9])
                    self.proc_c.log('Key = %s' % (key),2)
                    break


#-------------------------
    def process_command(self):

        in_proc_list=False
        usercpu=0.0
        for aline in self.eval_command():
            self.proc_c.log("LINE: %s" % (aline), 2)
            arr_line = aline.split()
            if len(arr_line) == 0:
                continue
            if in_proc_list:
                self.fill_element(arr_line)
                continue
            if 'PID' in arr_line[0]:
                in_proc_list=True
            if 'Cpu' in arr_line[0]:
                if "%" in arr_line[1]:
                    usercpu = float(arr_line[1].split('%')[0])
                else:
                    usercpu = float(arr_line[1])

        self.output(usercpu)

#-----------------------------------
    def go(self):

#       A tally for keeping count of various stats
#        tally = dict(pico_cp_tries=0, pico_cp_succ = 0, pico_cp_fail = 0, 
#                    hpss_tries = 0, hpss_succ = 0, hpss_fail =0)
#        self.proc_c.log("MYTEXT = %s" % (self.some_text), 0)

        nloop = 0
        notdone=True
        cmd="top -n1 \| grep Cpu \| awk '{print $2}'"

           
        while notdone:
            self.nloop+=1
            self.process_command()
            time.sleep(1)
            if nloop >= self.nfinal:
                notdone = False

def main():
    """ Generic program structure to parse args, initialize and start application """
    desc = """ prepare files for transfer """
    
    p = argparse.ArgumentParser(description=desc, epilog="None")
    p.add_argument("-n",dest="nfinal",default=NFINAL,help="number of loops")
    p.add_argument("-u",dest="username",default=UNAME,help="select user name")
    p.add_argument("-p",dest="procname",default=PNAME,help="select process name")

    p.add_argument("--time-to-notify",dest="time_to_notify",default=TIME_TO_NOTIFY,help="how frequent to email notice")
    p.add_argument("-v", "--verbose", action="count", dest="verbosity", default=0,help="be verbose about actions, repeatable")
    p.add_argument("--config-file",dest="config_file",default="None",help="override any configs via a json config file")

    args = p.parse_args()

#-------- parse config file to override input and defaults
    val=vars(args)
    if not args.config_file == "None":
        try:
            print "opening ", args.config_file
            with open(args.config_file) as config_file:
                configs=json.load(config_file)
            for key in configs:
                if key in val:
                    if isinstance(configs[key],unicode):
                        val[key]=configs[key].encode("ascii")
                    else:
                        val[key]=configs[key]
        except:
            p.error(" Could not open or parse the configfile ")
            return -1

    try:
        myapp = my_app(args)
        return(myapp.go())
    except (Exception), oops:
        if args.verbosity >= 2:
            import traceback
            traceback.print_exc()
        else:
            print oops
            return -1
                                                                                                                                                                
if __name__ == "__main__":                      
    sys.exit(main())


