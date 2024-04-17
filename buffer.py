import configparser
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
        self.log.debug(f"Checking available")
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
        res = -1
        if arg and len(arg)>2:
            try:
                res = int(arg[2:].split(' ')[0])
            except:
                logging.debug("It is not a position")
        return res

    def getCont(self, arg):
        res = None
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
                self.log.debug("line 1 {}".format(line1))
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
        if (('blogalia' in nick) 
            or ('wordpress' in nick)
            or ('github.com' in nick)
            or ('feed.xml' in nick)):
            nick = urllib.parse.urlparse(nick).netloc
        else:
            nick = nick.replace('/','-').replace(':','-')
        return (f"{self.rules.getNameRule(rule).capitalize()}_"
                f"{self.rules.getTypeRule(rule)}_"
                f"{nick}_" 
                # f"{self.rules.getIdRule(rule).capitalize()}_"
                f"{self.rules.getSecondNameRule(rule).capitalize()}_"
                f"_{self.rules.getNameAction(action).capitalize()}"
                f"_{self.rules.getTypeAction(action)}s"
                f"_{self.rules.getNickAction(action)}"
                f"_{self.rules.getProfileAction(action).capitalize()}"
               )

    def cleanLine(self, line, key="", i=None):
        line = line.split('_')
        if key:
            line = f"{key}{i} {line[0]} ({line[2]} {line[1]})"
        else:
            line = f"{line[0]} ({line[2]} {line[1]})"
        line = line.replace('https', '').replace('http','')
        line = line.replace('---','').replace('.com','')
        line = line.replace('- ',' ')
        return line

    @botcmd(split_args_with=None, template="buffer")
    def list_next(self, mess, args):
        self.setAvailable()
        textW = []
        textF = []
        for key in self.available:
            for i, elem in enumerate(self.available[key]["data"]):
                src = elem['src']
        #for src in self.rules.rules:
                hold = self.rules.more[src].get('hold','')
                if (not hold or (not hold == 'yes')):
                    msg =  f"Rule: {src}"
                    self.log.debug(msg)
                    msg =  f"Actions: {self.rules.rules[src]}"
                    self.log.debug(msg)
                    msg =  f"More: {self.rules.more[src]}"
                    self.log.debug(msg)
                    for action in self.rules.rules[src]:
                        actionF = self.fileNameBase2(src, action)
                        actionF = actionF.replace('caches', 'posts')
                        actionF = actionF.replace('cache', 'posts')
                        self.log.debug(f"Action file: {actionF}")
                        # yield f"Action: {actionF}"
                        if os.path.exists(f"{DATADIR}/{actionF}.timeNext"):
                            fileNext = f"{DATADIR}/{actionF}.timeNext"
                            self.log.debug(f"File next: {fileNext}")
                            with open(fileNext, "rb") as f:
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

                        if t1:
                            orig, dest = actionF.split('__')
                            orig = f"{self.cleanLine(orig, key, i)}"
                            dest = self.cleanLine(dest)
                            textElement = (f"{theTime} | {theTime} {orig} -> {dest}")
                            if msg.find("[W]") >= 0:
                                textW.append(textElement)
                            else:
                                textF.append(textElement)
                            self.log.debug(f"Element text {textElement}")
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

    @botcmd(split_args_with=None)
    def list_actions(self, msg, args):
        """Add all available actions"""
        self.setAvailable()

        rules = self.rules
        available = {}
        myKeys = {}
        myIniKeys = []
        actions = {}
        logging.debug(f"Rules: {rules.rules}")
        rules.indent = ''
        for rule in rules.rules:
            for action in rules.rules[rule]:
                service = rules.getProfileAction(action)
                if rules.hasPublishMethod(service):
                    #FIXME: publishPost is in modulecontent
                    iniK, nameK = rules.getIniKey(service.upper(), 
                                                  myKeys, myIniKeys)
                    more = rules.more[rule]
                    if not (iniK in available):
                        available[iniK] = {"name": service, 
                                           "data": [], "social": [], 
                                           "actions": []} 
                        available[iniK]["data"] = []
                    available[iniK]["data"].append({'src': action,
                                                    'more': more})
                    logging.debug(f"Action: {action}")
                    logging.debug(f"Service: {service}")
                    if service not in actions:
                        actions[service] = [action, ]
                    else:
                        actions[service].append(action)
                    if action not in available[iniK]["actions"]:
                        available[iniK]["actions"].append(action)

        logging.debug(f"Actions: {actions}")
        logging.debug(f"Available: {available}")

        myList = {}
        theKey = ("M0")
        myList[theKey] = []
        keys = []
        for key in available:
            #yield f"- Key: {key} {available[key]['name']}"
            for i,action in enumerate(available[key]['actions']):
                service = rules.getProfileAction(action)
                myList[theKey].append((f"{service.capitalize()} "
                                       f"{rules.getNickAction(action)}@"
                                       f"{service}"
                                       f"{rules.getTypeAction(action)}",
                                       key, f"{key}{i}"))
                # yield f"{key}{i}) {service} {rules.getNickAction(action)}"
            keys.append(f"{key}{i}")
        self.log.debug("list actions (myList): {str(myList)}")
        keys = ','.join(keys)
        myList[theKey].append((keys, "", "I"))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ('\n'.join(rep.split('\n')[3:]))

    @botcmd
    def list_all(self, mess, args):
        """List available services"""
        yield f"Args: {args}"
        self.setAvailable()

        rules = self.rules

        self.log.debug("Available: %s" % str(self.available))
        # yield("Available: %s" % str(self.available))
        myList = {}
        theKey = ("L0")
        myList[theKey] = []
        keys = []
        for key in self.available:
            for i, elem in enumerate(self.available[key]["data"]):
                if (args and (key == args.lower())) or not args:
                    self.log.debug(f"Elem: {elem}")
                    name = rules.getNameRule(elem['src'])
                    profile = rules.getSecondNameRule(elem['src'])
                    nick = rules.getNickRule(elem['src'])
                    if 'http' in nick:
                        #FIXME: duplicate code
                        nick = urllib.parse.urlparse(nick).netloc
                    src = elem['src']
                    myList[theKey].append((f"{name.capitalize()} "
                                           f"({nick}@{profile} "
                                           f"{self.rules.getTypeRule(src)})", 
                                           key, f"{key}{i}"))
            keys.append(f"{key}{i}")
        self.log.debug("myList: %s" % str(myList))
        keys = ','.join(keys)
        myList[theKey].append((keys, "", "I"))
        # yield("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ('\n'.join(rep.split('\n')[3:]))

        return end

    def appendMyList(self, arg, myList):
        self.log.debug(f"Args... {arg}")
        self.setAvailable()

        if self.getId(arg) in self.available:
            pos = self.getSel(arg)
            if pos < len(self.available[self.getId(arg)]["data"]):
                myList.append(arg.capitalize())
            
        self.log.debug(f"myList: {myList}")

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
                self.log.debug("Element %s" % str(element))
                self.log.debug("Clients %s" % str(clients))
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

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """A command to show available posts in a list of available sites"""
        self.log.debug("Posts posts %s" % (self.posts))
        self.log.debug("args %s" % str(args))

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

            self.log.debug("myList %s" % str(myList))

        self.lastList = myList
        clients = self.clients

        if not myList: 
            yield (self.addMore())

        for element in myList:
            self.log.debug("Clients %s" % str(clients))
            self.log.debug("Element %s" % str(element))
            self.log.debug(f"Available {available}")
            profile = available[self.getId(element)]
            name = profile["name"]
            myElem = profile["data"][self.getSel(element)]
            self.log.debug(f"myElem {myElem}")
            src = myElem['src']
            self.log.debug(f"src {src}")
            more = self.rules.more[src]
            self.log.debug(f"more {more}")

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
                    # self.log.debug("I: %s %s %d"%(title,link,i))

            self.posts[element] = posts
            self.log.debug("Posts posts %s" % (self.posts))

        response = self.sendReply("", "", self.posts, ["sent", "pending"])
        self.log.debug("Response %s End" % str(response))

        for resp in response:
            self.log.debug(f"Resp: {resp}")
            yield (resp)

        self.clients = clients
        yield end()

    @botcmd(split_args_with=' ')
    def last(self, command, args):
        clients = self.clients
        self.log.debug(f"Clients: {clients}")
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
        yield (f"Name: {rules.getIdRule(src)}")
        myActions = rules.rules[src]
        selectClient = f"{self.getId(firstArg)}{self.getSel(firstArg)}"
        if not selectClient in clients:
            yield f"You should execute 'list {selectClient}' first"
            return 
        apiSrc = clients[selectClient]
        for i, action in enumerate(myActions):
            yield(f"Action {i}. {rules.getNickAction(action)}@"
                  f"{rules.getProfileAction(action)}"
                  f"({rules.getNameAction(action)}-"
                  f"{rules.getTypeAction(action)})")
            apiDst = rules.readConfigDst('', action, rules.more[src], apiSrc)
            apiSrc.fileName = ''
            apiSrc.setLastLink(apiDst)
            if lastLink:
                self.log.debug(f"Updating last link")
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
        self.log.debug(resTxt)
        resTxt = f"{resTxt}Args: {args}\n"
        self.log.debug(resTxt)
        updates = ""
        update = None
        res = None
        if self.available:
            clients = self.clients
            self.log.debug("Clients {}".format(clients))
            available = self.available
            rules = self.rules
            res = ""
            #for profile in self.clients:
            profile = self.getId(args)
            self.log.debug(f"Executing in profile: {profile} with "
                          f"args {args}")
            idArg = self.getId(args)
            name = available[idArg]["name"]
            selArg = int(self.getSel(args))
            src = available[idArg]["data"][selArg]['src']
            self.log.debug(f"Src: {src}")
            dest = str(src)

            self.log.debug(f"Clients: {clients}")
            self.log.debug(f"Rules rules: {rules.rules}")
            self.log.debug(f"Name {name} dest: {dest}")
            self.log.debug(f"It is: {dest in rules.rules}")
            for i in rules.rules:
                self.log.debug(f"Rule: {i}")

            myActions = rules.rules[src]
            self.log.debug(f"My actions: {myActions}")
            myClient = f"{idArg}{selArg}".upper()
            apiSrc = clients[myClient]
            apiSrc.setPosts()
            pos = self.getPos(args)
            self.log.debug(f"Pos: {pos}")
            argCont = self.getCont(args)
            self.log.debug(f"Cont: {argCont}")
            post = apiSrc.getPost(pos)

            self.log.debug(f"Selecting {command} with {args} " 
                         f"in {apiSrc.getService()}")
            self.log.debug(f"Posts: {apiSrc.getPosts()}")
            cmd = getattr(apiSrc, command)
            self.log.debug(f"Command: {command} is {cmd}")
            if argCont is not None: 
                self.log.debug(f"Argcont: {argCont}")
                if isinstance(argCont, str) and argCont.capitalize() in clients:
                    argCont = clients[argCont.capitalize()]
                update = cmd(pos, argCont)
            else:
                update = cmd(pos)
            
            updates = f"{updates}* {update} ({profile[0]})\n"

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
            self.log.debug(f"Clients: {clients}")
            available = self.available
            rules = self.rules

            self.log.debug(f"Publishing {args}")
            yield (f"Publishing {args}")
            res = ""

            idArg = self.getId(args)
            name = available[idArg]["name"]
            selArg = int(self.getSel(args))
            src = available[idArg]["data"][selArg]['src']
            self.log.debug(f"Src: {src}")
            dest = str(src)

            self.log.debug(f"Clients: {clients}")
            self.log.debug(f"Rules rules: {rules.rules}")
            self.log.debug(f"Name {name} dest: {dest}")
            self.log.debug(f"It is: {dest in rules.rules}")
            # for i in rules.rules:
            #     self.log.debug(f"Rule: {i}")

            post = None
            myActions = rules.rules[src]
            self.log.debug(f"My actions: {myActions}")
            myClient = f"{idArg}{selArg}".upper()
            apiSrc = clients[myClient]
            apiSrc.setPosts()
            pos = self.getPos(args)
            self.log.debug(f"Pos: {pos}")
            if pos>=0:
                post = apiSrc.getPost(pos)
                title = apiSrc.getPostTitle(post)
                link = apiSrc.getPostLink(post)
                self.log.debug(f"Title: {title}")
                yield(f"Will publish: {title} - {link}")
                self.log.debug(f"Link: {link}")
                self.log.debug(f"Actions: {myActions}")

                published = False

                if 'hold' in rules.more[src]:
                    rules.more[src]['hold'] = 'no'
                for i, action in enumerate(myActions):
                    nameAction = rules.getNameAction(action)
                    typeAction = rules.getTypeAction(action)
                    self.log.debug(f"Action {i}: {action} {nameAction}")
                    yield(f"Action {i}. {rules.getNickAction(action)}@"
                          f"{rules.getProfileAction(action)}"
                          f"({nameAction}-{typeAction})")
                    resExecute = rules.executeAction(src, rules.more[src], 
                                                     action, noWait=True, 
                                                     timeSlots=0, 
                                                     simmulate=False, 
                                                     name=(f"{name} " 
                                                           f"{typeAction}",
                                                     nextPost=False, 
                                                     pos=pos, delete=False)
                    self.log.info(f"Res execute: {resExecute}")
                    yield f"{resExecute}"
            else: 
                argSplit = args.split(' ')
                if len(argSplit)>1:
                    post = ' '.join(argSplit[1:])
                    for i, action in enumerate(myActions): 
                        nameAction = rules.getNameAction(action)
                        typeAction = rules.getTypeAction(action)
                        self.log.debug(f"Action {i}: {action} {nameAction}")
                        yield(f"Action {i}. {rules.getNickAction(action)}@"
                          f"{rules.getProfileAction(action)}"
                          f"({nameAction}-{typeAction})") 
                        apiDst = rules.readConfigDst('', action, 
                                                rules.more[src], None) 
                        apiDst.publishPost(post, '', '')
                yield f"We need some position or something to publish"
                yield f"Args: {args}"
                yield f"Post: {post}"

            yield (f"Finished actions!")

            postaction = apiSrc.getPostAction()
            self.log.debug(f"Postaction: {postaction}")
            self.log.debug(f"Src: {src}")
            self.log.debug(f'{available[self.getId(args)]["data"][int(self.getSel(args))]}')
            if (not postaction) and ((src[0] in ["cache","slack"])
                                     or('slack' in src[1])):
                # Different from batch process because we do not want the item
                # to reappear in scheduled sending. There can be problems if
                # the link is in some cache.
                postaction = "delete"
                self.log.debug(f"Post Action {postaction}")
                try:
                    cmdPost = getattr(apiSrc, postaction)
                    self.log.debug(f"Post Action cmd: {cmdPost}")
                    res = cmdPost(pos)
                    self.log.debug(f"End {postaction}, reply: {res}")
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
    def edit_add(self, mess, args):
        """A command to edit some update"""
        res = self.execute("edita", args)
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
        self.log.debug(f"Pposts {updates}")
        self.log.debug(f"Keys {updates.keys()}")
        tt = "pending"
        for socialNetwork in updates.keys():
            self.log.debug(f"Update social network {socialNetwork}")
            self.log.debug(f"Updates {updates[socialNetwork]}\nEnd")
            self.log.debug(f"Element: {socialNetwork}")
            theUpdates = []
            maxLen = 0
            for update in updates[socialNetwork]:
                if update:
                    if len(update) > 0:
                        self.log.debug(f"Update {update} ")
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
            self.log.debug(f"self.available ... {self.available}")
            self.log.debug(f"socialNetwork ... {socialNetwork}")
            data = self.available[self.getId(socialNetwork)]
            name = data["name"]
            self.log.debug(f"Name ... {name}")
            pos = int(socialNetwork[1])
            self.log.debug(f"Data: {data['data'][pos]}")
            social = socialNetwork
            src = data['data'][pos]['src']
            actions = self.rules.rules[src]
            myDest = ""
            if not (('hold' in self.rules.more[src])
                    and (self.rules.more[src]['hold'] == 'yes')):
                for action in actions:
                    myDest = (f"{myDest}\n"
                              # f" {self.rules.getNameAction(action)} "
                              f"        ⟶ "
                              f"{self.rules.getNameAction(action).capitalize()} "
                              f"({self.rules.getNickAction(action)}@"
                              f"{self.rules.getProfileAction(action)} "
                              f"{self.rules.getTypeAction(action)})")
            self.log.debug(f"myDest: {myDest}")
            self.log.debug(f"Actions: {actions}")
            self.log.debug(f"Social ... {social}")
            self.log.debug(f"Src ... {src}")
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
                self.log.debug(" not socialNetwork > 2")
                compResponse.append((tt, socialNetworktxt, myDest, theUpdates))
            else:
                self.log.debug(" no updates")
                compResponse.append((tt, socialNetworktxt, myDest, theUpdates,))

        return compResponse

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types)
        self.log.debug(f"Reps: {reps}")
        for rep in reps:
            self.log.debug(f"Rep: {rep}")
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
        self.setAvailable()
        if not self.clients:
            yield(f"You have not selected any service to show. "
                  f"You need to list at least one service")
        for profile in self.clients:
            self.log.debug("Profile: %s" % str(profile))
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

