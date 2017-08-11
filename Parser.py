#Parses legal opinions and documents to JSON files with metadata and raw opinion text
import os
from bs4 import BeautifulSoup
import json
import re
import warnings
import requests
import nltk
from requests.auth import HTTPBasicAuth

#determines how a document should be parsed and send the data to the appropriate parser
#Currently supports .xml files from the Library Innovation Lab's Caselaw Access Project
#and .json files from CourtListener's API
def parse(data):
    if 'HLS-CASELAW-CASEXML' in data:
        parse_CAP(data)
    if "http://www.courtlistener.com/api/rest/v3" in data:
        parse_CL(data)

#todo: SHould be ok -- Note footnote numbering may not be seperated from the first word of the footnote. May cause issues if footnote is solely a citation
#todo: recusals!
#todo: joinings & seperate opinions ... looks for need to see how consistently it works
#todo: check percuriam authoriships
def parse_CAP(data):
    #todo: Currently unused
    def try_add_2_json(json_2_b,name,tag_to_try):
        try:
            tag_to_try
        except:
            pass
        else:
            json_2_b[name]=tag_to_try
        return json_2_b

    data = re.sub(r'(\D)(\u00ad)(\D)', r'\1\3',data)
    data = re.sub(r'(\D)(\-)(\D)', r'\1\3',data)
    data = re.sub(r'\u2019',"'",data)
    data = re.sub(r'\u201c', '"', data)
    data = re.sub(r'\u201d', '"', data)
    soup = BeautifulSoup(data, "xml")
    json_2_b={}
    case_id = soup.case['caseid']
    json_2_b['id'] = case_id
    json_2_b['court']=soup.court.string
    json_2_b['jurisdiction']=soup.court['jurisdiction']
    json_2_b['docket_no']=soup.docketnumber.string
    json_2_b['decision_date']=soup.decisiondate.string
    try:
        soup.otherdate.string
    except:
        pass
    else:
        json_2_b['other_date']=soup.otherdate.string
    count_cite = 1
    for tag in soup.find_all('citation'):
        json_2_b['citation_' + str(count_cite)] = tag.string
        json_2_b['citation_category_' + str(count_cite)] = tag['category']
        json_2_b['citation_type_' + str(count_cite)] = tag['type']
        count_cite = count_cite + 1
    json_2_b['parties']=soup.parties.string
    name_tag = soup.find('name')
    json_2_b['case_name'] = name_tag.string
    case_name_short = name_tag['abbreviation']
    case_name_short = case_name_short.replace("/","--")
    json_2_b['case_name_short'] = case_name_short
    count_attorneys = 1
    #Collect attorney information
    for tag in soup.find_all('attorneys'):
        json_2_b['attorney_'+str(count_attorneys)] = tag.string
        count_attorneys = count_attorneys + 1
    #Collect opinion text and authors for each opinion
    count_opinions = 1
    for tag in soup.find_all('opinion'):
        json_2_b['opinion_text_' + str(count_opinions)] = ""
        for p_tag in tag.find_all('p'):
            if p_tag.string is not None:
                json_2_b['opinion_text_' + str(count_opinions)] = json_2_b['opinion_text_' + str(
                    count_opinions)] + " " + p_tag.string
            else:
                for string in p_tag.stripped_strings:
                    json_2_b['opinion_text_' + str(count_opinions)] = json_2_b['opinion_text_' + str(
                        count_opinions)] + " " + string
        json_2_b['opinion_type_' + str(count_opinions)] = tag['type']
        #Get opinion author information
        try:
            tag.author.string
        except:
            if re.match(r'(?:\s*Opinion\sof\sthe\sCourt.)|(?:\s*Order\sof\sthe\sCourt)',
                        json_2_b['opinion_text_' + str(count_opinions)], re.IGNORECASE):
                json_2_b['opinion_' + str(count_opinions)+ "_author"] = "per curium"
            try:
                json_2_b['opinion_' + str(count_opinions) + "_author"]
            except:
                pass
            else:
                if json_2_b['opinion_' + str(count_opinions)+ "_author"] is None:
                    json_2_b['opinion_' + str(count_opinions)+ "_author"] = "per curium"
        else:
            json_2_b['opinion_' + str(count_opinions)+ "_author"] = tag.author.string
        count_opinions = count_opinions + 1
    m = 1
    #Finding joining justices
    while m < count_opinions:
        join_count = 1
        matches = re.findall(r'JUSTICE\s(\w+)\sjoins|(?:Chief\sJustice\s(\w+?)\sand\s)?(?:Justices\s(\w+)\,\s)?'
                             r'(?:(\w+)\,\s)?(?:(\w+)\,\s)?(?:(\w+)\,\s)?(?:(\w+)\,?\sand\s)?(\w+?)\sconcurred',
                             json_2_b['opinion_text_' + str(m)],re.IGNORECASE)
        if matches:
            for match in matches:
                for group in match:
                    if group != "" and group != "specially":
                        json_2_b['opinion_' + str(m) + '_joining_' + str(join_count)] = group
                        #print(json_2_b['opinion_' + str(m) + '_joining_' + str(join_count)])
                        join_count = join_count + 1
        #matches_2 = re.findall(r'JUSTICE\s([a-zA-Z]+)\sjoins\sin\sthis',json_2_b['opinion_text_' + str(m)],re.IGNORECASE)
        #if matches_2:
        #    for match in matches_2:
        #        json_2_b['opinion_' + str(m) + '_joining_' + str(join_count)] = match
        #        join_count + 1
        m = m+1

    full_text = ""
    k = 1
    while k < count_opinions:
        full_text = full_text + json_2_b['opinion_text_' + str(k)]
        k = k+1

    json_2_b['full_opinion_text']=full_text
    json_2_b['length']=len(nltk.word_tokenize(full_text))

    json_out = json.dumps(json_2_b, indent=4, separators=(',', ': '))
    out_dir = get_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    doc = open(out_dir + case_id + "_" + case_name_short + ".json", 'w')
    doc.write(json_out)
    doc.close()

