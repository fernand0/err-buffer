from errbot import BotPlugin, botcmd, webhook, backends
from errbot.templating import tenv
import moduleBuffer
import moduleCache
import moduleGmail
import configparser
import logging
import os
import pprint
from buffpy.models.update import Update
from buffpy.managers.profiles import Profiles
from buffpy.managers.updates import Updates
from buffpy.api import API


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

        config = configparser.ConfigParser()
        config.read([os.path.expanduser('~/.mySocial/config/.rssBuffer')])
        # We are not configuring the bot via commands so we do not use the
        # provided mechanism but some config files.
    
        clientId = config.get("appKeys", "client_id")
        clientSecret = config.get("appKeys", "client_secret")
        redirectUrl = config.get("appKeys", "redirect_uri")
        accessToken = config.get("appKeys", "access_token")
        
        pp = pprint.PrettyPrinter(indent=4)
        # instantiate the api object 
        self.api = API(client_id=clientId,
                          client_secret=clientSecret,
                          access_token=accessToken)
        self.cache = moduleCache.API('Blog7', pp)
        self.gmail = []
        self.gmail.append(moduleGmail.API('ACC1', pp))
        self.gmail.append(moduleGmail.API('ACC2', pp))
        self.log.info("Gmail %s " % self.gmail) 
        self.posts = {}
        self.log.info("Cache %s " % self.cache['profiles']) 
        fileName = os.path.expanduser('~/.mySocial/config/')+ '.rssProgram'
        if os.path.isfile(fileName): 
            with open(fileName,'r') as f: 
                self.files = f.read().split()

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
        toPublish = self.selectPost(pp, args)

        logging.info("Looking post in Buffer")
        update = moduleBuffer.publishPost(self.api, pp, self.profiles, toPublish)
        update2 = moduleCache.publishPost(self.cache, pp, self.posts, toPublish)
        update3 = moduleGmail.publishPost(self.gmail, pp, self.posts, toPublish)
        logging.info("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Published %s!" % update['text_formatted']
        if update2: 
            yield "Published %s!" % pp.pformat(update2)
        if update3: 
            yield "Published %s!" % pp.pformat(update3)
        logging.info("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to publish some update"""
        pp = pprint.PrettyPrinter(indent=4)
        toPublish = self.selectPost(pp, args)

        logging.info("Looking post in Buffer")
        update = moduleBuffer.showPost(self.api, pp, self.profiles, toPublish)
        update2 = moduleCache.showPost(self.cache, pp, self.posts, toPublish)
        update3 = moduleGmail.showPost(self.gmail, pp, self.posts, toPublish)
        logging.info("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Post %s!" % update['text_formatted']
        if update2: 
            yield "Post %s!" % pp.pformat(update2)
        if update3: 
            yield "Post %s!" % pp.pformat(update3)
        logging.info("Post in Local cache %s", pp.pformat(self.posts))
        yield end()



    @botcmd(split_args_with=None)
    def move(self, mess, args):
        moduleBuffer.movePost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)
        toDelete = self.selectPost(pp, args)
        moduleBuffer.deletePost(self.api, pp, self.profiles, args)
        moduleCache.deletePost(self.cache, pp, self.posts, toDelete)
        moduleGmail.deletePost(self.gmail, pp, self.posts, toDelete)
        yield "Deleted"
        yield end()

    def sendReply(self, mess, args, updates, types):
        reps = moduleBuffer.prepareReply(updates, types) 
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
        if self.api: 
            (posts, profiles) = moduleBuffer.listPosts(self.api, pp, "")
            
            if profiles: 
                # This got lost sometime in the past. It is needed to publish
                # pending posts in buffer. We should consider adding something
                # similar in '.queue' files.
                self.profiles = profiles

        self.log.info("Posts buffer %s" % (posts))

        if self.cache['profiles']:
            self.log.info("Profiles antes %s " % self.cache['profiles'])
            postsP, prof = moduleCache.listPosts(self.cache, pp, '')
            self.log.info("Profiles despues %s " % prof) 
            self.cache['profiles'] = prof
            posts.update(postsP)
            self.log.info("Posts despues %s" % (posts))
            self.log.info("Self Posts antes %s" % (self.posts))
            self.posts.update(posts)
            self.log.info("Self Posts despues %s" % (self.posts))
            self.log.info("Profiles despuees %s " % self.cache['profiles']) 
        self.log.info("Profiles despueees %s " % self.cache['profiles']) 

        if self.gmail:
            accC = 0
            for accG in self.gmail:
                self.log.info("Testing Mail ")
                postsP, prof = moduleGmail.listPosts(accG, pp, str(accC))
                posts.update(postsP)
                self.log.info("Self Posts despues gmail local %s" % (posts))
                self.posts.update(posts)
                self.log.info("Self Posts despues gmail %s" % (self.posts))
                accC = accC + 1


        self.log.info("Cache Profiles %s End" % self.cache['profiles'])
        response = self.sendReply(mess, args, posts, ['sent','pending'])
        self.log.debug("Reponse %s End" % response)
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

