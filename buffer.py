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
import moduleBuffer


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

    def hasSetMethods(self, service):
        if service == "social":
            return []
        clsService = getModule(service)
        listMethods = clsService.__dir__()

        methods = []
        for method in listMethods:
            if (not method.startswith("__")) and (method.find("set") >= 0):
                action = "set"
                target = ""
                myModule = eval(f"clsService.{method}.__module__")

                if method.find("Api") >= 0:
                    target = method[len("setApi"):].lower()
                # elif (clsService.setPosts.__module__
                elif myModule == f"module{service.capitalize()}":
                    target = method[len("set"):].lower()
                if target and (
                    target.lower() in ["posts", "drafts", "favs",
                                       "messages", "queue"]
                              ):
                    toAppend = (action, target)
                    if not (toAppend in methods):
                        methods.append(toAppend)
        return methods

    def hasPublishMethod(self, service):
        clsService = getModule(service)
        listMethods = clsService.__dir__()

        methods = []
        target = None
        for method in listMethods:
            if method.find("publish") >= 0:
                action = "publish"
                target = ""
                moduleService = clsService.publishPost.__module__
                if method.find("Api") >= 0:
                    target = method[len("publishApi"):].lower()
                    logging.info(f"Target api {target}")
                elif moduleService == f"module{service.capitalize()}":
                    target = method[len("publish"):].lower()
                    logging.info(f"Target mod {target}")
                # else:
                #    target = 'post'
                #    logging.info(f"Target else {target}")
                if target:
                    toAppend = (action, target)
                    if not (toAppend in methods):
                        methods.append(toAppend)
        return methods

    def getServices(self):
        modulesFiles = os.listdir("/home/ftricas/usr/src/socialModules")
        modules = {"special": ["cache", "direct"], "regular": []}
        # Initialized with some special services
        name = "module"
        for module in modulesFiles:
            if module.startswith(name):
                moduleName = module[len(name): -3].lower()
                if not (moduleName in modules["special"]):
                    # We drop the 'module' and the '.py' parts
                    modules["regular"].append(moduleName)

        return modules

    def checkRules(self):
        msgLog = "Checking rules"
        logMsg(msgLog, 1, 2)
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + "/.rssBlogs")

        services = self.getServices()
        services['regular'].append('cache')
        indent = 3*"  "+4*" "

        srcs = []
        srcsA = []
        more = []
        dsts = []
        ruls = {}
        mor = {}
        impRuls = []
        for section in config.sections():
            url = config.get(section, "url")
            msgLog = f"Section: {section} Url: {url}"
            logMsg(msgLog, 1, 1)
            # Sources
            moreS = dict(config.items(section))
            moreSS = None
            if "rss" in config.options(section):
                rss = config.get(section, "rss")
                msgLog = (f"Service: rss -> {rss}")
                logMsg(msgLog, 2, 0)
                toAppend = ("rss", "set", 
                            urllib.parse.urljoin(url, rss), "posts")
                srcs.append(toAppend)
                more.append(moreS)
            else:
                msgLog = (f"url {url}")
                logMsg(msgLog, 2, 0)
                for service in services["regular"]:
                    if (
                        ("service" in config[section])
                        and (service == config[section]["service"])
                    ) or (url.find(service) >= 0):
                        methods = self.hasSetMethods(service)
                        logging.debug(f"Service: {service} has set {methods}")
                        for method in methods:
                            msgLog = (f"Method: {method}")
                            logMsg(msgLog, 2, 0)
                            msgLog = (f"moreS: {moreS}")
                            logMsg(msgLog, 2, 0)
                            # If it has a method for setting, we can set
                            # directly using this
                            if service in config[section]:
                                nick = config[section][service]
                            else:
                                nick = url
                                if nick.find("slack") < 0:
                                    nick = nick.split("/")[-1]
                            if (service == 'imdb') or (service == 'imgur'):
                                nick = url

                            if 'posts' in moreS: 
                                if moreS['posts'] == method[1]: 
                                   toAppend = (service, "set", nick, method[1])
                            else:
                               toAppend = (service, "set", nick, method[1])
                            msgLog = (f"toAppend: {toAppend}")
                            logMsg(msgLog, 2, 0)
                            if not (toAppend in srcs):
                                if (('posts' in moreS) 
                                    and (moreS['posts'] == method[1])):
                                    srcs.append(toAppend)
                                    more.append(moreS)
                                else:
                                    # Available, but with no rules
                                    srcsA.append(toAppend)
            fromSrv = toAppend
            msgLog = (f"fromSrv toAppend: {toAppend}")
            logMsg(msgLog, 2, 0)
            msgLog = (f"fromSrv moreS: {moreS}")
            logMsg(msgLog, 2, 0)

            if "time" in config.options(section):
                timeW = config.get(section, "time")
            else:
                timeW = 0
            if "buffermax" in config.options(section):
                bufferMax = config.get(section, "buffermax")
            else:
                bufferMax = 0
            if "max" in config.options(section):
                bufferMax = config.get(section, "max")

            # Destinations
            hasSpecial = False
            if "posts" in config[section]:
                postsType = config[section]["posts"]
            else:
                postsType = "posts"
            if fromSrv:
                fromSrv = ( fromSrv[0], fromSrv[1], fromSrv[2], postsType,)
                for service in services["special"]:
                    toAppend = ""
                    msgLog = (f"Service: {service}")
                    logMsg(msgLog, 2, 0)
                    if service in config.options(section):
                        valueE = config.get(section, service).split("\n")
                        for val in valueE:
                            nick = config.get(section, val)
                            msgLog = (f"Service special: {service} "
                                      f"({val}, {nick})")
                            logMsg(msgLog, 2, 0)
                            if service == "direct":
                                url = "posts"
                            toAppend = (service, url, val, nick, timeW, bufferMax)
                            msgLog = (f"Service special toAppend: {toAppend} ")
                            logMsg(msgLog, 2, 0)
                            msgLog = (f"Service special from: {fromSrv} ")
                            logMsg(msgLog, 2, 0)
                            if toAppend not in dsts:
                                dsts.append(toAppend)
                            if toAppend:
                                if fromSrv not in mor:
                                    mor[fromSrv] = moreS
                                if fromSrv in ruls:
                                    if not toAppend in ruls[fromSrv]:
                                        ruls[fromSrv].append(toAppend)
                                        msgLog = (f"1 added: {toAppend} "
                                                  f"in {fromSrv} ")
                                        logMsg(msgLog, 2, 0)
                                else:
                                    ruls[fromSrv] = []
                                    ruls[fromSrv].append(toAppend)
                                    msgLog = (f"1.1 added: {toAppend} "
                                              f"in {fromSrv} ")
                                    logMsg(msgLog, 2, 0)

                                hasSpecial = True

                for service in services["regular"]:
                    if (service == 'cache'):
                        continue
                    toAppend = ""
                    if service in config.options(section):
                        methods = self.hasPublishMethod(service)
                        msgLog = (f"Service: {service} has {methods}")
                        logMsg(msgLog, 2, 0)
                        for method in methods:
                            msgLog = (f"Method: {method}")
                            logMsg(msgLog, 2, 0)
                            # If it has a method for publishing, we can
                            # publish directly using this

                            if not method[1]:
                                mmethod = 'post'
                            else:
                                mmethod = method[1]
                            toAppend = (
                                    "direct",
                                    mmethod,
                                    service,
                                    config.get(section, service),
                                    timeW,
                                    bufferMax,
                                    )

                            if not (toAppend in dsts):
                                dsts.append(toAppend)
                            if toAppend:
                                if hasSpecial: 
                                    msgLog = (f"hasSpecial: {fromSrv}---")
                                    logMsg(msgLog, 2, 0)
                                    msgLog = (f"hasSpecial: {toAppend}---")
                                    logMsg(msgLog, 2, 0)
                                    nickSn = f"{toAppend[2]}@{toAppend[3]}"
                                    fromSrvSp = (
                                            "cache",
                                            "set",
                                            nickSn,
                                            "posts",
                                            )
                                    impRuls.append((fromSrvSp, toAppend))
                                    if fromSrvSp not in mor:
                                        mor[fromSrvSp] = moreS
                                    if fromSrvSp in ruls:
                                        if not toAppend in ruls[fromSrvSp]:
                                            ruls[fromSrvSp].append(toAppend)
                                            msgLog = (f"2 added: {toAppend} "
                                                      f"in {fromSrvSp} ")
                                            logMsg(msgLog, 1, 0)
                                    else:
                                        ruls[fromSrvSp] = []
                                        ruls[fromSrvSp].append(toAppend)
                                        if url:
                                            msgLog = (f"2.1 added: {toAppend} "
                                                      f"in {fromSrvSp} "
                                                      f"with {url}")
                                        else:
                                            msgLog = (f"2.1 added: {toAppend} "
                                                      f"in {fromSrvSp} "
                                                      f"with no url")
                                        logMsg(msgLog, 1, 0)
                                else:
                                    msgLog = (f"From {fromSrv}")
                                    logMsg(msgLog, 2, 0)
                                    msgLog = (f"direct: {dsts}---")
                                    logMsg(msgLog, 2, 0)

                                    if fromSrv not in mor:
                                        msgLog = (f"Adding {moreS}")
                                        logMsg(msgLog, 2, 0)
                                        mor[fromSrv] = moreS
                                    if fromSrv in ruls:
                                        if not toAppend in ruls[fromSrv]:
                                            ruls[fromSrv].append(toAppend)
                                            msgLog = (f"3 added: {toAppend} in "
                                                      f"{fromSrv} ")
                                            logMsg(msgLog, 2, 0)
                                    else:
                                        ruls[fromSrv] = []
                                        ruls[fromSrv].append(toAppend)
                                        msgLog = (f"3.1 added: {toAppend} in "
                                                  f"{fromSrv} ")
                                        logMsg(msgLog, 2, 0)

        # Now we can add the sources not added.

        for src in srcsA:
            if not src in srcs: 
                msgLog = (f"Adding implicit {src}")
                logMsg(msgLog, 2, 0)
                srcs.append(src)
                more.append({})

        # Now we can see which destinations can be also sources
        for dst in dsts:
            if dst[0] == "direct":
                service = dst[2]
                methods = self.hasSetMethods(service)
                for method in methods:
                    msgLog = (f"cache dst {dst}")
                    logMsg(msgLog, 2, 0)
                    toAppend = (service, "set", dst[3], method[1], dst[4])
                    msgLog = (f"toAppend src {toAppend}")
                    logMsg(msgLog, 2, 0)
                    if not (toAppend[:4] in srcs):
                        srcs.append(toAppend[:4])
                        more.append({})
            elif dst[0] == "cache":
                if len(dst)>4 :
                    toAppend = (dst[0], "set", (dst[1], (dst[2], dst[3])), 
                                "posts", dst[4], 1)
                else:
                    toAppend = (dst[0], "set", (dst[1], (dst[2], dst[3])), 
                                "posts", 0, 1)
                if not (toAppend[:4] in srcs):
                        srcs.append(toAppend[:4])
                        more.append({})

        available = {}
        myKeys = {}
        myIniKeys = []
        for i, src in enumerate(srcs):
            if not src:
                continue
            iniK, nameK = self.getIniKey(src[0], myKeys, myIniKeys)
            if not (iniK in available):
                available[iniK] = {"name": src[0], "data": [], "social": []}
                available[iniK]["data"] = [{'src': src[1:], 'more': more[i]}]
            else:
                available[iniK]["data"].append({'src': src[1:], 
                                                'more': more[i]})
            # srcC = (src[0], "set", src[1], src[2])
            # if srcC not in ruls:
            #     ruls[srcC] = 

        myList = []
        for elem in available:
            component = (
                f"{elem}) "
                f"{available[elem]['name']}: "
                f"{len(available[elem]['data'])}"
            )
            myList.append(component)

        if myList:
            availableList = myList
        else:
            availableList = []

        self.available = available
        self.availableList = availableList

        msgLog = (f"Avail: {self.available}")
        logMsg(msgLog, 2, 0)
        msgLog = (f"Ruls: {ruls}")
        logMsg(msgLog, 2, 0)
        self.rules = ruls
        self.more = mor

        return (srcs, dsts, ruls, impRuls)


    def checkRules2(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + "/.rssBlogs")

        services = self.getServices()

        srcs = []
        dsts = []
        ruls = {}
        impRuls = []
        for section in config.sections():
            url = config.get(section, "url")
            logging.info(f"Url: {url}")
            # Sources
            if "rss" in config.options(section):
                rss = config.get(section, "rss")
                logging.info(f"Service: rss -> {rss}")
                toAppend = ("rss", "set", 
                            urllib.parse.urljoin(url, rss), "posts")
                srcs.append(toAppend)
            else:
                logging.debug(f"url {url}")
                for service in services["regular"]:
                    if (
                        ("service" in config[section])
                        and (service == config[section]["service"])
                    ) or (url.find(service) >= 0):
                        methods = self.hasSetMethods(service)
                        print(f"Has set {methods}")
                        for method in methods:
                            # If it has a method for setting, we can set
                            # directly using this
                            if service in config[section]:
                                nick = config[section][service]
                            else:
                                nick = url
                                if nick.find("slack") < 0:
                                    nick = nick.split("/")[-1]
                            if service == 'imdb':
                                nick = url

                            toAppend = (service, "set", nick, method[1])
                            if not (toAppend in srcs):
                                srcs.append(toAppend)
            fromSrv = toAppend

            # Destinations
            hasSpecial = False
            for service in services["special"]:
                toAppend = ""
                print(f"Service: {service}")
                if service in config.options(section):
                    valueE = config.get(section, service).split("\n")
                    for val in valueE:
                        nick = config.get(section, val)
                        logging.info(f"Service special: {service} "
                                     f"({val}, {nick})")
                        if service == "direct":
                            url = "posts"
                            if "posts" in config[section]:
                                fromSrv = (
                                    fromSrv[0],
                                    fromSrv[1],
                                    fromSrv[2],
                                    config[section]["posts"],
                                )
                            # else:
                            #    url = ""
                        toAppend = (service, url, val, nick)
                        logging.info(f"Service special toAppend: {toAppend} ")
                        logging.info(f"Service special from: {fromSrv} ")
                        if toAppend not in dsts:
                            dsts.append(toAppend)
                        if toAppend:
                            if fromSrv in ruls:
                                ruls[fromSrv].append(toAppend)
                            else:
                                ruls[fromSrv] = []
                                ruls[fromSrv].append(toAppend)

                            hasSpecial = True

            for service in services["regular"]:
                toAppend = ""
                if service in config.options(section):
                    methods = self.hasPublishMethod(service)
                    logging.info(f"Service: {service} has {methods}")
                    logging.info(f"Methods: {methods}")
                    for method in methods:
                        # If it has a method for publishing, we can publish
                        # directly using this

                        toAppend = (
                            "direct",
                            method[1],
                            service,
                            config.get(section, service),
                        )
                        if not (toAppend in dsts):
                            dsts.append(toAppend)
                        if toAppend:
                            if hasSpecial:
                                fromSrvSp = (
                                    "cache",
                                    "set",
                                    (fromSrv[2], (toAppend[2], toAppend[3])),
                                    "posts",
                                )
                                impRuls.append((fromSrvSp, toAppend))

                                if fromSrvSp in ruls:
                                    ruls[fromSrvSp].append(toAppend)
                                else:
                                    ruls[fromSrvSp] = []
                                    ruls[fromSrvSp].append(toAppend)

                            else:
                                if fromSrv in ruls:
                                    ruls[fromSrv].append(toAppend)
                                else:
                                    ruls[fromSrv] = []
                                    ruls[fromSrv].append(toAppend)

        # Now we can see which destinations can be also sources
        for dst in dsts:
            if dst[0] == "direct":
                service = dst[2]
                methods = self.hasSetMethods(service)
                for method in methods:
                    logging.debug(f"cache dst {dst}")
                    toAppend = (service, "set", dst[3], method[1])
                    if not (toAppend in srcs):
                        srcs.append(toAppend)
            elif dst[0] == "cache":
                toAppend = (dst[0], "set", (dst[1], (dst[2], dst[3])), "posts")
                if not (toAppend in srcs):
                    srcs.append(toAppend)

        available = {}
        myKeys = {}
        myIniKeys = []
        for src in srcs:
            iniK, nameK = self.getIniKey(src[0], myKeys, myIniKeys)
            if not (iniK in available):
                available[iniK] = {"name": src[0], "data": [], "social": []}
                available[iniK]["data"] = [src[1:]]
            else:
                available[iniK]["data"].append(src[1:])

        myList = []
        for elem in available:
            component = (
                f"{elem}) "
                f"{available[elem]['name']}: "
                f"{len(available[elem]['data'])}"
            )
            myList.append(component)

        if myList:
            availableList = myList
        else:
            availableList = []

        self.available = available
        self.availableList = availableList

        self.rules = ruls

        return (srcs, dsts, ruls, impRuls)

    def printList(self, myList, title):
        print(f"{title}:")
        for i, element in enumerate(myList):
            print(f"  {i}) {element}")

    def getIniKey(self, key, myKeys, myIniKeys):
        if key not in myKeys:
            if key[0] not in myIniKeys:
                iniK = key[0]
            else:
                i = 1
                while (i < len(key)) and (key[i] in myIniKeys):
                    i = i + 1
                if i < len(key):
                    iniK = key[i]
                else:
                    iniK = "j"
                    while iniK in myIniKeys:
                        iniK = chr(ord(iniK) + 1)
            myKeys[key] = iniK
        else:
            iniK = myKeys[key]
        myIniKeys.append(iniK)
        pos = key.find(iniK)
        if pos >= 0:
            nKey = key[:pos] + iniK.upper() + key[pos + 1:]
        else:
            nKey = iniK + key
        nKey = key + "-{}".format(iniK)

        return iniK, nKey

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
            for line in text:
                lineS = line.split("|")[1]
                line1, line2 = lineS.split("->")
                logging.debug("line 1 {}".format(line1))
                textR.append(line1)
                textR.append("      ⟶{}".format(line2))
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
            if element.find("Next") > 0:
                # yield element
                if element.find("_") > 0:
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
        for key in self.available:
            for i, elem in enumerate(self.available[key]["data"]):
                if (args and (key == args)) or not args:
                    myList[theKey].append((elem[1], key, f"{key}-{i}"))
        logging.info("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            yield (rep)
        return end

    def appendMyList(self, arg, myList):
        logging.debug("Args... {}".format(str(arg)))
        for key in self.available:
            if arg[0].capitalize() == key.capitalize():
                if arg[1:].isdigit():
                    pos = int(arg[1:])
                if pos < len(self.available[key]["data"]):
                    myList.append(arg.capitalize())
        logging.debug("mylist... %s" % str(myList))

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
        if not self.available:
            self.checkRules()

        myList = []

        for arg in args:
            self.appendMyList(arg, myList)

        if myList:
            self.config.append(myList)

        yield (self.config)
        yield (end())

    @botcmd
    def list_list(self, msg, args):
        if not self.available:
            self.checkRules()

        response = [self.availableList]
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
        logging.info("Key: %s", str(key))
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
        if not self.available:
            self.checkRules()

        available = self.available

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
            self.appendMyList(args[0].upper(), myList)
            pos = 0

        logging.debug("myList %s" % str(myList))
        self.lastList = myList
        clients = self.clients

        if pos >= 0:
            for element in myList:
                logging.debug("Clients %s" % str(clients))
                logging.debug("Element %s" % str(element))
                logging.debug(f"Available {available}")
                profile = available[element[0].lower()]
                logging.debug(f"Profile {profile}")
                name = profile["name"]
                myElem = profile["data"][int(element[1:])]
                logging.debug(f"myElem {myElem}")
                try:
                    clients[element].setPosts()
                except:
                    api = getApi(name.capitalize(), myElem['src'][1])
                    clients[element] = api
                    clients[element].setPostsType(myElem['src'][2])
                    clients[element].setPosts()

                self.log.debug("posts", clients[element].getPosts())

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
            for resp in response:
                logging.info(f"Resp: {resp}")
                yield (resp)
        else:
            yield (self.addMore())

        self.clients = clients
        yield end()

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
            logging.debug(f"Executing in profile: {profile} with args {args}")
            theProfile = profile[:2]
            if (
                (theProfile.upper() == args[: len(theProfile)].upper())
                or (args[0] == "*")
                or (("*" in args) and (args[:1] == profile[0][:1]))
            ):
                # We need to do something for '*' commands
                logging.info(f"I'll {command} in {profile}")
                update = self.clients[profile].selectAndExecute(command, args)
                if update:
                    updates = f"{updates}* {update} ({profile[0]})\n"
                    update = None

        if updates:
            res = f"{resTxt}\n{updates}"

        return res

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

        clients = self.clients
        logging.debug(f"Clients: {clients}")
        available = self.available
        rules = self.rules

        logging.info(f"Publishing {args}")
        yield (f"Publishing {args}")
        res = ""

        # yield(f"Avail: {available}")
        logging.debug(f"Avail: {available}")
        dst = (
            available[args[0].lower()]["name"],
            "set",
            available[args[0].lower()]["data"][int(args[1])]['src'][1],
            available[args[0].lower()]["data"][int(args[1])]['src'][2],
        )
        src = (dst[0], dst[2])
        # yield(f"Src: {src}")
        # yield(f"Dst: {dst}")
        logging.info(f"Src: {src}")
        logging.info(f"Dst: {dst}")
        logging.debug(f"Rules: {rules}")
        if isinstance(dst[2], tuple):
            nickSn = f"{dst[2][1][0]}@{dst[2][1][1]}"
            dst2 = dst[:2]+ (nickSn,)+('posts', )
        else:
            dst2 = dst
        logging.debug(f"Dst2: {dst2}")
        actions = rules[dst2]
        apiSrc = getApi(src[0], src[1])
        # yield apiSrc
        apiSrc.setPostsType(dst[3])
        apiSrc.setPosts()
        j = int(args[2:])
        post = apiSrc.getPost(j)
        title = apiSrc.getPostTitle(post)
        link = apiSrc.getPostLink(post)
        logging.debug(f"Title: {title}")
        logging.debug(f"Link: {link}")
        logging.debug(f"Actions: {actions}")

        for i, action in enumerate(actions):
            logging.info(f"Action {i}: {action}")
            if action[0] == "cache":
                apiDst = getApi("cache", (src[1], (action[2], action[3])))
                res = apiDst.addPosts(
                    [
                        apiSrc.obtainPostData(j),
                    ]
                )
            else:
                apiDst = getApi(action[2], action[3])
                apiDst.setPostsType(action[1])
                if 'tumblr' in dst2[0]:
                    # Dirty trick. The publishing method checks data which
                    # comes from source. Not OK
                    apiDst.setPostsType('queue')
                yield (f"I'll publish {title} - {link} ({action[1]})")
                if hasattr(apiDst, "publishApiPost"):
                    res = apiDst.publishPost(title, link, "")
                else:
                    res = apiDst.publish(j)
                # res = apiDst.publishPost(title, link, '')
            yield (f"Published, reply: {res}")

        postaction = apiSrc.getPostAction()
        if (not postaction) and (src[0] in ["cache","slack"]):
            # Different from batch process because we do not want the item to
            # reappear in scheduled sending. There can be problems if the link
            # is in some cache.
            postaction = "delete"
        logging.debug(f"Post Action {postaction}")
        try:
            cmdPost = getattr(apiSrc, postaction)
            yield (f"Post Action: {postaction}")
            res = cmdPost(j)
            yield (f"End {postaction}, reply: {res}")
        except:
            yield ("No postaction or wrong one")
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
                        # time.strftime("%Y-%m-%d-%H:%m",
            # if updates[socialNetwork]:
            #     if theUpdates[0][0] != "Empty":
            #         socialTime = theUpdates[0][2]
            #     else:
            #         socialTime = ""
            # else:
            #     socialTime = ""

            logging.debug(f"self.available ... {self.available}")
            logging.info(f"socialNetwork ... {socialNetwork}")
            data = self.available[socialNetwork[0].lower()]
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
            logging.info(f"Nick ... {social}")
            logging.info(f"Nick ... {socNick}")
            socialNetworktxt = (
                f"{social.capitalize()} " f"({name.capitalize()} - {socNick})"
            )
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

    @botcmd(split_args_with=None)
    def copy(self, mess, args):
        """A command to copy some update"""
        pp = pprint.PrettyPrinter(indent=4)
        moduleBuffer.copyPost(self.api, logging, pp,
                              self.profiles, args[0], args[1])
        yield "Copied"
        yield end()
