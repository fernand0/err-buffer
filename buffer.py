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
# import socialModules.moduleBuffer


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
                if element.find("__") > 0:
                    res = element[:-len('.timeNext')]
                    res = res.split("__")
                    src = res[0].split('_')
                    dst = res[1].split('_')
                    if isinstance(res, str):
                        res = res.split("__")

                    url = f"{src[0]} ({src[2]} {src[1]})"
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
        yield f"Args: {args}"
        if not self.available:
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available
            self.rules = rules

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
                    myList[theKey].append((elem['src'][1], key, f"{key}{i}"))
            keys.append(f"{key}{i}")
        logging.info("myList: %s" % str(myList))
        keys = ','.join(keys)
        myList[theKey].append((keys, "", "I"))
        # yield("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ('\n'.join(rep.split('\n')[3:]))

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
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available
            self.rules = rules

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
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available

        response = self.config
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
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available
            self.rules = rules

            # for key in self.available.keys():
            #     #yield f"Key: {key} - {rules.available[key]}"
            #     # available -> {"name": src[0], "data": [], "social": []}
            #     # 'data' -> [{'src': src[1:], 'more': more[i]}]
            #     for i, element in enumerate(self.available[key]['data']):
            #         "yield (f"     {key}{i}) {element}")
            #     time.sleep(0.2)

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
                src = (self.rules.available[element[0].lower()]['name'], )
                src = src + myElem['src']
                more = self.rules.more[src]

                try:
                    clients[element].setPosts()
                except:
                    # api = getApi(profile['name'], profile["data"][int(element[1:])]['src'][1])
                    api = self.rules.readConfigSrc('', src, more)
                    # if name == 'cache':
                    #     # FIXME
                    #     api.socialNetwork=myElem['src'][1][1][0]
                    #     api.nick=myElem['src'][1][1][1]
                    # api = getApi(name.capitalize(), myElem['src'][1])
                    clients[element] = api
                    clients[element].setPostsType(myElem['src'][2])
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

        # # yield(f"Avail: {available}")
        name = available[args[0].lower()]["name"]
        src = available[args[0].lower()]["data"][int(args[1])]['src']
        dest = src[1]
        logging.debug(f"Clients: {clients}")
        logging.debug(f"Rules rules: {rules.rules}")
        myRule = rules.selectRule(name,  dest)[0]
        logging.debug(f"My rule: {myRule}")
        myActions = rules.rules[myRule]
        logging.debug(f"My actions: {myActions}")
        apiSrc = clients[args[:2].upper()]
        apiSrc.setPosts()
        pos = int(args[2:])
        post = apiSrc.getPost(pos)
        title = apiSrc.getPostTitle(post)
        link = apiSrc.getPostLink(post)
        logging.debug(f"Title: {title}")
        yield(f"Will publish: {title} - {link}")
        logging.debug(f"Link: {link}")
        logging.debug(f"Actions: {myActions}")

        published = False
        for i, action in enumerate(myActions):
            logging.info(f"Action {i}: {action}")
            yield(f"Action {i}: {action}")
            yield(f"Rule: {rules.more[myRule]}")
            if 'hold' in rules.more[myRule]:
                rules.more[myRule]['hold'] = 'no'
            rules.executeAction(myRule, rules.more[myRule], action,
                                noWait=True, timeSlots=0, simmulate=False,
                                name=f"{name} {action[1]}",
                                nextPost=False, pos=pos, delete=False)
        yield (f"Finished actions!")

        postaction = apiSrc.getPostAction()
        logging.debug(f"Postaction: {postaction}")
        logging.debug(f"Src: {src}")
        logging.debug(f'{available[args[0].lower()]["data"][int(args[1])]}')
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
