from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc import WordPressPost
from datetime import date
from picamera import PiCamera
import RPi.GPIO as GPIO
from time import sleep


site = Client('http://192.168.137.26/xmlrpc.php', 'lawlesj@purdue.edu', 'Bpl2 vF31 ePl6 Unoa rAcC kJGm')
my_posts = site.call(posts.GetPosts())
GPIO.setmode(GPIO.BOARD)
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
incomplete = True
while incomplete:
	if GPIO.input(12) == False:
		camera = PiCamera()
		print("3...")
		sleep(1)
		print("2...")
		sleep(1)
		print("1...")
		sleep(1)
		print("Say cheese!")
		sleep(1)
		camera.capture('test_image.jpg')
		print("Picture taken!")
		filepath = 'test_image.jpg'
		data = {'name': 'test_image.jpg', 'type': 'image/jpeg'}
		with open(filepath, 'rb') as img:
			data['bits'] = xmlrpc_client.Binary(img.read())
		response = site.call(media.UploadFile(data))
		attachment_id = response['id']


		yay = WordPressPost()
		yay.title = 'Picture Time!'
		yay.content = 'Lookin\' snazzy'
		date = date.today().strftime("%b-%d-%Y")
		yay.terms_names = {'post_tag' : [date], 'category': ['Successful Login']}
		yay.post_status = 'publish'
		yay.thumbnail = attachment_id
		site.call(posts.NewPost(yay))
		camera.close()
		incomplete = False


