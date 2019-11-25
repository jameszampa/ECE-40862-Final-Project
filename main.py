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
import newFaceRecognizer
import getNewUser


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(8, GPIO.IN)

    GPIO.setmode(GPIO.BOARD)  # Sets the pin numbering system to use the physical layout
    GPIO.setup(11, GPIO.OUT)  # Sets up pin 11 to an output (instead of an input)


def unlock_servo():

    p = GPIO.PWM(11, 50)  # Sets up pin 11 as a PWM pin
    p.start(0)  # Starts running PWM on the pin and sets it to 0

    # Move the servo back and forth
    p.ChangeDutyCycle(6)  # Changes the pulse width to 3 (so moves the servo)

    p.stop()  # At the end of the program, stop the PWM
    GPIO.cleanup()  # Resets the GPIO pins back to defaults

def lock_servo():
    p = GPIO.PWM(11, 50)  # Sets up pin 11 as a PWM pin
    p.start(0)  # Starts running PWM on the pin and sets it to 0

    # Move the servo back and forth
    p.ChangeDutyCycle(10)  # Changes the pulse width to 3 (so moves the servo)

    p.stop()  # At the end of the program, stop the PWM
    GPIO.cleanup()  # Resets the GPIO pins back to defaults


def process_button(site, camera):
    # check github directories and make sure they match whats stored locally
    # if directories match:
    newFaceRecognizer._smile321()
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
    d = date.today().strftime("%b-%d-%Y")
    yay.terms_names = {'post_tag': [d], 'category': ['Successful Login']}
    yay.post_status = 'publish'
    yay.thumbnail = attachment_id
    site.call(posts.NewPost(yay))
    camera.close()

    # call cv2 script for unlocking the box
    id, conf = newFaceRecognizer.checkUser()
    if conf >= 45 and id not in newFaceRecognizer.getBannedUsers():
        # call servo unlock fxn
        unlock_servo()



if __name__ == "__main__":

    newFaceRecognizer.refreshBans()

    # setup
    site = Client('http://169.254.244.132/xmlrpc.php', 'lawlesj@purdue.edu', 'Bpl2 vF31 ePl6 Unoa rAcC kJGm')
    my_posts = site.call(posts.GetPosts())
    camera = PiCamera()

    setup_gpio()

    # lock_servo()

    while True:
        # user clicks button to try and unlock
        getNewUser.importNewUser()
        # newFaceRecognizer.addUser()
        if GPIO.input(8) == GPIO.HIGH:
            process_button(site, camera)