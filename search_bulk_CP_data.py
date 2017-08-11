from shutil import copyfile
import os
from bs4 import BeautifulSoup
import warnings
import json
import requests

def get_dir(dir="./../scotus_CL"):
    return dir

def get_save_dir(dir="./../Parser_Cases/search_results"):
    os.makedirs(dir, exist_ok=True)
    return dir

def main():
    #print("start")
    parameters={}
    parameters['year']=2004
    dir = get_dir()
    save_dir = get_save_dir()

    user = "Reidmwhitaker"
    password = "courtlistenerwhitaker"

    for root, dirs, files in os.walk(dir):
        for file in files:

            warnings.filterwarnings('ignore',
                                    message=r".*looks like a URL. Beautiful Soup is not an HTTP client. You should probably.*")
            data = open(os.path.join(root, file)).read()
            data = json.loads(data)
            cluster = BeautifulSoup(data['cluster'], 'html.parser').text.replace("http://", "https://")

            cluster_response = requests.get(cluster, auth=(user, password))
            cluster_json = cluster_response.json()
            try:
                cluster_json['date_filed']
            except:
                pass
            else:
                year = cluster_json['date_filed'][0-3]

            if year==parameters['year']:
                copyfile(os.path.join(root,file), save_dir + file)

if __name__ == "__main__":
    main()