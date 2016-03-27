from errbot import BotPlugin, botcmd, webhook


class Buffer(BotPlugin):
    """
    A plugin to manage our buffer account with the bot (at least some features,
this is not a translation for the whole API).
    """

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd(split_args_with=None)
    def example(self, mess, args):
        """A command which simply returns 'Example'"""
        return "Example"
