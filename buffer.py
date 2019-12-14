from errbot import BotPlugin, botcmd, webhook, backends
from errbot.templating import tenv
import moduleBuffer
import moduleCache
import moduleGmail
import moduleTwitter
import configparser
import logging
import os
import pprint
from buffpy.models.update import Update
from buffpy.managers.profiles import Profiles
from buffpy.managers.updates import Updates
from buffpy.api import API

from configMod import *

def end(msg=""):
    return("END"+msg)



class Buffer(BotPlugin):
    """
    A plugin to manage our buffer account with the bot (at least some features, this is not a translation for the whole API).
    """

    def activate(self):
        """
        Triggers on plugin activation
        You should delete it if you're not using it to override any default behaviour
        """
        super(Buffer, self).activate()

        self.clients = {}
        self.posts = {}
        self.config = []
        self.available = None

    @botcmd
    def listC(self, mess, args):
        """ List available services
        """
        if not self.available:
            self.checkConfigFiles()
        self.log.debug("Available: %s" % str(self.available))
        response = self.sendReply('', '', self.available, ['sent','pending'])
        for rep in response:
            yield(rep)

    def checkConfigFiles(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + '/.rssBlogs')

        dataSources = {}
        delayed = ['cache', 'buffer']
        for section in config.sections():
            url = config.get(section, 'url')

            for option in config.options(section):
                value = config.get(section, option)
                if option == 'rssfeed':
                    option = 'rss'
                    value = url+value
                if option in dataSources:
                    dataSources[option].append((url, value))
                else:
                    dataSources[option] = [(url, value)] 
                    
            for prog in delayed:
                if prog in config.options(section): 
                    for key in dataSources[prog][0][1]: 
                        for option in config.options(section):
                            if option[0] == key:
                                toAppend = (url, (option, dataSources[option][-1][1]))
                                dataSources[prog].append(toAppend)
                    dataSources[prog] = dataSources[prog][1:]

            if url.find('slack')>=0: 
                #.rssBlogs
                # url: slack site
                # channel: 
                # destinations....
                option = 'slack'
                if option in dataSources:
                    dataSources[option].append((url, url))
                else:
                    dataSources[option] = [(url, url)] 

        config = configparser.ConfigParser()
        config.read(CONFIGDIR + '/.oauthG.cfg')

        for section in config.sections(): 
            user = config.get(section, 'user')
            server = config.get(section, 'server')
            if 'gmail' in dataSources: 
                dataSources['gmail'].append(user+'@'+server) 
            else: 
                dataSources['gmail'] = [user+'@'+server]

        myKeys = []
        self.available = {}
        for key in dataSources:
            if key[0] not in myKeys:
                iniK = key[0]
            else:
                i = 1
                while (i < len(key) ) and (key[i] in myKeys):
                    i = i + 1
                if i < len(key): 
                    iniK = key[i]
                else:
                    iniK = 'j'
                    while iniK in myKeys:
                        iniK = chr(ord(iniK)+1)
            myKeys.append(iniK)
            pos = key.find(iniK)
            if pos>=0:
                nKey = key[:pos] + iniK.upper() + key[pos + 1:]
            else:
                nKey = iniK+key
            self.available[(iniK, nKey)] = []
            for i, element in enumerate(dataSources[key]):
                 self.available[(iniK, nKey)].append((element,'',''))
        self.log.debug("dataSources %s" % str(dataSources))

    @botcmd
    def showC(self, mess, args):
        """ Show selected services in the quick list
        """
        if self.config: 
            yield self.config
        else:
            yield "None"

    def addMore(self):
        response = "There are {0} lists. You can add more with command addC.".format(len(self.config))
        return (response)

    @botcmd
    def delC(self, mess, args):
        """ Delete a list of services from the quick list
        """

        pos = 0
        if args: 
            if args[0].isdigit(): 
                pos = int(args[0])

        if pos < len(self.config):
            self.config = self.config[:pos]+self.config[pos+1:]
            response = self.config
        else:
            response = self.addMore()

        yield(response)
        yield(end())

    @botcmd
    def addC(self, mess, args):
        """ Add list of services to the quick list
        """

        if not self.available:
            self.checkConfigFiles()

        myList = []

        for arg in args.split():
            for key in self.available:
                if arg[0].capitalize() == key[0].capitalize(): 
                    if arg[1:].isdigit():
                        pos = int(arg[1:] )
                        if pos < len(self.available[key]): 
                            # Silently discard not valid args 
                            myList.append(arg)

        if myList: 
            self.config.append(myList)

        yield(self.config)

    def selectPost(self, pp, post):
        self.log.debug("Selecting %s" % pp.pformat(post))
        i = 0
        profMov = ""    

        while post[i].isalpha():
            profMov = profMov + post[i]
            i = i + 1
    
        j = int(post[-1])
        if post[-2].isdigit():
            # Qualifier when there are several accounts 
            return(profMov, j, post[-2])
        else: 
            return(profMov, j)


    def execute(self, command, args):
        """Execute a command """
        resTxt = 'Executing: {}\n'.format(command)
        updates = ''
        update = None
        res = None
        for profile in self.clients:
            self.log.debug("Profile: %s" % str(profile))
            if args[:len(profile[0])] == profile[0] or (args[0] == '*' and False):
                # We need to do something for '*' commands
                update = self.clients[profile].selectAndExecute(command,args)
                if update: 
                    updates = updates + "* " + update + '\n'
                    update = None

        if updates: res = resTxt + '\n' + updates + '\n'

        return res 

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""
        res = self.execute('publish', args)
        yield res 
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to show the content of some update"""
        res = self.execute('show', args)    
        yield res 
        yield end()

    @botcmd
    def editl(self, mess, args):
        """A command to edit the link of some update"""
        res = self.execute('editl', args)    
        yield res
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        res = self.execute('edit', args)    
        self.addEditsCache(args)
        yield res
        yield end()

    def addEditsCache(self, args):
        if 'argsArchive' not in self:
            self['argsArchive'] = []
        argsArchive = self['argsArchive']
        argsArchive.append(args)
        self['argsArchive'] = argsArchive

    @botcmd
    def showE(self, mess, args):
        """ Show the last edit commands
        """
        if 'argsArchive' in self:
            for arg in self['argsArchive'][-5:]:
                yield("- %s" % arg)
        else:
            yield('No cache')
        yield end()

    @botcmd
    def move(self, mess, args):
        """A command to move some update"""
        res = self.execute('move', args)    
        yield res
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        res = self.execute('delete', args)    
        yield(res)
        yield end()

    def prepareReply(self, updates, types):
        compResponse = [] 
        self.log.debug("Pposts %s" % updates)
        self.log.debug("Keys %s" % updates.keys())
        for socialNetwork in updates.keys():
            self.log.debug("Update social network %s " % str(socialNetwork))
            self.log.debug("Updates %s End" % updates[socialNetwork])
            theUpdates = []
            maxLen = 0
            for update in updates[socialNetwork]:
                if update:
                    if len(update)>0:
                        self.log.debug("Update %s " % str(update))
                        if update[0]:
                            theUpdatetxt = str(update[0]).replace('_','\_')
                            lenUpdate = len(theUpdatetxt[:40]) 
                            if lenUpdate > maxLen: 
                                maxLen = lenUpdate
                        else:
                            # This should not happen
                            theUpdatetxt = ''
                        theUpdates.append((theUpdatetxt, update[1], update[2])) 
                            #time.strftime("%Y-%m-%d-%H:%m", 
            if updates[socialNetwork]: 
                if theUpdates[0][0] != 'Empty': 
                    socialTime = theUpdates[0][2] 
                else: 
                    socialTime = ""
            else:
                socialTime = ""
    
            tt = 'pending'
            self.log.info("socialNetwork ... %s" % str(socialNetwork))
            if theUpdates: 
                if len(socialNetwork)>2:
                    socialNetworktxt = socialNetwork[1].capitalize()+' (' + socialNetwork[0] + ' ' + socialNetwork[2]+')'
                    if len(socialNetworktxt)+3 > maxLen:
                        maxLen = len(socialNetworktxt)+3
                    if (1 + len(theUpdates))*maxLen > 1024:
                        numEle = 1024 / maxLen
                        import math
                        iniPos = 0
                        maxPos = math.trunc(numEle)
                        while iniPos <= len(theUpdates): 
                            compResponse.append((tt, socialNetworktxt, theUpdates[iniPos:maxPos]))
                            iniPos = maxPos
                            maxPos = maxPos + math.trunc(numEle)
                    else:
                        compResponse.append((tt, socialNetworktxt, theUpdates))



                    #compResponse.append((tt, socialNetworktxt, theUpdates))
                else:
                    compResponse.append((tt, 
                        socialNetwork[0].capitalize()+' (' + socialNetwork[1]+')', theUpdates))
    
        return(compResponse)

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types) 
        compResponse = ""
        for rep in reps:
            response = tenv().get_template('buffer.md').render({'type': rep[0],
                        'nameSocialNetwork': rep[1], 
                        'updates': rep[2]})
            yield(response)

    @botcmd(split_args_with=None, template="buffer")
    def delS(self, mess, args): 
        """ A command to delete some schedule
        """

        yield "Adding %s" % args
        for profile in self.clients:
            if 'delSchedules' in dir(self.clients[profile]): 
                self.clients[profile].delSchedules(args)
                yield "%s: (%s) %s" % (profile[0], profile[1], self.clients[profile].getHoursSchedules())

    @botcmd(split_args_with=None, template="buffer")
    def addS(self, mess, args): 
        """ A command to add a publishing time in the schedule
        """
        yield "Adding %s" % args
        for profile in self.clients:
            if 'addSchedules' in dir(self.clients[profile]): 
                self.clients[profile].addSchedules(args)
                yield "%s: (%s) %s" % (profile[0], profile[1], self.clients[profile].getHoursSchedules())

    @botcmd(split_args_with=None, template="buffer")
    def listS(self, mess, args): 
        """ A command to show scheduled times
        """
        for profile in self.clients:
            self.log.debug("Profile: %s" % str(profile))
            if 'setSchedules' in dir(self.clients[profile]): 
                self.clients[profile].setSchedules('rssToSocial')
                yield "%s: (%s) %s" % (profile[0], profile[1], self.clients[profile].getHoursSchedules())
        yield(end())

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """ A command to show available posts in a list of available sites
        """

        self.log.debug("Posts posts %s" % (self.posts))
        self.posts = {}

        pos = 0
        self.log.info("args %s" % str(args))

        myList = []
        response = None
        if args: 
            arg1 = args[0]
            if arg1.isdigit(): 
                pos = int(arg1) 
                if pos < len(self.config):
                    myList = self.config[pos]
            else: 
                if not self.available:
                    self.checkConfigFiles()

                for key in self.available: 
                    if arg1[0].capitalize() == key[0].capitalize(): 
                        if arg1[1:].isdigit(): 
                            pos = int(arg1[1:] ) 
                            if pos < len(self.available[key]): 
                                myList.append(arg1)
        else:
            pos = 0
            self.log.info("config %s" % str(self.config))
            if pos < len(self.config):
                myList = self.config[pos] 
            else: 
                response = [ self.addMore() ]
                myList = []
        self.log.info("myList %s" % str(myList))

        for element in myList:
            self.log.debug("Element %s" % str(element))
            #yield element
            if not self.available:
                self.checkConfigFiles()

            for key in self.available:
                self.log.debug("key %s" % str(key))
                if element[0].lower() == key[0]: 
                    self.log.debug("Element: %s" % element)
                    profile = key[1]
                    self.log.debug("Profile: %s" % profile)
                    pos = int(element[1])
                    nick = self.available[key][pos][0]
                    self.log.debug("Nick: %s" % str(nick))
                    posts = []
                    self.log.debug("clients %s" % str(self.clients))
                    if (key[0]=='g'): # or (key[0] == '2'):
                        profile = 'gmail' #+element[1]
                        name = nick
                        nick = (profile+element[1], name)
                    elif (key[0] == 'a') or (key[0] == 'b'):
                        name = nick[1][1]+'@'+nick[1][0]
                    elif key[0] == 's':
                        name = nick[0]
                        nick = None
                    elif type(nick) == tuple:
                        nick = nick[1]
                        name = nick
                    elif nick.find('@') >= 0:
                        nick, profile = nick.split('@')
                        name = nick
                    try:
                        self.clients[(element, profile, nick)].setPosts()
                    except:
                        self.log.debug("element %s", str(element))
                        self.log.debug("profile %s", str(profile))
                        self.log.debug("nick %s", str(nick))
                        import importlib
                        moduleName = 'module'+profile.capitalize()
                        mod = importlib.import_module(moduleName) 
                        cls = getattr(mod, moduleName)
                        api = cls()
                        api.setClient(nick)
                        self.clients[(element, profile,name)] = api
                        self.clients[(element, profile,name)].setPosts()

                        #client = module...

                    if self.clients[(element, profile, name)].getPosts():
                        for (i, post) in enumerate(self.clients[(element, profile, name)].getPosts()):
                            title = self.clients[(element, profile, name)].getPostTitle(post)
                            link = self.clients[(element, profile, name)].getPostLink(post)
                            posts.append((title, link, '{:2})'.format(i)))
                    self.posts[(element, profile, name)] = posts
                    continue
            self.log.debug("Posts posts %s" % (self.posts))
            response = self.sendReply(mess, args, self.posts, ['sent','pending'])
            self.log.debug("Response %s End" % response)


        if response: 
            for resp in response: 
                yield(resp) 
        else:
            yield(self.addMore())
        yield end()

    #@botcmd(split_args_with=None)
    #def sent(self, mess, args):
    #    pp = pprint.PrettyPrinter(indent=4)
    #    posts = moduleBuffer.listPosts(self.api, pp, "")
    #    response = self.sendReply(mess, args, posts, ['pending', 'sent'])
    #    self.log.debug(response)
    #    yield(response)
    #    yield end()

    @botcmd(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        pp = pprint.PrettyPrinter(indent=4)
        moduleBuffer.copyPost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield "Copied"
        yield end()