def parse_CL(json_CL):
    #todo: fill out all available and relevant metadata
    user = "Reidmwhitaker"
    password = "courtlistenerwhitaker"

    warnings.filterwarnings('ignore',
                            message=r".*looks like a URL. Beautiful Soup is not an HTTP client. You should probably.*")
    data = json.loads(json_CL)
    cluster = BeautifulSoup(data['cluster'], 'html.parser').text.replace("http://","https://")
    id = re.match(r"https://www.courtlistener.com/api/rest/v3/clusters/(\d+)", cluster)
    case_id=id.group(1)

    absolute = BeautifulSoup(data['absolute_url'], 'html.parser').text
    name_match = re.match(r"/opinion/(\d+)/(.*)/", absolute)
    case_name = name_match.group(2)

    cluster_response = requests.get(cluster, auth=(user,password))
    cluster_json=cluster_response.json()
    #print(cluster_json)

    try:
        BeautifulSoup(data['author'], 'html.parser').text
    except:
        pass
    else:
        author_respose = requests.get(BeautifulSoup(data['author'], 'html.parser').text.replace("http://","https://"),auth=(user,password))
        author_json=author_respose.json()

    if data['html'] != "":
        text = BeautifulSoup(data['html'],'html.parser')
    #todo: fix parsing of decisions without html entries
    else:
        text = BeautifulSoup(data['html_with_citations'], 'html.parser')

    cites = []
    #todo:fix get citations
    for tag in text.find_all('p', class_='case_cite'):
        cites.append(tag.text)

    reduced_soup = text.find_all('div', class_="num")
    opinion_text = ""
    for tag in reduced_soup:
        opinion_text_soup = tag.find_all('p', class_="indent")
        for tag in opinion_text_soup:
        #Note, for speed gains you can directly prettify the tags here,
        #  but it leaves formatting tags in the final version which may cause prblems
            for string in tag.stripped_strings:
                opinion_text = opinion_text + " " + string

    # todo: fix footnote parsing...make sure linked footnotes are present
    footnotes = text.find_all('div', class_="footnote", id=re.compile("^fn\d+"))
    for tag in footnotes:
        for string in tag.stripped_strings:
            opinion_text = opinion_text + " " + string

    json_2_b = {}
    json_2_b['id']=case_id
    json_2_b['case_name'] = cluster_json['case_name']
    json_2_b['case_name_short'] = cluster_json['case_name_short']
    json_2_b['case_name_short'] = json_2_b['case_name_short'].replace("/","--")
    json_2_b['scdb_id'] = cluster_json['scdb_id']
    #todo:fix above
    try:
        cites[0]
    except:
        pass
    else:
        json_2_b['citation_1'] = cites[0]
    json_2_b['decision_date']=cluster_json['date_filed']
    try:
        author_json['slug']
    except:
        pass
    else:
        json_2_b['author'] = author_json['slug']

    json_2_b['opinion_text_1']=opinion_text
    json_out = json.dumps(json_2_b, indent=4, separators=(',', ': '))
    out_dir = get_out_dir()
    out_dir = out_dir + "CL/"
    os.makedirs(out_dir, exist_ok=True)
    doc = open(out_dir + case_id + "_" + json_2_b['case_name_short'] + ".json", 'w')
    doc.write(json_out)
    doc.close()

