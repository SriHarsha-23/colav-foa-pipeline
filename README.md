# CoLaV FOA Ingestion Pipeline

## Overview
This is a lightweight Python pipeline built for the CoLaV GSoC 2026 screening task. It ingests Funding Opportunity Announcements (FOAs) from Grants.gov, normalizes the extracted data, applies rule-based semantic tags, and exports the structured results to JSON and CSV formats.

## Setup & Installation
Ensure you have Python 3 installed. Navigate to the project directory and install the required dependencies (Requests and BeautifulSoup4):

`pip install -r requirements.txt`

## How to Run
The script runs via the command line and requires a target Grants.gov URL and an output directory. Here is the exact command to run the pipeline using the primary test URL:

`python main.py --url "https://www.grants.gov/web/grants/view-opportunity.html?oppId=351336" --out_dir ./out`

*Note: The script uses a regex parser to extract the oppId, so it is robust against variations in the URL format or accidental trailing characters.*

## Architecture & Engineering Decisions

### 1. Ingestion Strategy (API Bypass)
Initially, I considered standard web scraping. However, Grants.gov relies heavily on client-side JavaScript to render opportunity details, meaning a simple GET request returns an empty HTML shell. 

Instead of forcing a heavy browser automation tool like Selenium, I analyzed the network traffic and targeted the backend REST API directly. The script extracts the `oppId` from the provided URL and sends a POST request with a JSON payload. This approach is significantly faster, more reliable, and returns cleanly structured JSON.

### 2. Normalization & Edge Case Handling
* **Data Hunting:** The Grants.gov API schema varies depending on the grant. The script uses a dynamic fallback function to hunt for required fields across these structures.
* **HTML Stripping:** The raw API often returns descriptions containing messy HTML tags. I integrated `BeautifulSoup` to instantly strip these tags, ensuring the exported text is pure.
* **Date Formatting:** Because the API returns dates in various formats, I implemented a multi-format parsing function to guarantee the output strictly adheres to the requested `YYYY-MM-DD` ISO format.

### 3. Semantic Tagging
To fulfill the tagging requirement without relying on heavy local ML models or paid external APIs, I implemented a fast, rule-based NLP function. It scans the normalized title and program description for specific keyword clusters and maps them to a controlled ontology.

## Output Files
Running the script will generate the following in your specified output directory:
* `foa.json`: An array containing the structured grant data.
* `foa.csv`: A flattened, tabular version of the data for downstream analysis.