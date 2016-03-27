#!/usr/bin/env python
# encoding: utf-8

#
# - The second one includes the secret data of the buffer app [~/.rssBuffer]
# [appKeys]
# client_id:XXXXXXXXXXXXXXXXXXXXXXXX
# client_secret:XXXXXXXXXXXXXXXXXXXXXXXXXXXxXXXX
# redirect_uri:XXXXXXXXXXXXXXXXXXXXXXXXX
# access_token:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# 
# These data can be obtained registering an app in the bufferapp site.
# Follow instructions at:
# https://bufferapp.com/developers/api
# 
# - The third one contains the last published URL [~/.rssBuffer.last]
# It contains just an URL which is the last one published. 
# At this moment it only considers one blog

import ConfigParser, os
from bs4 import BeautifulSoup
import logging

# sudo pip install buffpy version does not work
# Better use:
# git clone https://github.com/vtemian/buffpy.git
# cd buffpy
# sudo python setup.py install
from colorama import Fore
from buffpy.models.update import Update
from buffpy.managers.profiles import Profiles
from buffpy.managers.updates import Updates
from buffpy.api import API

import pprint
import time
import sys
import urllib
reload(sys)
sys.setdefaultencoding("UTF-8")


# We can put as many items as the service with most items allow
# The limit is ten.
# Get all pending updates of a social network profile

