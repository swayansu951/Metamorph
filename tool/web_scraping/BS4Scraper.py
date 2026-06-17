import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from urllib.parse import urljoin, urlparse

class bs4scraper():
    """function:
        - soupscraper\n
        scraps the page filtered from the DDGS_finder"""
    def __init__(self):
        self.timeout = 10
        self.header = {
            "user-agent" : (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "Chrome/120.0 Safari/537.36"
            )
        }

    def _fetch_html(self, url :str) -> str:
        """featch domain according to the given url"""
        try:
            response = requests.get(url,
                                    headers=self.header,
                                    timeout=self.timeout
                                    )
            if response.status_code != 200: return None

            content = response.headers.get("Content-Type", "")
            if "text/html" not in content: return None

            return response.text
        except Exception as e:
            return None
        
    def _soup_data(self, soup : BeautifulSoup)-> BeautifulSoup:
        """cleans out and return the data from the beautifulsoup, by removing some unusefull tags\n
            inputs:
                soup: """
        tags = (
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "button",
            "iframe",
        )

        for tag in soup.find_all(tags):
            tag.decompose()

        return soup
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """extracts title using beautifulsoup\n
            inputs:
                soup: \n"""
        if soup.title and soup.title.string: return soup.title.string.strip()

        return ""
    
    def _extract_description(self, soup:BeautifulSoup) -> str:
        """extracts description of the page using beautifulsoup\n
            input:
                soup:\n"""
        description = soup.find("meta", attrs={"name": "description"})

        if description and description.get("content"):
            return description.get("content").strip()
        
        og_description = soup.find("meta", attrs={"propertity" : "og:description"})

        if og_description and og_description.get("content"):
            return og_description.get('content').strip()
        
        return ""
    
    def _extract_headings(self, soup:BeautifulSoup) ->str:
        """extracts heading of the page using beautifulsoup\n
            input:
                soup: \n"""
        headings = []

        for tag in soup.find_all(['h1', 'h2','h3']):
            text = tag.get_text(" ",strip=True)
            if text :
                return headings.append(text)
        
        return headings
    
    def _extract_links(self, soup:BeautifulSoup, base_url:str) -> List[Dict[str,str]]:
        """extracts link from the provided url using beautifulsoup\n
            inputs:
                soup: 
                base_url: \n"""
        links = []

        for tag in soup.find_all("a"):
            href = tag.get('href')
            text = tag.get_text(" ", strip=True)

            full_url = urljoin(base_url,href)

            if full_url.startswith("https"):
                links.append({
                    "text" : text,
                    "url" : full_url,
                })
        return links
    
    def _extract_text(self, soup:BeautifulSoup) -> List[str]:
        """extracts text using beautifulsoup\n
            inputs:
                soup: \n
        """

        data = []

        for tag in soup.find_all(["p", "li"]):
            texts = tag.get_text(" ", strip=True)

            if texts and len(texts) > 20:
                data.append(texts)

        return data
    
    def _images(self, soup:BeautifulSoup, base_url:str) -> List[Dict[str,str]]:
        """extracts iamges from the provided url using beautifulsoup\n
            inputs:
                soup: 
                base_url: \n
            returns:
            {
                "type" : 'image',
                "media_url" : full_url,
                "alt" : tag.get("alt", ""),
                "title" : tag.get("title",""),
                "source_url" : base_url,
            }\n    """
        image_data =[]

        for tag in soup.find_all("img"):
            src = (
                tag.get('src')
                or tag.get("data-src")
                or tag.get("data-original")
            )
            if not src:
                continue

            full_url = urljoin(base_url, src)

            if not src.startswith("https"):
                continue
                
            image_data.append({
                "type" : 'image',
                "media_url" : full_url,
                "alt" : tag.get("alt", ""),
                "title" : tag.get("title",""),
                "source_url" : base_url,
            })

        return image_data
    
    def _video(self, soup:BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """extracts video from the provided url using beautifulsoup\n
            inputs:
                soup: 
                base_url: \n
            returns:
            {
                "type" : 'video',
                "media_url" : full_url,
                "source_url" : base_url,
            }"""
        video_data = []

        for tag in soup.find_all("video"):
            src = tag.get('src')

            if not src:
                source = tag.find("source")
                if source:
                    src = source.get("src")

            full_url = urljoin(base_url, src)

            if src:
                video_data.append({
                    "type" : 'video',
                    "media_url" : full_url,
                    "source_url" : base_url,
                })
        
        for frame in soup.find_all("iframe"):
            src = frame.get("src")

            if not src:
                continue

            full_url = urljoin(base_url, src)
            
            if "youtube" or "vimeo" in src:
                video_data.append(
                    {
                        "type" : "video",
                        "media_url" : full_url,
                        "source_url" : base_url,
                    }
                )

        return video_data
    
    def _table(self, soup:BeautifulSoup) -> List[List[List[str]]]:
        """ scrapes the table from the page if present \n
            input: 
                soup:
            return the table in a format like:
                table [ column of nth [row1, row2, ...]]\n"""
        tables = []

        for table in soup.find_all("table"):
            table_data = []

            for row in table.find_all("tr"): # row from the table, tr
                row_data = []

                for data in row.find_all(['th', 'tb']): # table depth or table height all of them
                    datas = data.get_text(" ", strip=True) # get the texts only from the data collected
                    row_data.append(datas)

                if row_data:
                    table_data.append(row_data)

            if table_data:
                tables.append(table_data)
        
        return tables
    
    def soupscraper(self, url: str) -> Dict[str, Any] | None:
        """systematic web scraper.\n
            connect all the functions above\n
            returns a dict containg : \n
            {\n
                "url" : html,
                "title" :
                "description" : 
                "source_domain" : 
                "text" : 
                "headings" : 
                "links" : 
                "images" : 
                "video" : 
                "tables" : 
            }\n"""
        html =  self._fetch_html(url) # to fetch the url provided

        if not html:
            return None
        
        soup_data = BeautifulSoup(html, "lxml") # scrap the page 
        soup_data = self._soup_data(soup_data)# clean the data collected..
        parsed = urlparse(url)#  get the domain url parsed..

        return {
            "url" : url,
            "title" : self._extract_title(soup_data),
            "description" : self._extract_description(soup_data),
            "source_domain" : parsed.netloc,
            "text" : self._extract_text(soup_data),
            "headings" : self._extract_headings(soup_data),
            "links" : self._extract_links(soup_data, url),
            "images" : self._images(soup_data, url),
            "videos" : self._video(soup_data, url),
            "tables" : self._table(soup_data)
        }
    
    
