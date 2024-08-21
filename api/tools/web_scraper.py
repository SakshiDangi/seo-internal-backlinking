import requests
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import StructuredTool
from sqlalchemy import create_engine, URL, Column, String,Integer,TEXT
import json
from sqlalchemy.orm import sessionmaker,declarative_base
import textwrap

from llama_index.core import SimpleDirectoryReader, StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.tidbvector import TiDBVectorStore


Base = declarative_base()
class SearchInputDomain(BaseModel):
    url: str = Field(description="Takes the domain/url.")


class WebContent(Base):
    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    canonicalUrl = Column(String(255))
    title = Column(TEXT)
    description = Column(TEXT)
    author = Column(String(32))
    keywords = Column(TEXT)
    languageCode = Column(String(32))
    text = Column(TEXT)
    markdown = Column(TEXT)

    __tablename__ = "web_content"

class WebsiteContentCrawler:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.engine = self.get_db_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.create_table()

    def create_table(self):
        Base.metadata.create_all(self.engine) 

    def extract_web_content(self,data:list,url:str) -> list[WebContent]:
        web_contents = []
        for item in data:
            metadata = item['metadata']
            web_content = WebContent(
                url=url,
                canonicalUrl=metadata['canonicalUrl'],
                title=metadata['title'],
                description=metadata.get('description',""),
                author=metadata.get('author',""),
                keywords=metadata.get('keywords',""),
                languageCode=metadata['languageCode'],
                text=item['text'],
                markdown=item['markdown']
            )
            web_contents.append(web_content)
        return web_contents


    def get_db_engine(self):
        connect_args = {
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
                "ssl_ca": "C:\\Users\\Jhachirag7\\path_to_ca\\isrgrootx1.pem",
        }
        return create_engine(
            URL.create(
                drivername="mysql+pymysql",
                username="3nSmu2d6TtaVP1J.root",
                password="gYFH8i7mTrMnDw8X",
                host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
                port=4000,
                database="test",
            ),
            connect_args=connect_args
        )
    

    def web_scraper(self, url):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        body = {
            'startUrls': [
                {
                    'url': url
                }
            ],
            'useSitemaps': False,
            'crawlerType': 'playwright:adaptive',
            'includeUrlGlobs': [],
            'excludeUrlGlobs': [],
            'ignoreCanonicalUrl': False,
            'maxCrawlDepth': 5,
            'maxCrawlPages': 30,
            'initialConcurrency': 0,
            'maxConcurrency': 10,
            'initialCookies': [],
            'proxyConfiguration': {
                'useApifyProxy': True
            },
            'maxSessionRotations': 10,
            'maxRequestRetries': 5,
            'requestTimeoutSecs': 60,
            'minFileDownloadSpeedKBps': 128,
            'dynamicContentWaitSecs': 10,
            'waitForSelector': '',
            'maxScrollHeightPixels': 5000,
            'removeElementsCssSelector': 'nav, footer, script, style, noscript, svg, [role="alert"], [role="banner"], [role="dialog"], [role="alertdialog"], [role="region"][aria-label*="skip" i], [aria-modal="true"]',
            'removeCookieWarnings': True,
            'expandIframes': True,
            'clickElementsCssSelector': '[aria-expanded="false"]',
            'htmlTransformer': 'readableText',
            'readableTextCharThreshold': 100,
            'aggressivePrune': False,
            'debugMode': False,
            'debugLog': False,
            'saveHtml': False,
            'saveHtmlAsFile': False,
            'saveMarkdown': True,
            'saveFiles': False,
            'saveScreenshots': False,
            'maxResults': 9999999,
            'clientSideMinChangePercentage': 15,
            'renderingTypeDetectionPercentage': 10
        }

        try:
            response = requests.post(
                url=self.api_url,
                headers=headers,
                json=body
            )
            response.raise_for_status()
            data = response.json()
            with self.Session() as session:
                session.bulk_save_objects(self.extract_web_content(data,url))
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"Error": str(e)}
        

class WebScrapperTool:
    def __init__(self,api_key,api_url="https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items"):
        self.wrapper=WebsiteContentCrawler(api_url,api_key)
        self.webscraper=self.get_scraper()

    def get_scraper(self):
        return StructuredTool.from_function(
            name="webscraper",
            description="Use this tool to scrape content from the give website.",
            func=self.wrapper.web_scraper,
            args_schema=SearchInputDomain
        )

scraper=WebScrapperTool("apify_api_ixAWo59VFK8dwdF9wVrQm7TVgYtODM1aRh2d")

func=scraper.get_scraper()

print(func({"url":"https://blog.neoleads.com"}))