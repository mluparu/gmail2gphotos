#%%
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
import email
from datetime import datetime
from dateutil.parser import parse
import os

#%%
# Setting up working directory
os.chdir('c:\\data\\gmail2gphotos')
print(os.getcwd())

#%%
# Authenticate to gmail and gphotos
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/photoslibrary']
creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        # credentials.json can be downloaded from https://console.developers.google.com/apis/credentials
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server()
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

gmailservice = build('gmail', 'v1', credentials=creds)
photosservice = build('photoslibrary', 'v1', credentials=creds)

#%%
# Download Gmail messages matching the search criteria
query = 'from:me has:attachment subject:poze'
response = gmailservice.users().messages().list(userId='me', q=query).execute()
messages = []
if 'messages' in response:
    messages.extend (response['messages'])

while 'nextPageToken' in response:
    page_token = response['nextPageToken']
    response = gmailservice.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
    messages.extend(response['messages'])
print(len(messages))

#%%
# Save the messages as pickles
os.mkdir('messages')
for msg in messages:
    with open('messages\\' + msg['id'], 'wb') as f:
        pickle.dump(msg, f)

#%%
# Save the full messages as pickles
os.mkdir('fullmessages')
for msg in messages:
    msgFull = gmailservice.users().messages().get(id=msg['id'], userId='me', format='raw').execute()
    msgSrc = base64.urlsafe_b64decode(msgFull['raw'].encode('ASCII'))
    message = email.message_from_bytes(msgSrc)
    with open ('fullmessages\\' + msg['id'], 'wb') as f:
        pickle.dump(message, f)


#%%
# Reading messageids from disk and calling Gmail APIs for subject, date
from os import listdir
from os.path import isfile, join
path = 'messages'
files = [f for f in listdir(path) if isfile(join(path, f))]
for f in files:
    # List date and subject 
    msgHeaders = gmailservice.users().messages().get(id=f, userId='me', format='metadata').execute()
    headers = msgHeaders['payload']['headers']
    Subject = next(subj for subj in headers if subj['name'] == 'Subject')['value']
    Date = parse(next(date for date in headers if date['name'] == 'Date')['value'])
    print(Date, '   ', Subject)

#%%
# Reading full messages from disk and printing Subjects
path = 'fullmessages'
files = [f for f in listdir(path) if isfile(join(path, f))]
for filename in files:
    fullMsg = None
    fullName = join(path, filename)
    with open(fullName, 'rb') as f:
        fullMsg = pickle.load(f)
        date = parse(fullMsg['Date'])
        subject = fullMsg['Subject']
        subject = subject.replace('Poze: ', '').replace('Poze ', '').replace('Fwd: ', '')
        subject = subject.replace('FW: ', '').replace('poze ', '')
        
        print(f"{date:%Y-%m-%d}", subject)

#%%
# Delete all Fun emails
path = 'fullmessages'
files = [f for f in listdir(path) if isfile(join(path, f))]
for filename in files:
    fullMsg = None
    fullName = join(path, filename)
    with open(fullName, 'rb') as f:
        fullMsg = pickle.load(f)
    if fullMsg:
        subject = fullMsg['Subject']
        if "Fun" in subject:
            print(subject)
            os.remove(fullName)

#%%
# Reading full messages from disk and creating albums 
from os.path import isdir
path = 'fullmessages'
files = [f for f in listdir(path) if isfile(join(path, f))]
newpath = 'albums'
os.mkdir(newpath)

for filename in files:
    fullMsg = None
    fullName = join(path, filename)
    with open(fullName, 'rb') as f:
        fullMsg = pickle.load(f)
        date = parse(fullMsg['Date'])
        subject = fullMsg['Subject']
        subject = subject.replace('Poze: ', '').replace('Poze ', '').replace('Fwd: ', '')
        subject = subject.replace('FW: ', '').replace('poze ', '')
        subject = subject.replace(':', ' ')
        subject = subject.replace('/', ' of ')
        subject = subject.replace('\"', '\'').replace('.', '-')
        
        foldername = f"{date:%Y-%m-%d}" + ' ' + subject
        print(foldername)
        if not isdir(join(newpath, foldername)):
            os.mkdir(join(newpath, foldername))

#%%
# Reading full messages and saving attachments in the right albums
class Attachement(object):
    def __init__(self):
        self.data = None;
        self.content_type = None;
        self.size = None;
        self.name = None;

def parse_attachment(message_part):
    content_disposition = message_part.get("Content-Disposition", None);
    if content_disposition:
        dispositions = content_disposition.strip().split(";");
        if bool(content_disposition and dispositions[0].lower() == "attachment"):

            attachment = Attachement();
            attachment.data = message_part.get_payload(decode=True);
            attachment.content_type = message_part.get_content_type();
            attachment.size = len(attachment.data);
            attachment.name = message_part.get_filename();

            return attachment;
    return None;

