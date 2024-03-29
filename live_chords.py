import json
import os
import time
import urllib.error
import urllib.request
from difflib import SequenceMatcher

import requests
import spotipy
import spotipy.util as util
from bs4 import BeautifulSoup
import datetime

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# Get current song playing from spotify
def get_current_song(username, clientid, clientsecret, redirect_uri, scope='user-read-currently-playing'):
    # get acces token by logging in or get it from cache
    if __name__ != "__main__":
        print("SEARCHING FOR SONG NOW AT " + str(datetime.datetime.now().time()))
    token = util.prompt_for_user_token(username, scope, client_id=clientid, client_secret=clientsecret,
                                       redirect_uri=redirect_uri)
    # create spotipy object
    sp = spotipy.Spotify(auth=token)

    # call the function currently playing. The standard spotipy python file does not have this function. Edit the source file by adding the following function:
    # "def current_playing()
    #   return self._get('me/player/currently-playing')
    # "
    song = sp.current_playing()  # returns json dict containing song info
    if song is not None and song['item'] is not None:
        title = song['item']['name']  # extract the current song title
        t0 = song['progress_ms'] / 1000
        if "acoustic" in title:
            title = title.replace("acoustic", "")
        if "Acoustic" in title:
            title = title.replace("Acoustic", "")
        if " - " in title:
            title = title.replace(" - ", "")
        title = title.replace("(", "")
        title = title.replace(")", "")
        title = title.replace("live", "")
        title = title.replace("Live", "")
        title = title.replace("\'","")
        title = title.replace("Version","")
        title = title.replace("version","")
        artist = song['item']['artists'][0]['name']  # extracte the song artist
    else:
        title = "no song playing"
        artist = "no song playing"
        t0 = 0

    # print("currently playing: " + title + " by " + artist)
    return title, artist, t0


# the input is a single string, this function seperates the multiple lines outputting an array of strings, where every index is a new line
def seperate_lines(data, tabslines=False):
    # Seperate the HTML text in multiple lines of text, skipping the newline tag
    data = data + "\n" #add a newline character to data so that the last line is picked up as well.
    string = " "  # generate empty string
    strings = []  # list of lines
    for char in data:  # for every character in the data
        if char == "\n":  # if it's a new line, put the existing string in the list, empty the existing string.
            if tabslines: #if the inputted string is from ultimate guitar tabs, replace \r and \\ with nothing.
                string = string.replace("\r", "")
                string = string.replace("\\", "")
            strings.append(string)
            string = ""
        else:
            string = string + char  # if its not a new line, add the current character to the string
    return strings  # return list of strings


# Input is string array of HTML of website with tabs, outputs a string with the tabs.
def extract_tabs(strings):
    # Loop over all the lines and extract the content json file, which contains the tabs.
    content = " "
    for string in strings:
        if string[4:27] == "window.UGAPP.store.page":  # find the correct line where the json data is stored
            content = string[30:-1]  # extract data
            break

    # Put the content tabs json file in a dictionary
    if content == " ":
        tabs = "no tabs found"  # if no tabs are found...
    else:
        data = json.loads(content)  # convert json file to python dictionary
        # print(data)
        tabs = data["data"]["tab_view"]["wiki_tab"]["content"]  # extract the tab text
        tabs = tabs.replace("[ch]", "")  # remove these characters
        tabs = tabs.replace("[/ch]", "")
    return tabs


# Extract the search results for ultimate guitar tabs search
def extract_search_results(strings):
    content = ""
    for string in strings:
        if string[4:27] == "window.UGAPP.store.page":  # List of search results are here
            content = string[29:-1]
            break

    data = json.loads(content)  # create dictionary from string

    if ('not_found' in data['data']) and (data['data']['not_found'] == True):
        data = "no data found"
    else:
        data = json.loads(content)  # convert stringed json file to python dict
        data = data["data"]["results"]  # extract search results
    # print(data)

    return data