#Get the directory where the cases to be parsed are stored
def get_dir(dir="./../CAP_data"):
    #dir="./../Parser_Cases"
    return dir

def get_out_dir(dir="/Volumes/WD My Passport/LILProject/CAP_data_parsed/"):
    return dir

#todo: develop algorithm to split opinion clusters
def split_opinion(cluster, init_opinion):
    text_full_soup = init_opinion.text
    text = init_opinion.opinion_text
    split_text=text.split()

#Test parsing algorithm on *Daubert* as downloaded from CourtListener
def daubert_Test():
    json_data = open("./../Citator_Cases/Daubert.json").read()
    data = json.loads(json_data)
    cluster = BeautifulSoup(json.loads(json_data)['cluster'],'html.parser').text
    id = re.match(r"http://www.courtlistener.com/api/rest/v3/clusters/(\d+)", cluster)
    daubert = OpinionCluster(id=id.group(1))
    daubert_opinion = Opinion()
    daubert_opinion.text = BeautifulSoup(json.loads(json_data)['html'], 'html.parser')

    reduced_soup = daubert_opinion.text.find_all('div', class_="num")
    opinion_text = ""
    for tag in reduced_soup:
        opinion_text_soup = tag.find_all('p', class_="indent")
        for tag in opinion_text_soup:
            opinion_text = opinion_text + tag.prettify()
    footnotes = daubert_opinion.text.find_all('div', class_="footnote", id=re.compile("^fn\d+"))
    for tag in footnotes:
        opinion_text = opinion_text + tag.prettify()
    daubert_opinion.opinion_text = opinion_text

    doc = open('Daubert_final_reduced', 'w')
    doc.write(daubert_opinion.opinion_text)
    doc.close()

    cites = []
    for tag in daubert_opinion.text.find_all('p',class_='case_cite'):
        cites.append(tag.text)
    daubert.cite = cites

#Loads files and sends each file to the parser
def main():
    #print("start")
    dir = get_dir(dir="/Volumes/WD My Passport/LILProject/CAP_data")
    for root, dirs, files in os.walk(dir):
        for file in files:
            #For testing purposes
            #print(os.path.join(root,file))
            if file.endswith(".xml") or file.endswith(".json"):
                data = open(os.path.join(root,file)).read()
                parse(data)
    #print("end")

if __name__ == "__main__":
    main()