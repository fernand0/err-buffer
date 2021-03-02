import configparser
import logging
import os
import pickle
import pprint
import time
import sys

from errbot import BotPlugin, botcmd, webhook, backends
from errbot.templating import tenv

# Needs to set $PYTHONPATH to the dir where this modules are located

from configMod import *
import moduleBuffer
import moduleCache


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
                    target = method[len("setApi") :].lower()
                # elif (clsService.setPosts.__module__
                elif myModule == f"module{service.capitalize()}":
                    target = method[len("set") :].lower()
                if target and (
                    target.lower() in ["posts", "drafts", "favs", "messages", "queue"]
                ):
                    toAppend = (action, target)
                    if not (toAppend in methods):
                        methods.append(toAppend)
        return methods

    def hasPublishMethod(self, service):
        clsService = getModule(service)
        listMethods = clsService.__dir__()

        methods = []
        for method in listMethods:
            if method.find("publish") >= 0:
                action = "publish"
                target = ""
                moduleService = clsService.publishPost.__module__
                if method.find("Api") >= 0:
                    target = method[len("publishApi") :].lower()
                    logging.info(f"Target api {target}")
                elif moduleService == f"module{service.capitalize()}":
                    target = method[len("publish") :].lower()
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
                moduleName = module[len(name) : -3].lower()
                if not (moduleName in modules["special"]):
                    # We drop the 'module' and the '.py' parts
                    modules["regular"].append(moduleName)

        return modules

    def checkRules(self):
        config = configparser.ConfigParser()
        config.read(CONFIGDIR + "/.rssBlogs")

        services = self.getServices()

        srcs = []
        dsts = []
        ruls = {}
        impRuls = []
        acts = []
        for section in config.sections():
            url = config.get(section, "url")
            logging.info(f"Url: {url}")
            # Sources
            if "rss" in config.options(section):
                rss = config.get(section, "rss")
                logging.info(f"Service: rss -> {rss}")
                toAppend = ("rss", "set", urllib.parse.urljoin(url, rss), "posts")
                srcs.append(toAppend)
            else:
                print(f"url {url}")
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
                        logging.info(f"Service special: {service} " f"({val}, {nick})")
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

                            # if 'imp' in ruls:
                            #     ruls['imp'].append((('direct', 'post',
                            #             toAppend[2], toAppend[3])))
                            # else:
                            #     ruls['imp'] = []
                            #     ruls['imp'].append((('direct', 'post',
                            #             toAppend[2], toAppend[3])))
                            # ruls.append((toAppend,
                            #        (('direct', 'post',
                            #            toAppend[2], toAppend[3]))))
                            # (toAppend[2][1][0], 'set', toAppend[2][1][1], 'posts'), ('direct', 'post',

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
            nKey = key[:pos] + iniK.upper() + key[pos + 1 :]
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
        text = []
        textW = []
        textF = []
        for element in myList:
            logging.info(f"Element {element}")
            if (element.find("last") > 0) and (element.find("Next") > 0):
                continue
            if element.find("Next") > 0:  # or (element.find('last')>0):
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
                            t1, t2 = pickle.load(f)
                        if time.time() < t1 + t2:
                            msg = "[W]: "
                        else:
                            msg = "[F]: "
                        theTime = time.strftime("%H:%M:%S", time.localtime(t1 + t2))
                    else:
                        if dest and nick:
                            link, t1 = checkLastLink(url, (dest, nick))
                        else:
                            link, t1 = checkLastLink(url)
                        theTime = time.strftime("%H:%M:%S", time.localtime(t1))
                        msg = "[L]: "
                        t2 = 0
                else:
                    msg = "No Time"
                    theTime = ""
                if t1:
                    if nick and nick.find("_") > 0:
                        nick = nick.split("_")[1]
                    if msg.find("[W]") >= 0:
                        textW.append(
                            "{5}|{2} {0} -> {1} ({3})".format(
                                orig, dest.capitalize(), theTime, nick, msg, t1 + t2
                            )
                        )
                    else:
                        textF.append(
                            "{5}|{2} {0} -> {1} ({3})".format(
                                orig, dest.capitalize(), theTime, nick, msg, t1 + t2
                            )
                        )
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
            self.checkConfigFiles()
        logging.info("Available: %s" % str(self.available))
        myList = {}
        theKey = ("All", "All", ("All", "All", "All"))
        myList[theKey] = []
        for key in self.available:
            for i, elem in enumerate(self.available[key]["data"]):
                if (args and (key == args)) or not args:
                    myList[theKey].append((elem[0], key, "{}-{}".format(key, i)))
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
                    myList.append(arg)
        logging.debug("mylist... %s" % str(myList))

    @botcmd(split_args_with=None, template="buffer")
    def list_read(self, mess, args):
        # Maybe define a flow?
        myList = []
        pos = 0
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

                name, profile, socialNetworks = self.getSocialProfile(element)
                logging.debug("Result: {} {} {}".format(element, profile, name))
                logging.debug("clients : {}".format(str(self.clients)))
                profile = profile.split("-")[0]
                if (element, profile, name) in self.clients:
                    thePosts = self.clients[(element, profile, name)].getPosts()
                    if thePosts:
                        link = self.clients[(element, profile, name)].getPosts()[-1][1]
                        # yield("name %s  profile %s elem %s"%(str(name),
                        #    str(profile), str(element)))
                        # yield("link %s"%link)
                        if profile.upper() == "Forum".upper():
                            # Not sure it makes sense for other types of
                            # content
                            # logging.debug("Param %s"%str(param))
                            # if isinstance(param, tuple):
                            # param = self.getUrl() #param[0]
                            updateLastLink(name[1], link)
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
            self.config = self.config[:pos] + self.config[pos + 1 :]
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
    def list_list2(self, msg, args):
        if not self.available2:
            self.checkRules()

        response = [self.availableList2]
        yield response
        yield end()

    @botcmd
    def list_list(self, msg, args):
        if not self.available:
            self.checkConfigFiles()

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
    def listOld(self, mess, args):
        """A command to show available posts in a list of available sites"""
        logging.debug("Posts posts %s" % (self.posts))
        logging.debug("args %s" % str(args))

        myList = []
        response = []
        self.posts = {}
        if not self.available:
            self.checkConfigFiles()

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

        if pos >= 0:
            for element in myList:
                logging.debug("Clients %s" % str(self.clients))
                logging.debug("Element %s" % str(element))
                name, profile, socialNetworks = self.getSocialProfile(element)
                logging.debug(f"Name: {name}")
                logging.debug(f"Profile: {profile}")
                logging.debug(f"SocialNetworks: {socialNetworks}")
                if isinstance(name, tuple):
                    typePosts = name[1]
                else:
                    # Some problem with moduleSlack
                    typePosts = "posts"
                logging.debug("ssN: {}".format(socialNetworks[0][1]))
                sN = socialNetworks[0][0]
                logging.debug(f"Social Network: {sN}")
                sNNick = socialNetworks[0][1]
                logging.debug(f"Social Network Nick: {sNNick}")
                if sN != name[0]:
                    logging.warning(f"sN {sN} and {name[0]} differ")
                if sNNick != name[1]:
                    logging.warning(f"sNNick {sNNick} and {name[1]} differ")

                logging.debug(f"Element profile Name")
                logging.debug(f"({element}, {profile}, {name})")
                if profile.startswith("cache"):
                    name = (name[0], (sN, sNNick))
                elif profile.startswith("direct"):
                    # Only for pocket
                    if name[0].find("pocket") >= 0:
                        name = (name[0], ("pocket", name[0].split("/")[-1][1:]))
                    elif name[0].find("tumblr") >= 0:
                        name = (
                            name[0],
                            ("tumblr", name[0].split(".")[0].split("/")[-1]),
                        )
                logging.debug(f"({element}, {profile}, {name})")

                try:
                    logging.debug("sN--> {}".format(str(sN)))
                    self.clients[(element, profile, name)].setPosts()
                    logging.debug("sN---> {}".format(str(sN)))
                    self.clients[(element, profile, name)].setSocialNetworks(
                        {sN: sNNick}
                    )
                    logging.debug("sN----> {}".format(str(sN)))
                    logging.debug(
                        "sNetworks--> {}".format(
                            str(
                                self.clients[
                                    (element, profile, name)
                                ].getSocialNetworks()
                            )
                        )
                    )
                except:
                    if profile.find("-") >= 0:
                        profile = profile.split("-")[0]

                    logging.debug(
                        f"Element {element} " f"Profile {profile} Name {name}"
                    )
                    if sN == "rss":
                        name = (name[0], socialNetworks[0][0], name[2])
                    # if ((socialNetworks[0][0].find('slack')>=0)
                    #         or (socialNetworks[0][0].find('img')>=0)):
                    #     name = (socialNetworks[0][0], name[0], name[1])
                    logging.debug(f"new Name {name}")

                    logging.debug(
                        f"Element {element} " f"Profile {profile} Name {name}"
                    )
                    api = getApi(profile.capitalize(), name)
                    self.clients[(element, profile, name)] = api
                    self.clients[(element, profile, name)].setPostsType(typePosts)

                    self.clients[(element, profile, name)].setPosts()
                    self.clients[(element, profile, name)].setSocialNetworks(
                        {sN: sNNick}
                    )

                    logging.debug(
                        "sNetworks--> {}".format(
                            str(
                                self.clients[
                                    (element, profile, name)
                                ].getSocialNetworks()
                            )
                        )
                    )
                self.log.debug(
                    "posts", self.clients[(element, profile, name)].getPosts()
                )

                postsTmp = []
                posts = []

                if hasattr(self.clients[(element, profile, name)], "getPostsType"):
                    logging.debug(
                        "Types %s"
                        % (self.clients[(element, profile, name)].getPostsType())
                    )

                    if (
                        self.clients[(element, profile, name)].getPostsType()
                        == "drafts"
                    ):
                        postsTmp = self.clients[(element, profile, name)].getDrafts()
                    else:
                        postsTmp = self.clients[(element, profile, name)].getPosts()
                else:
                    postsTmp = self.clients[(element, profile, name)].getPosts
                if postsTmp:
                    for (i, post) in enumerate(postsTmp):
                        if hasattr(
                            self.clients[(element, profile, name)], "getPostLine"
                        ):
                            title = self.clients[(element, profile, name)].getPostLine(
                                post
                            )
                            link = ""
                        else:
                            title = self.clients[(element, profile, name)].getPostTitle(
                                post
                            )
                            link = self.clients[(element, profile, name)].getPostLink(
                                post
                            )
                        posts.append((title, link, "{:2}".format(i)))
                        # logging.debug("I: %s %s %d"%(title,link,i))

                self.posts[(element, profile, name)] = posts
                logging.info("Posts posts %s" % (self.posts))
                response = self.sendReply(mess, args, self.posts, ["sent", "pending"])
                logging.debug("Response %s End" % str(response))

        if response:
            for resp in response:
                logging.info(f"Resp: {resp}")
                yield (resp)
        else:
            yield (self.addMore())
        yield end()

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
                try:
                    clients[element].setPosts()
                except:
                    api = getApi(name.capitalize(), myElem[1])
                    clients[element] = api
                    clients[element].setPostsType(myElem[2])
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
                response = self.sendReply(mess, args, self.posts, ["sent", "pending"])
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
        available = self.available
        rules = self.rules

        logging.info(f"Publishing {args}")
        yield (f"Publishing {args}")
        res = ""
        logging.info(f"Clients: {self.clients}")
        for client in clients:
            logging.info(f"client client {client}")
            if client[0].upper() == args[:2].upper():
                myClient = client

        # yield(f"Avail: {available}")
        logging.debug(f"Avail: {available}")
        dst = (
            available[args[0].lower()]["name"],
            "set",
            available[args[0].lower()]["data"][int(args[1])][1],
            available[args[0].lower()]["data"][int(args[1])][2],
        )
        src = (dst[0], dst[2])
        # yield(f"Src: {src}")
        # yield(f"Dst: {dst}")
        logging.info(f"Dst: {dst}")
        logging.info(f"Rules: {rules}")
        actions = rules[dst]
        apiSrc = getApi(src[0], src[1])
        # yield apiSrc
        apiSrc.setPostsType(dst[3])
        apiSrc.setPosts()
        j = int(args[2:])
        post = apiSrc.getPost(j)
        title = apiSrc.getPostTitle(post)
        link = apiSrc.getPostLink(post)
        # yield(title)
        # yield(link)
        yield (actions)

        for action in actions:
            # yield(f"Action: {action}")
            if action[0] == "cache":
                apiDst = getApi("cache", (action[1], (action[2], action[3])))
                # yield(apiDst)
                res = apiDst.addPosts(
                    [
                        apiSrc.obtainPostData(j),
                    ]
                )
            else:
                apiDst = getApi(action[2], action[3])
                apiDst.setPostsType(dst[3])
                # yield(apiDst)
                # apiDst.setPosts()
                yield (f"I'll publish {title} - {link}")
                yield (f"I'll publish {post}")
                if hasattr(apiDst, "publishApiPost"):
                    res = apiDst.publishPost(title, link, "")
                else:
                    res = apiDst.publish(j)
                continue
                # res = apiDst.publishPost(title, link, '')
            yield (f"Published, reply: {res}")

        postaction = apiSrc.getPostAction()
        if (not postaction) and (src[0] in ["cache"]):
            postaction = "delete"
        yield (f"Post Action {postaction}")
        try:
            cmdPost = getattr(apiSrc, postaction)
            yield (f"Post Action {postaction} command {cmdPost}")
            res = cmdPost(j)
            yield (f"End {postaction}, reply: {res}")
        except:
            yield (f"No postaction or wrong one")
        yield end()

    # # Passing split_args_with=None will cause arguments to be split on any kind
    # # of whitespace, just like Python's split() does
    # @botcmd
    # def publishOld(self, mess, args):
    #     """A command to publish some update"""

    #     # Dirty trick?
    #     logging.info(f"Publishing {args}")
    #     res = ""
    #     logging.info(f"Clients: {self.clients}")
    #     for client in self.clients:
    #         logging.info(f"client client {client}")
    #         if client[0].upper() == args[:2].upper():
    #             myClient = client
    #     for avail in self.available['c']['data']:
    #         logging.info(f"avail avail {avail} {self} {args}")
    #         logging.info(f"avail avail {avail[0][1]} {self} {args}")
    #         logging.info(f"avail myClient {myClient}")
    #         # if (myClient[2][1][0] == avail[0][1][0]):
    #         if ((myClient[2][1][0] == avail[0][1][0])
    #                 and (myClient[2][0] == avail[0][0][0])):
    #             logging.info(f"is avail c {avail}")
    #             orig = self.clients[myClient]
    #             dest = getApi(avail[0][1][0], avail[0][1][1])
    #             logging.debug(f"Api orig: {orig}")
    #             logging.debug(f"Api dest: {dest}")
    #             post = orig.obtainPostData(int(args[2:]))
    #             logging.info(f"Post: {post}")
    #             reply = dest.publishPost(post[0], post[1], '')
    #             if reply != 'Fail!':
    #                 orig.delete(int(args[2:]))
    #             res = f"{res}\n{reply}"
    #     for avail in self.available['j']['data']:
    #         logging.info(f"avail {avail[0][0]} {self} {args}")
    #         logging.info(f"avail avail {avail}")
    #         logging.info(f"avail myClient {myClient}")
    #         if myClient[2][0] == avail[0][0][0]:
    #             logging.info(f"is avail j {avail}")
    #             orig = self.clients[myClient]
    #             dest = getApi(avail[0][1][0], avail[0][1][1])
    #             logging.info(f"Orig: {orig}")
    #             logging.debug(f"Api dest: {dest}")
    #             reply = orig.publish(int(args[2:]))
    #             # This should be: getting post from orig, using dest to publish
    #             # ??
    #             res = f"{res}\n{reply}"

    #     # Not sure about this
    #     # res = self.execute('publish', args)
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
                args = "{} {}".format(args, self.lastEdit)
        res = self.execute("edit", args)
        self.addEditsCache(args)
        self.lastEdit = args.split(" ", 1)[1:][0]
        yield res
        yield end()

    def addEditsCache(self, args):
        argsArchive = self.argsArchive
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
                            theUpdatetxt = str(update[0]).replace("_", "\_")
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
            if updates[socialNetwork]:
                if theUpdates[0][0] != "Empty":
                    socialTime = theUpdates[0][2]
                else:
                    socialTime = ""
            else:
                socialTime = ""

            logging.debug(f"self.available ... {self.available}")
            logging.info(f"socialNetwork ... {socialNetwork}")
            data = self.available[socialNetwork[0].lower()]
            name = data["name"]
            logging.info(f"Name ... {name}")
            pos = int(socialNetwork[1])
            logging.info(f"Soc ... {data['data'][pos][1]}")
            social = socialNetwork
            if isinstance(data["data"][pos][1], str):
                socNick = f"{data['data'][pos][1]}"
            else:
                socNick = (
                    f"{data['data'][pos][1][1][0].capitalize()} "
                    f"{data['data'][pos][1][1][1]}"
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
                            compResponse.append(
                                (tt, socialNetworktxt, theUpdates[iniPos:maxPos])
                            )
                            iniPos = maxPos
                            maxPos = maxPos + math.trunc(numEle)
                    else:
                        compResponse.append((tt, socialNetworktxt, theUpdates))
                else:
                    compResponse.append((tt, socialNetworktxt, theUpdates))
            else:
                compResponse.append(
                    (
                        tt,
                        socialNetwork[0].capitalize() + " (" + socialNetwork[1] + ")",
                        theUpdates,
                    )
                )

        return compResponse

    def sendReply(self, mess, args, updates, types):
        reps = self.prepareReply(updates, types)
        compResponse = ""
        for rep in reps:
            response = (
                tenv()
                .get_template("buffer.md")
                .render(
                    {"type": rep[0], "nameSocialNetwork": rep[1], "updates": rep[2]}
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
        moduleBuffer.copyPost(self.api, logging, pp, self.profiles, args[0], args[1])
        yield "Copied"
        yield end()