# Print the search results to the console
def sort_search_results(data):
    # while loop that loops over all the results and checks if it contains chords or tabs. If there are results which are not tabs or chords these results are popped.

    i = 0  # iterator
    #while i < len(data) and len(data) > 1:  # while iterator
    #    result = data[i]
    #    if "type_name" in result:
    #        # if not (result["type_name"] == "Chords" or result["type_name"] == "Tab"):
    #        if not result["type_name"] == "Chords":
    #            data.pop(i)
    #        else:
    #            i += 1
    #    else:
    #        data.pop(i)

    while i < len(data) and len(data) > 1:
        result = data[i]
        if "type" in result:
            if result['type'].lower() == "chords":
                i += 1
            else:
                data.pop(i)
        else:
            data.pop(i)

    # Sort remaining search results by highest rating.
    highest_rating = 0
    if len(data) > 1:
        for result in data:
            if result["rating"] >= highest_rating:
                highest_rating = result["rating"]
                tab_url = result["tab_url"]
    else:
        tab_url = data[0]['tab_url']

    return tab_url  # return tab_url


# Print tabs to console
def print_tabs(file):
    if file.has_azlyrics and file.has_tabs:
        for line in file.chorded_lyrics:
            if line['group'] == 'intro' or line['group'] == 'start':
                print(line['lyrics'])
            else:
                if line['chords'] != "": print("chords: " + line['chords'])
                if line['lyrics'] != "": print("lyrics: " + line['lyrics'])
    elif file.has_tabs and not file.has_azlyrics:
        for line in file.tabslines:
            print(line['text'])


# Find the lyrics and tabs for a artsist,title. Firstly looking at both artist and title than, if nothing found, only looking at title of song.
def search_lyrics(artist, title, print_to_console=False):
    tabs = "no data found"
    print("STARTING SEARCH ON ULTIMATE GUITAR TABS")
    found = False  # to keep track if the lyrics have been found or not
    # URL to search the website
    searchurl = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + artist + "%20" + title
    print(searchurl)
    r = requests.get(searchurl)
    data = r.text  # Pure HTML as single string
    searchhtml = seperate_lines(data)  # seperate the lines by searching for the newline tag
    search_results = extract_search_results(searchhtml)  # extract search results
    if search_results == "no data found":  # if no data is found print this to the console and search on only title
        print("NO SEARCH RESULTS FOUND")
        print("SEARCHING ON JUST TITLE")
        searchurl = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + title
        print(searchurl)
        r = requests.get(searchurl)
        data = r.text
        searchhtml = seperate_lines(data)
        search_results = extract_search_results(searchhtml)
        if search_results != "no data found":
            found = True
        else:
            print("NO SEARCH RESULTS FOUND ON ULTIMATE GUITAR TABS")
    else:
        found = True

    if found:
        print("GETTING LYRICS FROM ULTIMATE GUITAR TABS")
        url = sort_search_results(search_results)  # print search results, and get the url of the highest rating result
        # url = "https://tabs.ultimate-guitar.com/tab/flogging_molly/the_last_serenade_sailors_and_fishermen_chords_2045663"
        print(url)
        r = requests.get(url)  # get the website for the search result
        data = r.text  # HTMLtext
        htmldata = seperate_lines(data)  # seperated lines
        tabs = extract_tabs(htmldata)  # extracted the tabs line
        if print_to_console:
            print_tabs(tabs)  # print the tabs, slowly scrolling (maybe)

    print("STARTING SEARCH ON AZLYRICS")
    azlyrics = "no azlyrics found"  # if no azlyrics are found, this string will remain the same so that other functions know no azlyrics are found
    azartist = artist.lower()
    azartist = azartist.replace("%20", "+")
    aztitle = title.lower()
    aztitle = aztitle.replace("%20", "+") #on azlyrics the artist and title need to be formatted as "flogging+molly+life+is+good".
    url = "https://search.azlyrics.com/search.php?q={}+{}".format(azartist, aztitle)  # search on azlyrics
    print(url)
    r = requests.get(url)
    data = r.text
    lines = seperate_lines(data)
    found = False
    for line in lines:  # go through the html data from searching azlyrics and find the first result.
        if line.replace(" ", "")[0:2] == "1.":
            print(line) #the link is found between the quotes
            ind1 = line.find('"')
            ind2 = line[ind1 + 1:-1].find('"')
            link = line[ind1 + 1:ind2 + ind1 + 1]
            print(link)
            found = True
            break
    if found:
        r = requests.get(link)  # get the first result and extract the lyrics
        data = r.text
        lyrics = extract_lyrics(data)
        azlyrics = seperate_lines(lyrics[0])
        azlyrics.append("str")

    print("DONE WITH SEARCHING")

    return tabs, azlyrics


