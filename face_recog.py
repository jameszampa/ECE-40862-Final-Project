import os
import cv2
import numpy as np
import pickle
import pigpio
import random
from datetime import date
import RPi.GPIO as GPIO
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, taxonomies
from wordpress_xmlrpc.methods import media as WordpressMedia
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc import WordPressPost
from time import sleep
import re
import requests
import shutil
from PIL import Image
from picamera import PiCamera

# Image face recog setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")
NUM_IMGS = 9
PATH_TO_FACE = r'/home/pi/opencv/data/haarcascades/haarcascade_frontalface_alt2.xml'
BANS = []

# Button Setup
GPIO.setmode(GPIO.BOARD)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Wordpress client initialize
site = Client('http://192.168.137.26/xmlrpc.php', 'lawlesj@purdue.edu', 'Bpl2 vF31 ePl6 Unoa rAcC kJGm')
#This IP is dependent on the wordpress site being hosted on my laptop's hotspot.


#Global locked/unlocked status variable
# False = Unlocked
# True = Locked
Locked = False


def _lock():
    pi = pigpio.pi()
    pi.set_servo_pulsewidth(18, 0)
    sleep(.5)
    pi.set_servo_pulsewidth(18, 1350)
    sleep(.5)
    pi.set_servo_pulsewidth(18, 0)
    pi.stop()

def _unlock():
    pi = pigpio.pi()
    pi.set_servo_pulsewidth(18, 0)
    sleep(.5)
    pi.set_servo_pulsewidth(18, 2250)
    sleep(.5)
    pi.set_servo_pulsewidth(18, 0)
    pi.stop()
    
def _unlockPost(user):
    post = WordPressPost()
    post.title = 'Box Unlocked'
    post.content = 'Unlocked by {}'.format(user)
    post.terms_names = {'post_tag' : [date.today().strftime("%b-%d-%Y")], 'category': ['Successful Login']}
    post.post_status = 'publish'
    site.call(posts.NewPost(post))
    
def _addedUserPost(user):
    post = WordPressPost()
    post.title = 'User added'
    post.content = 'New User {}'.format(user)
    post.terms_names = {'post_tag' : [date.today().strftime("%b-%d-%Y")], 'category': ['New User']}
    post.post_status = 'publish'
    site.call(posts.NewPost(post))
    
def _removedUserPost(user):
    post = WordPressPost()
    post.title = 'User removed'
    post.content = 'New User {}'.format(user)
    post.terms_names = {'post_tag' : [date.today().strftime("%b-%d-%Y")], 'category': ['Remove User']}
    post.post_status = 'publish'
    site.call(posts.NewPost(post))
    
def _intruderPost(image):

    data = {'name': image, 'type': 'image/jpeg'}
    with open(image, 'rb') as img:
        data['bits'] = xmlrpc_client.Binary(img.read())
    response = site.call(media.UploadFile(data))
    attachment_id = response['id']
    post = WordPressPost()
    post.title = 'Unauthorized Access Attempt'
    post.content = 'Face not recognized'
    post.terms_names = {'post_tag' : [date.today().strftime("%b-%d-%Y")], 'category': ['Unsuccessful Login']}
    post.post_status = 'publish'
    post.thumbnail = attachment_id
    site.call(posts.NewPost(post))

def getNewUser():
    recently_modified = site.call(posts.GetPosts({'orderby': 'post_modified', 'number': 10}))
    # Get the most recent 10 posts (Would theoretically break if we did 10 random posts and then added a new user post, can expand number if needed

    media_library = site.call(WordpressMedia.GetMediaLibrary([])) #Get media library of database
    new_users = []
    for post in recently_modified:
        names = [term.name for term in post.terms]
        if 'Processed' in names:
            pass
        elif 'New User' in names and post not in new_users:
            new_users.append(post)
            proc_tag = [tag for tag in site.call(taxonomies.GetTerms('post_tag')) if tag.name == "Processed"]
            print(proc_tag)
            post.terms.append(proc_tag[0])
            site.call(posts.EditPost(post.id, post))
            break
    # We are only interested in posts with the catagory "New User", so keep track of those
    if len(new_users) >= 1:
        post_id = new_users[0].id 
        #In theory, we would only process 1 new user post at a time; the most recent post

        photo_links = re.findall("class=\"wp-image-([\d]+)\"", new_users[0].content)
        # Get the media attachment ids for the post 
        directory = "images/" + new_users[0].title
        os.makedirs(directory)
        
        for media in media_library:
            if str(media.id)in photo_links:	
                resp = requests.get(media.link, stream=True)
                local_name = directory + "/{}.jpeg".format(media_library.index(media))
                local = open(local_name, "wb")
                resp.raw.decode_content = True
                shutil.copyfileobj(resp.raw, local)
                del resp
        _trainModel()
        # Using the attachment ids, get pictures from media library and use links to download pictures to a temporary folder on the pi
        # Temp folder can be used by main.py to import the new images and create a new recognizer


