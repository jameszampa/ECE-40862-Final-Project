from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc import WordPressPost
from time import sleep
import re
import requests
import shutil
import os

def importNewUser():
	BASE_DIR = os.path.dirname(os.path.abspath(__file__))
	IMG_DIR = os.path.join(BASE_DIR, "images")

	site = Client('http://192.168.137.26/xmlrpc.php', 'lawlesj@purdue.edu', 'Bpl2 vF31 ePl6 Unoa rAcC kJGm')
	# This IP is dependent on the wordpress site being hosted on my laptop's hotspot.

	recently_modified = site.call(posts.GetPosts({'orderby': 'post_modified', 'number': 100}))
	# Get the most recent 100 posts (Would theoretically break if we did 100 random posts and then added a new user post,
	# can expand number if needed

	media_library = site.call(media.GetMediaLibrary([]))  # Get media library of database
	new_users = []
	added_new_user = False
	for post in recently_modified:
		terms = post.terms
		for term in terms:
			if 'New User' == term.name and post not in new_users:
				new_users.append(post)
				added_new_user = True
	# We are only interested in posts with the category "New User", so keep track of those

	# Should be deleting requests after each message
	# Or maybe add a tag that says "Processed" to keep history? That way it is ignored on a second call to this script

	post_id = new_users[0].id
	# In theory, we would only process 1 new user post at a time and then either delete the post or
	# add a tag that prevents future processing (i.e. the list will always have only 1 post in it)

	photo_links = re.findall("class=\"wp-image-([\d]+)\"", new_users[0].content)
	print(photo_links)
	# Get the media attachment ids for the post

	for m in media_library:
		if str(m.id)in photo_links:
			print(m)
			print(m.link)
			resp = requests.get(m.link, stream=True)
			local_name = "Temp_Pictures/get_image_test{}.jpeg".format(media_library.index(m))
			local = open(local_name, "wb")
			resp.raw.decode_content = True
			shutil.copyfileobj(resp.raw, local)
			del resp
	# Using the attachment ids, get pictures from media library and use links to download pictures to a temporary folder
	# on the pi
	# Temp folder can be used by main.py to import the new images and create a new recognizer
	return added_new_user
