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
        self.schedules = None
        self.lastList = None
        self.lastEdit = None
        self.lastLink = None

    def getIniKey(self, key, myKeys, myIniKeys):
       if key not in myKeys:
           if key[0] not in myIniKeys: 
                   iniK = key[0] 
           else: 
              i = 1
              while (i < len(key) ) and (key[i] in myIniKeys):
                  i = i + 1
              if i < len(key): 
                  iniK = key[i]
              else:
                  iniK = 'j'
                  while iniK in myIniKeys:
                      iniK = chr(ord(iniK)+1)
           myKeys[key] = iniK
       else:
           iniK = myKeys[key]
       myIniKeys.append(iniK)
       pos = key.find(iniK)
       if pos>=0:
           nKey = key[:pos] + iniK.upper() + key[pos + 1:]
       else:
           nKey = iniK+key
       nKey = key+'-{}'.format(iniK)

       return iniK, nKey

    def checkConfigFiles(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + '/.rssBlogs')

        delayed = ['cache', 'buffer']
        content = ['twitter', 'facebook', 'mastodon', 'linkedin',
                'imgur','rss','forum', 'slack', 'gmail']
        types = ['posts','drafts']

        contentProviders = {'cache':[],'buffer':[], 'content': []}

        myKeys = {}
        myIniKeys = []
        
        self.available = {}

        for section in config.sections():
            url = config.get(section,'url')
            if 'posts' in config.options(section): 
                posts = config.get(section, 'posts') 
            else: 
                posts = 'posts' 
            for option in config.options(section):
                if option in delayed:
                    key = option 
                    iniK = key[0] 
                    myDelayed = config.get(section, option)
                    delayedList = []
                    if isinstance(myDelayed, str) and len(myDelayed)<5: 
                        for dd in content:
                            if ((dd[0] in myDelayed) 
                                    and (dd in config.options(section))): 
                                delayedList.append(dd)
                    elif isinstance(myDelayed, str): 
                            delayedList.append(myDelayed)

                    for dd in delayedList: 
                        nick = config.get(section, dd) 
                        toAppend = (config.get(section, 'url'), 
                                (dd,nick, posts))

                        iniK, nKey = self.getIniKey(key, myKeys, myIniKeys) 
                        if (iniK,nKey) not in self.available: 
                            self.available[(iniK, nKey)] = [] 
                        self.available[(iniK, nKey)].append((toAppend, '')) 
                        contentProviders[option].append(toAppend)
                if option in content:
                    key = option 
                    nick = config.get(section, option)
                    toAppend = (config.get(section, 'url'), 
                            (option, nick, posts))
                    iniK, nKey = self.getIniKey(key, myKeys, myIniKeys) 
                    if (iniK,nKey) not in self.available: 
                        self.available[(iniK, nKey)] = [] 
                    self.available[(iniK, nKey)].append((toAppend, '')) 

                    contentProviders['content'].append(toAppend)  
            if url.find('slack')>=0:
                key = 'slack'
                toAppend = (url, ('slack', url, posts))
                iniK, nKey = self.getIniKey(key, myKeys, myIniKeys) 
                if (iniK,nKey) not in self.available: 
                    self.available[(iniK, nKey)] = [] 
                self.available[(iniK, nKey)].append((toAppend, '')) 
                contentProviders['content'].append(toAppend)  
        self.log.debug("contentProviders %s"%str(contentProviders))
        # contentProviders
        # {'cache': [(url, (socialNetwork, nick , posts)), ...], 
        #'buffer': [(url, (socialNetwork, nick, posts)), ...], 
        #'content': [(url, (type of content, nick, 'posts')), ...]}

        #myKeys = {}
        #myIniKeys = []
        #
        #self.available = {}
        #for t in contentProviders:
        #    #print("key",t)
        #    for element in contentProviders[t]:
        #        #print("elem",element)
        #        if t in delayed:
        #            key = t
        #            iniK = key[0] 
        #        else:
        #            key = element[1][0] 
        #        if key not in myKeys:
        #            if key[0] not in myIniKeys: 
        #                    iniK = key[0] 
        #            else: 
        #               i = 1
        #               while (i < len(key) ) and (key[i] in myIniKeys):
        #                   i = i + 1
        #               if i < len(key): 
        #                   iniK = key[i]
        #               else:
        #                   iniK = 'j'
        #                   while iniK in myIniKeys:
        #                       iniK = chr(ord(iniK)+1)
        #            myKeys[key] = iniK
        #        else:
        #            iniK = myKeys[key]
        #        myIniKeys.append(iniK)
        #        pos = key.find(iniK)
        #        if pos>=0:
        #            nKey = key[:pos] + iniK.upper() + key[pos + 1:]
        #        else:
        #            nKey = iniK+key
        #        nKey = key+'-{}'.format(iniK)
        #        if (iniK,nKey) not in self.available: 
        #            self.available[(iniK, nKey)] = []
        #        self.available[(iniK, nKey)].append((element, '')) 

        self.log.debug("available %s"%str(self.available))

        myList = []
        for elem in self.available:
            component = '{}: {}'.format(elem[1], len(self.available[elem]))
            myList.append(component) 
            

        if myList:
            #self.config.append((myList,'',''))
            self.availableList = myList

    def checkConfigFiles2(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + '/.rssBlogs')

        delayed = ['cache', 'buffer']
        content = ['twitter', 'facebook', 'mastodon', 'linkedin',
                'imgur','rss','forum', 'slack', 'gmail']
        types = ['posts','drafts']

        contentProviders = {'cache':[],'buffer':[], 'content': []}

        for section in config.sections():
            url = config.get(section,'url')
            if 'posts' in config.options(section): 
                posts = config.get(section, 'posts') 
            else: 
                posts = 'posts' 
            for option in config.options(section):
                if option in delayed:
                    myDelayed = config.get(section, option)
                    delayedList = []
                    if isinstance(myDelayed, str) and len(myDelayed)<5: 
                        for dd in content:
                            if ((dd[0] in myDelayed) 
                                    and (dd in config.options(section))): 
                                delayedList.append(dd)
                    elif isinstance(myDelayed, str): 
                            delayedList.append(myDelayed)

                    for dd in delayedList: 
                        nick = config.get(section, dd) 
                        toAppend = (config.get(section, 'url'), 
                                (dd,nick, posts))
                        contentProviders[option].append(toAppend)
                if option in content:
                    nick = config.get(section, option)
                    toAppend = (config.get(section, 'url'), 
                            (option, nick, posts))
                    contentProviders['content'].append(toAppend)  
            if url.find('slack')>=0:
                toAppend = (url, ('slack', url, posts))
                contentProviders['content'].append(toAppend)  
        self.log.debug("contentProviders %s"%str(contentProviders))
        # contentProviders
        # {'cache': [(url, (socialNetwork, nick , posts)), ...], 
        #'buffer': [(url, (socialNetwork, nick, posts)), ...], 
        #'content': [(url, (type of content, nick, 'posts')), ...]}

        myKeys = {}
        myIniKeys = []
        
        self.available = {}
        for t in contentProviders:
            #print("key",t)
            for element in contentProviders[t]:
                #print("elem",element)
                if t in delayed:
                    key = t
                    iniK = key[0] 
                else:
                    key = element[1][0] 

                #if key not in myKeys:
                #    if key[0] not in myIniKeys: 
                #            iniK = key[0] 
                #    else: 
                #       i = 1
                #       while (i < len(key) ) and (key[i] in myIniKeys):
                #           i = i + 1
                #       if i < len(key): 
                #           iniK = key[i]
                #       else:
                #           iniK = 'j'
                #           while iniK in myIniKeys:
                #               iniK = chr(ord(iniK)+1)
                #    myKeys[key] = iniK
                #else:
                #    iniK = myKeys[key]
                #myIniKeys.append(iniK)
                #pos = key.find(iniK)
                #if pos>=0:
                #    nKey = key[:pos] + iniK.upper() + key[pos + 1:]
                #else:
                #    nKey = iniK+key
                #nKey = key+'-{}'.format(iniK)

                iniK, nKey = self.getIniKey(key, myKeys, myIniKeys)
                if (iniK,nKey) not in self.available: 
                    self.available[(iniK, nKey)] = []
                self.available[(iniK, nKey)].append((element, '')) 

        self.log.debug("available %s"%str(self.available))

        myList = []
        for elem in self.available:
            component = '{}: {}'.format(elem[1], len(self.available[elem]))
            myList.append(component) 
            

        if myList:
            #self.config.append((myList,'',''))
            self.availableList = myList


    #def checkConfigFiles2(self):
    #    config = configparser.ConfigParser()
    #    config.read(CONFIGDIR + '/.rssBlogs')

    #    dataSources = {}
    #    delayed = ['cache', 'buffer']
    #    options = ['twitter', 'facebook', 'mastodon', 'linkedin','imgur']
    #    types = ['posts','drafts']
    #    for section in config.sections():
    #        url = config.get(section, 'url')


    #        for option in config.options(section):
    #            value = config.get(section, option)
    #            if option in dataSources:
    #                dataSources[option].append((url, value))
    #            else:
    #                dataSources[option] = [(url, value)] 
    #                
    #        for prog in delayed:
    #            if prog in config.options(section): 
    #                values = dataSources[prog][-1][1]
    #                dataSources[prog] = dataSources[prog][:-1]
    #                for key in values: 
    #                    for option in config.options(section):
    #                        if (option[0] == key) and (option in options):
    #                            toAppend = (url, 
    #                                    (option, dataSources[option][-1][1]))
    #                            dataSources[prog].append(toAppend)

    #        for prog in types:
    #            if prog in config.options(section): 
    #                values = dataSources[prog][-1][1]
    #                dataSources[prog] = dataSources[prog][:-1]
    #                for key in values: 
    #                    for option in config.options(section):
    #                        if (option[0] == key) and (option in options):
    #                            toAppend = (url, 
    #                                    (option, dataSources[option][-1][1]))
    #                            dataSources[prog].append(toAppend)
 
    #        if url.find('slack')>=0: 
    #            #.rssBlogs
    #            # url: slack site
    #            # channel: 
    #            # destinations....
    #            option = 'slack'
    #            if option in dataSources:
    #                dataSources[option].append((url, url))
    #            else:
    #                dataSources[option] = [(url, url)] 
    #        elif url.find('imgur')>=0: 
    #            option = 'imgur'
    #            if option in dataSources:
    #                dataSources[option].append((url, url))
    #            else:
    #                dataSources[option] = [(url, url)] 

    #    myKeys = []
    #    self.available = {}
    #    myList = []
    #    for key in dataSources:

    #        if key[0] not in myKeys:
    #            iniK = key[0]
    #        else:
    #            i = 1
    #            while (i < len(key) ) and (key[i] in myKeys):
    #                i = i + 1
    #            if i < len(key): 
    #                iniK = key[i]
    #            else:
    #                iniK = 'j'
    #                while iniK in myKeys:
    #                    iniK = chr(ord(iniK)+1)
    #        myKeys.append(iniK)
    #        pos = key.find(iniK)
    #        if pos>=0:
    #            nKey = key[:pos] + iniK.upper() + key[pos + 1:]
    #        else:
    #            nKey = iniK+key
    #        nKey = key+'-{}'.format(iniK)
    #        self.available[(iniK, nKey)] = []
    #        component = '{}: {}'.format(nKey, len(dataSources[key]))
    #        myList.append(component)
    #        for i, element in enumerate(dataSources[key]):
    #            if isinstance(element, str): 
    #                self.available[(iniK, nKey)].append((element, '',str(i)))
    #            else: 
    #                self.available[(iniK, nKey)].append((element[0],element[1],str(i)))
    #    if myList:
    #        #self.config.append((myList,'',''))
    #        self.availableList = myList

    def addMore(self):
        response = "There are {0} lists. You can add more with command list add".format(len(self.config))
        return (response)

    @botcmd(split_args_with=None, template="buffer")
    def list_last(self, mess, args): 
        if self.lastList:
            yield "Last list: {}".format(str(self.lastList))
        else:
            yield "No lists"
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def list_read(self, mess, args):
        # Maybe define a flow?
        myList = []
        if not args:
            if self.lastList:
                myList = self.lastList
                pos = 0
                #yield "I'll mark as read in {}".format(str(myList))
            else:
                yield "Which list?"
                pos = -1
        else:
            arg1 = args[0]
            yield (arg1)
            for key in self.available: 
                if arg1[0].capitalize() == key[0].capitalize(): 
                    if arg1[1:].isdigit(): 
                        pos = int(arg1[1:] ) 
                        if pos < len(self.available[key]): 
                            myList.append(arg1)

        
        if pos >= 0:
            for element in myList:
                self.log.info("Element %s" % str(element))

                for key in self.available:
                    if element[0].lower() == key[0]: 
                        name, nick, profile, param = self.getSocialNetwork(key,element)
                        self.log.debug("Result: {} {} {}".format(element, 
                            profile, name))
                        self.log.debug("clients : {}".format(str(self.clients)))
                        profile = profile.split('-')[0]
                        if (element, profile,name) in self.clients:
                            link = self.clients[(element, profile, name)].getPosts()[-1][1]
                            #yield("name %s nick %s profile %s param %s"%(str(name), str(nick), str(profile), str(param)))
                            #yield("link %s"%link)
                            if profile.upper() == 'Forum'.upper():
                                # Not sure it makes sense for other types of
                                # content
                                self.log.debug("Param %s"%str(param))
                                if isinstance(param, tuple):
                                    param = param[0]
                                updateLastLink(param, link)
                            yield("Marked read {}".format(element))
        yield end()



    @botcmd
    def list_all(self, mess, args):
        """ List available services
        """
        if not self.available:
            self.checkConfigFiles()
        self.log.debug("Available: %s" % str(self.available))
        response = self.sendReply('', '', self.available, ['sent','pending'])
        for rep in response:
            yield(rep)
        return(end)

    @botcmd
    def list_show(self, msg, args):
        """ Show selected services in the quick list
        """
        if self.config: 
            yield self.config
        else:
            yield "None"
        yield end()

    @botcmd
    def list_del(self, msg, args):
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

    @botcmd(split_args_with=None)
    def list_add(self, msg, args):
        """ Add list of services to the quick list
        """
        if not self.available:
            self.checkConfigFiles()

        myList = []

        for arg in args:
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
        yield(end())

    @botcmd
    def list_list(self, msg, args):
        if not self.available:
            self.checkConfigFiles()

        response = [ self.availableList ]
        yield response
        yield end()

    def getSocialNetwork(self, key, element):
        pos = int(element[1])
        profile = key[1]
        self.log.debug("Pos %d",pos)
        self.log.debug("Prof %s",str(profile))
        self.log.debug("Key %s",str(key))
        self.log.debug("Avail %s",str(self.available[key]))
        self.log.debug("Avail %s",str(self.available[key][pos]))
        url = self.available[key][pos][0][0]
        nick = ((self.available[key][pos][0][0], 
                self.available[key][pos][0][1]))
        self.log.info("Nick %s",str(nick))
        name = nick
        param = nick
        if (key[0]=='g'): # or (key[0] == '2'):
            profile = 'gmail' #+element[1]
            name = url
            nick = name
            param = name
        #elif (key[0] == 'a') or (key[0] == 'b'):
        #    name = nick[1]+'@'+nick[0]
        #    self.log.info("Name: %s" % str(name))
        #    param = (url, nick)
        elif key[0] == 's':
            name = nick[0]
            nick = None
            param = None
        #elif key[0] == 'r':
        #    if isinstance(nick, str):
        #        if nick.find('http')>=0:
        #            param = nick
        #        else:
        #            param = url + nick
        elif type(nick) == tuple:
            nick = nick[1]
            name = nick
        elif nick.find('@') >= 0:
            nick, profile = nick.split('@')
            name = nick
        return (name, nick, profile, param)

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """ A command to show available posts in a list of available sites
        """

        self.log.debug("Posts posts %s" % (self.posts))
        self.log.debug("args %s" % str(args))

        pos = -1
        myList = []
        response = []
        self.posts = {}
        if not self.available:
            self.checkConfigFiles()

        if not args:
            args = ['0']

        arg1 = args[0]
        if arg1.isdigit(): 
            pos = int(arg1) 
            if pos < len(self.config): 
                myList = self.config[pos]
        else: 
            for key in self.available: 
                if arg1[0].capitalize() == key[0].capitalize(): 
                    if arg1[1:].isdigit(): 
                        pos = int(arg1[1:] ) 
                        if pos < len(self.available[key]): 
                            myList.append(arg1)

        self.log.debug("myList %s" % str(myList))
        self.lastList = myList

        if pos >= 0:
            for element in myList:
                self.log.debug("Edebug %s" % str(element))

                for key in self.available:
                    self.log.debug("key %s" % str(key))
                    self.log.debug("element %s" % str(element[0]))
                    self.log.debug("available %s" % str(self.available[key]))
                    if element[0].lower() == key[0]: 
                        self.log.debug("clients %s" % str(self.clients))
                        self.log.debug("SocialNetworks %s"%(str(self.getSocialNetwork(key,element))))
                        name, nick, profile, param = self.getSocialNetwork(key,element)
                        self.log.debug("Name %s Nick %s Profile %s Param %s"%(str(name), str(nick), str(profile), str(param)))
                        self.log.debug("Clients %s" % str(self.clients))
                        self.log.debug("Url: %s" % str(nick))
                        self.log.debug("Nick: %s" % str(nick))
                        try:
                            self.clients[(element, profile, name)].setPosts()
                        except:
                            import importlib
                            if profile.find('-')>=0:
                                profile = profile.split('-')[0]
                            moduleName = 'module'+profile.capitalize()

                            mod = importlib.import_module(moduleName) 
                            cls = getattr(mod, moduleName)
                            api = cls()
                            self.log.debug("Param: %s" % str(param))
                            api.setClient(param)
                            self.clients[(element, profile,name)] = api
                            self.clients[(element, profile,name)].setPosts()
                            self.log.debug("Posts %s"% str(self.clients[(element, profile,name)].getPosts()))
                            self.log.debug("Posts ->%s"% str(self.clients[(element, profile,name)].getPostsType()))

                            #client = module...

                        postsTmp = [] 
                        posts = [] 

                        if hasattr(self.clients[(element, profile, name)], 'getPostsType'): 
                            self.log.debug("Types %s"%(self.clients[(element, profile, name)].getPostsType()))


                            if self.clients[(element, profile, name)].getPostsType() == 'drafts': 
                                postsTmp = self.clients[(element, profile, name)].getDrafts() 
                            else: 
                                postsTmp = self.clients[(element, profile, name)].getPosts()
                        else:
                                postsTmp = self.clients[(element, profile, name)].getPosts
                        if postsTmp:
                            for (i, post) in enumerate(postsTmp):
                                date = self.clients[(element, profile, name)].getPostDate(post)

                                title = self.clients[(element, profile, name)].getPostTitle(post)
                                if date:
                                    title = '{} ({}='.format(title,date)

                                link = self.clients[(element, profile, name)].getPostLink(post)
                                posts.append((title, link, '{:2}'.format(i)))
                                self.log.info("I: %s %s %d"%(title,link,i))

                        self.posts[(element, profile, name)] = posts
                self.log.info("Posts posts %s" % (self.posts))
                response = self.sendReply(mess, args, self.posts, ['sent','pending'])
                self.log.debug("Response %s End" % response)


        if response: 
            for resp in response: 
                yield(resp) 
        else:
            yield(self.addMore())
        yield end()

    def execute(self, command, args):
        """Execute a command """
        resTxt = 'Executing: {}\n'.format(command)
        self.log.info(resTxt)
        updates = ''
        update = None
        res = None
        for profile in self.clients:
            self.log.debug("Executing in profile: %s" % str(profile))
            if args[:len(profile[0])] == profile[0] \
                  or (args[0] == '*') \
                  or (('*' in args) and (args[:1] == profile[0][:1])):
                # We need to do something for '*' commands
                update = self.clients[profile].selectAndExecute(command,args)
                if update: 
                    updates = '{}* {} ({})\n'.format(updates, update, 
                            profile[0])
                    update = None

        if updates: res = resTxt + '\n' + updates + '\n'

        return res 

    @botcmd
    def insert(self, mess, args):
        """A command to publish some update"""
        res = self.execute('insert', args)
        yield res 
        yield end()

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
    def edit_show(self, mess, args):
        """ Show the last edit commands
        """
        if 'argsArchive' in self:
            for arg in self['argsArchive'][-5:]:
                yield("- %s" % arg)
        else:
            yield('No cache')
        yield end()

    @botcmd
    def edit_link(self, mess, args):
        """A command to edit the link of some update"""
        if ' ' not in args:
            if self.lastLink:
                args = "{} {}".format(args,self.lastLink)
        res = self.execute('editl', args)    
        self.lastLink = args.split(" ",1)[1:][0]
        yield res
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        if ' ' not in args:
            if self.lastEdit:
                args = "{} {}".format(args,self.lastEdit)
        res = self.execute('edit', args)    
        self.addEditsCache(args)
        self.lastEdit = args.split(" ",1)[1:][0]
        yield res
        yield end()

    def addEditsCache(self, args):
        if 'argsArchive' not in self:
            self['argsArchive'] = []
        argsArchive = self['argsArchive']
        argsArchive.append(args)
        self['argsArchive'] = argsArchive


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
        tt = 'pending'
        for socialNetwork in updates.keys():
            self.log.info("Update social network %s " % str(socialNetwork))
            self.log.debug("Updates %s End" % updates[socialNetwork])
            theUpdates = []
            maxLen = 0
            for update in updates[socialNetwork]:
                if update:
                    if len(update)>0:
                        self.log.info("Update %s " % str(update))
                        if update[0]:
                            #if update[1] and (update[0] != update[1]): 
                            #    theUpdatetxt = '{} {}'.format(update[0],str(update[1])).replace('_','\_')
                            #else: 
                            theUpdatetxt = str(update[0]).replace('_','\_')
                            if theUpdatetxt.find('>')>=0:
                                tt = 'longer'

                            lenUpdate = len(theUpdatetxt[:60]) 
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
    
            self.log.info("socialNetwork ... %s" % str(socialNetwork))
            if theUpdates: 
                if len(socialNetwork)>2:
                    socialNetworktxt = socialNetwork[2][1].capitalize()+' (' + socialNetwork[2][0] + ' ' + socialNetwork[0]+')'
                    if len(socialNetworktxt)+3 > maxLen:
                        maxLen = len(socialNetworktxt)+3
                    if (1 + len(theUpdates))*maxLen > 1024:
                        numEle = 1024 / maxLen
                        import math
                        iniPos = 0
                        maxPos = math.trunc(numEle)
                        if self.schedules:
                            maxPos = self.schedules
                            numEle = self.schedules
                        while iniPos <= len(theUpdates): 
                            compResponse.append((tt, socialNetworktxt, theUpdates[iniPos:maxPos]))
                            iniPos = maxPos
                            maxPos = maxPos + math.trunc(numEle)
                    else:
                        compResponse.append((tt, socialNetworktxt, theUpdates))
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
    def prog_del(self, mess, args): 
        """ A command to delete some schedule
        """

        yield "Adding %s" % args
        for profile in self.clients:
            if 'delSchedules' in dir(self.clients[profile]): 
                self.clients[profile].delSchedules(args)
                yield "%s: (%s) %s" % (profile[0], profile[1], self.clients[profile].getHoursSchedules())
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_add(self, mess, args): 
        """ A command to add a publishing time in the schedule
        """
        yield "Adding %s" % args
        for profile in self.clients:
            if 'addSchedules' in dir(self.clients[profile]): 
                self.clients[profile].addSchedules(args)
                yield "%s: (%s) %s" % (profile[0], profile[1], self.clients[profile].getHoursSchedules())
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_show(self, mess, args): 
        """ A command to show scheduled times
        """
        for profile in self.clients:
            self.log.debug("Profile: %s" % str(profile))
            if 'setSchedules' in dir(self.clients[profile]): 
                self.clients[profile].setSchedules('rssToSocial')
                schedules = self.clients[profile].getHoursSchedules()
                if isinstance(schedules, str):
                    numS = len(schedules.split(','))
                else:
                    numS = len(schedules)
                    
                if numS:
                    self.schedules = numS
                yield "%s: (%s) %s Number: %s" % (profile[0], profile[1], schedules, numS)
        yield(end())

    @botcmd(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        pp = pprint.PrettyPrinter(indent=4)
        moduleBuffer.copyPost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield "Copied"
        yield end()

