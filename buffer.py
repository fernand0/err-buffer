import configparser
import logging
import os
import pickle
import pprint
import time

from errbot import BotPlugin, botcmd
from errbot.templating import tenv

# Needs to set $PYTHONPATH to the dir where this modules are located

from configMod import *
# import moduleBuffer
import moduleRules


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

    # def hasSetMethods(self, service):
    #     if service == "social":
    #         return []
    #     clsService = getModule(service)
    #     listMethods = clsService.__dir__()

    #     methods = []
    #     for method in listMethods:
    #         if (not method.startswith("__")) and (method.find("set") >= 0):
    #             action = "set"
    #             target = ""
    #             myModule = eval(f"clsService.{method}.__module__")

    #             if method.find("Api") >= 0:
    #                 target = method[len("setApi"):].lower()
    #             # elif (clsService.setPosts.__module__
    #             elif myModule == f"module{service.capitalize()}":
    #                 target = method[len("set"):].lower()
    #             if target and (
    #                 target.lower() in ["posts", "drafts", "favs",
    #                                    "messages", "queue"]
    #                           ):
    #                 toAppend = (action, target)
    #                 if not (toAppend in methods):
    #                     methods.append(toAppend)
    #     return methods

    # def hasPublishMethod(self, service):
    #     clsService = getModule(service)
    #     listMethods = clsService.__dir__()

    #     methods = []
    #     target = None
    #     for method in listMethods:
    #         if method.find("publish") >= 0:
    #             action = "publish"
    #             target = ""
    #             moduleService = clsService.publishPost.__module__
    #             if method.find("Api") >= 0:
    #                 target = method[len("publishApi"):].lower()
    #                 logging.info(f"Target api {target}")
    #             elif moduleService == f"module{service.capitalize()}":
    #                 target = method[len("publish"):].lower()
    #                 logging.info(f"Target mod {target}")
    #             # else:
    #             #    target = 'post'
    #             #    logging.info(f"Target else {target}")
    #             if target:
    #                 toAppend = (action, target)
    #                 if not (toAppend in methods):
    #                     methods.append(toAppend)
    #     return methods

    # def getServices(self):
    #     modulesFiles = os.listdir("/home/ftricas/usr/src/socialModules")
    #     modules = {"special": ["cache", "direct"], "regular": []}
    #     # Initialized with some special services
    #     name = "module"
    #     for module in modulesFiles:
    #         if module.startswith(name):
    #             moduleName = module[len(name): -3].lower()
    #             if not (moduleName in modules["special"]):
    #                 # We drop the 'module' and the '.py' parts
    #                 modules["regular"].append(moduleName)

    #     return modules

    def checkRules(self):
        # FIXME Does this belong here?
        self.rules = moduleRules.moduleRules()
        self.rules.checkRules()

    # def printList(self, myList, title):
    #     print(f"{title}:")
    #     for i, element in enumerate(myList):
    #         print(f"  {i}) {element}")

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

    def addMore(self):
        response = (
            f"There are {len(self.config)} lists. "
            f"You can add more with command list add"
        )
        return response

    def formatList(self, text, status):
        textR = []
        if text:
            textR.append("=======")
            textR.append("{}:".format(status.capitalize()))
            textR.append("=======")
            logging.info(f"Text: {text}")
            for line in text:
                lineS = line.split("|")[1]
                textR.append(lineS.replace('->',' ⟶'))
        else:
            textR.append("===========")
            textR.append("None {}".format(status))
            textR.append("===========")

        return textR

    @botcmd(split_args_with=None, template="buffer")
    def list_next(self, mess, args):
        myList = os.listdir(DATADIR)
        textW = []
        textF = []
        for element in myList:
            logging.info(f"Element {element}")
            if (element.find("last") > 0) and (element.find("Next") > 0):
                continue
            if ((element.find("Next") > 0)
                    or ((args and (args[0] in 'available'))
                        and (element.find("Available")>0))):
                # yield element
                if element.find("__") > 0:
                    res = element[:-len('.timeNext')]
                    res = res.split("__")
                    src = res[0].split('_')
                    dst = res[1].split('_')

                    orig = src[0]
                    if src[1] != 'posts':
                        nickOrig = f"{src[1]}@{src[2]}"
                    else:
                        nickOrig = f"{src[2]}"
                    #url = f"{src[0]} ({src[2]} {src[1]})"
                    nickOrig = nickOrig.replace('https', '').replace('http','')
                    nickOrig = nickOrig.replace('---','').replace('.com','')
                    nickOrig = nickOrig.replace('-(','(').replace('- ',' ')
                    nickOrig = nickOrig .replace('feeds-','').replace('feed','')
                    nickOrig = nickOrig.replace('user-','').replace('services','')
                    if nickOrig.endswith('-'):
                        nickOrig = nickOrig[:-1]

                    #dest = f"{dst[0]}({dst[1]}){dst[2]}"
                    dest = f"{dst[0]}"
                    if dst[1] != 'posts':
                        nick = f"{dst[1]}@{dst[2]}"
                    else:
                        if len(dst)>2:
                            nick = f"{dst[2]}"
                        else:
                            nick = f"{dst}"
                    nick = nick.replace('https', '').replace('http','')
                    nick = nick.replace('---','').replace('.com','')
                    nick = nick.replace('-(','(').replace('- ',' ')
                    nick= nick.replace('feeds-','').replace('feed','')
                    nick= nick.replace('user-','').replace('services','')
                    if nick.endswith('-'):
                        nick = nick[:-1]
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
                logging.info(f"Res {res}")
                logging.info(f"Orig: {orig}")
                t1 = None
                if True:
                    if element.find("Next") > 0:
                        logging.info(f"File {DATADIR}/{element}")
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
                    textElement = (f"{t1 + t2}|{theTime} {orig} -> "
                                   f"{dest.capitalize()}\n"
                                   f"   ({nickOrig} -> {nick})")
                    if msg.find("[W]") >= 0:
                        textW.append(textElement)
                    else:
                        textF.append(textElement)
                    logging.info(f"Element text {textElement}")
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
        if not self.available:
            self.checkRules()
        logging.info("Available: %s" % str(self.available))
        myList = {}
        theKey = ("A0")
        myList[theKey] = []
        for key in self.rules.available:
            for i, elem in enumerate(self.rules.available[key]["data"]):
                if (args and (key == args)) or not args:
                    logging.debug(f"key: {key}")
                    logging.debug(f"elem: {elem}")
                    logging.debug(f"available: {self.rules.available[key]}")
                    myList[theKey].append((elem['src'], key, f"{key}-{i}"))
        logging.info("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            yield (rep)

        return end

    def appendMyList2(self, arg, myList):
        logging.debug(f"Args... {arg}")
        logging.debug(f"Avail... {self.rules.available}")
        logging.debug(f"Ruls... {self.rules.rules}")
        for key in self.rules.available.keys():
            if arg[0].capitalize() == key.capitalize():
                if arg[1:].isdigit():
                    pos = int(arg[1:])
                    # What happens when str(int(arg[1:])) is not  arg[1:]?
                    # For example, 00, 01, ...
                    # C00, C01
                    arg = arg[0]+str(pos)
                if pos < len(self.rules.available[key]["data"]):
                    myList.append(arg.capitalize())
        logging.debug("mylist... %s" % str(myList))

    def appendMyList(self, arg, myList):
        logging.debug("Args... {}".format(str(arg)))
        for key in self.available.keys():
            if arg[0].capitalize() == key.capitalize():
                if arg[1:].isdigit():
                    pos = int(arg[1:])
                if pos < len(self.available[key]["data"]):
                    myList.append(arg.capitalize())
        logging.debug("mylist... %s" % str(myList))

    # def appendMyListOld(self, arg, myList):
    #     logging.debug("Args... {}".format(str(arg)))
    #     logging.debug(f"avail: {self.rules.available}")
    #     logging.debug(f"avail: {self.rules.available.keys()}")
    #     for key in self.available:
    #         if arg[0].capitalize() == key.capitalize():
    #             if arg[1:].isdigit():
    #                 pos = int(arg[1:])
    #             if pos < len(self.available[key]["data"]):
    #                 myList.append(arg.capitalize())
    #     logging.debug("mylist... %s" % str(myList))

    @botcmd(split_args_with=None, template="buffer")
    def list_read(self, mess, args):
        # Maybe define a flow?
        myList = []
        pos = 0
        clients = self.clients
        if args:
            if args[0].isdigit():
                pos = int(args[0])
            yield (args[0])
            self.appendMyList(args[0], myList)
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
                logging.info("Element %s" % str(element))
                logging.info("Clients %s" % str(clients))
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
            if args[0].isdigit():
                pos = int(args[0])
            yield (args[0])

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
        if not hasattr(self, 'rules'):
            self.checkRules()

        myList = []

        for arg in args:
            self.appendMyList2(arg, myList)

        if myList:
            self.config.append(myList)

        yield (self.config)
        yield (end())

    @botcmd
    def list_list(self, msg, args):
        if not hasattr(self, 'rules'):
            self.checkRules()

        response = [self.rules.availableList]
        yield response
        yield end()

    def getKey(self, element):
        # FIXME this should be done via moduleRules and so on
        profile = self.rules.available[element[0].lower()]
        logging.debug(f"getKey: {profile['data'][int(element[1])]['src']}")
        key = (profile['name'], ) + profile['data'][int(element[1])]['src']
        return key 

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """A command to show available posts in a list of available sites"""
        import moduleRules
        if not hasattr(self, 'rules'):
            self.checkRules()

        myList = []
        response = []
        self.posts = {}
        clients = self.clients
        logging.info("Clients %s" % str(clients))

        pos = -1

        if args:
            if args[0].isdigit():
                pos = int(args[0])
        else:
            pos = 0

        if (len(self.config) == 0) and (not args):
            yield ("There are not lists defined")
            yield ("Add some elements with list add")
            return
        elif (pos >= 0) and (pos < len(self.config)):
            if len(self.config) > 0:
                myList = self.config[pos]
        else:
            self.appendMyList2(args[0].upper(), myList)
            pos = 0

        logging.debug(f"myList {myList}")
        self.lastList = myList

        if pos >= 0:
            for element in myList: 
                src = self.getKey(element)
                if src in self.rules.more:
                    more = self.rules.more[src]
                else:
                    more = {}

                try:
                    clients[element].setPosts()
                except:
                    api = self.rules.readConfigSrc("", src, more)
                    clients[element] = api
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
                logging.info("Posts posts %s" % (self.posts))
                response = self.sendReply(mess, args, self.posts,
                                          ["sent", "pending"])
                logging.debug("Response %s End" % str(response))

        if response:
            logging.debug("Response %s End" % str(response))
            for resp in response:
                logging.info(f"Resp: {resp}")
                yield (resp)
        else:
            yield (self.addMore())

        self.clients = clients
        yield end()

    # @botcmd(split_args_with=None, template="buffer")
    # def listOld(self, mess, args):
    #     """A command to show available posts in a list of available sites"""
    #     logging.debug("Posts posts %s" % (self.posts))
    #     logging.debug("args %s" % str(args))

    #     myList = []
    #     response = []
    #     self.posts = {}
    #     if not self.available:
    #         self.checkRules()

    #     available = self.available

    #     pos = -1
    #     if args:
    #         if args[0].isdigit():
    #             pos = int(args[0])
    #     else:
    #         pos = 0

    #     if (len(self.config) == 0) and (not args):
    #         yield ("There are not lists defined")
    #         yield ("Add some elements with list add")
    #         return
    #     elif (pos >= 0) and (pos < len(self.config)):
    #         if len(self.config) > 0:
    #             myList = self.config[pos]
    #     else:
    #         self.appendMyList(args[0].upper(), myList)
    #         pos = 0

    #     logging.debug("myList %s" % str(myList))
    #     self.lastList = myList
    #     clients = self.clients

    #     if pos >= 0:
    #         for element in myList:
    #             logging.debug("Clients %s" % str(clients))
    #             logging.debug("Element %s" % str(element))
    #             logging.debug(f"Available {available}")
    #             profile = available[element[0].lower()]
    #             logging.debug(f"Profile {profile}")
    #             name = profile["name"]
    #             logging.debug(f"Name {name}")
    #             myElemOld = profile["data"][int(element[1:])]['src']
    #             logging.debug(f"myElem {myElemOld}")
    #             #myElem = (myElemOld[1][0], myElemOld[1][1], 'posts')
    #             if name == 'cache':
    #                 # FIXME
    #                 if 'slack' in myElemOld[1][0]:
    #                     name1 = 'slack'
    #                 elif 'imgur' in myElemOld[1][0]:
    #                     name1 = 'imgur'
    #                 elif 'gitter' in myElemOld[1][0]:
    #                     name1 = 'gitter'
    #                 myElem = (name1, myElemOld[1][0], 
    #                     f"{myElemOld[1][1][0]}@{myElemOld[1][1][1]}")
    #                 typePosts = 'posts'
    #             else:
    #                 myElem = (name, myElemOld[1])
    #                 typePosts = myElemOld[2]
    #             logging.debug(f">myElem {myElem}")
    #             try:
    #                 clients[element].setPosts()
    #             except:
    #                 api = getApi(name.capitalize(), myElem)
    #                 #if name == 'cache':
    #                 #    # FIXME
    #                 #    api.socialNetwork=myElem['src'][1][1][0]
    #                 #    api.nick=myElem['src'][1][1][1]
    #                 clients[element] = api
    #                 clients[element].setPostsType(typePosts)
    #                 clients[element].setPosts()

    #             self.log.debug("posts", clients[element].getPosts())

    #             postsTmp = []
    #             posts = []

    #             if hasattr(clients[element], "getPostsType"):
    #                 if clients[element].getPostsType() == "drafts":
    #                     postsTmp = clients[element].getDrafts()
    #                 else:
    #                     postsTmp = clients[element].getPosts()
    #             else:
    #                 postsTmp = clients[element].getPosts
    #             if postsTmp:
    #                 for (i, post) in enumerate(postsTmp):
    #                     if hasattr(clients[element], "getPostLine"):
    #                         title = clients[element].getPostLine(post)
    #                         link = ""
    #                     else:
    #                         title = clients[element].getPostTitle(post)
    #                         link = clients[element].getPostLink(post)
    #                     posts.append((title, link, "{:2}".format(i)))
    #                     # logging.debug("I: %s %s %d"%(title,link,i))

    #             self.posts[element] = posts
    #             logging.info("Posts posts %s" % (self.posts))
    #             response = self.sendReply(mess, args, self.posts,
    #                                       ["sent", "pending"])
    #             logging.debug("Response %s End" % str(response))

    #     if response:
    #         for resp in response:
    #             logging.info(f"Resp: {resp}")
    #             yield (resp)
    #     else:
    #         yield (self.addMore())

    #     self.clients = clients
    #     yield end()

    def execute(self, command, args):
        """Execute a command """
        resTxt = f"Executing: {command}\n"
        logging.info(resTxt)
        resTxt = f"Args: {args}\n"
        logging.info(resTxt)
        updates = ""
        update = None
        res = None
        logging.debug("Clients {}".format(self.clients))
        for profile in self.clients:
            logging.debug(f"Trying to execute in profile: {profile} "
                          f"with args {args}")
            theProfile = profile[:2]
            if (
                (theProfile.upper() == args[: len(theProfile)].upper())
                or (args[0] == "*")
                or (("*" in args) and (args[:1] == profile[0][:1]))
            ):
                # We need to do something for '*' commands
                logging.info(f"I'll {command} in {profile}")
                if command in ["copy"]:
                    destination = args[len(theProfile)+1+1:].upper()
                    logging.debug(f"Args: {destination}")
                    logging.debug(f"Client: {self.clients}")
                    logging.debug(f"Client: {self.clients[destination]}")
                    update = self.clients[profile].selectAndExecute(command, 
                            [args, self.clients[destination]])
                else:
                    update = self.clients[profile].selectAndExecute(command, args)
                if update:
                    updates = f"{updates}* {update} ({profile[0]})\n"
                    update = None

        if updates:
            res = f"{resTxt}\n{updates}"

        return res

    @botcmd
    def insert(self, mess, args):
        """A command to insert some update"""
        res = self.execute("insert", args)
        yield res
        yield end()

    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""
        yield(f"arg: {args}")
        src = self.getKey(args)
        more = self.rules.more[src]
        actions = self.rules.rules[src]
        for k, action in enumerate(actions):
            yield f"{k}) {action}"
            #FIXME code duplicated with  moduleRules
            pos = int(args[2:])
            if 'hold' in more:
                more['hold'] = 'no'
            res = self.rules.executeAction(src, more, action, True, 0, 
                                            False, "", False, pos)
        #res = self.execute("publish", args)
            yield res

        # if (src[0] in ["cache","slack", "gitter", "twitter", "mastodon"]):
        if (src[0] in ["slack", "gitter"]):
            # FIXME
            # Different from batch process because we do not want the item to
            # reappear in scheduled sending. There can be problems if the link
            # is in some cache.
            yield self.execute("delete", args)
 
        yield end()

    # # Passing split_args_with=None will cause arguments to be split on any kind
    # # of whitespace, just like Python's split() does
    # @botcmd
    # def publishOld(self, mess, args):
    #     """A command to publish some update"""

    #     clients = self.clients
    #     logging.debug(f"Clients: {clients}")
    #     available = self.available
    #     rules = self.rules

    #     logging.info(f"Publishing {args}")
    #     yield (f"Publishing {args}")
    #     res = ""

    #     # yield(f"Avail: {available}")
    #     logging.debug(f"Avail: {available}")
    #     dst = (
    #         available[args[0].lower()]["name"],
    #         "set",
    #         available[args[0].lower()]["data"][int(args[1])]['src'][1],
    #         available[args[0].lower()]["data"][int(args[1])]['src'][2],
    #     )
    #     src = (dst[0], dst[2])
    #     # yield(f"Src: {src}")
    #     # yield(f"Dst: {dst}")
    #     logging.info(f"Src: {src}")
    #     logging.info(f"Dst: {dst}")
    #     logging.debug(f"Rules: {rules}")
    #     if isinstance(dst[2], tuple):
    #         nickSn = f"{dst[2][1][0]}@{dst[2][1][1]}"
    #         dst2 = dst[:2]+ (nickSn,)+('posts', )
    #     else:
    #         dst2 = dst
    #     logging.debug(f"Dst2: {dst2}")
    #     actions = rules[dst2]
    #     apiSrc = getApi(src[0], src[1])
    #     # yield apiSrc
    #     apiSrc.setPostsType(dst[3])
    #     apiSrc.setPosts()
    #     j = int(args[2:])
    #     post = apiSrc.getPost(j)
    #     title = apiSrc.getPostTitle(post)
    #     link = apiSrc.getPostLink(post)
    #     logging.debug(f"Title: {title}")
    #     logging.debug(f"Link: {link}")
    #     logging.debug(f"Actions: {actions}")

    #     published = False
    #     for i, action in enumerate(actions):
    #         if post: 
    #             logging.info(f"Action {i}: {action} with post: {post}")
    #         if action[0] == "cache":
    #             apiDst = getApi("cache", (src[1], (action[2], action[3])))
    #             # FIXME
    #             apiDst.socialNetwork=action[2]
    #             apiDst.nick=action[3]
    #             res = apiDst.addPosts(
    #                 [
    #                     apiSrc.obtainPostData(j),
    #                 ]
    #             )
    #         else:
    #             apiDst = getApi(action[2], action[3])
    #             apiDst.setPostsType(action[1])
    #             if 'tumblr' in dst2[0]:
    #                 # Dirty trick. The publishing method checks data which
    #                 # comes from source. Not OK
    #                 apiDst.setPostsType('queue')
    #             elif 'gmail' in dst2[0]:
    #                 # Needs some working
    #                 apiDst.setPostsType('drafts')
    #             yield (f"I'll publish {title} - {link} ({action[1]})")
    #             if not published:
    #                 if hasattr(apiDst, "publishApiPost"):
    #                     res = apiDst.publishPost(title, link, "")
    #                 else:
    #                     res = apiDst.publish(j)
    #                 if not ('Fail' in res):
    #                     published = True
    #             else:
    #                 res = "Other action published before"
    #             # res = apiDst.publishPost(title, link, '')
    #         yield (f"Published, reply: {res}")

    #     postaction = apiSrc.getPostAction()
    #     if (not postaction) and (src[0] in ["cache","slack"]):
    #         # Different from batch process because we do not want the item to
    #         # reappear in scheduled sending. There can be problems if the link
    #         # is in some cache.
    #         postaction = "delete"
    #     logging.debug(f"Post Action {postaction}")
    #     try:
    #         cmdPost = getattr(apiSrc, postaction)
    #         yield (f"Post Action: {postaction}")
    #         res = cmdPost(j)
    #         yield (f"End {postaction}, reply: {res}")
    #     except:
    #         res = "No postaction or wrong one"
    #         yield (res)
    #     yield end()

    # @botcmd
    # def showR(self, mess, args):
    #     """A command to show the content of some update"""
    #     res = self.execute("showR", args)
    #     yield res
    #     yield end()

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
                args = f"{args} {self.lastEdit}"
            else: 
                res = "We need a new title"
        if " " in args:
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

    def prepareReply(self, updates, types):
        compResponse = []
        logging.debug(f"Pposts {updates}")
        logging.debug(f"Keys {updates.keys()}")
        tt = "pending"
        for socialNetwork in updates.keys():
            logging.debug(f"Update social network {socialNetwork}")
            logging.debug(f"Updates {updates[socialNetwork]}\nEnd")
            theUpdates = []
            maxLen = 0
            for update in updates[socialNetwork]:
                if update:
                    if len(update) > 0:
                        logging.info(f"Update {update} ")
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

            logging.debug(f"self.rules.available ... {self.available}")
            logging.info(f"socialNetwork ... {socialNetwork}")
            data = self.rules.available[socialNetwork[0].lower()]
            name = data["name"]
            logging.info(f"Name ... {name}")
            pos = int(socialNetwork[1])
            logging.info(f"Soc ... {data['data']}")
            logging.info(f"Soc ... {data['data'][pos]['src'][1]}")
            myType = data['data'][pos]['src'][2]
            logging.info(f"Type ... {myType}")
            social = socialNetwork
            if isinstance(data["data"][pos]['src'][1], str):
                socNick = f"{data['data'][pos]['src'][1]}"
            else:
                socNick = (
                    f"{data['data'][pos]['src'][1][1][0].capitalize()} "
                    f"{data['data'][pos]['src'][1][1][1]}"
                )
            logging.info(f"Social ... {social}")
            logging.info(f"Social Nick ... {socNick}")
            socialNetworktxt = (
                f"{social.capitalize()} " f"({name.capitalize()} - {socNick})"
            )
            logging.info(f"Social Network txt... {socialNetwork} len {len(socialNetwork)}")
            logging.info(f"Social Network txt... {socialNetworktxt}")
            if theUpdates:
                if (not isinstance(socialNetwork, str) 
                        and len(socialNetwork) > 2):
                    socialNetworktxt = (
                        socialNetwork[2][1][0].capitalize()
                        + " ("
                        + socialNetwork[2][1][1]
                        + " "
                        + socialNetwork[0]
                        + ")"
                    )
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
                                                 myType,
                                                 theUpdates[iniPos:maxPos]
                                                 )
                                                )
                            iniPos = maxPos
                            maxPos = maxPos + math.trunc(numEle)
                    else:
                        compResponse.append((tt, socialNetworktxt, 
                            myType, theUpdates))
                else:
                    compResponse.append((tt, socialNetworktxt, 
                        myType, theUpdates))
            else:
                compResponse.append((tt, socialNetworktxt,
                                     myType, theUpdates,))

        return compResponse

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types)
        logging.info(f"Reps: {reps}")
        for rep in reps:
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

    @botcmd#(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        res = self.execute("copy", args)
        #pp = pprint.PrettyPrinter(indent=4)
        #moduleBuffer.copyPost(self.api, logging, pp,
        #                      self.profiles, args[0], args[1])
        yield res
        yield "Copied"
        yield end()
