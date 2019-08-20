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
                'linkedin': 'Fernando Tricas'}

        self.bufferapp ='l'
        self.program ='tfm'
        self.cache = {}
        self.buffer = {}
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program:
                logging.info("Cache %s %s"% (profile, nick))
                cache = moduleCache.moduleCache()
                cache.setClient(url, (profile, nick))
                cache.setPosts()
                self.cache[(profile, nick)] = cache
            if profile[0] in self.bufferapp: 
                buff = moduleBuffer.moduleBuffer() 
                buff.setClient(url, (profile, nick)) 
                logging.info("apiii %s" % buff.client)
                buff.setPosts()
                self.buffer[(profile, nick)] = buff

        self.gmail = []
        gmailAcc = moduleGmail.moduleGmail()
        gmailAcc.setClient('ACC0')
        self.gmail.append(gmailAcc) 
        gmailAcc = moduleGmail.moduleGmail()
        gmailAcc.setClient('ACC1')
        self.gmail.append(gmailAcc) 
        gmailAcc = moduleGmail.moduleGmail()
        gmailAcc.setClient('ACC2')
        self.gmail.append(gmailAcc) 
        #moduleGmail.API('ACC1', pp))
        #self.gmail.append(moduleGmail.API('ACC2', pp))
        self.log.info("Gmail %s " % self.gmail) 
        self.posts = {}
        #self.log.debug("Cache %s " % self.cache['profiles']) 
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

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""
        resTxt = 'Published! '
        updates = ''
        update = None
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('publish',args)
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('publish',args)
            if update: 
                updates = updates + "- " + update + '\n'
                update = None

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                profile  = accG.name
                nick = accG.nick
                update = accG.selectAndExecute('publish', args)
                if update:
                    updates = updates + "- " + update + '\n'
                    update = None

        if updates: res = resTxt + '\n' + updates + '\n'

        yield res 
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to publish some update"""
        resTxt = 'Post: '
        updates = ""
        update = None
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('show',args)
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('show',args)
            if update:
                updates = updates + '- ' + update + '\n'
                update = None

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                profile  = accG.name
                nick = accG.nick
                update = accG.selectAndExecute('show', args)
                if update:
                    updates = updates + "- " + update + '\n'
                    update = None
        if updates: 
            res = resTxt + '\n'+ updates + '\n'
            
        yield res 
        logging.debug("Post in Local cache %s", self.posts)
        #logging.debug("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def editl(self, mess, args):
        """A command to edit the link of some update"""

        resTxt = 'Edited link! '
        updates = ''
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('editl',args)
                if update:
                    updates = updates + update + '\n'
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('editl',args)
                if update:
                    updates = updates + update + '\n'

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                profile  = accG.name
                nick = accG.nick
                update = accG.selectAndExecute('editl', args)
                if update:
                    updates = updates + update + '\n'

        if updates: 
            res = resTxt + updates + '\n'
            self.addEditsCache(args)

        yield(res)
        yield end()

    def addEditsCache(self, args):
        if 'argsArchive' not in self:
            self['argsArchive'] = []
        argsArchive = self['argsArchive']
        argsArchive.append(args)
        self['argsArchive'] = argsArchive

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""

        resTxt = 'Edited! '
        updates = ''
        update = None
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('edit',args)
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('edit',args)
            if update:
                updates = updates + '- ' + update + '\n'
                update = None

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                profile  = accG.name
                nick = accG.nick
                update = accG.selectAndExecute('edit', args)
                if update:
                    updates = updates + update + '\n'
                    update = None

        if updates: 
            res = resTxt + '\n' + updates + '\n'
            self.addEditsCache(args)

        yield res
        yield end()

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
        
        resTxt = "Moved! "
        updates = ''
        update = None
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('move',args)
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('move',args)

            if update:
                updates = updates + update + '\n'
                update = None
        if updates: res = resTxt + updates + '\n'
        yield(res)
        
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""

        resTxt = "Deleted! "
        updates = ''
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                update = self.cache[(profile, nick)].selectAndExecute('delete',args)
                if update:
                    updates = updates + update + '\n'
            if profile[0] in self.bufferapp: 
                update = self.buffer[(profile, nick)].selectAndExecute('delete',args)
                if update:
                    updates = updates + update + '\n'

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                profile  = accG.name
                nick = accG.nick
                update = accG.selectAndExecute('delete', args)
                if update:
                    updates = updates + update + '\n'

        if updates: res = resTxt + updates + '\n'
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
            if profile[0] in self.program: 
                posts = []
                self.cache[(profile, nick)].setPosts()
                if self.cache[(profile, nick)].getPosts():
                    for post in self.cache[(profile, nick)].getPosts():
                        title = self.cache[(profile, nick)].getPostTitle(post)
                        link = self.cache[(profile, nick)].getPostLink(post)
                        posts.append((title, link, ''))
                self.posts[(profile, nick)] = posts
            if profile[0] in self.bufferapp: 
                posts = []
                self.buffer[(profile, nick)].setPosts()
                if self.buffer[(profile, nick)].getPosts():
                    for post in self.buffer[(profile, nick)].getPosts():
                        title = self.buffer[(profile, nick)].getPostTitle(post)
                        link = self.buffer[(profile, nick)].getPostLink(post)
                        posts.append((title, link, ''))
                self.posts[(profile, nick)] = posts

        self.log.debug("Posts posts %s" % (self.posts))

        if self.gmail:
            for i, accG in enumerate(self.gmail):
                posts = []
                profile  = accG.name
                nick = accG.nick
                self.log.info("Testing Mail ")
                accG.setPosts()
                for post in accG.getPosts():
                    logging.info("Gmail post %s" %post)
                    title = accG.getHeader(post)
                    link = ''
                    posts.append((title, link, ''))
                self.posts[(profile, nick)] = posts

        self.log.debug("Posts posts %s" % (self.posts))
        #self.log.debug("Cache Profiles %s End" % self.cache['profiles'])
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

