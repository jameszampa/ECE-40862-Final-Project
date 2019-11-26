import os
import cv2
import numpy as np
import pickle
from time import sleep
from PIL import Image
from picamera import PiCamera

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")
NUM_IMGS = 9
PATH_TO_FACE = r'/home/pi/opencv/data/haarcascades/haarcascade_frontalface_alt2.xml'
BANS = []


def addUser(username, mode):
    global BANS
    face_cascade = cv2.CascadeClassifier(PATH_TO_FACE)
    directory = "images/" + username
    if not os.path.exists(directory):
        os.makedirs(directory)
        # Download images from webserver or use camera to take pictures
        # Use camera to take pictures - using laptop webcam might need to change for
        # rasberry pi cam
        if mode == "webserver":
            print("mode:", mode, "not implemented yet")
        elif mode == "camera":
            camera = PiCamera()
            #cap = cv2.VideoCapture(0)
            i = 0
            while(i < 10):
                _smile321()
                camera.capture(directory + '/' + str(i+1) + '.jpg')
                pil_image = Image.open(directory + '/' + str(i+1) + '.jpg').convert("L")
                image_array = np.array(pil_image, "uint8")
                faces = face_cascade.detectMultiScale(image_array, scaleFactor=1.5, minNeighbors=5)
                if len(faces) == 0:
                    print("No faces")
                else:
                    print("Found a face!")
                    i += 1
            camera.close()
            '''
            for i in range(NUM_IMGS):
                ret, frame = cap.read()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                new_img = Image.fromarray(frame, "RGB")
                new_img.save(directory + '/' + str(i+1) + '.jpg')
                print("[camera noises]")
                sleep(1)
            cap.release()
            '''
        _trainModel()
    else:
        if username in BANS:
            print("Unbanned", username)
            removeFromBan(username)


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

    # James Webcam stuff CHANGE TO RASBERRY PI CAM
    #cap = cv2.VideoCapture(0)
    camera = PiCamera()
    foundFace = 0
    while(foundFace == 0):
        _smile321()
        camera.capture('temp_check.jpg')
        picture = Image.open('temp_check.jpg')
        frame = np.array(picture, "uint8")
    #ret, frame = cap.read()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.5, minNeighbors=5)
    
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
            # roi_color = frame[y:y+h, x:x+w]
                id_, conf = recognizer.predict(roi_gray)
                if labels[id_] in BANS:
                    print(labels[id_] + " is banned!")
                else:
                    print(labels[id_], conf)
            foundFace = 1
        else:
            print("No faces in image!")
    camera.close()
#    cap.release()


def banUser(username):
    global BANS
    if username not in BANS:
        BANS.append(username)
        with open("bans.pickle", 'wb') as f:
            pickle.dump(BANS, f)


def removeFromBan(username):
    global BANS
    if username in BANS:
        BANS.remove(username)
        with open("bans.pickle", 'wb') as f:
            pickle.dump(BANS, f)


def refreshBans():
    global BANS
    with open("bans.pickle", 'rb') as f:
        BANS = pickle.load(f)


if __name__ == "__main__":
    #username = "james-zampa"
    #refreshBans()
    #addUser(username, "camera")
   # banUser(username)
   checkUser()
   # removeFromBan(username)
   # checkUser()