path = 'fullmessages'
files = [f for f in listdir(path) if isfile(join(path, f))]
for filename in files:
    fullMsg = None
    fullName = join(path, filename)
    with open(fullName, 'rb') as f:
        fullMsg = pickle.load(f)
    if (fullMsg):
        date = parse(fullMsg['Date'])
        subject = fullMsg['Subject']
        subject = subject.replace('Poze: ', '').replace('Poze ', '').replace('Fwd: ', '')
        subject = subject.replace('FW: ', '').replace('poze ', '')
        subject = subject.replace(':', ' ')
        subject = subject.replace('/', ' of ')
        subject = subject.replace('\"', '\'').replace('.', '-')
        
        foldername = f"{date:%Y-%m-%d}" + ' ' + subject
        print('*** Folder: ', foldername)

        # Load attachments     
        attachments = list()
        if (fullMsg.is_multipart()):
            for part in fullMsg.walk():
                attachment = parse_attachment(part)
                if (attachment):
                    attachments.append(attachment)

        for att in attachments:
            attname = att.name
            fcount = 0
            while os.path.isfile(join('albums', foldername, attname)):
                fcount += 1
                parts = os.path.splitext(att.name)
                attname = parts[0] + ' (' + str(fcount) + ')' + parts[1]
            print(join('albums', foldername, attname))
            if (fcount != 0):
                print('-- ', att.name, ' changed to: ', attname)
            
            with open(join('albums', foldername, attname), 'wb') as f:
                f.write(att.data)


#%%
# Test: list some albums
results = photosservice.albums().list(pageSize=10).execute()
items = results.get('albums', [])
for item in items:
    print(u'{0} ({1})'.format(item['title'].encode('utf8'), item['id']))


#%%
# For each album folder, upload the pics, create the album, then create the pics 
# Serialize the upload token for each pic, if it already exists? skip upload
# Rename folder to UPLOADED-folder once done
# Make sure folders that start with UPLOADED are skipped during enumeration
import requests
from os import listdir
from os.path import isfile, join, isdir
def upload(service, file, shortfilename):
    f = open(file, 'rb').read()

    print ('\nUploading %s' % file) 
    url = 'https://photoslibrary.googleapis.com/v1/uploads'
    headers = {
        'Authorization': "Bearer " + service._http.credentials.token, # service._http.request.credentials.access_token,
        'Content-Type': 'application/octet-stream',
        'X-Goog-Upload-File-Name': shortfilename, 
        'X-Goog-Upload-Protocol': "raw",
    }

    r = requests.post(url, data=f, headers=headers)
    return r.content

root = 'albums'
albumFolders = [f for f in listdir(root) if isdir(join(root, f)) and not 'UPLOADED' in f]
for albumFolder in albumFolders:
    print('*** ALBUM ***', albumFolder)
    pictureFiles = [f for f in listdir(join(root, albumFolder)) if not 'UPLOAD-TOKEN' in f]

    # Upload files
    uploadTokens = list()
    for picFile in pictureFiles:
        uploadToken = None
        if not isfile(join(root, albumFolder, picFile) + '.UPLOAD-TOKEN'):
            uploadToken = upload(photosservice, join(root, albumFolder, picFile), picFile)
            if not '"code":' in uploadToken.decode('utf-8'):
                with open(join(root, albumFolder, picFile) + '.UPLOAD-TOKEN', 'wb') as f:
                    pickle.dump(uploadToken, f)
            else:
                with open(join(root, albumFolder, picFile) + '.ERROR.UPLOAD-TOKEN', 'wb') as f:
                    pickle.dump(uploadToken, f)
        else:
            with open(join(root, albumFolder, picFile) + '.UPLOAD-TOKEN', 'rb') as f:
                uploadToken = pickle.load(f)
            print('-- token reloaded')
        
        if (uploadToken):
            uploadTokens.append(uploadToken)
        else: 
            break #Exit if upload failed
        print(uploadToken)
    
    if len(pictureFiles) != len(uploadTokens):
        print('ERROR: One or more files failed to upload')
        break

    # Create album
    albumResults = None
    if not isfile(join(root, albumFolder, '.UPLOAD-TOKEN')):
        albumResults = photosservice.albums().create(body={'album' : {'title' : albumFolder}}).execute()
        with open(join(root, albumFolder, '.UPLOAD-TOKEN'), 'wb') as f:
            pickle.dump(albumResults, f)
    else:
        with open(join(root, albumFolder, '.UPLOAD-TOKEN'), 'rb') as f:
            albumResults = pickle.load(f)
        print('-- album reloaded')
    print(albumResults)
    print('*** ProductUrl ***')
    print(albumResults['productUrl'])
    print()
        
    # Batch create pictures
    mediaItems = list()
    for ut in uploadTokens:
        mediaItems.append( {"simpleMediaItem" : {"uploadToken" : ut.decode('utf-8')}})
    
    # If there are too many mediaItems the batchCreate call will fail
    mediaItemChunks = [mediaItems[x:x+12] for x in range(0, len(mediaItems), 12)]

    for mediaItemChunk in mediaItemChunks:
        response = photosservice.mediaItems().batchCreate(body=dict(
            albumId=albumResults['id'],
            newMediaItems = mediaItemChunk
        )).execute()
        print(response)

    # Rename folder once done
    os.rename(join(root, albumFolder), join(root, 'UPLOADED-' + albumFolder))

#%%
# List all URLs for newly created albums
from os import listdir
from os.path import isfile, join, isdir
root = 'albums'
albumFolders = [f for f in listdir(root) if isdir(join(root, f)) and 'UPLOADED' in f]
for albumFolder in albumFolders:
    if isfile(join(root, albumFolder, '.UPLOAD-TOKEN')):
        with open(join(root, albumFolder, '.UPLOAD-TOKEN'), 'rb') as f:
            albumResults = pickle.load(f)
            print(albumResults['title'])
            print(albumResults['productUrl'])
            print()

#%%
