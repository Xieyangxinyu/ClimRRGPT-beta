from geopy.distance import geodesic
import numpy as np
import pandas as pd
import requests

def format_apa_citation(publication):
    """
    Formats a publication dictionary into an APA style citation, handling empty entries appropriately.
    """
    authors = publication.get('Authors', '')
    year = publication.get('Published_Date_or_Year', 'n.d.')
    title = publication.get('Published_Title', '')
    journal = publication.get('Journal_Name', '')
    volume = publication.get('Volume', '')
    issue = publication.get('Issue', '')
    pages = publication.get('Pages', '')
    doi = publication.get('DOI', '')

    # Formatting the authors for APA style
    authors_list = authors.split(',')
    if len(authors_list) > 2:
        apa_authors = f"{authors_list[0]} et al."
    elif authors:
        apa_authors = ' & '.join(authors_list)
    else:
        apa_authors = ''

    # Constructing the citation
    citation_parts = [apa_authors, f"({year})", title]
    if journal:
        citation_parts.append(journal)
        if volume:
            citation_parts.append(f"{volume}({issue})" if issue else volume)
        if pages:
            citation_parts.append(pages)
    if doi:
        citation_parts.append(doi)

    citation = ', '.join(part for part in citation_parts if part)
    return citation

def extract_abstract_and_citation(publications):
    """
    Extracts publications from the given file and returns a list of dictionaries 
    containing the abstract (if available), APA style citation, and DOI (if available) for each publication.
    """
    publication_details = []

    for publication in publications:
        abstract = publication.get('Abstract', '')
        doi = publication.get('DOI', '')

        if not abstract:
            if doi:
                abstract = f"Abstract not found; but you may try DOI: {doi}."
            else:
                abstract = "Abstract not found."

        apa_citation = format_apa_citation(publication)
        publication_details.append({'Paper': apa_citation, 'Abstract': abstract})

    return publication_details


def get_publications(url):
    '''
    Downloads the file from the given URL and parses it to extract the publication details.
    Returns a list of dictionaries containing the publication details.
    
    :param url: URL of the file to download
    :return: List of dictionaries containing the publication details
    '''

    # Attempting to download and read the content of the file
    try:
        response = requests.get(url)
        # Checking if the request was successful
        if response.status_code == 200:
            data_content = response.text
        else:
            data_content = f"Failed to download the data. Status code: {response.status_code}"
    except Exception as e:
        data_content = f"An error occurred: {e}"


    try:
        file_contents = data_content

        # Splitting the file content into lines for easier processing
        lines = file_contents.split('\n')

        # Flag to indicate if we are currently reading a publication block
        in_publication_block = False

        # List to store all publication dictionaries
        publications = []

        # Temporary dictionary to hold the current publication's details
        current_publication = {}
        abstract_flag = False

        # Iterating over each line
        for line in lines:
            # Check for the start of a publication block
            if line.strip() == '# Publication':
                in_publication_block = True
                current_publication = {}
                abstract_flag = False
            elif line.strip() == '#--------------------':
                # End of a publication block
                if in_publication_block and current_publication:
                    publications.append(current_publication)
                    current_publication = {}
                in_publication_block = False
            elif in_publication_block:
                # Process the publication details
                if line.startswith('#   Abstract: '):
                    abstract_flag = True
                    current_publication['Abstract'] = line.split('#   Abstract: ', 1)[1]
                elif abstract_flag and line != '#':
                    # Continue appending to the abstract
                    current_publication['Abstract'] += line.split('# ', 1)[1]
                elif ': ' in line and not abstract_flag:
                    key, value = line.split(': ', 1)
                    key = key.replace('#', '').strip()
                    current_publication[key] = value.strip()

        # Ensuring the last publication is added if the file doesn't end with the separator
        if in_publication_block and current_publication:
            publications.append(current_publication)

    except Exception as e:
        publications = f"An error occurred: {e}"

    # remove duplicates
    publications = np.unique(publications)
    
    publication_details = extract_abstract_and_citation(publications)
    return publication_details


# Re-defining the functions and re-loading the data as the code execution state was reset

def find_closest_fire_histories_within_50_miles(lat, lon, messages=None):
    """
    Finds the 3 closest fire history records to the given latitude and longitude within 50 miles.
    Returns a list of dictionaries of the fire history data, up to a maximum of max_results records.
    """
    fire_data = pd.read_csv('./data/s1-NAFSS.csv')
    max_distance_km = 50 * 1.60934  # 50 miles in kilometers
    distances = fire_data.apply(lambda row: geodesic((lat, lon), (row['latitude'], row['longitude'])).kilometers, axis=1)
    fire_data['distance'] = distances
    nearby_records = fire_data[fire_data['distance'] <= max_distance_km].sort_values(by='distance')[:3]

    aggregation_functions = {
        'siteName': list,
        'latitude': list,
        'longitude': list,
        'link_to_data': list,
        'link_to_metadata': list
    }
    combined_records = nearby_records.groupby('reference').agg(aggregation_functions).reset_index().to_dict('records')

    for record in combined_records:
        url = record['link_to_metadata']
        # if url is a list, take the first one
        if isinstance(url, list):
            url = url[0]
        record['publications'] = get_publications(url)

    # if no records found, return a message
    if not combined_records:
        return "No fire history records found within 50 miles. This only means that we do not find research data from NOAA’s fire history and paleoclimate services. I will let the user know and try to search for other data sources such as FWI and recent fire incidents."
    else:
        return str(combined_records) + "\n----------\nThis data is extracted from the International Multiproxy Paleofire Database (IMPD), an archive of fire history data derived from natural proxies such as tree scars and charcoal and sediment records. You can access the website: https://www.ncei.noaa.gov/products/paleoclimatology/fire-history\n----------\n\nDiscuss the research about the fire history of these sites and make sure to include all the links to data and metadata. Also include a 'References' section at the end of your answer.\n\n**Example**:\n As for the long term fire history, a study by Guiterman et al. (2015) used dendroecological methods (tree-ring analysis) to reconstruct a high-severity fire that occurred in 1993 in a ponderosa pine-dominated forest. The historical fire regime (1625-1871) at this site was characterized by frequent, low-severity fires, usually in dry years following wet years. Notably, fires ceased after 1871, coinciding with increased livestock grazing in the region.\n\n References:\nGuiterman et al., (2015), Dendroecological methods for reconstructing high-severity fire in pine-oak forests, Tree-Ring Research, 71(2), 67-77, 10.3959/1536-1098-71.2.67\n"
    

if __name__ == '__main__':
    # Testing the function
    print(find_closest_fire_histories_within_50_miles(34.0356, -118.5156))