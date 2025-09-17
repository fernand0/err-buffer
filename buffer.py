import configparser
import os
import pickle
import pprint
import time
import urllib.parse
import glob
import re
from datetime import datetime

from errbot import BotPlugin, botcmd
from errbot.templating import tenv

# Needs to set $PYTHONPATH to the dir where this modules are located

from socialModules.configMod import *
import socialModules
import socialModules.moduleRules


def end(msg=""):
    return "END" + msg


class CommandArgs:
    """
    Parses command arguments from a string, preserving the original logic
    from getId, getSel, getPos, and getCont.
    """

    def __init__(self, arg_str):
        self.arg = arg_str if arg_str else ""

    @property
    def id(self):
        """Extracts the ID from the argument."""
        if self.arg and len(self.arg) > 0:
            return self.arg[0].upper()
        return None

    @property
    def selection(self):
        """
        Extracts the selection from the argument.
        Returns None if conversion to int fails.
        """
        if self.arg and len(self.arg) > 1:
            try:
                return int(self.arg[1])
            except ValueError:
                pass  # Do nothing, result remains None
        return None

    @property
    def position(self):
        """
        Extracts the position from the argument.
        Returns None if conversion to int fails.
        """
        if self.arg and len(self.arg) > 2:
            try:
                part = self.arg[2:].split(" ")[0]
                return int(part)
            except ValueError:
                pass  # Do nothing, result remains None
        return None

    @property
    def content(self):
        """Extracts the content from the argument."""
        if self.arg and " " in self.arg:
            pos = self.arg.find(" ")
            return self.arg[pos + 1 :]
        return None


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
        self.link_to_title_cache = {}
        self.config = []
        self.buffer_path = '/tmp/buffer' #config.get('buffer_path', 'buffer.md')
        self.buffer_lines = [] # Initialize buffer_lines
        self._load_buffer()
        # self.buffer_path = self.config.get('buffer_path', 'buffer.md')
        # self.link_to_title_cache = {}
        # self.buffer_lines = [] # Initialize buffer_lines
        # self._load_buffer()
        self.available = None
        self.schedules = None
        self.lastList = None
        self.lastEdit = None
        self.lastLink = None
        self.argsArchive = []

    def _load_buffer(self):
        if os.path.exists(self.buffer_path):
            with open(self.buffer_path, 'r') as f:
                self.buffer_lines = [line.strip() for line in f if line.strip()]
        else:
            self.buffer_lines = []

    def _save_buffer(self):
        with open(self.buffer_path, 'w') as f:
            for line in self.buffer_lines:
                f.write(line + '\n')


    def _edit_buffer(self, link, title=None):
        # Store the original title argument to differentiate between explicit None and derived title
        original_title_arg = title

        yield f"Cache: {self.link_to_title_cache}"
        # If a title is explicitly provided, cache it.
        if original_title_arg:
            self.link_to_title_cache[link] = original_title_arg
        # If no title is provided, try to get it from the cache.
        elif link in self.link_to_title_cache:
            title = self.link_to_title_cache[link]

        yield f"Recovered title: {title}"
        entry_found = False
        updated_lines = []
        for line in self.buffer_lines:
            # Use regex to find the exact link in the format [- [title](link)]
            match = re.search(r'\[.*?\]\((.*?)\)', line)
            if match and match.group(1) == link:
                entry_found = True
                # Extract current title from the buffer line if it exists
                current_title_from_line_match = re.search(r'\[(.*?)\]', line)
                current_title_from_line = current_title_from_line_match.group(1) if current_title_from_line_match else ""

                # If title is still None (not provided, not in cache), try to use title from line
                if title is None and current_title_from_line:
                    title = current_title_from_line
                
                # If after all attempts, title is still None for an existing entry, it's an error.
                if title is None:
                    print(f"Error: No title provided for link '{link}', and no cached or existing title found in buffer.")
                    return # Exit the function, as we cannot proceed without a title

                # Update the line with the determined title and link
                updated_lines.append(f"- [{title}]({link})")
            else:
                updated_lines.append(line)

        if not entry_found:
            # If link not found, add a new entry
            if title is None:
                # If no title for a new entry, default to "Untitled"
                title = "Untitled"
            updated_lines.append(f"- [{title}]({link})")

        self.buffer_lines = updated_lines
        self._save_buffer()
        yield(f"Buffer updated for: {link}")


    #def _edit_buffer(self, link, title=None):
    #    # Store the original title argument to differentiate between explicit None and derived title
    #    original_title_arg = title

    #    # If a title is explicitly provided, cache it.
    #    if original_title_arg:
    #        self.link_to_title_cache[link] = original_title_arg
    #    # If no title is provided, try to get it from the cache.
    #    elif link in self.link_to_title_cache:
    #        title = self.link_to_title_cache[link]

    #    entry_found = False
    #    updated_lines = []
    #    for line in self.buffer_lines:
    #        if link in line:
    #            entry_found = True
    #            # Extract current title from the buffer line if it exists
    #            current_title_from_line_match = re.search(r'\[(.*?)\]', line)
    #            current_title_from_line = current_title_from_line_match.group(1) if current_title_from_line_match else ""

    #            # If title is still None (not provided, not in cache), try to use title from line
    #            if title is None and current_title_from_line:
    #                title = current_title_from_line
    #            
    #            # If after all attempts, title is still None for an existing entry, it's an error.
    #            if title is None:
    #                print(f"Error: No title provided for link '{link}', and no cached or existing title found in buffer.")
    #                return # Exit the function, as we cannot proceed without a title

    #            # Update the line with the determined title and link
    #            updated_lines.append(f"- [{title}]({link})")
    #        else:
    #            updated_lines.append(line)

    #    if not entry_found:
    #        # If link not found, add a new entry
    #        if title is None:
    #            # If no title for a new entry, default to "Untitled"
    #            title = "Untitled"
    #        updated_lines.append(f"- [{title}]({link})")

    #    self.buffer_lines = updated_lines
    #    self._save_buffer()
    #    print(f"Buffer updated for: {link}")


    def _split_available_data(self, key, rules, myKeys, myIniKeys, available_item):
        """
        Splits the available data if its length is greater than 9.
        """
        if len(available_item["data"]) > 9:
            iniK, nKey = rules.getIniKey(
                available_item["name"].upper(), myKeys, myIniKeys
            )
            self.availableN[key] = {
                "name": "rss",
                "data": available_item["data"][:10],
                "social": [],
            }
            self.availableN[iniK] = {
                "name": "rss",
                "data": available_item["data"][10:],
                "social": [],
            }
        else:
            self.availableN[key] = available_item

    def setAvailable(self):
        """
        Checks and sets the available social media rules.
        """
        self.log.debug(f"Checking available")
        if not self.available:
            rules = socialModules.moduleRules.moduleRules()
            rules.checkRules()
            self.available = rules.available
            #self.log.info(f"Available: {self.available}")
            myKeys = {}
            myIniKeys = list(self.available.keys())
            self.availableN = dict(self.available)
            for key in self.available:
                # self.log.info(f"Available: {key} - {self.available[key]}")
                self._split_available_data(
                    key, rules, myKeys, myIniKeys, self.available[key]
                )

            self.rules = rules
            self.available = self.availableN

    def addMore(self):
        """
        Returns a message indicating how to add more lists.
        """
        response = (
            f"There are {len(self.config)} lists. "
            f"You can add more with command list add"
        )
        return response

    def _format_publication_section(self, publications, status):
        """Sorts and formats a list of publications for a given status."""
        textR = []
        if not publications:
            textR = ["===========", f"None {status}", "==========="]
        else:
            publications.sort()
            textR = ["=======", f"{status.capitalize()}:", "======="]
            for line in publications:
                _, line_content = line.split("|", 1)
                line1, line2 = line_content.split("->")
                textR.append(line1.strip())
                textR.append(f"      ⟶{line2.strip()}")
        return textR

        """
        Processes a single .timeNext file and returns a dictionary with publication info.
        """
        publication_info = None
        try:
            if not os.path.islink(file_path):
                with open(file_path, "rb") as f:
                    tNow, tSleep = pickle.load(f)

                next_publication_time = datetime.fromtimestamp(tNow + tSleep)
                theTime = next_publication_time.strftime("%H:%M:%S")

                orig, dest = os.path.basename(file_path).split("__")
                orig = self.cleanLine(orig, "key", i)
                dest = self.cleanLine(dest)

                textElement = f"{next_publication_time} | {theTime} {orig} -> {dest}"
                status = "waiting" if time.time() < tNow + tSleep else "finished"

                publication_info = {"text": textElement, "status": status}

        except (pickle.UnpicklingError, EOFError, TypeError, ValueError) as e:
            self.log.error(f"Error processing file {os.path.basename(file_path)}: {e}")
        except Exception as e:
            self.log.error(
                f"Unexpected error with file {os.path.basename(file_path)}: {e}"
            )

        return publication_info

    def fileNameBase2(self, rule, action):
        """
        Generates a file name based on the rule and action.
        """
        nick = self.rules.getNickRule(rule)
        if ('blogalia' in nick) \
            or ('wordpress' in nick)\
            or ('github.com' in nick)\
            or ('feed.xml' in nick):
            nick = urllib.parse.urlparse(nick).netloc
        else:
            nick = nick.replace('/','-').replace(':','-')
        return (f"{self.rules.getNameRule(rule).capitalize()}_"
                f"{self.rules.getTypeRule(rule)}_"
                f"{nick}_"
                f"{self.rules.getSecondNameRule(rule).capitalize()}_"
                f"_{self.rules.getNameAction(action).capitalize()}"
                f"_{self.rules.getTypeAction(action)}s"
                f"_{self.rules.getNickAction(action)}"
                f"_{self.rules.getProfileAction(action).capitalize()}"
               )

    def cleanLine(self, line, key="", i=None):
        """
        Cleans a given line of text.
        """
        line = line.split('_')
        if 'key' in key:
            line = f"{line[0]} ({line[2]} {line[1]})"
        elif key:
            line = f"{key}{i} {line[0]} ({line[2]} {line[1]})"
        else:
            line = f"{line[0]} ({line[2]} {line[1]})"
        line = line.replace('https', '').replace('http','')
        line = line.replace('---','').replace('.com','')
        line = line.replace('- ',' ')
        return line

    def _process_time_file(self, file_path, i):
        """
        Processes a single .timeNext file and returns a dictionary with
        publication info.  
        """
        publication_info = None
        try:
            if not os.path.islink(file_path):
                with open(file_path, 'rb') as f:
                    tNow, tSleep = pickle.load(f)
                self.log.info(f"tNow Textinfaaa: {file_path} ... {tNow} - {tSleep}")
                self.log.info(f"tNow Textinfooo: {tNow + tSleep}")

                next_publication_time = datetime.fromtimestamp(tNow + tSleep)
                self.log.info(f"next Textinfooo: {next_publication_time}")
                theTime = next_publication_time.strftime("%H:%M:%S")
                self.log.info(f"next Textinfooo: {theTime}")

                orig, dest = os.path.basename(file_path).split('__')
                orig = self.cleanLine(orig, 'key', i)
                dest = self.cleanLine(dest)

                textElement = f"{next_publication_time} | {theTime} {orig} -> {dest}"
                status = "waiting" if time.time() < tNow + tSleep else "finished"

                publication_info = {"text": textElement, "status": status}
                self.log.info(f"Textinfooo: {textElement}")

        except (pickle.UnpicklingError, EOFError, TypeError, ValueError) as e:
            self.log.error(f"Error processing file {os.path.basename(file_path)}: {e}")
        except Exception as e:
            self.log.error(f"Unexpected error with file {os.path.basename(file_path)}: {e}")

        return publication_info

    @botcmd(split_args_with=None, template="buffer")
    def list_next(self, mess, args):
        """Lists upcoming and finished publications based on .timeNext files."""
        time_files_pattern = os.path.join(DATADIR, "*.timeNext")
        time_files = glob.glob(time_files_pattern)
        
        if args:
            filtered_files = []
            for f in time_files:
                filename_lower = os.path.basename(f).lower()
                if any(service.lower() in filename_lower for service in args):
                    filtered_files.append(f)
            time_files = filtered_files

        if not time_files:
            yield "Time files not found."
        else:
            waiting_publications = []
            finished_publications = []
            for i, file_path in enumerate(time_files):
                publication_info = self._process_time_file(file_path, i)
                if publication_info:
                    if publication_info["status"] == "waiting":
                        waiting_publications.append(publication_info["text"])
                    else:
                        finished_publications.append(publication_info["text"])

            output_lines = (
                self._format_publication_section(finished_publications, "finished") +
                self._format_publication_section(waiting_publications, "waiting")
            )
            yield "\n".join(output_lines)
            
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def list_last(self, mess, args):
        """
        Shows the last listed items.
        """
        if self.lastList:
            yield f"Last list: {str(self.lastList)}"
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
        self.log.debug(f"Rules: {rules.rules}")
        rules.indent = ""
        for rule in rules.rules:
            for action in rules.rules[rule]:
                service = rules.getProfileAction(action)
                if rules.hasPublishMethod(service):
                    # FIXME: publishPost is in modulecontent
                    iniK, nameK = rules.getIniKey(service.upper(), myKeys, myIniKeys)
                    more = rules.more[rule]
                    if not (iniK in available):
                        available[iniK] = {
                            "name": service,
                            "data": [],
                            "social": [],
                            "actions": [],
                        }
                        available[iniK]["data"] = []
                    available[iniK]["data"].append({"src": action, "more": more})
                    self.log.debug(f"Action: {action}")
                    self.log.debug(f"Service: {service}")
                    if service not in actions:
                        actions[service] = [
                            action,
                        ]
                    else:
                        actions[service].append(action)
                    if action not in available[iniK]["actions"]:
                        available[iniK]["actions"].append(action)

        self.log.debug(f"Actions: {actions}")
        self.log.debug(f"Available: {available}")

        myList = {}
        theKey = "M0"
        myList[theKey] = []
        keys = []
        for key in available:
            # yield f"- Key: {key} {available[key]['name']}"
            for i, action in enumerate(available[key]["actions"]):
                service = rules.getProfileAction(action)
                myList[theKey].append(
                    (
                        f"{service.capitalize()} "
                        f"{rules.getNickAction(action)}@"
                        f"{service}"
                        f"{rules.getTypeAction(action)}",
                        key,
                        f"{key}{i}",
                    )
                )
                # yield f"{key}{i}) {service} {rules.getNickAction(action)}"
            keys.append(f"{key}{i}")
        self.log.debug("list actions (myList): {str(myList)}")
        keys = ",".join(keys)
        myList[theKey].append((keys, "", "I"))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ("\n".join(rep.split("\n")[3:]))

    @botcmd
    def list_all(self, mess, args):
        """List available services"""
        if args:
            yield f"Args: {args}"
        self.setAvailable()

        rules = self.rules

        # self.log.debug(f"Available all: {str(self.available)}")
        # yield("Available: %s" % str(self.available))
        myList = {}
        theKey = "L0"
        myList[theKey] = []
        keys = []
        for key in self.available:
            if ((args and ((key.lower() == args.lower())
                          or (args.lower() in self.available[key]['name']))) 
                or not args):
                for i, elem in enumerate(self.available[key]["data"]):
                    self.log.debug(f"Elem: {elem}")
                    name = rules.getNameRule(elem["src"])
                    profile = rules.getSecondNameRule(elem["src"])
                    nick = rules.getNickRule(elem["src"])
                    if nick:
                        if "http" in nick:
                            # FIXME: duplicate code
                            nick = urllib.parse.urlparse(nick).netloc
                        src = elem["src"]
                        myList[theKey].append(
                            (
                                f"{name.capitalize()} "
                                f"({nick}@{profile} "
                                f"{self.rules.getTypeRule(src)})",
                                key,
                                f"{key}{i}",
                            )
                        )
                keys.append(f"{key}{i}")
        self.log.debug(f"myList: {str(myList)}")
        keys = ",".join(keys)
        myList[theKey].append((keys, "", "I"))
        # yield("myList: %s" % str(myList))

        response = self.sendReply("", "", myList, ["sent", "pending"])
        for rep in response:
            # Discard the first, fake, result
            yield ("\n".join(rep.split("\n")[3:]))

        return end

    def appendMyList(self, arg, myList):
        """
        Appends an element to myList if it exists in available.
        """
        self.log.debug(f"Args... {arg}")
        self.setAvailable()

        parsed_args = CommandArgs(arg)
        id_arg = parsed_args.id
        if id_arg in self.available:
            pos = parsed_args.selection
            if pos is not None and pos < len(self.available[id_arg]["data"]):
                myList.append(arg.capitalize())

        self.log.debug(f"myList: {myList}")

    @botcmd(split_args_with=None, template="buffer")
    def list_read(self, mess, args):
        """
        Marks selected items as read.
        """
        # Maybe define a flow?
        myList = []
        pos = 0
        clients = self.clients
        if args:
            parsed_args = CommandArgs(args)
            if parsed_args.id.isdigit():
                pos = int(parsed_args.id)
            yield (parsed_args.id)
            self.appendMyList(parsed_args.id, myList)
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
                self.log.debug(f"Element {str(element)}")
                self.log.debug(f"Clients {str(clients)}")
                if element in clients:
                    thePosts = clients[element].getPosts()
                    if thePosts:
                        lenPosts = len(thePosts)
                        link = clients[element].getLink(lenPosts - 1)
                        # link = thePosts[-1][1]
                        service = clients[element].getService()
                        if service.lower() in ["forum", "reddit"]:
                            name = clients[element].getUrl()
                            updateLastLink(name, link)
                        yield (f"Marked read {element}")
        yield end()

    @botcmd
    def list_del(self, msg, args):
        """Delete a list of services from the quick list"""

        pos = 0
        if args:
            parsed_args = CommandArgs(args)
            if parsed_args.id.isdigit():
                pos = int(parsed_args.id)
            yield (parsed_args.id)

        if pos < len(self.config):
            self.config = self.config[:pos] + self.config[pos + 1 :]
            response = self.config
        else:
            response = self.addMore()

        yield (response)
        yield (end())

    def show_config(self):
        """
        Returns a formatted string of the current configuration.
        """
        response = ""
        for i, ll in enumerate(self.config):
            response = f"{response}{i}: {ll}\n"
        if not response:
            response = f"Empty list, you can add items with list add"
        return response

    @botcmd(split_args_with=None)
    def list_add(self, msg, args):
        """Add list of services to the quick list"""
        myList = []

        for arg in args:
            self.appendMyList(arg, myList)

        if myList:
            self.config.append(myList)

        response = self.show_config()
        yield response

        yield (end())

    @botcmd
    def list_list(self, msg, args):
        """
        Lists the current configuration.
        """
        self.setAvailable()

        rules = self.rules

        response = self.show_config()
        yield response
        yield end()

    def getUrlSelected(self, selected):
        """
        Extracts the URL from the selected item.
        """
        url = selected[0][0][0]
        return url

    def getSelectedProfile(self, key, pos):
        """
        Returns the selected profile from available data.
        """
        selected = self.available[key]["data"][pos]
        return selected

    def getProfile(self, key):
        """
        Returns the profile name for a given key.
        """
        profile = self.available[key]["name"]
        return profile

    def _init_client_and_set_posts(self, element):
        """Initializes a client if it doesn't exist and calls setPosts."""
        if element not in self.clients:
            self.log.debug(f"Client {element} not found, creating a new one.")
            parsed_element = CommandArgs(element)
            profile = self.available[parsed_element.id]  # Reintroduced this line
            sel = parsed_element.selection
            if sel is not None and sel < len(profile["data"]):
                myElem = profile["data"][sel]
                src = myElem["src"]
                more = self.rules.more.get(src, [])

                api = self.rules.readConfigSrc(f"{element} ", src, more)
                api.setPostsType(myElem["src"][3])
                self.clients[element] = api
            else:
                self.log.warning(
                    f"Could not initialize client for element {element} due to invalid selection."
                )
                return  # Exit if client cannot be initialized

        self.clients[element].setPosts()

    @botcmd(split_args_with=None, template="buffer")
    def list(self, mess, args):
        """A command to show available posts in a list of available sites"""
        self.log.debug(f"Posts posts {self.posts}")
        self.log.debug(f"args {str(args)}")

        myList = []
        response = []
        self.posts = {}
        self.setAvailable()

        available = self.available

        if not args:
            # If no args, we asume we want the first one
            args = ["0"]

        for arg in args:
            pos = -1
            if arg:
                parsed_arg = CommandArgs(arg)
                canBeAPos = parsed_arg.id
                if canBeAPos.isdigit():
                    pos = int(canBeAPos)
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

            self.log.debug(f"myList {str(myList)}")

        self.lastList = myList
        clients = self.clients

        if not myList:
            yield (self.addMore())

        self.log.debug(f"Clients {str(clients)}")
        self.log.debug(f"Available {available}")
        for element in myList:
            self.log.debug(f"Element {str(element)}")
            self._init_client_and_set_posts(element)
            client = self.clients[element]

            postsTmp = []
            posts = []

            if hasattr(client, "getPostsType"):
                if client.getPostsType() == "drafts":
                    postsTmp = client.getDrafts()
                else:
                    postsTmp = client.getPosts()
            else:
                postsTmp = client.getPosts
            if postsTmp:
                for i, post in enumerate(postsTmp):
                    if hasattr(client, "getPostLine"):
                        title = client.getPostLine(post)
                        link = ""
                    else:
                        title = client.getPostTitle(post)
                        link = client.getPostLink(post)
                    posts.append((title, link, f"{i:2}"))
                    # self.log.debug("I: %s %s %d"%(title,link,i))

            self.posts[element] = posts
            # self.log.debug("Posts posts %s" % (self.posts))

        response = self.sendReply("", "", self.posts, ["sent", "pending"])
        self.log.debug(f"Response {str(response)} End")

        for resp in response:
            # self.log.debug(f"Resp: {resp}")
            yield (resp)

        self.clients = clients
        yield end()

    @botcmd(split_args_with=" ")
    def last(self, command, args):
        """
        Handles the 'last' command to get the last published link.
        """
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
        lastLink = ""

        parsed_args = CommandArgs(" ".join(args))
        sel_arg = parsed_args.selection

        if len(args) > 1 and sel_arg is not None:
            lastLink = sel_arg
            yield f"Url: {lastLink}"
        # yield f"First: {first}"

        parsed_first = CommandArgs(first)
        id_first = parsed_first.id
        if id_first not in available:
            yield f"Invalid first argument: {first}"
            return

        sel_first = parsed_first.selection
        if sel_first is None or sel_first >= len(available[id_first]["data"]):
            yield f"Invalid selection for first argument: {first}"
            return

        name = available[id_first]["name"]
        src = available[id_first]["data"][sel_first]["src"]
        yield (f"Name: {rules.getIdRule(src)}")
        myActions = rules.rules[src]

        parsed_first_arg = CommandArgs(firstArg)
        selectClient = f"{parsed_first_arg.id}{parsed_first_arg.selection}"
        if not selectClient in clients:
            yield f"You should execute 'list {selectClient}' first"
            return
        apiSrc = clients[selectClient]
        for i, action in enumerate(myActions):
            yield (
                f"Action {i}. {rules.getNickAction(action)}@"
                f"{rules.getProfileAction(action)}"
                f"({rules.getNameAction(action)}-"
                f"{rules.getTypeAction(action)})"
            )
            apiDst = rules.readConfigDst("", action, rules.more[src], apiSrc)
            apiSrc.fileName = ""
            apiSrc.setLastLink(apiDst)
            if lastLink:
                self.log.debug(f"Updating last link")
                yield (f"Updating last link")
                apiSrc.updateLastLink(apiDst, lastLink)
                myLastLink = apiSrc.getLastLinkPublished()
            else:
                myLlastLink = apiSrc.getLastLinkPublished()
            yield (f"Last link: {myLlastLink}")
        yield end()

    def _get_client_for_command(self, args):
        """
        Parses args, validates them, and retrieves the client.
        Returns a tuple of (client, parsed_args, error_message).
        """
        if not self.available:
            return None, None, "Error: No available services found."

        parsed_args = CommandArgs(args)
        idArg = parsed_args.id
        selArg = parsed_args.selection

        if (
            idArg not in self.available
            or selArg is None
            or selArg >= len(self.available[idArg]["data"])
        ):
            return None, None, f"Error: Invalid selection argument: {args}"

        myClient = f"{idArg}{selArg}".upper()
        if myClient not in self.clients:
            return None, None, f"You should execute 'list {myClient}' first"

        return self.clients[myClient], parsed_args, None

    def _prepare_args_for_dispatch(self, parsed_args, command): # Added 'command' argument
        """Prepares the list of arguments for the dynamic command call."""
        args_for_cmd = []

        if command in ["edit", "edita"]:
            # For 'edit' and 'edita', parsed_args.content contains "title link" or "link"
            content = parsed_args.content
            if content:
                parts = content.split(" ", 1)
                if len(parts) == 2:
                    title = parts[0]
                    link = parts[1]
                else: # Only link provided
                    title = None
                    link = parts[0]
                
                args_for_cmd.append(title)
                args_for_cmd.append(link)
        else:
            # Existing logic for other commands
            pos = parsed_args.position
            argCont = parsed_args.content

            if pos is not None:
                args_for_cmd.append(pos)

            if argCont is not None:
                if isinstance(argCont, str) and argCont.capitalize() in self.clients:
                    args_for_cmd.append(self.clients[argCont.capitalize()])
                else:
                    args_for_cmd.append(argCont)

        return args_for_cmd

    def _format_success_response(
        self, command, original_args, update_result, profile_id
    ):
        """Formats the final string response for the user."""
        resTxt = f"Executing: {command}\n with args: {original_args}"
        updates = f"* {update_result} ({profile_id[0]})\n"
        return f"{resTxt}\n{updates}"

    def execute(self, command, args):
        """Executes a command by coordinating helper methods."""
        client, parsed_args, error = self._get_client_for_command(args)
        if error:
            self.log.warning(error)
            return error

        command_args = self._prepare_args_for_dispatch(parsed_args, command) # Pass 'command' here

        try:
            client.setPosts()
            command_method = getattr(client, command)
            update_result = command_method(*command_args)
        except Exception as e:
            self.log.error(f"Error executing command '{command}': {e}")
            return f"Error executing command '{command}'."

        return self._format_success_response(
            command, args, update_result, parsed_args.id
        )

    @botcmd
    def insert(self, mess, args):
        """A command to publish some update"""
        res = self.execute("insert", args)
        yield res
        yield end()

    # Passing split_args_with=None will cause arguments to be split on any kind
    # of whitespace, just like Python's split() does
    def _parse_publish_args(self, args):
        """Parses arguments for the publish command."""
        self.log.debug(f"Parsing publish args: {args}")
        if " " in args:
            pos = args.find(" ")
            dst = args[:pos]
            mes = args[pos + 1 :]
        else:
            dst = args
            mes = ""

        myList = []
        if dst.isdigit():
            pos = int(dst)
            if (pos >= 0) and (pos < len(self.config)):
                myList.extend(self.config[pos])
        else:
            myList.append(dst)

        return myList, mes

    def _publish_content(self, post_content, myActions, src, name, apiSrc, pos=None):
        """
        Publishes the given content to various social media platforms.
        """
        if "hold" in self.rules.more[src]:
            self.rules.more[src]["hold"] = "no"

        for i, action in enumerate(myActions):
            nameAction = self.rules.getNameAction(action)
            typeAction = self.rules.getTypeAction(action)
            msgAction = (
                f"Action {i}. {self.rules.getNickAction(action)}@"
                f"{self.rules.getProfileAction(action)}"
                f"({nameAction}-{typeAction})"
            )
            yield msgAction

            apiDst = self.rules.readConfigDst("", action, self.rules.more[src], None)
            if pos is not None and pos >= 0:
                resExecute = self.rules.executeAction(
                    src,
                    self.rules.more[src],
                    action,
                    msgAction,
                    apiSrc,
                    apiDst,
                    noWait=True,
                    timeSlots=0,
                    simmulate=False,
                    name=(f"{name} " f"{typeAction}"),
                    nextPost=False,
                    pos=pos,
                    delete=False,
                )
                self.log.info(f"Res execute: {resExecute}")
                yield f"{resExecute}"
            else:
                apiDst.publishPost(post_content, "", "")

    def _publish_post(self, element, mes):
        """
        Prepares and publishes a post based on element or message.
        """
        clients = self.clients
        available = self.available
        rules = self.rules

        self.log.debug(f"Publishing {element}")
        yield (f"Publishing {element}")

        parsed_element = CommandArgs(element)
        idArg = parsed_element.id
        name = available[idArg]["name"]
        selArg = parsed_element.selection
        if selArg is None or selArg >= len(available[idArg]["data"]):
            self.log.warning(f"Invalid selection for element: {element}")
            yield "Error: Invalid selection for element."
            return

        src = available[idArg]["data"][selArg]["src"]
        self.log.debug(f"Src: {src}")

        myActions = rules.rules[src]
        myClient = f"{idArg}{selArg}".upper()
        apiSrc = clients[myClient]
        apiSrc.setPosts()
        pos = parsed_element.position

        post_content = None
        if pos is not None and pos >= 0:
            post = apiSrc.getPost(pos)
            title = apiSrc.getPostTitle(post)
            link = apiSrc.getPostLink(post)
            post_content = f"{title} {link}"
            yield (f"Will publish: {post_content}")
        else:
            post_content = mes

        if not post_content:
            yield "We need some position or something to publish"
            return

        yield from self._publish_content(
            post_content, myActions, src, name, apiSrc, pos
        )

    @botcmd
    def publish(self, mess, args):
        """A command to publish some update"""

        myList, mes = self._parse_publish_args(args)

        yield f"Args: {args}"
        yield f"Dst list: {myList}"
        yield f"Mes: {mes}"

        if self.available:
            for element in myList:
                for response in self._publish_post(element, mes):
                    yield response
            yield (f"Finished actions!")
        else:
            yield (f"We have no data, you should use 'list {args[:2]}'")
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
            yield (f"- {arg}")
        yield end()

    @botcmd
    def edit_link(self, mess, args):
        """A command to edit the link of some update"""
        if " " not in args:
            if self.lastLink:
                args = f"{args} {self.lastLink}"
        res = self.execute("editl", args)
        self.lastLink = args.split(" ", 1)[1:][0]
        yield res
        yield end()

    @botcmd
    def edit_add(self, mess, args):
        """A command to add/edit some update with caching"""
        link = None
        title = None

        if " " in args:
            parts = args.split(" ", 1)
            title = parts[0]
            link = parts[1]
        else:
            link = args
            # title remains None

        if link:
            # Update local buffer
            self._edit_buffer(link, title)
            yield f"Buffer updated for link: {link}"

            # Trigger external effect via execute
            # Assuming 'edita' command on client expects title and link
            if title:
                res = self.execute("edita", f"{title} {link}")
            else:
                res = self.execute("edita", link) # Pass only link if no title
            yield res # Yield the result of the external execution
        else:
            yield "Error: No link provided for edit_add command."
        yield end()

    @botcmd
    def edit(self, mess, args):
        """A command to edit some update"""
        link = None
        title = None

        if not " " in args:
        #    parts = args.split(" ", 1)
        #    title = parts[0]
        #    link = parts[1]
        # else:
        #     link = args
        #     # title remains None
        # else: 
            parts = self.execute("show", args) 
            # title = parts[0]
            # link = parts[1]
            yield f"Args: {args}"
            link = parts.split('\n')[-2]
            yield f"Link: {link}"

        if link:
            # Update local buffer
            self._edit_buffer(link, title)
            yield f"Buffer updated for link: {link}"

            # Trigger external effect via execute
            # Assuming 'edit' command on client expects title and link
            if title:
                res = self.execute("edit", f"{title} {link}")
            else:
                res = self.execute("edit", link) # Pass only link if no title
            yield res # Yield the result of the external execution
        else:
            yield "Error: No link provided for edit command."
        yield end()

    def addEditsCache(self, args):
        """
        Adds edit arguments to the archive.
        """
        argsArchive = self.argsArchive  # ????
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

    @botcmd  # (split_args_with=None)
    def copy(self, mess, args):
        """
        A command to copy some update.
        """
        res = self.execute("copy", args)
        yield "Copied"
        yield res
        yield end()

    def prepareReply(self, updates, types):
        compResponse = []
        # self.log.debug(f"Pposts {updates}")
        # self.log.debug(f"Keys {updates.keys()}")
        tt = "pending"
        for socialNetwork in updates.keys():
            #  self.log.debug(f"Update social network {socialNetwork}")
            #  self.log.debug(f"Updates {updates[socialNetwork]}\nEnd")
            #  self.log.debug(f"Element: {socialNetwork}")
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
            # self.log.debug(f"self.available ... {self.available}")
            # self.log.debug(f"socialNetwork ... {socialNetwork}")
            data = self.available[CommandArgs(socialNetwork).id]
            name = data["name"]
            # self.log.debug(f"Name ... {name}")
            pos = int(socialNetwork[1])
            # self.log.debug(f"Data: {data['data'][pos]}")
            social = socialNetwork
            src = data["data"][pos]["src"]
            try:
                actions = self.rules.rules[src]
            except:
                # Experimental. We will try with the rule associated to a
                # similar src
                altSrc = src[:-1] + ("posts",)
                actions = self.rules.rules[altSrc]
            myDest = ""
            if src in self.rules.more and not (
                ("hold" in self.rules.more[src])
                and (self.rules.more[src]["hold"] == "yes")
            ):
                for action in actions:
                    myDest = (
                        f"{myDest}\n"
                        # f" {self.rules.getNameAction(action)} "
                        f"        ⟶ "
                        f"{self.rules.getNameAction(action).capitalize()} "
                        f"({self.rules.getNickAction(action)}@"
                        f"{self.rules.getProfileAction(action)} "
                        f"{self.rules.getTypeAction(action)})"
                    )
            # self.log.debug(f"myDest: {myDest}")
            # self.log.debug(f"Actions: {actions}")
            # self.log.debug(f"Social ... {social}")
            # self.log.debug(f"Src ... {src}")
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
                    f"{self.rules.getNameRule(src).capitalize()} "
                )
            if theUpdates:
                # self.log.debug(" not socialNetwork > 2")
                compResponse.append((tt, socialNetworktxt, myDest, theUpdates))
            else:
                # self.log.debug(" no updates")
                compResponse.append(
                    (
                        tt,
                        socialNetworktxt,
                        myDest,
                        theUpdates,
                    )
                )

        return compResponse

    def sendReply(self, mess, args, updates, types):
        """
        Sends the prepared reply to the user.
        """
        self.log.debug(f"Updates: {updates}")
        reps = self.prepareReply(updates, types)
        self.log.debug(f"Reps: {reps}")
        for rep in reps:
            # self.log.debug(f"Rep: {rep}")
            response = (
                tenv()
                .get_template("buffer.md")
                .render(
                    {
                        "type": rep[0],
                        "nameSocialNetwork": rep[1],
                        "post": rep[2],
                        "updates": rep[3],
                    }
                )
            )
            yield (response)

    @botcmd(split_args_with=None, template="buffer")
    def prog_del(self, mess, args):
        """A command to delete some schedule"""

        yield f"Adding {args}"
        for profile in self.clients:
            if "delSchedules" in dir(self.clients[profile]):
                self.clients[profile].delSchedules(args)
                yield f"{profile[0]}: ({profile[1]}) {self.clients[profile].getHoursSchedules()}"
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_add(self, mess, args):
        """A command to add a publishing time in the schedule"""
        yield f"Adding {args}"
        for profile in self.clients:
            if "addSchedules" in dir(self.clients[profile]):
                self.clients[profile].addSchedules(args)
                yield f"{profile[0]}: ({profile[1]}) {self.clients[profile].getHoursSchedules()}"
        yield end()

    @botcmd(split_args_with=None, template="buffer")
    def prog_show(self, mess, args):
        """A command to show scheduled times"""
        self.setAvailable()
        if not self.clients:
            yield (
                f"You have not selected any service to show. "
                f"You need to list at least one service"
            )
        for profile in self.clients:
            self.log.debug(f"Profile: {str(profile)}")
            if "setSchedules" in dir(self.clients[profile]):
                self.clients[profile].setSchedules("rssToSocial")
                schedules = self.clients[profile].getHoursSchedules()
                if isinstance(schedules, str):
                    numS = len(schedules.split(","))
                else:
                    numS = len(schedules)

                if numS:
                    self.schedules = numS
                yield f"{profile[0]}: ({profile[1]}) {schedules} Number: {numS}"
        yield (end())
