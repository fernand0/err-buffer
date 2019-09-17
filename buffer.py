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

CONFIG_TEMPLATE = {'bufferapp' :'l', 'program' : 'tfm', 'gmail' : 'g', 'socialNetworks' : {'twitter':'fernand0', 'facebook':'Enlaces de fernand0', 'mastodon':'fernand0', 'linkedin': 'Fernando Tricas', 'gmail0':'fernand0@elmundoesimperfecto.com', 'gmail1':'ftricas@elmundoesimperfecto.com', 'gmail2':'ftricas@gmail.com' }
}


class Buffer(BotPlugin):
    """
    A plugin to manage our buffer account with the bot (at least some features,
this is not a translation for the whole API).
    """
    def get_configuration_template(self):
        """ configuration entries """
        config = CONFIG_TEMPLATE
        return config

    #def configure(self, configuration): 
    #    if configuration is not None and configuration != {}: 
    #        config = dict(chain(CONFIG_TEMPLATE.items(), 
    #            configuration.items())) 
    #    else: 
    #        config = CONFIG_TEMPLATE 
    #        
    #    super(Buffer, self).configure(config)

    def activate(self):
        """
        Triggers on plugin activation
        You should delete it if you're not using it to override any default behaviour
        """
        super(Buffer, self).activate()


        confBlog = configparser.ConfigParser() 
        confBlog.read(CONFIGDIR + '/.rssBlogs')

        section = "Blog7"
        self.socialNetworks = {}
        for socialNetwork in self.config['socialNetworks']:
            self.socialNetworks[socialNetwork] = self.config['socialNetworks'][socialNetwork]

        self.clients = {}
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.config['program']:
                client = moduleCache.moduleCache() 
                url = confBlog.get(section, 'url')
            if profile[0] in self.config['bufferapp']: 
                client = moduleBuffer.moduleBuffer() 
                url = confBlog.get(section, 'url')
            if profile[0] in self.config['gmail']:
                client = moduleGmail.moduleGmail() 
                url = ''
                self.log.info("Profile %s %s" % (profile,nick))
            client.setClient(url,(profile, nick)) 
            client.setPosts()
            self.clients[(profile, nick)] = client

        self.posts = {}
        self.nconfig = []
        #fileName = CONFIGDIR + '/.rssProgram'
        #if os.path.isfile(fileName): 
        #    with open(fileName,'r') as f: 
        #        self.files = f.read().split()
        #self.twitter = moduleTwitter.moduleTwitter()
        #self.twitter.setClient('fernand0')

    @botcmd
    def listC(self, mess, args):
        yield(self.checkConfigFiles())

    def checkConfigFiles(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + '/.rssBlogs')

        dataSources = {}
        delayed = ['program', 'bufferapp']
        delayed2 = ['cache', 'buffer']
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
                    
            #for prog in delayed:
            #    if prog in config.options(section): 
            #        for key in dataSources[prog][0][1]: 
            #            for option in config.options(section):
            #                if option[0] == key:
            #                    toAppend = dataSources[option][-1][1]+'@'+option
            #                    dataSources[prog].append(toAppend)
            #        dataSources[prog] = dataSources[prog][1:]

            for prog in delayed2:
                if prog in config.options(section): 
                    for key in dataSources[prog][0][1]: 
                        for option in config.options(section):
                            if option[0] == key:
                                toAppend = (url, (option, dataSources[option][-1][1]))
                                dataSources[prog].append(toAppend)
                    dataSources[prog] = dataSources[prog][1:]

            if url.find('slack')>=0: 
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
            self.available[(iniK, key)] = []
            for i, element in enumerate(dataSources[key]):
                 self.available[(iniK, key)].append((element,'',''))
        response = self.sendReply('', '', self.available, ['sent','pending'])
        return(response)

    @botcmd
    def showC(self, mess, args):
        if self.nconfig: 
            yield self.nconfig
        else:
            yield "None"

    @botcmd
    def delC(self, mess, args):

        if args:
            toDel = int(args[0])
        if toDel < len(self.nconfig):
            self.nconfig = self.nconfig[:toDel]+self.nconfig[toDel+1:]
        yield(self.nconfig)


    @botcmd
    def addC(self, mess, args):
        self.nconfig.append(args.split())
        yield(self.nconfig)


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
        for profile in self.clients:
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
        """A command to publish some update"""
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
            for update in updates[socialNetwork]:
                if update:
                    if len(update)>0:
                        self.log.info("Update %s " % str(update))
                        #self.log.debug("Update %s " % update[0])
                        if update[0]:
                            theUpdatetxt = str(update[0]).replace('_','\_')
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
            if theUpdates: 
                compResponse.append((tt, 
                    socialNetwork[0].capitalize()+' ('+socialNetwork[1]+')', theUpdates))
    
        return(compResponse)

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types) 
        compResponse = ""
        for rep in reps:
            response = tenv().get_template('buffer.md').render({'type': rep[0],
                        'nameSocialNetwork': rep[1], 
                        'updates': rep[2]})
            compResponse = compResponse + response

        return(compResponse)

    @botcmd(split_args_with=None, template="buffer")
    def delS(self, mess, args): 
        yield "Adding %s" % args
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if 'delSchedules' in dir(self.clients[(profile,nick)]): 
                self.clients[(profile,nick)].delSchedules(args)
                yield "%s: (%s) %s" % (profile, nick, self.clients[(profile,nick)].getHoursSchedules())


    @botcmd(split_args_with=None, template="buffer")
    def addS(self, mess, args): 
        yield "Adding %s" % args
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if 'addSchedules' in dir(self.clients[(profile,nick)]): 
                self.clients[(profile,nick)].addSchedules(args)
                yield "%s: (%s) %s" % (profile, nick, self.clients[(profile,nick)].getHoursSchedules())


    @botcmd(split_args_with=None, template="buffer")
    def listS(self, mess, args): 
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if 'setSchedules' in dir(self.clients[(profile,nick)]): 
                self.clients[(profile,nick)].setSchedules('rssToSocial')
                yield "%s: (%s) %s" % (profile, nick, self.clients[(profile,nick)].getHoursSchedules())

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):

        self.log.debug("Posts posts %s" % (self.posts))
        self.posts = {}
        if not args:
            args = '0'
        else:
            args = args[0]
        for element in self.nconfig[int(args)]:
            #yield element
            if not self.available:
                self.checkConfigFiles()

            for key in self.available:
                self.log.info("key %s" % str(key))
                if element[0].lower() == key[0]: 
                    profile = key[1]
                    nick = self.available[key][int(element[1])][0]
                    self.log.info("nick %s" % str(nick))
                    self.log.debug("socialNetworks %s %s"% (profile, nick))
                    posts = []
                    self.log.info("clients %s" % str(self.clients))
                    if key[0]=='g':
                        profile = 'gmail'+element[1]
                        name = nick
                    elif key[0] == 'a':
                        name = nick[1][1]+'@'+nick[1][0]
                    elif key[0] == 'k':
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
                        self.clients[(profile, nick)].setPosts()
                    except:
                        import importlib
                        moduleName = 'module'+profile.capitalize()
                        mod = importlib.import_module(moduleName) 
                        cls = getattr(mod, moduleName)
                        api = cls()
                        api.setClient(nick)
                        self.clients[(profile,name)] = api
                        self.clients[(profile,name)].setPosts()

                        #client = module...

                    if self.clients[(profile, name)].getPosts():
                        for post in self.clients[(profile, name)].getPosts():
                            title = self.clients[(profile, name)].getPostTitle(post)
                            link = self.clients[(profile, name)].getPostLink(post)
                            posts.append((title, link, ''))
                    self.posts[(profile, name)] = posts
                    continue


        self.log.debug("Posts posts %s" % (self.posts))

        response = self.sendReply(mess, args, self.posts, ['sent','pending'])
        self.log.debug("Response %s End" % response)
        yield(response)
        yield end()


    @botcmd(split_args_with=None, template="buffer")
    def listt(self, mess, args):

        self.log.debug("Posts posts %s" % (self.posts))
        self.posts = {}
        if args:
            url = args[0]
            yield(url)
            if 'slack' in url:
                # Code ad hoc for Slack. We should try to generalize this...
                import moduleSlack
                client = moduleSlack.moduleSlack()
                client.setSlackClient(os.path.expanduser('~/.mySocial/config/.rssSlack'))
                posts = []
                client.setPosts()
                if client.getPosts():
                    for post in client.getPosts():
                        title = client.getPostTitle(post)
                        link = client.getPostLink(post)
                        posts.append((title, link, ''))
                self.posts[('tmp', url)] = posts
        else:
            for profile in self.socialNetworks:
                nick = self.socialNetworks[profile]
                self.log.debug("socialNetworks %s %s"% (profile, nick))
                posts = []
                self.clients[(profile, nick)].setPosts()
                if self.clients[(profile, nick)].getPosts():
                    for post in self.clients[(profile, nick)].getPosts():
                        title = self.clients[(profile, nick)].getPostTitle(post)
                        link = self.clients[(profile, nick)].getPostLink(post)
                        posts.append((title, link, ''))
                self.posts[(profile, nick)] = posts

        self.log.debug("Posts posts %s" % (self.posts))

        response = self.sendReply(mess, args, self.posts, ['sent','pending'])
        self.log.debug("Response %s End" % response)
        yield(response)
        yield end()

    @botcmd(split_args_with=None)
    def sent(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        posts = moduleBuffer.listPosts(self.api, pp, "")
        response = self.sendReply(mess, args, posts, ['pending', 'sent'])
        self.log.debug(response)
        yield(response)
        yield end()

    @botcmd(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        pp = pprint.PrettyPrinter(indent=4)
        moduleBuffer.copyPost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield "Copied"
        yield end()

