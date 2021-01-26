# This programs runs facial recagnition on a security camera
# Author: Derek Franz
# Started: 7/11/2020
# Last Updated: 1/25/21

from datetime import datetime
from shutil import copyfile
import os, face_recognition, cv2, requests, time, mysql.connector, pickle, sys, emailSender
from multiprocessing import Process
import derek_functions as df

KNOWNFACESDIR = "knownFaces"
MODEL = 'cnn'
COLOR = [0,255,0]
FRAMETHICKNESS = 3
FRAMECOLOR = [0,255,0]
TOLERANCE = .6
FONTTHICKNESS = 2


def loadEncodings():
    knownFaces = []
    knownIds = []
    print('Loading encodings')

    if os.path.isdir(KNOWNFACESDIR) == False:
        os.mkdir(KNOWNFACESDIR)

    for ID in os.listdir(KNOWNFACESDIR):
        for fileName in os.listdir(os.path.join(KNOWNFACESDIR,ID)):
            if '.pkl' in fileName:
                data = pickle.load(open(os.path.join(KNOWNFACESDIR,ID,fileName),'rb'))
                if isinstance(data,list):
                    for item in data:
                        knownFaces.append(item)
                        knownIds.append(int(ID))
                else:
                    knownFaces.append(pickle.load(open(os.path.join(KNOWNFACESDIR,ID,fileName),'rb')))
                    knownIds.append(int(ID))
                

    numIDs = list(dict.fromkeys(knownIds))
    return knownFaces, knownIds

def faceRec(knownFaces, knownIds, devMode=False):
    global KNOWNFACESDIR
    global MODEL
    global TOLERANCE
    global FRAMECOLOR
    global FRAMETHICKNESS
    global FONTTHICKNESS
    global COLOR

    #Path to the video file, only used when processing a video file for testing
    videoFile = "C:\\Users\\Derek\\Resilio Sync\\Sync\\Sync\\Programs\\Python\\videoFace\\low.mp4"
    
    if devMode == True:
        # Captures video from the webcam
        video = cv2.VideoCapture(0)
    else:
        # Access video from IP camera 
        video = cv2.VideoCapture(df.CAMERA_PATH)

    # Uncomment to access video file
    #video = cv2.VideoCapture(videoFile)
    
    numIDs = list(dict.fromkeys(knownIds))

    if len(numIDs) > 0:
        next_id = int(max(numIDs)) + 1
    else:
        # Should only run when creating a the first ID
        next_id = 0

    namesID = getNames()

    while True:
        ret, image = video.read()
        # If there is a problem reading a frame will just skip to the next frame
        try:
            locations = face_recognition.face_locations(image,model=MODEL)
        except Exception as e:
            continue
        
        # Finds all the faces in the frame
        encodings = face_recognition.face_encodings(image,locations)

        # Go through each of the faces 
        for face_encoding, face_location in zip(encodings, locations):
            
            results = face_recognition.compare_faces(knownFaces, face_encoding, TOLERANCE)
            match = None

            #Checks if there is a known face detected
            if True in results:
                match = knownIds[results.index(True)]
                ID = knownIds[match]

                # Finds the coordinates to the center of the face
                yCord = (locations[0][0] + locations[0][2])/2
                xCord = (locations[0][1]+locations[0][3])/2

                height, width = image.shape[:2]
                xServo = xCord / height * 180 
                yServo = yCord / width * 180
                
                # Uncomment to add a circle to the middle of the face
                #cv2.circle(image, (int(xCord), int(yCord)), 1, [0,0,255], 2)


                createTime = str(datetime.now())
                sql = 'INSERT INTO SecurityInfo (ID,TimeSeen,Model) VALUES ("'+str(ID)+'","'+createTime+'","CNN") '
                df.runSql(sql)

                try:
                    name = namesID[ID]
                    match = name
                except Exception as e:
                    #print('This ID is '+str(ID))
                    pass

                if devMode == True:                
                    top_left = (face_location[3],face_location[0])
                    bottom_right = (face_location[1], face_location[2])
                    color = [0,255,0]
                    cv2.rectangle(image,top_left,bottom_right,color,FRAMETHICKNESS)
                    cv2.putText(image,str(match),(face_location[3]+10,face_location[2]+15), cv2.FONT_HERSHEY_SIMPLEX,.5,(200,200,200), FONTTHICKNESS)
                    print("This is "+str(match))

            else:
                # If there is a new face found
                match = str(next_id)
                next_id+=1
                knownIds.append(int(match))

                # Creates a new folder for the new face and dumps and encoding and an image of the face
                knownFaces.append(face_encoding)
                os.mkdir(os.path.join(KNOWNFACESDIR,match))
                tempFname = os.path.join(KNOWNFACESDIR,match,match+'.pkl')
                pickle.dump(face_encoding,open(tempFname, 'wb'))

                #Draws the rectangle around the recagnized face and writes this image to file
                top_left = (face_location[3],face_location[0])
                bottom_right = (face_location[1],face_location[2])
                cv2.rectangle(image,top_left,bottom_right,COLOR,FRAMETHICKNESS)
                frameImPath = os.path.join(KNOWNFACESDIR,match,match+'_frame.jpg')
                cv2.imwrite(frameImPath,image)
         

        if devMode == True:
            cv2.imshow("Video feed",image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
                cv2.destroyWindow()     



#@return: Returns a dict with the key as the ID and the value as the name
def getNames():
    sql = "SELECT Name, ID FROM IdToName WHERE Model = 'CNN'"
    results = df.runSql(sql)
    namesID = {}
    for result in results:
        namesID[result[1]] = result[0]
    return namesID
        

def main():
    getNames()
    f, g = loadEncodings()
    try:
        arg = sys.argv[1]
        if 'devMode' in arg:
            print('Entering DevMode')
            devMode=True
        else:
            devMode=False
    except Exception as e:
        devMode=False

    faceRec(f,g,devMode=devMode)

main()