#[{'_Profile__schedules': None, u'formatted_service': u'Twitter', u'cover_photo': u'https://pbs.twimg.com/profile_banners/62983/1355263933', u'verb': u'tweet', u'formatted_username': u'@fernand0', u'shortener': {u'domain': u'buff.ly'}, u'timezone': u'Europe/Madrid', u'counts': {u'daily_suggestions': 25, u'pending': 0, u'sent': 10862, u'drafts': 0}, u'service_username': u'fernand0', u'id': u'4ed35f97512f7ebb5d00000b', u'disconnected': False, u'statistics': {u'followers': 5736}, u'user_id': u'4ed35f8e512f7e325e000001', u'avatar_https': u'https://pbs.twimg.com/profile_images/487165212391256066/DFRGycds_normal.jpeg', u'service': u'twitter', u'default': True, u'schedules': [{u'days': [u'mon', u'tue', u'wed', u'thu', u'fri', u'sat', u'sun'], u'times': [u'09:10', u'09:45', u'10:09', u'10:34', u'11:10', u'11:45', u'12:07', u'13:29', u'15:15', u'16:07', u'16:42', u'17:07', u'17:40', u'18:10', u'18:33', u'19:05', u'19:22', u'20:15', u'21:30', u'22:45', u'23:10', u'23:25', u'23:45']}], u'reports_logo': None, 'api': <buffpy.api.API object at 0x7f4f1a8508d0>, u'avatar': u'http://pbs.twimg.com/profile_images/487165212391256066/DFRGycds_normal.jpeg', u'service_type': u'profile', u'service_id': u'62983', u'_id': u'4ed35f97512f7ebb5d00000b', u'utm_tracking': u'enabled', u'disabled_features': []}, {'_Profile__schedules': None, u'formatted_service': u'LinkedIn', u'cover_photo': u'https://d3ijcis4e2ziok.cloudfront.net/default-cover-photos/blurry-blue-background-iii_facebook_timeline_cover.jpg', u'verb': u'post', u'timezone_city': u'Madrid - Spain', u'formatted_username': u'Fernando Tricas', u'shortener': {u'domain': u'buff.ly'}, u'timezone': u'Europe/Madrid', u'counts': {u'daily_suggestions': 25, u'pending': 0, u'sent': 4827, u'drafts': 0}, u'service_username': u'Fernando Tricas', u'id': u'4f4606ec512f7e0766000003', u'disconnected': False, u'statistics': {u'connections': 500}, u'user_id': u'4ed35f8e512f7e325e000001', u'avatar_https': u'https://media.licdn.com/mpr/mprx/0_zVbmG3KX1MsA8cT9vyLgGCt5Ay0Aucl9BjPAGC1ZaMIhPPQnMpBCuGbn0-xffrKVqJ5KDLD_G-D1', u'service': u'linkedin', u'default': True, u'schedules': [{u'days': [u'mon', u'tue', u'wed', u'thu', u'fri', u'sat', u'sun'], u'times': [u'01:46', u'05:52', u'07:13', u'08:54', u'09:27', u'10:13', u'10:49', u'11:58', u'12:03', u'12:03', u'12:41', u'13:05', u'15:23', u'16:35', u'16:57', u'17:23', u'18:02', u'18:37', u'19:58', u'20:17', u'21:13', u'22:00', u'23:05', u'23:07', u'23:49']}], u'reports_logo': None, 'api': <buffpy.api.API object at 0x7f4f1a8508d0>, u'avatar': u'https://media.licdn.com/mpr/mprx/0_zVbmG3KX1MsA8cT9vyLgGCt5Ay0Aucl9BjPAGC1ZaMIhPPQnMpBCuGbn0-xffrKVqJ5KDLD_G-D1', u'service_type': u'profile', u'service_id': u'x4Eu0cqIhj', u'_id': u'4f4606ec512f7e0766000003', u'utm_tracking': u'enabled', u'disabled_features': []}, {'_Profile__schedules': None, u'formatted_service': u'Facebook', u'cover_photo': u'https://scontent.xx.fbcdn.net/hphotos-xfp1/t31.0-8/s720x720/904264_10151421662663264_1461180243_o.jpg', u'verb': u'post', u'timezone_city': u'Zaragoza - Spain', u'formatted_username': u'Fernando Tricas', u'shortener': {u'domain': u'buff.ly'}, u'timezone': u'Europe/Madrid', u'counts': {u'pending': 0, u'sent': 5971, u'drafts': 0}, u'service_username': u'Fernando Tricas', u'id': u'5241b3f0351ff0a83500001b', u'disconnected': False, u'user_id': u'4ed35f8e512f7e325e000001', u'avatar_https': u'https://scontent.xx.fbcdn.net/hprofile-xpf1/v/t1.0-1/c0.0.50.50/p50x50/10500300_10152337396498264_6509296623992251600_n.jpg?oh=1870d57d20aa70388bed86f1383051f2&oe=578BF216', u'service': u'facebook', u'default': True, u'schedules': [{u'days': [u'mon', u'tue', u'wed', u'thu', u'fri', u'sat', u'sun'], u'times': [u'00:58', u'07:53', u'09:06', u'09:44', u'10:03', u'10:30', u'11:07', u'11:37', u'12:16', u'13:04', u'13:40', u'16:02', u'16:32', u'16:51', u'17:18', u'17:38', u'18:03', u'18:44', u'19:14', u'23:02', u'23:41']}], u'reports_logo': None, 'api': <buffpy.api.API object at 0x7f4f1a8508d0>, u'avatar': u'https://scontent.xx.fbcdn.net/hprofile-xpf1/v/t1.0-1/c0.0.50.50/p50x50/10500300_10152337396498264_6509296623992251600_n.jpg?oh=1870d57d20aa70388bed86f1383051f2&oe=578BF216', u'service_type': u'profile', u'service_id': u'503403263', u'_id': u'5241b3f0351ff0a83500001b', u'utm_tracking': u'enabled', u'disabled_features': []}, {'_Profile__schedules': None, u'formatted_service': u'Google+ Page', u'cover_photo': u'https://d3ijcis4e2ziok.cloudfront.net/default-cover-photos/blurry-blue-background-iii_facebook_timeline_cover.jpg', u'verb': u'post', u'formatted_username': u'Reflexiones e Irreflexiones', u'shortener': {u'domain': u'buff.ly'}, u'timezone': u'Europe/London', u'counts': {u'daily_suggestions': 25, u'pending': 0, u'sent': 0, u'drafts': 0}, u'service_username': u'Reflexiones e Irreflexiones', u'id': u'521f6df14ddfcbc91600004a', u'disconnected': False, u'user_id': u'4ed35f8e512f7e325e000001', u'avatar_https': u'https://lh6.googleusercontent.com/-yAIEsEEQ220/AAAAAAAAAAI/AAAAAAAAAC8/Q8K1Li_kZSY/photo.jpg?sz=50', u'service': u'google', u'default': False, u'schedules': [{u'days': [u'mon', u'tue', u'wed', u'thu', u'fri', u'sat', u'sun'], u'times': [u'10:50', u'17:48']}], u'reports_logo': None, 'api': <buffpy.api.API object at 0x7f4f1a8508d0>, u'avatar': u'https://lh6.googleusercontent.com/-yAIEsEEQ220/AAAAAAAAAAI/AAAAAAAAAC8/Q8K1Li_kZSY/photo.jpg?sz=50', u'service_type': u'page', u'service_id': u'117187804556943229940', u'_id': u'521f6df14ddfcbc91600004a', u'utm_tracking': u'enabled', u'disabled_features': []}]

def listEnabledServices(api, pp):
    profiles = Profiles(api=api).all()
    logging.info(pp.pformat(profiles))
    return

def publishPost(api, pp, profiles, toPublish):
    logging.info(pp.pformat(toPublish))
    i = int(toPublish[0])
    j = int(toPublish[1:])
    logging.debug("%d %d"  % (i,j))
    update = Update(api=api, id=profiles[i].updates.pending[j].id)
    logging.debug(pp.pformat(update))
    update.publish()

