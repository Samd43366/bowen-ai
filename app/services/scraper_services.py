import asyncio
import httpx
from bs4 import BeautifulSoup
from app.services.firestore_services import save_document_metadata, delete_document_by_filename
from app.services.qdrant_services import delete_document_chunks
from app.services.document_pipeline import process_document_background
import concurrent.futures

BOWEN_URLS = [
    "https://bowen.edu.ng/",
    "https://bowen.edu.ng/about-us/",
    "https://bowen.edu.ng/office-of-the-vice-chancellor/",
    "https://bowen.edu.ng/office-of-the-deputy-vice-chancellor/",
    "https://bowen.edu.ng/office-of-the-registrar/",
    "https://bowen.edu.ng/bursary-unit/",
    "https://bowen.edu.ng/university-library/",
    "https://bowen.edu.ng/university-worship-centre/",
    "https://bowen.edu.ng/2024/11/21/new-bowen-university-anthem/",
    "https://bowen.edu.ng/directorate-of-digital-services/",
    "https://bowen.edu.ng/directorate-of-student-support-services/",
    "https://bowen.edu.ng/directorate-of-research-and-strategic-partnerships/",
    "https://bowen.edu.ng/faith-integration-program/",
    "https://bowen.edu.ng/admissions-bowen/",
    "https://bowen.edu.ng/tuition-fee/",
    "https://bowen.edu.ng/tuition-fee/a-level-fees/",
    "https://bowen.edu.ng/bowen-fees/100-level-fees/",
    "https://bowen.edu.ng/bowen-fees/200-level-fees/",
    "https://bowen.edu.ng/bowen-fees/300-level-fees/",
    "https://bowen.edu.ng/bowen-fees/400-level-fees/",
    "https://bowen.edu.ng/bowen-fees/500-level-fees/",
    "https://bowen.edu.ng/bowen-fees/600-level-fees/",
    "https://bowen.edu.ng/bowen-fees/700-level-fees/",
    "https://bowen.edu.ng/academics/",
    "https://bowen.edu.ng/coaes-2/",
    "https://bowen.edu.ng/coccs/",
    "https://bowen.edu.ng/comss/",
    "https://bowen.edu.ng/cohes/",
    "https://bowen.edu.ng/colaw/",
    "https://bowen.edu.ng/coevs/",
    "https://bowen.edu.ng/degree-programme/"
]

from bs4 import NavigableString

def convert_table_to_markdown(table):
    rows = []
    for tr in table.find_all('tr'):
        cells = [td.get_text(strip=True).replace('\n', ' ').replace('|', '-') for td in tr.find_all(['th', 'td'])]
        if cells:
            rows.append("| " + " | ".join(cells) + " |")
            
    if not rows:
        return ""
        
    markdown = "\n" + rows[0] + "\n"
    
    # Calculate columns for separator
    col_count = len(rows[0].split('|')) - 2
    if col_count > 0:
        separator = "| " + " | ".join(["---"] * col_count) + " |"
        markdown += separator + "\n"
        
    for row in rows[1:]:
        markdown += row + "\n"
        
    return markdown + "\n"

async def scrape_url(client: httpx.AsyncClient, url: str):
    print(f"Scraping {url}...")
    try:
        headers = {'User-Agent': 'BowenAIBot/1.0'}
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
                
            # Convert tables to markdown string so they don't lose structure
            for table in soup.find_all('table'):
                md_table = convert_table_to_markdown(table)
                table.replace_with(NavigableString(md_table))
                
            text = soup.get_text(separator=' ', strip=True)
            return url, text
        else:
            print(f"Failed to fetch {url}. Status: {response.status_code}")
            return url, None
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return url, None

URL_CATEGORIES = {
    "fees": "Fees",
    "tuition": "Fees",
    "admission": "Admissions",
    "office-of": "Administration",
    "bursary": "Administration",
    "library": "Campus Services",
    "worship-centre": "Campus Services",
    "directorate": "Directorates",
    "coaes": "Colleges",
    "coccs": "Colleges",
    "comss": "Colleges",
    "cohes": "Colleges",
    "colaw": "Colleges",
    "coevs": "Colleges",
    "academics": "Academics",
    "degree": "Academics",
    "faith-integration": "Spiritual Life",
    "anthem": "General"
}

def determine_category(url: str) -> str:
    url_lower = url.lower()
    for key, cat in URL_CATEGORIES.items():
        if key in url_lower:
            return cat
    return "General Website"

async def scrape_bowen_sites():
    """
    Background job to scrape URLs and push them directly to Qdrant via the document pipeline.
    """
    print("Starting scheduled Bowen University website scraping job...")
    
    async with httpx.AsyncClient() as client:
        # Create a pool of tasks
        tasks = [scrape_url(client, url) for url in BOWEN_URLS]
        results = await asyncio.gather(*tasks)
        
        for url, text in results:
            if text and len(text) > 50:
                filename = url.replace("https://", "").replace("http://", "").strip("/")
                if not filename:
                    filename = "bowen.edu.ng"
                
                # Determine the category strictly based on URL
                category = determine_category(url)
                
                filename = f"Web Scrape: {filename}"
                
                # Because we are re-scraping, we remove the old version first
                delete_document_chunks(filename)
                delete_document_by_filename(filename)
                
                # Create a new document metadata entry
                doc = save_document_metadata({
                    "filename": filename, 
                    "status": "processing",
                    "chunks_indexed": 0,
                    "category": category
                })
                
                # Now push it to Qdrant using our existing background pipeline
                # This must run on the thread pool to avoid blocking the asyncio loop if it has sync code
                process_document_background(
                    document_id=doc["id"],
                    file_name=filename,
                    full_text=text,
                    category=category
                )
                
    print("Completed scheduled website scraping job.")

def run_scraper_sync():
    """
    APScheduler requires a sync function to run. We wrap the async logic here.
    """
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(scrape_bowen_sites())
    except RuntimeError:
        asyncio.run(scrape_bowen_sites())
