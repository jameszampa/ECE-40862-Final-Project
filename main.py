from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc import WordPressPost
from datetime import date
import git
from picamera import PiCamera
import RPi.GPIO as GPIO
from time import sleep
import os
import facialRecognizer




if __name__ == "__main__":

    # pull files from github for initial images state
    #git.cmd.

    # train model
    exec(open("facialRecognizer.py").read())

    # setup
    site = Client('http://169.254.244.132/xmlrpc.php', 'lawlesj@purdue.edu', 'Bpl2 vF31 ePl6 Unoa rAcC kJGm')
    my_posts = site.call(posts.GetPosts())
    camera = PiCamera()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(8, GPIO.IN)
    incomplete = True

    while incomplete:
        # user clicks button to try and unlock
        if GPIO.input(8) == GPIO.HIGH:

            # check github directories and make sure they match whats stored locally
            # if directories match:
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
            yay.terms_names = {'post_tag': [date], 'category': ['Successful Login']}
            yay.post_status = 'publish'
            yay.thumbnail = attachment_id
            site.call(posts.NewPost(yay))
            camera.close()
            incomplete = False
            # call cv2 script for unlocking the box
        # if not, git pull and retrain

        # add attempt to server

    print("hello world")
    pass
