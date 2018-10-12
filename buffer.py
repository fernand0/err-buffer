from errbot import BotPlugin, botcmd, webhook, backends
from errbot.templating import tenv
import moduleBuffer
import moduleCache
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
        return(profMov, j)

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""
        pp = pprint.PrettyPrinter(indent=4)
        (post, j) = self.selectPost(pp, args)

        logging.info("Looking post in Buffer")
        update = moduleBuffer.publishPost(self.api, pp, self.profiles, (post, j))
        update2 = moduleCache.publishPost(self.cache, pp, self.posts, (post, j))
        logging.info("Looking post in Local cache bot %s", self.posts)
        if update: 
            yield "Published %s!" % update['text_formatted']
        if update2: 
            yield "Published %s!" % pp.pformat(update2)
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
        (post, j) = self.selectPost(pp, args)
        moduleBuffer.deletePost(self.api, pp, self.profiles, args)
        moduleCache.deletePost(self.cache, pp, self.posts, (post, j))
        yield "Deleted"
        yield end()

    def sendReply(self, mess, args, updates, types):
        compResponse = ""
        for tt in types:
            for socialNetwork in updates.keys():
                self.log.debug("Updates %s End" % updates[socialNetwork][tt])
                theUpdates = []
                for update in updates[socialNetwork][tt]:
                    theUpdatetxt = update[0].replace('_','\_')
                    theUpdates.append((theUpdatetxt, update[1], update[2])) 
                if updates[socialNetwork][tt]: 
                    if theUpdates[0][0] != 'Empty': 
                        socialTime = theUpdates[0][2] 
                    else: 
                        socialTime = ""
                else:
                    socialTime = ""
                response = tenv().get_template('buffer.md').render({'type': tt,
                        'nameSocialNetwork': socialNetwork, 
                        'updates': theUpdates})
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

