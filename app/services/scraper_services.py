import asyncio
import httpx
from bs4 import BeautifulSoup
from app.services.firestore_services import save_document_metadata, delete_document_by_filename, get_all_scrape_urls, set_system_metadata
from app.services.qdrant_services import delete_document_chunks
from app.services.document_pipeline import process_document_background
from datetime import datetime, timezone
import concurrent.futures

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
            
            # Add explicit spacing for headers and list items to prevent bunching
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'br']):
                tag.insert_after(NavigableString('\n'))
                
            # Convert tables to markdown string so they don't lose structure
            for table in soup.find_all('table'):
                md_table = convert_table_to_markdown(table)
                table.replace_with(NavigableString('\n' + md_table + '\n'))
                
            text = soup.get_text(separator='\n', strip=True)
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
    urls_data = get_all_scrape_urls()
    if not urls_data:
        print("No URLs configured for scraping. Skipping.")
        return
        
    async with httpx.AsyncClient() as client:
        # Create a pool of tasks
        tasks = [scrape_url(client, u.get("url", "")) for u in urls_data if u.get("url")]
        results = await asyncio.gather(*tasks)
        
        for idx, (url, text) in enumerate(results):
            if text and len(text) > 50:
                filename = url.replace("https://", "").replace("http://", "").strip("/")
                if not filename:
                    filename = "bowen.edu.ng"
                
                # Determine the category strictly based on URL or DB setting
                category = urls_data[idx].get("category")
                if not category:
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
                
    set_system_metadata("last_full_scrape_time", datetime.now(timezone.utc).isoformat())
    print("Completed scheduled website scraping job.")

async def scrape_single_url_task(url: str, category: str):
    print(f"Manually scraping {url}...")
    async with httpx.AsyncClient() as client:
        url_res, text = await scrape_url(client, url)
        
        if text and len(text) > 50:
            filename = url.replace("https://", "").replace("http://", "").strip("/")
            if not filename:
                filename = "bowen.edu.ng"
            
            if not category:
                category = determine_category(url)
            
            filename = f"Web Scrape: {filename}"
            
            delete_document_chunks(filename)
            delete_document_by_filename(filename)
            
            doc = save_document_metadata({
                "filename": filename, 
                "status": "processing",
                "chunks_indexed": 0,
                "category": category
            })
            
            process_document_background(
                document_id=doc["id"],
                file_name=filename,
                full_text=text,
                category=category
            )
            print(f"Finished initiating scrape for {url}")
        else:
            print(f"Failed or insufficient content for manual scrape of {url}")

def trigger_single_scrape(url: str, category: str):
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(scrape_single_url_task(url, category))
    except RuntimeError:
        asyncio.run(scrape_single_url_task(url, category))

def run_scraper_sync():
    """
    APScheduler requires a sync function to run. We wrap the async logic here.
    """
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(scrape_bowen_sites())
    except RuntimeError:
        asyncio.run(scrape_bowen_sites())
