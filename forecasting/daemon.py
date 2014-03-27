#!/usr/bin/env python

import sys
import os
import time
import atexit
import datetime
from signal import SIGTERM

from model import Model

# 'nam:\n  database: {database: weather, user: salexander}\n  fields: [tmp2m]\n  geos: {k: 4, lat: 40, lon: -100}\n'

class DaemonParent:
    modelname = None
    database = None
    geos = None
    fields = None
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process       
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

class Daemon(DaemonParent):

    config = None

    def run(self):
        print 'running Daemon'

        # check that it has all of the needed fields
        if all([i in config for i in ('model','database','fields')]):
            print 'its got all the needed fields'
        else:
            print 'youre missing some important fields... make sure you have model, database, and fields'
            raise Exception('Config file missing item')

        m = Model(self.config['model'])
        m.connect(**self.config['database'])
        latest = m.getlatesttime()
        args = {}
        if 'geos' in config:
            args['geos'] = config['geos']
        else:
            args['geos'] = None
        if 'pressure' in config:
            args['pressure'] = config['pressure']
        else:
            args['pressure'] = None

        if 'calculatedfields' in config:
            print config
            for field in config['calculatedfields']:
                for key, value in field.items():
                    m.addcalculatedfield(key,value['dependents'],value['calculation'])

        ntries = 0
        ntriesmax = max(int(config['modelint']/config['poll']*2/3),1)
        print "We'll try each download up to four times."
  
        while True:
            
            starttime = time.time()

            url = m._createurl(latest)
            check = m._checkurl(url)
            if check:
                print 'The new data is available! Downloading ...'
                try:
                    if ntries < ntriesmax:
                        ntries = ntries+1
                        m.transfer(config['fields'],latest,**args)
                    latest = latest + datetime.timedelta(seconds=self.config['modelint'])
                    ntries = 0
                except:
                    print 'An error occured in downloading the data... it might not actually be available'
                print 'The next run will happen at %s' % latest
            else:
                print 'No new data. Sad face'
            endtime = time.time()
            pausetime = max(
                            config['poll'] - ( endtime - starttime ),
                            0
                            )
            print 'Pausing for %d seconds' % pausetime
            time.sleep(pausetime)


if __name__ == '__main__':
    # if we're called from the commandline, let's try a couple of things:
    #   no arguments: start up with reasonable defaults
    #   arguments: check if it's a yaml file with all the cool stuff


    if len(sys.argv) < 2:
        pid=    os.path.abspath('./daemon.pid')
        stdin = os.path.abspath('./in.log')
        stdout= os.path.abspath('./out.log')
        stderr= os.path.abspath('./err.log')

        d = Daemon(pid, stdin, stdout, stderr)
        config = {}

        # model info
        config['model'] = 'rap'
        config['database'] = {'database': 'weather', 'user': 'salexander'}
        config['fields'] = ['tmp2m','vgrd10m','ugrd10m','gustsfc']
        config['geos'] = {'n': 42, 's': 35, 'e':-100, 'w':-113}
        config['modelint'] = 3600*6 # 6 hours
        config['poll']     = 600    # 10 minutes

        d.config = config
        d.start()
    elif os.path.isfile(sys.argv[1]) and sys.argv[1].split('.')[-1] == 'yaml':
        import yaml
        # treat it as a yaml file
        try:
            config = yaml.load(open(sys.argv[1],'r').read())
        except:
            raise Exception('Could not load yaml information')

        if all([i in config for i in ['model','fields','modelint','poll']]):
            if 'pid' in config:
                pid=os.path.abspath(config['pid'])
            else:
                pid = os.path.abspath('./daemon.pid')

            startup = {}
            for i in ['stdin','stdout','stderr']:
                if i in config:
                    startup[i] = os.path.abspath(config[i])

            d = Daemon(pid,**startup)

            print 'Starting daemon'
            d.config = config
            d.start()
        else:
            print 'Make sure you have the model, fields, modelint, and poll fields. Youll often need a database field as well'
            raise Exception('Badly configured file')

    else:
        print sys.argv[1].split('.')
        print 'I dont understand what youre saying. I accept a yaml file as an imput on the command line. Make sure it ends in yaml.'
        print 'Exiting ...'
        raise Exception('Unknown input file')

