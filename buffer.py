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
    A plugin to manage our buffer account with the bot (at least some features,
this is not a translation for the whole API).
    """

    def activate(self):
        """
        Triggers on plugin activation
        You should delete it if you're not using it to override any default behaviour
        """
        super(Buffer, self).activate()

        confBlog = configparser.ConfigParser() 
        confBlog.read(CONFIGDIR + '/.rssBlogs')

        section = "Blog7"
        url = confBlog.get(section, 'url')
        self.socialNetworks = {'twitter':'fernand0', 
                'facebook':'Enlaces de fernand0', 
                'mastodon':'fernand0',
                'linkedin': 'Fernando Tricas',
                'gmail0':'fernand0@elmundoesimperfecto.com',
                'gmail1':'ftricas@elmundoesimperfecto.com',
                'gmail2':'ftricas@gmail.com'}

        self.bufferapp ='l'
        self.program ='tfm'
        self.gmail = 'g'
        self.clients = {}
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program:
                client = moduleCache.moduleCache()
            if profile[0] in self.bufferapp: 
                client = moduleBuffer.moduleBuffer() 
                url = None
            if profile[0] in self.gmail:
                client = moduleGmail.moduleGmail() 
                url = ''
            self.log.info("Profile %s %s" % (profile,nick))
            client.setClient(url,(profile, nick)) 
            client.setPosts()
            self.clients[(profile, nick)] = client

        self.posts = {}
        fileName = os.path.expanduser('~/.mySocial/config/')+ '.rssProgram'
        if os.path.isfile(fileName): 
            with open(fileName,'r') as f: 
                self.files = f.read().split()
        self.twitter = moduleTwitter.moduleTwitter()
        self.twitter.setClient('fernand0')

    def selectPost(self, pp, post):
        logging.info("Selecting %s" % pp.pformat(post))
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
        resTxt = 'Executing: {}'.format(command)
        updates = ''
        update = None
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if (profile[0] in self.program) or (profile[0] in self.bufferapp) or (profile[0] in self.gmail): 
                update = self.clients[(profile, nick)].selectAndExecute(command,args)
            if update: 
                updates = updates + "- " + update + '\n'
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
        logging.info("Pposts %s" % updates)
        logging.info("Keys %s" % updates.keys())
        for socialNetwork in updates.keys():
            logging.info("Update social network %s " % str(socialNetwork))
            logging.debug("Updates %s End" % updates[socialNetwork])
            theUpdates = []
            for update in updates[socialNetwork]:
                if update:
                    if len(update)>0:
                        logging.info("Update %s " % str(update))
                        logging.info("Update %s " % update[0])
                        if update[0]:
                            theUpdatetxt = update[0].replace('_','\_')
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
    def list(self, mess, args):

        self.log.debug("Posts posts %s" % (self.posts))
        self.posts = {}
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            logging.info("socialNetworks %s %s"% (profile, nick))
            if (profile[0] in self.program) or (profile[0] in self.bufferapp) or (profile[0] in self.gmail): 
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
        self.log.info("Reponse %s End" % response)
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

