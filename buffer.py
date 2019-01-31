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
        gmailAcc = moduleGmail.moduleGmail()
        gmailAcc.API('ACC0', pp)
        self.gmail.append(gmailAcc) 
        gmailAcc = moduleGmail.moduleGmail()
        gmailAcc.API('ACC1', pp)
        self.gmail.append(gmailAcc) 
        #moduleGmail.API('ACC1', pp))
        #self.gmail.append(moduleGmail.API('ACC2', pp))
        self.log.info("Gmail %s " % self.gmail) 
        self.posts = {}
        self.log.debug("Cache %s " % self.cache['profiles']) 
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

        profIni = toPublish[0]
        j = toPublish[1]
        if len(toPublish)>2:
            profIni = profIni + toPublish[2]

        logging.info("Looking post in Buffer")
        update = moduleBuffer.publishPost(self.api, pp, self.profiles, args)
        update2 = moduleCache.publishPost(self.cache, pp, self.posts, args)
        update3 = self.gmail[0].publishPost(pp, self.posts, args)
        update4 = self.gmail[1].publishPost(pp, self.posts, args)
        logging.info("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Published %s!" % update['text_formatted']
        if update2: 
            yield "Published %s!" % pp.pformat(update2)
        if update3: 
            yield "Published %s!" % pp.pformat(update3)
        if update4: 
            yield "Published %s!" % pp.pformat(update4)
        logging.info("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to publish some update"""
        pp = pprint.PrettyPrinter(indent=4)
        toPublish = self.selectPost(pp, args)

        profIni = toPublish[0]
        j = toPublish[1]

        logging.info("Looking post in Buffer")
        update = moduleBuffer.showPost(self.api, pp, self.profiles, args)
        update2 = moduleCache.showPost(self.cache, pp, self.posts, args)
        update3 = self.gmail[0].showPost(pp, self.posts, args)
        update4 = self.gmail[1].showPost(pp, self.posts, args)
        logging.debug("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Post %s!" % update['text_formatted']
        if update2: 
            yield "Post %s!" % pp.pformat(update2)
        if update3: 
            yield "Post %s!" % pp.pformat(update3)
        if update4: 
            yield "Post %s!" % pp.pformat(update4)
        logging.info("Post in Local cache %s", pp.pformat(self.posts))
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        pp = pprint.PrettyPrinter(indent=4)
        toPublish = self.selectPost(pp, args.split()[0])

        profIni = toPublish[0]
        j = toPublish[1]

        title = args[len(toPublish)+1:]

        args, title = args.split(maxsplit=1)
        yield("Only available for Cache and Gmail")

        resTxt = ""
        res = moduleCache.editPost(self.cache, pp, self.posts, args, title)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[0].editPost(pp, self.posts, args, title)
        if res: resTxt = resTxt + res + '\n'
        res = self.gmail[1].editPost(pp, self.posts, args, title)
        if res: resTxt = resTxt + res + '\n'
        yield(res)
        yield end()

    @botcmd(split_args_with=None)
    def move(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        moduleBuffer.movePost(self.api, self.log, pp, self.profiles, args[0], args[1])
        yield(moduleCache.movePost(self.cache, pp, self.posts, args[0], args[1]))
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)
        toDelete = self.selectPost(pp, args)

        profIni = toDelete[0]
        j = toDelete[1]

        moduleBuffer.deletePost(self.api, pp, self.profiles, args)
        yield(moduleCache.deletePost(self.cache, pp, self.posts, args))
        self.gmail[0].deletePost(self.gmail, pp, self.posts, args)
        update = self.gmail[1].deletePost(self.gmail, pp, self.posts, args)
        yield "Deleted"
        yield update
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

        self.log.debug("Posts buffer %s" % (posts))

        if self.cache['profiles']:
            self.log.debug("Profiles antes %s " % self.cache['profiles'])
            postsP, prof = moduleCache.listPosts(self.cache, pp, '')
            self.log.debug("Profiles despues %s " % prof) 
            self.cache['profiles'] = prof
            posts.update(postsP)
            self.log.debug("Posts despues %s" % (posts))
            self.log.debug("Self Posts antes %s" % (self.posts))
            self.posts.update(posts)
            self.log.debug("Self Posts despues %s" % (self.posts))
            self.log.debug("Profiles despuees %s " % self.cache['profiles']) 
        self.log.debug("Profiles despueees %s " % self.cache['profiles']) 

        if self.gmail:
            for accG in self.gmail:
                self.log.info("Testing Mail ")
                postsP, prof = accG.listPosts(pp)
                posts.update(postsP)
                self.log.debug("Self Posts despues gmail local %s" % (posts))
                self.posts.update(posts)
                self.log.debug("Self Posts despues gmail %s" % (self.posts))


        self.log.debug("Cache Profiles %s End" % self.cache['profiles'])
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

