from errbot import BotPlugin, botcmd, webhook
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



    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        pp = pprint.PrettyPrinter(indent=4)
        listBuffer.deletePost(self['api'], pp, self['profiles'], args)
        yield "Deleted"
        yield end()

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd(split_args_with=None)
    def list(self, mess, args):
        """A command which checks for pending updates"""
        pp = pprint.PrettyPrinter(indent=4)
        # We should use args for selecting the service
        pendingUpdates = listBuffer.listPendingPosts(self['api'], pp, "")
        formattedUpdates = ""
        if pendingUpdates:
            self['profiles'] = pendingUpdates[1]
            for line in pendingUpdates[0]:
                formattedUpdates =  formattedUpdates + '\n' + line[:33]
            
            if (self._bot.mode == "telegram"):
                self._bot.telegram.send_message(mess.frm.id, formattedUpdates, parse_mode = 'Markdown')
            else:
                yield(formattedUpdates)
        else:
            yield("No pending posts")
        yield end()

    @botcmd(split_args_with=None)
    def sent(self, mess, args):
        """A command which checks for pending updates"""
        pp = pprint.PrettyPrinter(indent=4)
        # We should use args for selecting the service
        sentUpdates = listBuffer.listSentPosts(self['api'], pp, "")
        formattedUpdates = ""
        if sentUpdates:
            self['profiles'] = sentUpdates[1]
            lines = sentUpdates[0][0]
            linesC = sentUpdates[0][1]
            for i in range(len(lines)):
                formattedUpdates = formattedUpdates + '\n' 
                formattedUpdates = formattedUpdates + lines[i][:25] 
                formattedUpdates = formattedUpdates + ' '+ linesC[i]
            if (self._bot.mode == "telegram"):
                self._bot.telegram.send_message(mess.frm.id, formattedUpdates, parse_mode = 'Markdown')
            else:
                yield(formattedUpdates)
        else:
            yield("No pending posts")
        yield("END")

