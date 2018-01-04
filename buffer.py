from errbot import BotPlugin, botcmd, webhook, backends
from errbot.templating import tenv
import listBuffer
import configparser
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
        config.read([os.path.expanduser('~/.rssBuffer')])
        # We are not configuring the bot via commands so we do not use the
        # provided mechanism but some config files.
    
        clientId = config.get("appKeys", "client_id")
        clientSecret = config.get("appKeys", "client_secret")
        redirectUrl = config.get("appKeys", "redirect_uri")
        accessToken = config.get("appKeys", "access_token")
        
        # instantiate the api object 
        self['api'] = API(client_id=clientId,
                          client_secret=clientSecret,
                          access_token=accessToken)


    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""
        pp = pprint.PrettyPrinter(indent=4)
        update = listBuffer.publishPost(self['api'], pp, self['profiles'], args)
        yield "Published %s!" % update['text_formatted']
        #yield "Published"
        yield end()


    @botcmd(split_args_with=None)
    def move(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.movePost(self['api'], self.log, pp, self['profiles'], args[0], args[1])
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.deletePost(self['api'], pp, self['profiles'], args)
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
                response = tenv().get_template('buffer.md').render({'type': tt,
                        'nameSocialNetwork': socialNetwork, 
                        'updates': theUpdates})
                compResponse = compResponse + response

        return(compResponse)

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        posts = listBuffer.listPosts(self['api'], pp, "")
        response = self.sendReply(mess, args, posts, ['sent','pending'])
        self.log.debug("Reponse %s End" % reponse)
        yield(response)
        yield("END")

    @botcmd(split_args_with=None)
    def sent(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        posts = listBuffer.listPosts(self['api'], pp, "")
        response = self.sendReply(mess, args, posts, ['pending', 'sent'])
        self.log.debug(response)
        yield(response)
        yield("END")

    @botcmd(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.copyPost(self['api'], self.log, pp, self['profiles'], args[0], args[1])
        yield "Copied"
        yield end()