# File class, This class has functions to open and save a file for the lyrics. The idea is that if the song has been downloaded before lyrics, tabdata and sync data will be saved to disk so that it can be opened quickly.
# methods in this class are:
#   'open_file()': checks if a file exists on disk, if not the search_lyrics function is called.
#   'close_file()': the data in the class is written to a json string file and the file is closed.
#   'to_dict()': Write all the class variables to the dictionary
#   'from_dict()': write all
class file:
    def __init__(self, artist, title, version):
        self.artist = artist
        self.title = title
        self.data = {}  # dictionary contains all class-variables as well in order to write them to json string file
        self.tabs = ""
        self.synced = False
        self.tabslines = []
        self.azlyrics = ""
        self.has_tabs = False
        self.has_azlyrics = False
        self.chorded_lyrics = []
        self.script_version = version
        self.file_version = ""
        self.to_dict()

    def to_dict(self): #helper function to write all the instance variables to the dictionary
        self.data['artist'] = self.artist
        self.data['title'] = self.title
        self.data['tabs'] = self.tabs
        self.data['synced'] = self.synced
        self.data['tabslines'] = self.tabslines
        self.data['azlyrics'] = self.azlyrics
        self.data['has_tabs'] = self.has_tabs
        self.data['has_azlyrics'] = self.has_azlyrics
        self.data['chorded_lyrics'] = self.chorded_lyrics
        self.data['version'] = self.script_version

    def from_dict(self): #when a file is loaded only the instance variable dictionary is loaded. This function loads values in.
        self.artist = self.data['artist']
        self.title = self.data['title']
        self.tabs = self.data['tabs']
        self.synced = self.data['synced']
        self.tabslines = self.data['tabslines']
        self.azlyrics = self.data['azlyrics']
        self.has_tabs = self.data['has_tabs']
        self.has_azlyrics = self.data['has_azlyrics']
        self.chorded_lyrics = self.data['chorded_lyrics']
        if 'version' in self.data:
            self.file_version = self.data['version']

    def clear_file(self):
        self.data = {}  # dictionary contains all class-variables as well in order to write them to json string file
        self.tabs = ""
        self.synced = False
        self.tabslines = []
        self.azlyrics = ""
        self.has_tabs = False
        self.has_azlyrics = False
        self.chorded_lyrics = []
        self.file_version = ""
        self.to_dict()

    def open_file(self): #this functions opens a file from the title if it exists and otherwise searches online
        print("LOOKING FOR EXISTING FILE")
        file_exists = os.path.isfile( #see if the file exists
            "./tabs/" + self.artist.replace("%20", "_") + "_" + self.title.replace("%20", "_") + ".txt")
        correct_version = True
        if file_exists:
            print("FILE FOUND")
            File = open("./tabs/" + self.artist.replace("%20", "_") + "_" + self.title.replace("%20", "_") + ".txt",
                        "r")
            text = File.read()
            File.close()
            self.data = json.loads(text)  # load the textfile into the dictionary data
            self.from_dict()  # load the dictionary data into the variables
            if self.file_version != self.script_version:
                self.clear_file()
                correct_version = False
                print("UPDATING TO NEWER VERSION")
        if (not file_exists) or (not correct_version): #if the file doesn't exist go and soarch the file
            print("FILE NOT FOUND")
            tabs, azlyrics = search_lyrics(self.artist, self.title) #searches on the internet for the tabs and azlyrics
            if tabs != "no data found": #if tabs are found, fill in the instance variables
                self.tabs = tabs
                self.synced = False #defaulty synced is false
                tabslines = seperate_lines(tabs, tabslines=True)
                for line in tabslines:
                    self.tabslines.append({}) #append an empty dictionary to the tabslines, for each tabslines this dictionary keeps track of the raw text, if it is a keyword, and if it is lyrics or chords. #todo add a dictionary item + logic for actual 6 lines tabs
                    self.tabslines[-1]['text'] = line
                    self.tabslines[-1]['keyword'] = False
                    if ("chorus" in line.lower()) or ("verse" in line.lower()) or ("intro" in line.lower()) or ( #check for keywords in the line
                            "outro" in line.lower()):
                        self.tabslines[-1]['keyword'] = True
                    self.tabslines[-1]['lyrics'] = False
                    self.tabslines[-1]['chords'] = False
                self.azlyrics = azlyrics
                self.has_azlyrics = True
                self.has_tabs = True
                if azlyrics == "no azlyrics found":
                    self.has_azlyrics = False
                if tabs == "no data found":
                    self.has_tabs = False
                if self.has_tabs and self.has_azlyrics:
                    self.compare_lyrics() #compare lyrics will analyze the tabslines for which lines are lyrics and which line is chords. this uses azlyrics as masterfile and marks any tabslines as lyrics when it is similar enough
                    self.group_on_keywords() #assign a group to every line by extending keywords to all following lines until the next keyword
                    self.sort_lyrics() #use all the tabslines to fill the 'chorded_lyrics', this is a group of lyrics chords belonging to this line. These can be printed to the screen as one single group.


    def close_file(self):
        self.to_dict() #load the variables into the dictionary
        text = json.dumps(self.data) #convert to json string
        file = open("./tabs/" + self.artist.replace("%20", "_") + "_" + self.title.replace("%20", "_") + ".txt", "w")
        file.write(text) #write file
        file.close()

    def compare_lyrics(self):
        i = 0
        for tabline in self.tabslines:
            line1 = tabline['text'].lower()  # line of text coming from the
            line1 = normalize_line(line1)
            matched = False
            if line1 != "" and len(line1) > 5:
                j = 0
                for line2 in self.azlyrics[0:-2]:  # loop over all the lines in azlyrics
                    line2 = line2.lower()
                    line2 = normalize_line(line2)
                    j += 1
                    line2app = self.azlyrics[j].lower()  # check the next line as well, incase the lyrics in tabslines correspond with 2 lines of text in azlyrics
                    line2app = normalize_line(line2app)
                    similarity = similar(line1,line2)  # check similarity, so that "blowin'" and "blowing" can still be matched
                    ind = line2.find(line1[0:4])
                    partlinesimilarity = similar(line1, line2[ind:ind + len(line1)])
                    if partlinesimilarity > 0.5 or similarity > 0.5:  # if tabslines text is only part of the azlyrics than it matches as well or if the similarity is similar. TODO check if part of line2 is similar enough?
                        tabline['lyrics'] = True
                        if not self.tabslines[i - 1]['lyrics']:
                            self.tabslines[i - 1]['chords'] = True
                        matched = True
                        break
                    line2 = line2 + line2app
                    similarity = similar(line1,
                                         line2)  # check now if 2 lines of azlyrics are similar enough with one line of tabslines
                    ind = line2.find(line1[0:4])
                    partlinesimilarity = similar(line1, line2[ind:ind + len(line1)])
                    if partlinesimilarity > 0.5 or similarity > 0.5:
                        tabline['lyrics'] = True
                        if not self.tabslines[i - 1]['lyrics']:
                            self.tabslines[i - 1]['chords'] = True
                        matched = True
                        # self.azlyrics[j] = " "
                        break

            i += 1
        print("done with comparing lyrics")

    def group_on_keywords(self):
        group = "start"
        in_intro = False
        passed_intro = False
        for line in self.tabslines: #go over each tabslines, when a new keyword is seen, assing all following lines the same keyword
            if line['keyword']:
                group = line['text']
                line['lyrics'] = True
                if "intro" in group.lower():
                    in_intro = True
            if in_intro:
                if passed_intro and line['text'] == "":
                    group = "verse"
                elif line['text'] != "":
                    passed_intro = True

            line['group'] = group

    def sort_lyrics(self):
        i = 0
        introtext = ""
        starttext = ""
        for line in self.tabslines:
            if "intro" in line['group'].lower(): #if the tabslines are part of the intro, assing them regardless if they're lyrics or not.
                introtext += line['text'] + "\n"
            elif "start" in line['group'].lower():
                starttext += line['text'] + "\n"
            else:
                if line['lyrics']: #if the tabslines is past the lyrics, only group them if this line is a lyrics. Assign the previous line for chords
                    self.chorded_lyrics.append({})
                    self.chorded_lyrics[-1]['lyrics'] = line['text'] #assign lyrics from tabslines into chorded_lyrics
                    if self.tabslines[i - 1]['chords']: #if the previous line are chords, add them as well
                        self.chorded_lyrics[-1]['chords'] = self.tabslines[i - 1]['text']
                    else:
                        self.chorded_lyrics[-1]['chords'] = ""
                    self.chorded_lyrics[-1]['start'] = 0 #start and stop are used for syncing information.
                    self.chorded_lyrics[-1]['stop'] = 0
                    self.chorded_lyrics[-1]['group'] = line['group']
            i += 1
        introdict = {}
        introdict['lyrics'] = introtext
        introdict['chords'] = ""
        introdict['start'] = 0
        introdict['end'] = 0
        introdict['group'] = "intro"
        self.chorded_lyrics.insert(0,introdict)

        startdict = {}
        startdict['lyrics'] = starttext
        startdict['chords'] = ""
        startdict['start'] = 0
        startdict['end'] = 0
        startdict['group'] = "start"
        self.chorded_lyrics.insert(0,startdict)


