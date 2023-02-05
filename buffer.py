import configparser
import logging
import os
import pickle
import pprint
import time

from errbot import BotPlugin, botcmd
from errbot.templating import tenv

# Needs to set $PYTHONPATH to the dir where this modules are located

from socialModules.configMod import *
import socialModules
import socialModules.moduleRules


def end(msg=""):
    return "END" + msg


class Buffer(BotPlugin):
    """
    A plugin to manage our buffer account with the bot (at least some
    features, this is not a translation for the whole API).
    """

    def activate(self):
        """
        Triggers on plugin activation
        """
        super(Buffer, self).activate()

        self.clients = {}
        self.posts = {}
        self.config = []
        self.available = None
        self.schedules = None
        self.lastList = None
        self.lastEdit = None
        self.lastLink = None
        self.argsArchive = []

    def setAvailable(self):
        logging.debug(f"Checking available")
        if not self.available:
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available
            self.rules = rules

    def getId(self, arg):
        res = ""
        if arg and len(arg)>0:
            res = arg[0].upper()
        return res

    def getSel(self, arg):
        res = ""
        if arg and len(arg)>1:
            res = int(arg[1])
        return res

    def getPos(self, arg):
        res = ""
        if arg and len(arg)>2:
            res = int(arg[2:].split(' ')[0])
        return res

    def getCont(self, arg):
        res = ""
        if arg and ' ' in arg:
            pos = arg.find(' ')
            res = arg[pos+1:]
            if res.isdigit():
                res = int(res)
        return res

    def addMore(self):
        response = (
            f"There are {len(self.config)} lists. "
            f"You can add more with command list add"
        )
        return response

    def formatList(self, text, status):
        textR = []
        linePrev = ''
        if text:
            textR.append("=======")
            textR.append("{}:".format(status.capitalize()))
            textR.append("=======")
            for line in text:
                lineS = line.split("|")[1]
                line1, line2 = lineS.split("->")
                logging.debug("line 1 {}".format(line1))
                if line[:8] == linePrev[:8]:
                    # FIXME: dirty trick to avoid duplicate content while the
                    # old and the new approach to file names coexists
                    if line[9].isupper():
                        textR[-2] = line1
                        textR[-1] = f"      ⟶{line2}"
                else:
                    textR.append(line1)
                    textR.append("      ⟶{}".format(line2))
                linePrev = line
        else:
            textR.append("===========")
            textR.append("None {}".format(status))
            textR.append("===========")

        return textR

    def fileNameBase2(self, rule, action):
        nick = self.rules.getNickRule(rule)
        if 'http' in nick:
            nick = urllib.parse.urlparse(nick).netloc
        return (f"{self.rules.getNameRule(rule).capitalize()}_"
                f"{self.rules.getTypeRule(rule)}_"
                f"{nick}_" 
                # f"{self.rules.getIdRule(rule).capitalize()}_"
                f"{self.rules.getSecondNameRule(rule).capitalize()}_"
                f"_{self.rules.getNameAction(action).capitalize()}"
                f"_{self.rules.getTypeAction(action)}"
                f"_{self.rules.getNickAction(action)}"
                f"_{self.rules.getProfileAction(action)}"
               )

    @botcmd(split_args_with=None, template="buffer")
    def list_next2(self, mess, args):
        self.setAvailable()
        for src in self.rules.rules:
            hold = self.rules.more[src].get('hold','')
            if (not hold or (not hold == 'yes')):
                msg =  (f"Rule: {src}\n"
                   f"Actions: {self.rules.rules[src]}"
                   f"More: {self.rules.more[src]}")
                yield msg
                logging.info(msg)
                for action in self.rules.rules[src]:
                    actionF = self.fileNameBase2(src, action)
                    yield actionF
                    logging.info(f"Nameeee: {actionF}")


    @botcmd(split_args_with=None, template="buffer")
    def list_next(self, mess, args):
        self.setAvailable()
        myList = os.listdir(DATADIR)
        textW = []
        textF = []
        rules = self.rules
        for element in myList:
            logging.debug(f"Element {element}")
            if (element.find("last") > 0) and (element.find("Next") > 0):
                continue
            if element.find("Next") > 0:
                if element.find("__") > 0:
                    res = element[:-len('.timeNext')]
                    res = res.split("__")
                    src = res[0].split('_')
                    dst = res[1].split('_')
                    if isinstance(res, str):
                        res = res.split("__")

                    url = (f"{src[0]} ({src[2]} "
                          f"{src[1]})")
                    url = url.replace('https', '').replace('http','')
                    url = url.replace('---','').replace('.com','')
                    url = url.replace('-(','(').replace('- ',' ')

                    if len(dst)>2:
                        dest = f"{dst[0]}({dst[1]}){dst[2]}"
                        nick = f"{dst[2]}-{dst[1]}"
                    else:
                        dest = f"{dst[0]}({dst[1]})"
                        nick = f"{dst[1]}"
                    dest = f"{dst[0]}"
                    nick = nick.replace('https', '').replace('http','')
                    nick = nick.replace('---','').replace('.com','')
                    nick = nick.replace('-(','(').replace('- ',' ')
                elif element.find("_") > 0:
                    res = element.split("_")
                    url = res[0]
                    dest = res[1]
                    nick = "_".join(res[1:])
                    nick = nick.split(".")[0]
                else:
                    url = element
                    dest = ""
                    nick = ""
                orig = url.split(".")[0]
                orig = url
                t1 = None
                if True:
                    if element.find("Next") > 0:
                        with open("{}/{}".format(DATADIR, element), "rb") as f:
                            try:
                                t1, t2 = pickle.load(f)
                            except:
                                t1, t2 = (0,0)
                        if time.time() < t1 + t2:
                            msg = "[W]: "
                        else:
                            msg = "[F]: "
                        theTime = time.strftime("%H:%M:%S",
                                                time.localtime(t1 + t2))
                    else:
                        if dest and nick:
                            link, t1 = checkLastLink(url, (dest, nick))
                        else:
                            link, t1 = checkLastLink(url)
                        theTime = time.strftime("%H:%M:%S",
                                                time.localtime(t1))
                        msg = "[L]: "
                        t2 = 0
                else:
                    msg = "No Time"
                    theTime = ""
                if t1:
                    if nick and nick.find("_") > 0:
                        nick = nick.split("_")[1]
                    if msg.find("[W]") >= 0:
                        textElement = (f"{t1 + t2}|{theTime} {orig} -> "
                                     f"{dest.capitalize()} ({nick})")
                        textW.append(textElement)
                    else:
                        textElement = (f"{t1 + t2}|{theTime} {orig} -> "
                                     f"{dest.capitalize()} ({nick})")
                        textF.append(textElement)
                    logging.debug(f"Element text {textElement}")
        textF = sorted(textF)
        textW = sorted(textW)
        textP = self.formatList(textF, "finished")
        textP = textP + self.formatList(textW, "waiting")
        yield ("\n".join(textP))
        yield (end())

    @botcmd(split_args_with=None, template="buffer")
    def list_last(self, mess, args):
        if self.lastList:
            yield "Last list: {}".format(str(self.lastList))
        else:
            yield "No lists"
        yield end()

    @botcmd
    def list_show(self, msg, args):
        """Show selected services in the quick list"""
        if self.config:
            yield self.config
        else:
            yield "None"
        yield end()

    @botcmd
    def list_all(self, mess, args):
        """List available services"""
        yield f"Args: {args}"
        self.setAvailable()

        rules = self.rules

        logging.debug("Available: %s" % str(self.available))
        # yield("Available: %s" % str(self.available))
        myList = {}
        theKey = ("L0")
        myList[theKey] = []
        keys = []
        for key in self.available:
            for i, elem in enumerate(self.available[key]["data"]):
                if (args and (key == args.lower())) or not args:
                    logging.info(f"Elem: {elem}")
                    logging.info(f"Elem 1: {elem['src'][1]}")
                    name = rules.getNameRule(elem['src'])
                    profile = rules.getSecondNameRule(elem['src'])
                    nick = rules.getNickRule(elem['src'])
                    if 'http' in nick:
                        #FIXME: duplicate code
                        nick = urllib.parse.urlparse(nick).netloc
                    src = elem['src']
                    logging.debug(f"Elem 1: {name}")
                    myList[theKey].append((f"{name.capitalize()} "
                                           f"({nick}@{profile} "
                                           f"{self.rules.getTypeRule(src)})", 
                                           key, f"{key}{i}"))
            keys.append(f"{key}{i}")
        logging.debug("myList: %s" % str(myList))
        keys = ','.join(keys)
        myList[theKey].append((keys, "", "I"))
        # yield("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ('\n'.join(rep.split('\n')[3:]))

        return end

    def appendMyList(self, arg, myList):
        logging.debug(f"Args... {arg}")
        self.setAvailable()

        if self.getId(arg) in self.available:
            pos = self.getSel(arg)
            if pos < len(self.available[self.getId(arg)]["data"]):
                myList.append(arg.capitalize())
            
        logging.debug(f"myList: {myList}")

    @botcmd(split_args_with=None, template="buffer")
    def list_read(self, mess, args):
        # Maybe define a flow?
        myList = []
        pos = 0
        clients = self.clients
        if args:
            if self.getId(args).isdigit():
                pos = int(self.getId(args))
            yield (self.getId(args))
            self.appendMyList(self.getId(args), myList)
        else:
            if self.lastList:
                myList = self.lastList
                pos = 0
                # yield "I'll mark as read in {}".format(str(myList))
            else:
                yield "Which list?"
                pos = -1

        if pos >= 0:
            for element in myList:
                logging.debug("Element %s" % str(element))
                logging.debug("Clients %s" % str(clients))
                if element in clients:
                    thePosts = clients[element].getPosts()
                    if thePosts:
                        link = thePosts[-1][1]
                        service = clients[element].getService().upper()
                        if service == "Forum".upper():
                            name = clients[element].getUrl()
                            updateLastLink(name, link)
                        yield ("Marked read {}".format(element))
        yield end()

    @botcmd
    def list_del(self, msg, args):
        """Delete a list of services from the quick list"""

        pos = 0
        if args:
            if self.getId(args).isdigit():
                pos = int(self.getId(args))
            yield (self.getId(args))

        if pos < len(self.config):
            self.config = self.config[:pos] + self.config[pos + 1:]
            response = self.config
        else:
            response = self.addMore()

        yield (response)
        yield (end())

    @botcmd(split_args_with=None)
    def list_add(self, msg, args):
        """Add list of services to the quick list"""
        myList = []

        for arg in args:
            self.appendMyList(arg, myList)

        if myList:
            self.config.append(myList)

        yield (self.config)
        yield (end())

    @botcmd
    def list_list(self, msg, args):

        self.setAvailable()

        rules = self.rules

        response = self.config
        if not response:
            response = f"Empty list, you can add items with list add"
        yield response
        yield end()

    def getUrlSelected(self, selected):
        url = selected[0][0][0]
        return url

    def getSelectedProfile(self, key, pos):
        selected = self.available[key]["data"][pos]
        return selected

    def getProfile(self, key):
        profile = self.available[key]["name"]
        return profile

    def getSocialProfile(self, element):
        key = element[0].lower()
        logging.debug("Key: %s", str(key))
        pos = int(element[1:])
        profile = self.getProfile(key)
        logging.debug(f"Profile: {profile}")
        selected = self.getSelectedProfile(key, pos)
        logging.debug(f"Selected: {selected}")
        url = self.getUrlSelected(selected)
        logging.debug(f"Url: {url}")
        nick = selected[0]
        logging.debug(f"Nick: {nick}")
        socialNetworks = [nick[1]]
        name = nick
        # if key[0] == 's':
        #     name = nick[0][0]
        # el
        if type(nick) == tuple:
            name = nick[0]
        elif nick.find("@") >= 0:
            nick, profile = nick.split("@")
            name = nick
        return (name, profile, socialNetworks)

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """A command to show available posts in a list of available sites"""
        logging.debug("Posts posts %s" % (self.posts))
        logging.debug("args %s" % str(args))

        myList = []
        response = []
        self.posts = {}
        self.setAvailable()

        available = self.available

        if not args:
            # If no args, we asume we want the first one
            args = ['0']
        
        for arg in args:
            pos = -1
            if arg:
                if self.getId(arg).isdigit():
                    pos = int(self.getId(arg))
            else:
                pos = 0

            if (len(self.config) == 0) and (not arg):
                yield ("There are not lists defined")
                yield ("Add some elements with list add")
                return
            elif (pos >= 0) and (pos < len(self.config)):
                if len(self.config) > 0:
                    myList = myList + self.config[pos]
            else:
                self.appendMyList(arg, myList)
                pos = 0

            logging.debug("myList %s" % str(myList))

        self.lastList = myList
        clients = self.clients

        if not myList: 
            yield (self.addMore())

        for element in myList:
            logging.debug("Clients %s" % str(clients))
            logging.debug("Element %s" % str(element))
            logging.debug(f"Available {available}")
            profile = available[self.getId(element)]
            name = profile["name"]
            myElem = profile["data"][self.getSel(element)]
            logging.debug(f"myElem {myElem}")
            src = myElem['src']
            logging.debug(f"src {src}")
            more = self.rules.more[src]
            logging.debug(f"more {more}")

            try:
                clients[element].setPosts()
            except:
                api = self.rules.readConfigSrc('', src, more)
                clients[element] = api
                clients[element].setPostsType(myElem['src'][3])
                clients[element].setPosts()

            postsTmp = []
            posts = []

            if hasattr(clients[element], "getPostsType"):
                if clients[element].getPostsType() == "drafts":
                    postsTmp = clients[element].getDrafts()
                else:
                    postsTmp = clients[element].getPosts()
            else:
                postsTmp = clients[element].getPosts
            if postsTmp:
                for (i, post) in enumerate(postsTmp):
                    if hasattr(clients[element], "getPostLine"):
                        title = clients[element].getPostLine(post)
                        link = ""
                    else:
                        title = clients[element].getPostTitle(post)
                        link = clients[element].getPostLink(post)
                    posts.append((title, link, "{:2}".format(i)))
                    # logging.debug("I: %s %s %d"%(title,link,i))

            self.posts[element] = posts
            logging.debug("Posts posts %s" % (self.posts))

        response = self.sendReply("", "", self.posts, ["sent", "pending"])
        logging.debug("Response %s End" % str(response))

        for resp in response:
            logging.debug(f"Resp: {resp}")
            yield (resp)

        self.clients = clients
        yield end()

    @botcmd(split_args_with=' ')
    def last(self, command, args):
        clients = self.clients
        logging.debug(f"Clients: {clients}")
        self.setAvailable()
        available = self.available
        rules = self.rules
        # yield (f"Last in {args}")

        if isinstance(args, list):
            firstArg = args[0]
        else:
            firstArg = args
        first = firstArg
        lastLink = ''
        if len(args)>1:
            lastLink =  self.getSel(args)
            yield f"Url: {lastLink}"
        # yield f"First: {first}"
        name = available[self.getId(first)]["name"]
        src = available[self.getId(first)]["data"][self.getSel(first)]['src']
        # yield f"Src: {src}"
        # yield (f"Name: {name} - {rules.getNickRule(src)} - "
        #        f"{rules.getProfileRule(src)}")
        yield (f"Name: {rules.getIdRule(src)}")
        # yield (f"Src: {src}")
        # myRule = rules.rules[src]
        # yield(f"myRule: {myRule}")
        # dest = src[1]
        # myRule = rules.selectRule(name,  dest)[0]
        # yield(f"myRule: {myRule}")
        myActions = rules.rules[src]
        # yield(f"myActions: {myActions}")
        selectClient = f"{self.getId(firstArg)}{self.getSel(firstArg)}"
        if not selectClient in clients:
            yield f"You should execute 'list {selectClient}' first"
            return 
        apiSrc = clients[selectClient]
        # yield(f"apiSrc: {apiSrc}")
        for i, action in enumerate(myActions):
            yield(f"Action {i}. {rules.getNickAction(action)}@"
                  f"{rules.getProfileAction(action)}"
                  f"({rules.getNameAction(action)}-"
                  f"{rules.getTypeAction(action)})")
            apiDst = rules.readConfigDst('', action, rules.more[src], apiSrc)
            apiSrc.fileName = ''
            apiSrc.setLastLink(apiDst)
            if lastLink:
                logging.debug(f"Updating last link")
                yield(f"Updating last link")
                apiSrc.updateLastLink(apiDst, lastLink)
                myLastLink = apiSrc.getLastLinkPublished()
            else:
                myLlastLink = apiSrc.getLastLinkPublished()
            yield(f"Last link: {myLlastLink}")
        yield end()

    def execute(self, command, args):
        """Execute a command """
        resTxt = f"Executing: {command}\n"
        logging.debug(resTxt)
        resTxt = f"{resTxt}Args: {args}\n"
        logging.debug(resTxt)
        updates = ""
        update = None
        res = None
        if self.available:
            clients = self.clients
            logging.debug("Clients {}".format(clients))
            available = self.available
            rules = self.rules
            res = ""
            #for profile in self.clients:
            profile = self.getId(args)
            logging.debug(f"Executing in profile: {profile} with "
                          f"args {args}")
            name = available[self.getId(args)]["name"]
            src = available[self.getId(args)]["data"][int(self.getSel(args))]['src']
            logging.debug(f"Src: {src}")
            dest = str(src)

            logging.info(f"Src: {src}")
            logging.info(f"Clients: {clients}")
            logging.info(f"Rules rules: {rules.rules}")
            logging.info(f"Name {name} dest: {dest}")
            logging.info(f"It is: {dest in rules.rules}")
            for i in rules.rules:
                logging.info(f"Rule: {i}")
            myActions = rules.rules[src]
            logging.info(f"My actions: {myActions}")
            apiSrc = clients[args[:2].upper()]
            apiSrc.setPosts()
            pos = self.getPos(args)
            logging.info(f"Pos: {pos}")
            argCont = self.getCont(args)
            logging.info(f"Cont: {argCont}")
            post = apiSrc.getPost(pos)

            theProfile = profile[:2]
            logging.info(f"theProfile: {theProfile}")

            logging.info(f"Selecting {command} with {args} " 
                         f"in {apiSrc.getService()}")
            logging.debug(f"Posts: {apiSrc.getPosts()}")
            cmd = getattr(apiSrc, command)
            logging.info(f"Command: {command} is {cmd}")
            if argCont: 
                if argCont.capitalize() in clients:
                    argCont = clients[argCont.capitalize()]
                update = cmd(pos, argCont)
            else:
                update = cmd(pos)
            
            updates = f"{updates}* {update} ({profile[0]})\n"
            # if (
            #     (theProfile.upper() == args[: len(theProfile)].upper())
            #     or (self.getId(args) == "*")
            #     or (("*" in args) and (self.getId(args) == profile[0][:1]))
            # ):
            #     # We need to do something for '*' commands
            #     logging.debug(f"I'll {command} in {profile}")
            #     update = self.clients[profile].selectAndExecute(command, args)
            #     if update:
            #         updates = f"{updates}* {update} ({profile[0]})\n"
            #         update = None

            if updates:
                resTxt = f"{resTxt}\n{updates}"

        return resTxt

    @botcmd
    def insert(self, mess, args):
        """A command to publish some update"""
        res = self.execute("insert", args)
        yield res
        yield end()

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""

        if self.available:
            clients = self.clients
            logging.debug(f"Clients: {clients}")
            available = self.available
            rules = self.rules

            logging.debug(f"Publishing {args}")
            yield (f"Publishing {args}")
            res = ""

            # # yield(f"Avail: {available}")
            name = available[self.getId(args)]["name"]
            src = available[self.getId(args)]["data"][int(self.getSel(args))]['src']
            logging.debug(f"Src: {src}")
            dest = str(src)
            logging.debug(f"Clients: {clients}")
            logging.debug(f"Rules rules: {rules.rules}")
            logging.debug(f"Name {name} dest: {dest}")
            # myRule = rules.selectRule(name,  dest)[0]
            # logging.debug(f"My rule: {myRule}")
            logging.debug(f"It is: {dest in rules.rules}")
            for i in rules.rules:
                logging.debug(f"Rule: {i}")
            myActions = rules.rules[src]
            logging.debug(f"My actions: {myActions}")
            apiSrc = clients[args[:2].upper()]
            apiSrc.setPosts()
            pos = self.getPos(args)
            logging.debug(f"Pos: {pos}")
            post = apiSrc.getPost(pos)
            title = apiSrc.getPostTitle(post)
            link = apiSrc.getPostLink(post)
            logging.debug(f"Title: {title}")
            yield(f"Will publish: {title} - {link}")
            logging.debug(f"Link: {link}")
            logging.debug(f"Actions: {myActions}")

            published = False

            if 'hold' in rules.more[src]:
                rules.more[src]['hold'] = 'no'
            for i, action in enumerate(myActions):
                logging.debug(f"Action {i}: {action} {rules.getNameAction(action)}")
                yield(f"Action {i}. {rules.getNickAction(action)}@"
                      f"{rules.getProfileAction(action)}"
                      f"({rules.getNameAction(action)}-"
                      f"{rules.getTypeAction(action)})")
                rules.executeAction(src, rules.more[src], action,
                                    noWait=True, timeSlots=0, simmulate=False,
                                    name=f"{name} {rules.getTypeAction(action)}",
                                    nextPost=False, pos=pos, delete=False)
            yield (f"Finished actions!")

            postaction = apiSrc.getPostAction()
            logging.debug(f"Postaction: {postaction}")
            logging.debug(f"Src: {src}")
            logging.debug(f'{available[self.getId(args)]["data"][int(self.getSel(args))]}')
            if (not postaction) and ((src[0] in ["cache","slack"])
                                     or('slack' in src[1])):
                # Different from batch process because we do not want the item
                # to reappear in scheduled sending. There can be problems if
                # the link is in some cache.
                postaction = "delete"
                logging.debug(f"Post Action {postaction}")
                try:
                    cmdPost = getattr(apiSrc, postaction)
                    logging.debug(f"Post Action cmd: {cmdPost}")
                    res = cmdPost(pos)
                    logging.debug(f"End {postaction}, reply: {res}")
                    ok = res.get('ok')
                    if ok: 
                        res = "Deleted!"
                    else:
                        res = "Something went wrong"
                except:
                    res = "No postaction or wrong one"
                yield (res)
        else:
            yield(f"We have no data, you should use 'list {args[:2]}'")
        yield end()

    @botcmd
    def show(self, mess, args):
        """A command to show the content of some update"""
        res = self.execute("show", args)
        yield res
        yield end()

    @botcmd
    def edit_show(self, mess, args):
        """Show the last edit commands"""
        for arg in self.argsArchive[-5:]:
            yield ("- %s" % arg)
        yield end()

    @botcmd
    def edit_link(self, mess, args):
        """A command to edit the link of some update"""
        if " " not in args:
            if self.lastLink:
                args = "{} {}".format(args, self.lastLink)
        res = self.execute("editl", args)
        self.lastLink = args.split(" ", 1)[1:][0]
        yield res
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        if " " not in args:
            if self.lastEdit:
                args = "{} {}".format(args, self.lastEdit)
        res = self.execute("edit", args)
        self.addEditsCache(args)
        self.lastEdit = args.split(" ", 1)[1:][0]
        yield res
        yield end()

    def addEditsCache(self, args):
        argsArchive = self.argsArchive   # ????
        self.argsArchive.append(args)

    @botcmd
    def archive(self, mess, args):
        """A command to move some update"""
        res = self.execute("archive", args)
        yield res
        yield end()

    @botcmd
    def move(self, mess, args):
        """A command to move some update"""
        res = self.execute("move", args)
        yield res
        yield end()

    @botcmd
    def delete(self, mess, args):
        """A command to delete some update"""
        res = self.execute("delete", args)
        yield (res)
        yield end()

    @botcmd #(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        res = self.execute("copy", args)
        yield "Copied"
        yield res
        yield end()

    def prepareReply(self, updates, types):
        compResponse = []
        logging.debug(f"Pposts {updates}")
        logging.debug(f"Keys {updates.keys()}")
        tt = "pending"
        for socialNetwork in updates.keys():
            logging.debug(f"Update social network {socialNetwork}")
            logging.debug(f"Updates {updates[socialNetwork]}\nEnd")
            logging.debug(f"Element: {socialNetwork}")
            theUpdates = []
            maxLen = 0
            for update in updates[socialNetwork]:
                if update:
                    if len(update) > 0:
                        logging.debug(f"Update {update} ")
                        if update[0]:
                            theUpdatetxt = str(update[0]).replace("_", r"\_")
                            if theUpdatetxt.find("> ") >= 0:
                                # We do not need to show the mark. Maybe we
                                # should consider a better approach.
                                theUpdatetxt = theUpdatetxt[1:]
                                tt = "longer"

                            lenUpdate = len(theUpdatetxt[:60])
                            if lenUpdate > maxLen:
                                maxLen = lenUpdate
                        else:
                            # This should not happen
                            theUpdatetxt = ""
                        theUpdates.append((theUpdatetxt, update[1], update[2]))
            logging.info(f"self.available ... {self.available}")
            logging.info(f"socialNetwork ... {socialNetwork}")
            data = self.available[self.getId(socialNetwork)]
            name = data["name"]
            logging.debug(f"Name ... {name}")
            pos = int(socialNetwork[1])
            logging.debug(f"Data: {data['data'][pos]}")
            social = socialNetwork
            src = data['data'][pos]['src']
            actions = self.rules.rules[src]
            myDest = ""
            for action in actions:
                myDest = (f"{myDest}\n"
                          #f" {self.rules.getNameAction(action)} "
                          f"        ⟶ "
                          f"{self.rules.getNameAction(action).capitalize()} "
                          f"({self.rules.getNickAction(action)}@"
                          f"{self.rules.getProfileAction(action)} "
                          f"{self.rules.getTypeAction(action)})")
            logging.debug(f"myDest: {myDest}")
            logging.debug(f"Actions: {actions}")
            logging.debug(f"Social ... {social}")
            logging.debug(f"Src ... {src}")
            typePosts = self.rules.getTypeRule(src)
            try:
                socialNetworktxt = (
                    f"{social.capitalize()} " 
                    f"{self.rules.getNameRule(src).capitalize()} "
                    f"({self.clients[socialNetwork].getNick()}@"
                    f"{self.rules.getSecondNameRule(src)} "
                    f"{typePosts})"
                )
            except:
                socialNetworktxt = (
                    f"{social.capitalize()} " 
                    f"{self.rules.getNameRule(src).capitalize()} ")
            if theUpdates:
                if len(socialNetwork) > 2:
                    socialNetworktxt = (
                        socialNetwork[2][1][0].capitalize()
                        + " ("
                        + socialNetwork[2][1][1]
                        + " "
                        + socialNetwork[0]
                        + ")"
                    )
                    logging.debug(f"socialNetwortxt: {socialNetworktxt}")
                    if len(socialNetworktxt) + 3 > maxLen:
                        maxLen = len(socialNetworktxt) + 3
                    if (1 + len(theUpdates)) * maxLen > 1024:
                        numEle = 1024 / maxLen
                        import math

                        iniPos = 0
                        maxPos = math.trunc(numEle)
                        if self.schedules:
                            maxPos = self.schedules
                            numEle = self.schedules
                        while iniPos <= len(theUpdates):
                            compResponse.append((tt,
                                                 socialNetworktxt,
                                                 myDest,
                                                 theUpdates[iniPos:maxPos]
                                                 )
                                                )
                            iniPos = maxPos
                            maxPos = maxPos + math.trunc(numEle)
                    else:
                        compResponse.append((tt, socialNetworktxt, 
                            myDest, theUpdates))
                else:
                    compResponse.append((tt, socialNetworktxt, 
                        myDest, theUpdates))
            else:
                compResponse.append((tt, socialNetworktxt,
                                     myDest, theUpdates,))

        return compResponse

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types)
        logging.debug(f"Reps: {reps}")
        for rep in reps:
            logging.debug(f"Rep: {rep}")
            response = (
                tenv()
                .get_template("buffer.md")
                .render(
                    {"type": rep[0],
                        "nameSocialNetwork": rep[1], 
                        "post": rep[2],
                        "updates": rep[3]}
                )
            )
            yield (response)

    @botcmd(split_args_with=None, template="buffer")
    def prog_del(self, mess, args):
        """A command to delete some schedule"""

        yield "Adding %s" % args
        for profile in self.clients:
            if "delSchedules" in dir(self.clients[profile]):
                self.clients[profile].delSchedules(args)
                yield "%s: (%s) %s" % (
                    profile[0],
                    profile[1],
                    self.clients[profile].getHoursSchedules(),
                )
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_add(self, mess, args):
        """A command to add a publishing time in the schedule"""
        yield "Adding %s" % args
        for profile in self.clients:
            if "addSchedules" in dir(self.clients[profile]):
                self.clients[profile].addSchedules(args)
                yield "%s: (%s) %s" % (
                    profile[0],
                    profile[1],
                    self.clients[profile].getHoursSchedules(),
                )
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_show(self, mess, args):
        """A command to show scheduled times"""
        for profile in self.clients:
            logging.debug("Profile: %s" % str(profile))
            if "setSchedules" in dir(self.clients[profile]):
                self.clients[profile].setSchedules("rssToSocial")
                schedules = self.clients[profile].getHoursSchedules()
                if isinstance(schedules, str):
                    numS = len(schedules.split(","))
                else:
                    numS = len(schedules)

                if numS:
                    self.schedules = numS
                yield "%s: (%s) %s Number: %s" % (
                    profile[0],
                    profile[1],
                    schedules,
                    numS,
                )
        yield (end())

    # def selectAndExecute(self, command, args):
    #     # FIXME Does this belong here?
    #     logging.info(f"Selecting {command} with {args} "
    #                  f"in {self.getService()}")
    #     argsCont = ''
    #     if not isinstance(args, str):
    #         logging.info(f"Aaaaargs: {args}")
    #         args,argsCont = args

    #     pos = args.find(' ')
    #     j = -1
    #     if pos > 0: 
    #         argsIni = args[:pos]
    #         if isinstance(argsCont, str):
    #             argsCont = args[pos+1:]
    #             logging.debug(f"Args {argsIni}-{argsCont}")
    #             if (argsCont and len(argsCont)>1): 
    #                 if argsCont[0].isdigit() and (argsCont[1] == ' '): 
    #                     j = int(argsCont[0])
    #                     argsCont = argsCont[2:]
    #     else: 
    #         argsIni = args
    #         logging.info(f"Args {argsIni}")

    #     pos = argsIni.find('*')
    #     if pos == 0: 
    #         """ If the first character of the argument is a '*' the
    #         following ones are the number. But we are supposing that they
    #         start at the third character, so we move the string one
    #         character to the right
    #         """
    #         argsIni=' {}'.format(argsIni)

    #     reply = ""

    #     if len(argsIni) > 2:
    #         j = int(argsIni[2:]) 
    #     logging.debug(f"Argscont {argsCont} j {j}")
    #     logging.debug(f"Self: {self}")
    #     cmd = getattr(self, command)
    #     logging.debug(f"Cmd: {cmd}")
    #     if (j>=0):
    #         logging.info("Command %s %d"% (command, j))
    #         if argsCont:
    #             reply = reply + str(cmd(j, argsCont))
    #         else: 
    #             reply = reply + str(cmd(j))
    #     else:
    #         logging.info("Missing argument %s %d"% (command, j))
    #         reply = "Missing argument"

    #     logging.info(f"Reply: {reply}")
    #     return(reply)

    # def getIniKey(self, key, myKeys, myIniKeys):
    #     if key not in myKeys:
    #         if key[0] not in myIniKeys:
    #             iniK = key[0]
    #         else:
    #             i = 1
    #             while (i < len(key)) and (key[i] in myIniKeys):
    #                 i = i + 1
    #             if i < len(key):
    #                 iniK = key[i]
    #             else:
    #                 iniK = "j"
    #                 while iniK in myIniKeys:
    #                     iniK = chr(ord(iniK) + 1)
    #         myKeys[key] = iniK
    #     else:
    #         iniK = myKeys[key]
    #     myIniKeys.append(iniK)
    #     pos = key.find(iniK)
    #     if pos >= 0:
    #         nKey = key[:pos] + iniK.upper() + key[pos + 1:]
    #     else:
    #         nKey = iniK + key
    #     nKey = key + "-{}".format(iniK)

    #     return iniK, nKey


