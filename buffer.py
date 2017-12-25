from errbot import BotPlugin, botcmd, webhook, backends
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
        listBuffer.publishPost(self['api'], pp, self['profiles'], args)
        yield "Published"
        yield end()


    @botcmd(split_args_with=None)
    def move(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.movePost(self['api'], pp, self['profiles'], args[0], args[1])
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.deletePost(self['api'], pp, self['profiles'], args)
        yield "Deleted"
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        pendingUpdates = listBuffer.listPosts(self['api'], pp, "")
        for socialNetwork in pendingUpdates.keys():
            yield {'type': 'pending',
                    'nameSocialNetwork': socialNetwork, 
                    'updates': pendingUpdates[socialNetwork]['pending']}
        yield("END")

    @botcmd(split_args_with=None, template="buffer")
    def sent(self, mess, args):
        pp = pprint.PrettyPrinter(indent=4)
        pendingUpdates = listBuffer.listPosts(self['api'], pp, "")
        for socialNetwork in pendingUpdates.keys():
            yield {'type': 'sent',
                    'nameSocialNetwork': socialNetwork, 
                    'updates': pendingUpdates[socialNetwork]['sent']}
        yield("END")


