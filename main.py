import re
import argparse
import requests
import json
import csv
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from bs4 import BeautifulSoup

# extract the ID from the query params
def get_opportunity_id(url):
    parsed = urlparse(url)
    opp_id = parse_qs(parsed.query).get('oppId')
    
    if opp_id:
        raw_id = opp_id[0]
        clean_id = re.sub(r'\D', '', raw_id)
        return clean_id if clean_id else None
        
    return None

# fetch data from the new grants.gov v1 API
def fetch_api_data(opp_id):
    endpoint = "https://api.grants.gov/v1/api/fetchOpportunity"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Content-Type': 'application/json'
    }
    
    try:
        res = requests.post(endpoint, headers=headers, json={"opportunityId": int(opp_id)}, timeout=15)
        res.raise_for_status() 
        data = res.json()
        
        # the api wraps everything in a 'data' object sometimes
        if "data" in data:
            return data["data"]
        return data
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return None

# helper to strip weird html tags out of the descriptions
def strip_html(text):
    if not text or str(text).strip() == "":
        return "N/A"
    soup = BeautifulSoup(str(text), "html.parser")
    return soup.get_text(separator=" ", strip=True)

# grants.gov uses a few different date formats, so we try a few
def parse_date(date_string):
    if not date_string or str(date_string).strip().lower() in ["n/a", "none", "null"]:
        return "N/A"
    
    # drop the timestamp if it exists
    clean_str = str(date_string).split(' 12:00:00')[0].strip()
    
    formats_to_try = ['%m/%d/%Y', '%b %d, %Y', '%b %d %Y', '%Y-%m-%d']
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(clean_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    return str(date_string)

# simple keyword matching for the tagging requirement
def generate_tags(text):
    text = str(text).lower()
    tags = []
    
    if any(w in text for w in ["health", "medical", "disease", "clinical"]):
        tags.append("Healthcare & Medicine")
    if any(w in text for w in ["research", "science", "laboratory", "study"]):
        tags.append("Scientific Research")
    if any(w in text for w in ["education", "training", "student", "educator", "university"]):
        tags.append("Education & Training")
    if any(w in text for w in ["technology", "software", "computer", "data"]):
        tags.append("Technology & Engineering")
    if any(w in text for w in ["environment", "climate", "energy"]):
        tags.append("Environment & Energy")
    if any(w in text for w in ["language", "english", "culture", "art"]):
        tags.append("Arts & Humanities")
        
    if len(tags) == 0:
        tags.append("General / Uncategorized")
        
    return tags

def main():
    parser = argparse.ArgumentParser(description="Extract FOA data from Grants.gov")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--out_dir", required=True, help="Output directory path")
    args = parser.parse_args()

    print(f"Starting extraction for: {args.url}")
    
    opp_id = get_opportunity_id(args.url)
    if not opp_id:
        print("Failed to find oppId in the URL.")
        return

    api_data = fetch_api_data(opp_id)
    if not api_data:
        print("Failed to retrieve data from Grants.gov.")
        return

    # nested data hunt - sometimes info is in root, sometimes in synopsis
    details = api_data.get("synopsis", {})
    if not details:
        details = api_data.get("forecast", {})

    def get_field(keys):
        for k in keys:
            if k in details and details[k]: return details[k]
            if k in api_data and api_data[k]: return api_data[k]
        return None

    raw_description = get_field(["synopsisDesc", "description", "forecastDesc"])
    clean_description = strip_html(raw_description)
    title = strip_html(get_field(["opportunityTitle", "title"]))
    
    # build the final dictionary mapping
    foa_record = {
        "FOA_ID": str(get_field(["opportunityNumber", "opportunityId"]) or opp_id),
        "Title": title,
        "Agency": str(get_field(["owningAgencyCode", "agencyCode", "agencyName"]) or "N/A"),
        "Open_Date": parse_date(get_field(["postingDate", "postDate"])),
        "Close_Date": parse_date(get_field(["responseDate", "closeDate", "closingDate"])),
        "Eligibility_Text": strip_html(get_field(["applicantEligibilityDesc", "eligibilityDesc", "additionalInformationOnEligibility"])),
        "Program_Description": clean_description,
        "Award_Range": str(get_field(["awardCeiling", "estimatedTotalProgramFunding"]) or "N/A"),
        "Source_URL": args.url,
        "Semantic_Tags": generate_tags(clean_description + " " + title)
    }

    # make sure the output folder exists
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
    
    # save to json
    json_file = os.path.join(args.out_dir, "foa.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump([foa_record], f, indent=4)
        
    # save to csv
    csv_file = os.path.join(args.out_dir, "foa.csv")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        csv_row = foa_record.copy()
        # join lists into a string for csv compatibility
        csv_row["Semantic_Tags"] = ", ".join(csv_row["Semantic_Tags"])
        
        writer = csv.DictWriter(f, fieldnames=csv_row.keys())
        writer.writeheader()
        writer.writerow(csv_row)

    print(f"Done. Saved files to {args.out_dir}")

if __name__ == "__main__":
    main()
    