def listPendingPosts(api, pp, service=""):
    logging.info("Checking services...")
    
    if (service == ""):
	profiles = Profiles(api=api).all()
    else:
	profiles = Profiles(api=api).filter(service=service)
        
    logging.debug("->%s" % pp.pformat(profiles))
    numProfiles = len(profiles)
    logging.debug("Profiles %d" % numProfiles)
    logging.debug("Profiles %s" % pp.pformat(profiles))
    somePending = False
    outputStr = ""
    for i in range(numProfiles):
        logging.debug("Service %d %s" % (i,profiles[i].formatted_service))
        if (profiles[i].counts.pending > 0):
            somePending = True
            serviceName = profiles[i].formatted_service
            outputStr = outputStr + "\n" + serviceName
            logging.info("Service %s" % serviceName)
            logging.debug("Hay: %d" % profiles[i].counts.pending)
            logging.debug(pp.pformat(profiles[i].updates.pending))
    	    for j in range(profiles[i].counts.pending):
                logging.debug("Service %s" % pp.pformat(profiles[i].updates.pending[j]))
                selectionStr = "%d%d) " % (i,j)
                if ('media' in profiles[i].updates.pending[j]): 
                    lineTxt = "%s %s %s" % (selectionStr,profiles[i].updates.pending[j].text, profiles[i].updates.pending[j].media.expanded_link)
                else:
                    lineTxt = "%s %s" % (selectionStr,profiles[i].updates.pending[j].text)
                logging.info(lineTxt)
                outputStr = outputStr + "\n" + lineTxt
                update = Update(api=api, id=profiles[i].updates.pending[j].id)
                logging.debug("-- %s" % (pp.pformat(update)))
                logging.debug("-- %s" % (pp.pformat(dir(update))))
        else:
            logging.debug("Service %d %s" % (i, profiles[i].formatted_service))
            logging.debug("No")
    
    if somePending:
        return (outputStr, profiles)
    else:
        logging.info("No pending posts")
        return somePending

def main():
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.rssBuffer')])
    
    clientId = config.get("appKeys", "client_id")
    clientSecret = config.get("appKeys", "client_secret")
    redirectUrl = config.get("appKeys", "redirect_uri")
    accessToken = config.get("appKeys", "access_token")
    
    # instantiate the api object 
    api = API(client_id=clientId,
              client_secret=clientSecret,
              access_token=accessToken)

    logging.basicConfig(#filename='example.log',
                            level=logging.INFO,format='%(asctime)s %(message)s')

    pp = pprint.PrettyPrinter(indent=4)
    logging.debug(pp.pformat(api.info))
    logging.debug(api.info.services.keys())

    profiles = listPendingPosts(api, pp, "")

    if profiles:
       toPublish = raw_input("Which one do you want to publish? ")
       publishPost(api, pp, profiles, toPublish)


if __name__ == '__main__':
    main()
    sys.exit()

    serviceList=['twitter','facebook','linkedin']
    profileList={}
    
    lenMax=0
    for service in serviceList:
    	print "  %s"%service,
    	profileList[service] = Profiles(api=api).filter(service=service)[0]
    	if (len(profileList[service].updates.pending)>lenMax):
    		lenMax=len(profileList[service].updates.pending)
    	print "  ok"
    
    print "There are", lenMax, "in some buffer, we can put", 10-lenMax
    print "We have", i, "items to post"
    
    for j in range(10-lenMax,0,-1):
    
    	if (i==0):
    		break
    	i = i - 1
    	if (selectedBlog.find('tumblr') > 0):
    		soup = BeautifulSoup(feed.entries[i].summary)
    		pageLink  = soup.findAll("a")
    		if pageLink:
    			theLink  = pageLink[0]["href"]
    			theTitle = pageLink[0].get_text()
    			if len(re.findall(r'\w+', theTitle)) == 1:
    				print "Una palabra, probamos con el titulo"
    				theTitle = feed.entries[i].title
    			if (theLink[:22] == "https://instagram.com/") and (theTitle[:17] == "A video posted by"):
    				#exception for Instagram videos
    				theTitle = feed.entries[i].title
    			if (theLink[:22] == "https://instagram.com/") and (theTitle.find("(en")>0):
    				theTitle = theTitle[:theTitle.find("(en")-1]
    		else:
    			# Some entries do not have a proper link and the rss contains
    			# the video, image, ... in the description.
    			# In this case we use the title and the link of the entry.
    			theLink   = feed.entries[i].link
    			theTitle  = feed.entries[i].title.encode('utf-8')
    	elif (selectedBlog.find('wordpress') > 0):
    		soup = BeautifulSoup(feed.entries[i].content[0].value)
    		theTitle = feed.entries[i].title
    		theLink  = feed.entries[i].link	
    	else:
    		print "I don't know what to do!"
    
    	#pageImage = soup.findAll("img")
    	theTitle = urllib.quote(theTitle.encode('utf-8'))
    
    
    	#print i, ": ", re.sub('\n+',' ', theTitle.encode('iso-8859-1','ignore')) + " " + theLink
    	#print len(re.sub('\n+',' ', theTitle.encode('iso-8859-1','ignore')) + " " + theLink)
    	
    	post=re.sub('\n+',' ', theTitle) +" "+theLink
    	# Sometimes there are newlines and unnecessary spaces
    	#print "post", post
    
    	# There are problems with &
    	print "Publishing... "+ post
    	for service in serviceList:
    		print "  %s service"%service,
    		profile=profileList[service]
    		try:
    			profile.updates.new(post)
    			print "  ok"
    			time.sleep(3)
    		except:
    			failFile = open(os.path.expanduser("~/"+PREFIX+identifier+".fail"),"w")
    			failFile.write(post)
    
    urlFile = open(os.path.expanduser("~/"+PREFIX+identifier+POSFIX),"w")
    urlFile.write(feed.entries[i].link)
    urlFile.close()
