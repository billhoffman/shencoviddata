import sys
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import glob
from datetime import datetime
import email
from word2number import w2n
import pandas
from email import policy

class ShenCovidTracker:
    def __init__(self, url):
        self.newsurl = url
        self.headers = {'user-agent': 'Mozilla/5.0'
                        +' (Windows NT 10.0; Win64; x64)'+
                        ' AppleWebKit/537.36 (KHTML, like Gecko)'+
                        ' Chrome/86.0.4240.75 Safari/537.36'}
        self.covid_places = {
            'Transportation': "Transportation Department",
            'Information': "Information Department",
            'Koda':'Koda middle',
            'Skano':'Skano Elementary',
            'Cheerleading':'Cheerleading',
            'Gowana':'Gowana middle',
            'District':'District Office',
            'Chango':'Chango Elementary',
            'Shatekon':'Shatekon Elementary',
            'Orenda':'Orenda Elementary',
            'East':'High School East',
            'Orenda':'Orenda Elementary',
            'West':'High School West',
            'Transportation':'Transportation Department',
            'Skano': 'Skano Elementary',
            'Chango':'Chango Elementary',
            'Tesago': 'Tesago Elementary',
            'Karigon':'Karigon Elementary',
            'Okte':'Okte Elementary',
            'Acadia':'Acadia middle',
            'Tesago':'Tesago Elementary',
            'Arongen':'Arongen Elementary',
            'Okte':'Okte Elementary'}

    def download_news_data(self):
        self.links = []
        self.downloaded_dates = set()
        self.find_already_downloaded_dates()
        self.get_covid_links()
        self.load_covid_data()

    def find_already_downloaded_dates(self):
        # find all the .eml and .txt files we already have
        eml_files = glob.glob("data/*.eml")
        txt_files = glob.glob("data/*.txt")
        for f in eml_files:
            f = f.replace("data\\", "")
            self.downloaded_dates.add(f.split()[0])
        for f in txt_files:
            f = f.replace("data\\", "")
            self.downloaded_dates.add(f.split(".")[0])
        self.downloaded_dates.add("5_10_2021") # just don't want this one

    def download_link_to_file(self,link,fname, date):
        print("Downloading data from ",link)
        print("Creating ", fname)
        month = date.strftime("%B")
        day = date.strftime("%d")
        year = date.strftime("%Y")
        rsp = requests.get(link,headers=self.headers)
        soup = BeautifulSoup(rsp.content, 'html.parser')
        fout = open(fname, "w")
        fout.write(f'{month} {day}, {year}\n')
        for li in soup.find_all("b"):
            fout.write(li.text+"\n")
        fout.close()

    def load_covid_data(self):
        downloaded = False
        for l in self.links:
            if l[-1] == "/":
                l = l[:-1]
            s = l.split('/')[-1]
            if '-notification-of' in s:
                date = s.partition("-notification")[0]
                if("2021" in date):
                    continue
                date_object = datetime.strptime(date, "%m-%d-%y")
                date = date.replace("-","_")
                # if the date is not already downloaded then
                # download it now
                if not date in self.downloaded_dates:
                    self.download_link_to_file(l,
                                               "data/"+date+".txt",
                                               date_object)
                    downloaded = True
            else:
                print("ERROR: -notification-of not found in link ",s)
        if not downloaded:
            print("no new data on news site")

    def get_covid_links(self):
        rsp = requests.get('https://www.shenet.org/news/',headers=self.headers)
        soup = BeautifulSoup(rsp.content, 'html.parser')
        for li in soup.find_all("li"):
            if "Notification of Positive" in li.text:
                for a in li.find_all("a"):
                    self.links.append(a.get("href"))

    def plot(self):
        print(self.df)
        fig, ax = plt.subplots()
        self.df.plot(kind = 'bar',stacked=True, ax=ax)
        ax.set_xticklabels([x.strftime("%m-%d-%y") for x in self.df.index],
                           rotation=45)
        sys.stdout.flush()
        plt.show()

    def load_local_files(self):
        self.columns = []
        self.data = {}

        self.load_eml_files()
        self.load_txt_files()
        self.df = pandas.DataFrame(data=self.data, columns=self.columns,
                                   index=self.covid_places.values())
        self.df = self.df.reindex(sorted(self.df.columns), axis=1)
        self.df = self.df.transpose()

    def get_place_name(self, text):
        for key in self.covid_places.keys():
            if key in text:
                return self.covid_places[key]

    def load_eml_files(self):
        files = glob.glob("data/*.eml")
        for f in files:
            message = email.message_from_file(open(f), policy=policy.default)
            text = message.get_body(preferencelist=('html')).get_content()
            soup = BeautifulSoup(text, features="html.parser")
            para = soup.find_all("p")
            date = para[2].text
            if "Due" in date:
                date = para[3].text
            date = date.replace(u'\xa0', u' ')
            date = datetime.strptime(date, "%B %d, %Y")
            # add the date to the columns list
            self.columns.append(date)
            # map from place to number of cases init to 0
            daily_count ={}
            for key in self.covid_places.values():
                daily_count[key] = 0
            for li in soup.find_all("li"):
                text = li.text.replace("\n", "")
                place = self.get_place_name(text)
                words = li.text.split()
                first = words[0].lower()
                if first == "an":
                    count = 1
                else:
                    count = w2n.word_to_num(words[0])
                daily_count[place] = daily_count[place] + count
            self.data[date] = daily_count

    def load_txt_files(self):
        files = glob.glob("data/*.txt")
        for f in files:
            with open(f) as file:
                lines = file.readlines()
                lines = [line.rstrip() for line in lines]
            # find the date on the first line of the file
            date = lines[0]
            date = datetime.strptime(date, "%B %d, %Y")
            # add the date to the columns to create a new column
            self.columns.append(date)
            # initilize for the day
            daily_count ={}
            for key in self.covid_places.values():
                daily_count[key] = 0
            for line in lines[1:]:
                place_count = line.split(":")
                count_str = place_count[1].split()[0]
                count = int(count_str)
                place = self.get_place_name(line)
                daily_count[place] = daily_count[place] + count
            self.data[date] = daily_count

shen = ShenCovidTracker('https://www.shenet.org/news/')
shen.download_news_data()
shen.load_local_files()
shen.plot()
