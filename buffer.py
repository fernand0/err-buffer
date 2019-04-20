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
                cache = moduleCache.moduleCache()
                cache.setClient(url, (profile, nick))
                cache.setPosts()
                self.cache[(profile, nick)] = cache
            if profile[0] in self.bufferapp: 
                buff = moduleBuffer.moduleBuffer() 
                buff.setClient(url, (profile, nick)) 
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
        pp = pprint.PrettyPrinter(indent=4)

        logging.info("Looking post in Buffer")
        update = self.buffer.selectAndExecute('publish', args)
        update2 = ""
        theUpdate = self.cache.selectAndExecute("publish", args)
        logging.info("Update ... %s" % str(theUpdate))
        update2 = update2 + theUpdate
        update3 = self.gmail[0].selectAndExecute("publish", args)
        update4 = self.gmail[1].selectAndExecute("publish", args)
        update5 = self.gmail[2].selectAndExecute("publish", args)
        logging.debug("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Published %s!" % update['text_formatted']
        if update2: 
            yield "Published %s!" % pp.pformat(update2)
        if update3: 
            yield "Published %s!" % pp.pformat(update3)
        if update4: 
            yield "Published %s!" % pp.pformat(update4)
        if update5: 
            yield "Published %s!" % pp.pformat(update5)
        logging.debug("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to publish some update"""
        logging.info("Looking post in Buffer")

        pp = pprint.PrettyPrinter(indent=4)
        update = self.buffer.selectAndExecute('show', args)
        update2 = self.cache.selectAndExecute('show', args)

        update3 = self.gmail[0].selectAndExecute('show', args)
        update4 = self.gmail[1].selectAndExecute('show', args)
        update5 = self.gmail[2].selectAndExecute('show', args)
        logging.debug("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Post %s!" % pp.pformat(update)#['text_formatted']+' '+update['media']['expanded_link']
        if update2: 
            yield "Post %s!" % pp.pformat(update2)
        if update3: 
            yield "Post %s!" % pp.pformat(update3)
        if update4: 
            yield "Post %s!" % pp.pformat(update4)
        if update5: 
            yield "Post %s!" % pp.pformat(update5)
        logging.info("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        pp = pprint.PrettyPrinter(indent=4)

        resTxt = ""
        res = self.buffer.selectAndExecute("edit", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.cache.selectAndExecute("edit", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[0].selectAndExecute("edit", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[1].selectAndExecute("edit", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[2].selectAndExecute("edit", args)
        if res: resTxt = resTxt + res + '\n'
        yield(res)
        yield end()

    @botcmd
    def move(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        yield(args)
        moduleBuffer.movePost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield(moduleCache.movePost(args))
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)

        resTxt = "Deleted! "
        res = self.buffer.selectAndExecute("delete", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.cache.selectAndExecute("delete", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[0].selectAndExecute("delete", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[1].selectAndExecute("delete", args)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[2].selectAndExecute("delete", args)
        if res: resTxt = resTxt + res + '\n'
        yield(res)
        yield end()

    def prepareReply(self, updates, types):
        compResponse = [] 
        for tt in types:
            # This define the ordering 'pending', 'sent'
            logging.info("Keys %s" % updates.keys())
            for socialNetwork in updates.keys():
                logging.info("Update social network %s " % str(socialNetwork))
                logging.debug("Updates %s End" % updates[socialNetwork][tt])
                theUpdates = []
                for update in updates[socialNetwork][tt]:
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
                if updates[socialNetwork][tt]: 
                    if theUpdates[0][0] != 'Empty': 
                        socialTime = theUpdates[0][2] 
                    else: 
                        socialTime = ""
                else:
                    socialTime = ""
    
                compResponse.append((tt, socialNetwork, theUpdates))
    
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
        pp = pprint.PrettyPrinter(indent=4)

        self.log.debug("Posts posts %s" % (self.posts))
        self.posts = {}
        for profile in self.socialNetworks:
            nick = self.socialNetworks[profile]
            if profile[0] in self.program: 
                posts = []
                for post in self.cache[(profile, nick)].getPosts():
                    title = self.cache[(profile, nick)].getPostTitle(post)
                    link = self.cache[(profile, nick)].getPostLink(post)
                    posts.append((title, link, ''))
                self.posts[(profile, link)] = posts
            if profile[0] in self.bufferapp: 
                posts = []
                for post in self.buffer[(profile, nick)].getPosts():
                    title = self.buffer[(profile, nick)].getPostTitle(post)
                    link = self.buffer[(profile, nick)].getPostLink(post)
                    posts.append((title, link, ''))
                self.posts[(profile, link)] = posts

        self.log.debug("Posts posts %s" % (self.posts))

        if self.gmail:
            for accG in self.gmail:
                self.log.info("Testing Mail ")
                accG.setPosts()
                postsP = accG.getPostsFormatted()
                posts.update(postsP)
                self.log.debug("Self Posts despues gmail local %s" % (posts))
                self.posts.update(posts)
                self.log.debug("Self Posts despues gmail %s" % (self.posts))

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

