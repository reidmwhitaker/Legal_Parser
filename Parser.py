#Parses legal opinions and documents to JSON files with metadata and raw opinion text
import os
from bs4 import BeautifulSoup
import json

def parse(data):
    if "HLS-CASELAW-CASEXML" in data:
        parse_CAP(data)
    if '"resource_uri": http://www.courtlistener.com/api/rest/v3/opinions/' in data:
        parse_CL(data)

#todo: footnotes
#todo: recusials
#todo: joinings & seperate opinions
def parse_CAP(data):
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
    json_2_b['case_name_short'] = case_name_short
    count_attorneys = 1
    for tag in soup.find_all('attorneys'):
        json_2_b['attorney_'+str(count_attorneys)] = tag.string
        count_attorneys = count_attorneys + 1
    count_opinions = 1
    for tag in soup.find_all('opinion'):
        json_2_b['opinion_type_' + str(count_opinions)] = tag['type']
        json_2_b['author_' + str(count_opinions)] = tag.author.string
        json_2_b['opinion_text' + str(count_opinions)] = ""
        for p_tag in tag:
            json_2_b['opinion_text' + str(count_opinions)] = json_2_b['opinion_text' + str(count_opinions)] + " " + p_tag.string
        count_opinions = count_opinions + 1

    json_out = json.dumps(json_2_b, indent=4, separators=(',', ': '))
    os.makedirs("./../parsed_cases_CAP/", exist_ok=True)
    doc = open("./../parsed_cases_CAP/" + case_id + "_" + case_name_short + ".json", 'w')
    doc.write(json_out)
    doc.close()

def parse_CL(json_CL):
    #todo: fill out all available and relevant metadata
    warnings.filterwarnings('ignore',message=r".*looks like a URL. Beautiful Soup is not an HTTP client. You should probably.*")
    data = json.loads(json_CL)
    cluster = BeautifulSoup(data['cluster'], 'html.parser').text
    id = re.match(r"http://www.courtlistener.com/api/rest/v3/clusters/(\d+)", cluster)
    cluster = OpinionCluster(id=id.group(1))
    opinion = Opinion()

    absolute = BeautifulSoup(data['absolute_url'], 'html.parser').text
    name = re.match(r"/opinion/(\d+)/(.*)/", absolute)
    opinion.name = name.group(1) + "_" + name.group(2)

    opinion.text = BeautifulSoup(data['html'], 'html.parser')
    cluster.opinion = opinion
    if data['html'] != "":
        opinion.text = BeautifulSoup(data['html'],'html.parser')
    #todo: fix parsing of decisions without html entries
    else:
        opinion.text = BeautifulSoup(data['html_with_citations'], 'html.parser')

    cites = []
    for tag in opinion.text.find_all('p', class_='case_cite'):
        cites.append(tag.text)
    opinion.cite = cites

    reduced_soup = opinion.text.find_all('div', class_="num")
    opinion_text = ""
    for tag in reduced_soup:
        opinion_text_soup = tag.find_all('p', class_="indent")
        for tag in opinion_text_soup:
            opinion_text = opinion_text + tag.prettify()

    # todo: fix footnote parsing...make sure linked footnotes are present
    footnotes = opinion.text.find_all('div', class_="footnote", id=re.compile("^fn\d+"))
    for tag in footnotes:
        opinion_text = opinion_text + tag.prettify()
    opinion.opinion_text = opinion_text

    if opinion.opinion_text == "":
        warnings.warn(opinion.name + " failed to parse")
    else:
        os.makedirs("./parsed_cases/", exist_ok=True)
        doc = open("./parsed_cases/" + opinion.name + "_parsed", 'w')
        doc.write(opinion.opinion_text)
        doc.close()

def get_dir(dir="./../Parser_Cases"):
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

def main():
    print("start")
    dir = get_dir()
    for file in os.listdir(dir):
        data = open(dir + "/" + file).read()
        parse(data)
    print("end")

if __name__ == "__main__":
    main()