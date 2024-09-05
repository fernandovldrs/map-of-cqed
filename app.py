from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from scholarly import scholarly
import json
import os
import requests
from datetime import datetime, timedelta


app = Flask(__name__)
CORS(app)

# Path to the JSON file
GROUPS_FILE_PATH = 'research_groups.json'
PUBS_FILE_PATH = 'publications.json'

# Load data from the JSON file
def load_data(path):
    if os.path.exists(path):
        with open(path, 'r') as file:
            return json.load(file)
    return []

# Save data to JSON file
def save_data(path, data):
    with open(path, 'w') as file:
        json.dump(data, file, indent=4)

# Initialize the research groups variable
research_groups = load_data(GROUPS_FILE_PATH)
all_publications = load_data(PUBS_FILE_PATH)

def parse_date(date_str):
    """Helper function to parse dates in multiple formats."""
    for fmt in ('%d-%m-%Y', '%m-%Y', '%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # If the date doesn't match any format, return None or a default value
    return None

def recent_publications(publication_ids, all_publications):
    """Count publications from the past two months based on a list of publication IDs."""
    current_date = datetime.now()
    two_months_ago = current_date - timedelta(days=60)

    recent_publication_ids = []
    
    for pub in all_publications:
        if pub['id'] in publication_ids:
            pub_date = parse_date(pub['date'])
            if pub_date and pub_date > two_months_ago:
                recent_publication_ids.append(pub['id'])

    return recent_publication_ids

# Function to retrieve DOI using CrossRef
def get_doi_and_date(title):
    url = "https://api.crossref.org/works"
    params = {'query.bibliographic': title, 'rows': 1}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'message' in data:
            if 'items' in data['message'] and len(data['message']['items']) > 0:
                doi = data['message']['items'][0].get('DOI', None)

            print(title)
            print(data['message']['items'][0].keys())
            try:
                pub_date_parts = data['message']['items'][0]['published']['date-parts'][0]
                # Assign year, month, and day based on the available data
                pub_year = str(pub_date_parts[0])
                pub_month = str(pub_date_parts[1]) + '-' if len(pub_date_parts) > 1 else ""
                pub_day = str(pub_date_parts[2]) + '-' if len(pub_date_parts) > 2 else ""
                pub_date =  pub_day +  pub_month + pub_year
            except: 
                pub_date = None
            
        return title, doi, pub_date
    return None

def get_scholar_pub_year(publication):
    if 'pub_year' in publication['bib']:
        return int(publication['bib']['pub_year'])
    else:
        return float('-inf')  # Treat publications with missing dates as the oldest

@app.route('/api/publications', methods=['GET'])
def get_publications():
    group_name = request.args.get('group_name')
    # Search for the group by name
    author_publications = []
    for group in research_groups:
        if group['group_name'] == group_name:
            publications = group.get('paper_identifiers', [])
            break

    print(len(author_publications))
    return jsonify(publications=author_publications)

@app.route('/api/research_groups', methods=['GET'])
def get_research_groups():
    return jsonify({"research_groups": research_groups})

@app.route('/api/scholar_search', methods=['POST'])
def scholar_search():
    data = request.json
    global all_publications
    pi_name = data['piName']
    search_query = scholarly.search_author(pi_name)
    author = next(search_query)
    author = scholarly.fill(author)

    # Sort publications by date and select 30 latest
    # sorted_author_publications = sorted(author['publications'], key=get_scholar_pub_year, reverse=True)[:30]

    publications_all_titles = [pub["title"] for pub in all_publications] 
    prev_publications = []
    new_publications = []
    
    for pub in author['publications'][:30]:
        title = pub['bib']['title']
        # Check if already exists in database
        if title in publications_all_titles:
            # Retrieve from publications
            prev_pub = all_publications[publications_all_titles.index(title)]
            prev_publications.append(prev_pub)
            continue
        else:
            pub_title, pub_doi, pub_date = get_doi_and_date(title)
            if pub_date is None:
                pub_date = str(pub['bib']['pub_year'])
        new_publication = {
            "title": pub_title,
            "id": pub_doi,
            "date": pub_date,
        }
        new_publications.append(new_publication)
    
    all_publications += new_publications
    save_data(PUBS_FILE_PATH, all_publications)
     
    return jsonify({"publications": new_publications + prev_publications})

@app.route('/api/group_publications_search', methods=['POST'])
def group_publications_search():
    data = request.json
    group_name = data['groupname']
    
    # Get the list of publication IDs for the group
    group_name_list = [group["group_name"] for group in research_groups]
    group_indx = group_name_list.index(group_name)
    group_pub_ids_list = research_groups[group_indx]["paper_identifiers"]
    group_new_pub_ids_list = research_groups[group_indx]["new_paper_identifiers"]
    
    # Filter publications based on these IDs
    group_new_publication_list = []
    group_previous_publication_list = []
    for pub in all_publications:
        if pub["id"] in group_pub_ids_list:
            if pub["id"] in group_new_pub_ids_list:
                group_new_publication_list.append(pub)
            else:
                group_previous_publication_list.append(pub)


    # group_publication_list = [pub for pub in all_publications if pub["id"] in group_pub_ids_list]
    
    # Sort publications by date, accounting for multiple formats
    group_new_publication_list.sort(
        key=lambda pub: parse_date(pub['date']) if parse_date(pub['date']) else datetime.min,
        reverse=True
    )
    
    # Sort publications by date, accounting for multiple formats
    group_previous_publication_list.sort(
        key=lambda pub: parse_date(pub['date']) if parse_date(pub['date']) else datetime.min,
        reverse=True
    )
    print(group_previous_publication_list, group_new_publication_list)

    ## group_publication_list
    # Return the sorted publication list as JSON
    return jsonify({"new_publications": group_new_publication_list, "previous_publications": group_previous_publication_list})

@app.route('/api/submit_group', methods=['POST'])
def submit_group():
    data = request.json
    recent_pubs = recent_publications(data['publications'], all_publications)
    new_group = {
        "group_name": data['groupName'],
        "group_site": data['groupSite'],
        "pi_name": data['piName'],
        "institution_name": data['instituteName'],
        "location": {
            "latitude": float(data['locationLat']),
            "longitude": float(data['locationLon'])
        },
        "paper_identifiers": data['publications'],
        "new_paper_identifiers": recent_pubs,
        "new_pub_count": len(recent_pubs)
    }
    group_names =  [group["group_name"] for group in research_groups]
    # If group is already in the database, replace with new data
    if new_group["group_name"] in group_names:
        research_groups[group_names.index(new_group["group_name"])] = new_group
    else:
        research_groups.append(new_group)
    save_data(GROUPS_FILE_PATH, research_groups)  # Save the updated list to the JSON file
    return jsonify({"message": "Research group added successfully!"})

# if __name__ == '__main__':
#     app.run(debug=True)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