def addUser():
    global BANS
    face_cascade = cv2.CascadeClassifier(PATH_TO_FACE)
    username = "user_" + str(random.randint(0,999999999))
    directory = "images/" + username
    if not os.path.exists(directory):
        os.makedirs(directory)
    camera = PiCamera()
    i = 0
    while(i < 10):
        camera.capture(directory + '/' + str(i+1) + '.jpg')
        pil_image = Image.open(directory + '/' + str(i+1) + '.jpg').convert("L")
        image_array = np.array(pil_image, "uint8")
        faces = face_cascade.detectMultiScale(image_array, scaleFactor=1.5, minNeighbors=5)
        if len(faces) == 0:
            print("Image {}: No faces".format(i))
        else:
            print("Image {}: Found a face!".format(i))
            i += 1
    _addedUserPost(username)
    camera.close()
    _trainModel()



def _trainModel():
    face_cascade = cv2.CascadeClassifier(PATH_TO_FACE)
    recognizer = cv2.face.LBPHFaceRecognizer_create()

    curr_id = 0
    label_ids = {}
    y_labels = []
    x_train = []

    for root, dirs, files in os.walk(IMG_DIR):
        for f in files:
            if f.endswith("png") or f.endswith("jpg") or f.endswith("jpeg"):
                path = os.path.join(root, f)
                label = os.path.basename(root).replace(" ", "-").lower()

                if label not in label_ids:
                    label_ids[label] = curr_id
                    curr_id += 1
                id_ = label_ids[label]
                pil_image = Image.open(path).convert("L")
                image_array = np.array(pil_image, "uint8")

                faces = face_cascade.detectMultiScale(image_array, scaleFactor=1.5, minNeighbors=5)
                for (x, y, w, h) in faces:
                    roi = image_array[y:y + h, x:x + w]
                    x_train.append(roi)
                    y_labels.append(id_)

    recognizer.train(x_train, np.array(y_labels))
    recognizer.save("face-recognizer.yml")

    with open("face-labels.pickle", 'wb') as f:
        pickle.dump(label_ids, f)


def _smile321():
    print("Taking pictures in...")
    sleep(.2)
    print("3")
    sleep(.2)
    print("2")
    sleep(.2)
    print("1")
    sleep(.2)
    print("Smile!")


def checkUser():
    global BANS
    face_cascade = cv2.CascadeClassifier(PATH_TO_FACE)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("./face-recognizer.yml")

    labels = {"person_name": 1}
    with open("face-labels.pickle", 'rb') as f:
        og_labels = pickle.load(f)
        labels = {v: k for k, v in og_labels.items()}

    camera = PiCamera()
    foundFace = 0
    while(foundFace == 0):
        camera.capture('temp_check.jpg')
        picture = Image.open('temp_check.jpg')
        frame = np.array(picture, "uint8")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.5, minNeighbors=5)
    
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
            # roi_color = frame[y:y+h, x:x+w]
                id_, conf = recognizer.predict(roi_gray)
                print(labels[id_], conf)
                if labels[id_] in BANS:
                    print(labels[id_] + " is banned!")
                else:
                    pass
            foundFace = 1
            if conf < 30.00: #Note: conf is distance to nearest match, so smaller numbers mean a closer match
                _unlock()
                _unlockPost(labels[id_])
                Locked = False
                break
            else:
                _intruderPost('temp_check.jpg')
                Locked = True
                break
        else:
            print("No faces in image!")
    camera.close()
#    cap.release()


def banUser():
    recently_modified = site.call(posts.GetPosts({'orderby': 'post_modified', 'number': 10}))
    remove_users = []
    for post in recently_modified:
        names = [term.name for term in post.terms]
        if 'Processed' in names:
            pass
        elif 'Remove User' in names and post not in remove_users:
            remove_users.append(post)
            proc_tag = [tag for tag in site.call(taxonomies.GetTerms('post_tag')) if tag.name == "Processed"]
            print(proc_tag)
            post.terms.append(proc_tag[0])
            site.call(posts.EditPost(post.id, post))
            break
    if len(remove_users) >= 1:
        username = remove_users[0].title
        if not os.path.exists("images/" + username):
            print("User not found")
        else:
            shutil.rmtree("images/" + username)
            _trainModel()


if __name__ == "__main__":
    index = 0 
    while True:
        if ((GPIO.input(16) == 0) and (Locked)):
            pass
        elif ((GPIO.input(16) == 0) and (not Locked)):
            _lock()
            Locked = True
        elif ((GPIO.input(18) == 0) and (Locked)):
            checkUser()
        elif ((GPIO.input(18) == 0) and (not Locked)):
            addUser()
        if (index > 1000):
            getNewUser()
            banUser()
            index = 0
        else:
            index += 1
    #addUser(username, "camera")
   # banUser(username)
   # removeFromBan(username)
   # checkUser()