def normalize_line(str):
    str = str.replace("%20", "")
    str = str.replace("'", "")
    str = str.replace(" ", "")
    str = str.replace(",", "")
    str = str.replace(".", "")
    str = str.replace("\r", "")
    str = str.replace("(", "")
    str = str.replace(")", "")
    return str


def format_lyrics(lyrics):
    formated_lyrics = "\n".join(lyrics)
    return formated_lyrics


def extract_lyrics(page):
    soup = BeautifulSoup(page, "html.parser")
    lyrics_tags = soup.find_all("div", attrs={"class": None, "id": None})
    lyrics = [tag.getText() for tag in lyrics_tags]
    return lyrics


def normalize_str(str):
    str = str.replace("%20", "")
    str = str.replace("\'", "")
    str = str.replace(".", "")
    str = str.replace("(", "")
    str = str.replace(")", "")
    str = str.lower()
    return str


class Azlyrics(object):

    def __init__(self, artist, music):
        self.artist = artist
        self.music = music

    def normalize_artist_music(self):
        return normalize_str(self.artist), normalize_str(self.music)

    def url(self):
        if not self.artist and not self.music:
            self.artist = "rickastley"
            self.music = "nevergonnagiveyouup"
        url = "http://azlyrics.com/lyrics/{}/{}.html".format(*self.normalize_artist_music())
        print(url)
        return url

    def get_page(self):
        try:
            page = urllib.request.urlopen(self.url())
            return page.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("Music not found")
                page = "no azlyrics found"
                return page

    def format_title(self):
        return "{} by {}".format(self.music.title(), self.artist.title())

    def get_lyrics(self):
        page = self.get_page()
        if page == "no azlyrics found":
            lyrics = page
        else:
            lyrics = extract_lyrics(page)
        return lyrics


def main():
    account_info = json.loads(open("./account_info.txt").read())
    username = account_info['username']
    scope = account_info['scope']
    clientid = account_info['clientid']
    clientsecret = account_info['clientsecret']
    redirect_uri = account_info['redirect_uri']

    artist_old = ""
    artist = ""
    title_old = ""
    title = ""

    while True:
        title, artist, t0 = get_current_song(username, clientid, clientsecret, redirect_uri)
        artist = artist.replace(" ", "%20")
        title = title.replace(" ", "%20")

        if (artist != artist_old) or (title != title_old):
            print(("-" * 100 + "\n") * 3)
            datafile = file(artist, title, version)
            datafile.open_file()
            print_tabs(datafile)
            datafile.close_file()
            artist_old = artist
            title_old = title

        else:
            time.sleep(5)

version = '2019-06-01'
if __name__ == "__main__":
    main()
