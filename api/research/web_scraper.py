import requests
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import StructuredTool
from sqlalchemy import create_engine, URL, Column, String, Integer, TEXT
import json
import base64
from sqlalchemy.orm import sessionmaker, declarative_base
import textwrap
from llama_index.core.settings import Settings
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.tidbvector import TiDBVectorStore
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.llms.bedrock import Bedrock
from llama_index.core.vector_stores.types import (
    MetadataFilter,
    MetadataFilters,
)

# llm = Bedrock(model="anthropic.claude-3-sonnet-20240229-v1:0", profile_name='bedrock')
# embed_model = BedrockEmbedding(model="amazon.titan-embed-text-v1",profile_name='bedrock')
# Settings.embed_model = embed_model
# Settings.llm = llm
# tidb_connection_url = URL(
#                 drivername="mysql+pymysql",
#                 username="3nSmu2d6TtaVP1J.root",
#                 password="gYFH8i7mTrMnDw8X",
#                 host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
#                 port=4000,
#                 database="test",
#                 query={
#                 "ssl_verify_cert": True,
#                 "ssl_verify_identity": True,
#                 "ssl_ca": "C:\\Users\\Jhachirag7\\path_to_ca\\isrgrootx1.pem",
#             },

#         )


# tidbvec = TiDBVectorStore(
#     connection_string=tidb_connection_url,
#     table_name="llama_index_rag",
#     distance_strategy="cosine",
#     vector_dimension=1536,
#     drop_existing_table=False,
# )

# tidb_vec_index = VectorStoreIndex.from_vector_store(tidbvec)

# query_engine = tidb_vec_index.as_query_engine(
#     filters=MetadataFilters(
#         filters=[
#             MetadataFilter(key="url",value="https://blog.neoleads.com", operator="=="),
#         ]
#     ),
#     similarity_top_k=2,
# )
# print(query_engine.get_prompts)
# response = query_engine.query("some SEO related text")

# print(response)


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
        Settings.llm = Bedrock(model="anthropic.claude-3-sonnet-20240229-v1:0", profile_name='bedrock')
        Settings.embed_model = BedrockEmbedding(model="amazon.titan-embed-text-v1", profile_name='bedrock')
        Settings.chunk_size = 2048
        self.api_url = api_url
        self.api_key = api_key
        self.engine = self.get_db_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.create_table()
        self.tidbvec = self.get_vector_store()
        self.query_engine = self.get_query_engine()

    def create_table(self):
        Base.metadata.create_all(self.engine)

    def get_query_engine(self):
        tidb_vec_index = VectorStoreIndex.from_vector_store(self.tidbvec)

        return tidb_vec_index.as_query_engine(streaming=True)

    def get_connection_string(self):
        return URL(
            drivername="mysql+pymysql",
            username="3nSmu2d6TtaVP1J.root",
            password="gYFH8i7mTrMnDw8X",
            host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
            port=4000,
            database="test",
            query={
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
                "ssl_ca": "C:\\Users\\Jhachirag7\\path_to_ca\\isrgrootx1.pem",
            },
        )

    def get_vector_store(self):
        return TiDBVectorStore(
            connection_string=self.get_connection_string(),
            table_name="llama_index_rag",
            distance_strategy="cosine",
            vector_dimension=1536,
            drop_existing_table=False,
        )

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

    def extract_web_content(self, data: list, url: str) -> list[WebContent]:
        web_contents = []
        print(data)
        for item in data:
            metadata = item['metadata']
            web_content = Document(
                text=item['text'],
                metadata={
                    "url": url,
                    "canonicalUrl": metadata['canonicalUrl'],
                    "title": metadata['title'],
                    "description": metadata.get('description', ""),
                    "author": metadata.get('author', ""),
                    "keywords": metadata.get('keywords', ""),
                    "languageCode": metadata['languageCode'],
                    "markdown": item['markdown'],
                }
            )
            web_contents.append(web_content)
        return web_contents

    def extract_web_content_sql_db(self, data: list, url: str) -> list[WebContent]:
        web_contents = []
        for item in data:
            metadata = item['metadata']
            web_content = WebContent(
                url=url,
                canonicalUrl=metadata['canonicalUrl'],
                title=metadata['title'],
                description=metadata.get('description', ""),
                author=metadata.get('author', ""),
                keywords=metadata.get('keywords', ""),
                languageCode=metadata['languageCode'],
                text=item['text'],
                markdown=item['markdown']
            )
            web_contents.append(web_content)
        return web_contents

    def web_scraper(self, url):
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
            'maxCrawlPages': 1,
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
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        webhook_definitions = [
            {
                "eventTypes": ['ACTOR.RUN.FAILED'],
                "requestUrl": 'https://b367-202-179-73-214.ngrok-free.app/webhook',
            },
            {
                "eventTypes": ['ACTOR.RUN.SUCCEEDED'],
                "requestUrl": 'https://b367-202-179-73-214.ngrok-free.app/webhook',
                "payloadTemplate": json.dumps({
                    "body": body,
                    "headers": headers,
                    "data": "{{resource}}"
                }).replace('"{{resource}}"', '{{resource}}'),
            },
        ]
        json_string = json.dumps(webhook_definitions)

        encoded_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        params = {
            "webhooks": encoded_string
        }

        try:
            response = requests.post(
                url=self.api_url,
                headers=headers,
                json=body,
                params=params
            )
            print(response.text)
            response.raise_for_status()
            data = response.json()

            # storage_context = StorageContext.from_defaults(vector_store=self.tidbvec)
            # tidb_vec_index = VectorStoreIndex.from_vector_store(self.tidbvec)
            # tidb_vec_index.from_documents(self.extract_web_content(data,url), storage_context=storage_context, show_progress=True)
            # with self.Session() as session:
            #     session.bulk_save_objects(self.extract_web_content_sql_db(data,url))
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"Error": str(e)}


class WebScrapperTool:
    def __init__(self, api_key,
                 api_url="https://api.apify.com/v2/acts/apify~website-content-crawler/run-sync-get-dataset-items"):
        self.wrapper = WebsiteContentCrawler(api_url, api_key)
        self.webscraper = self.get_scraper()

    def get_scraper(self):
        return StructuredTool.from_function(
            name="webscraper",
            description="Use this tool to scrape content from the give website.",
            func=self.wrapper.web_scraper,
            args_schema=SearchInputDomain
        )


scraper = WebsiteContentCrawler("https://api.apify.com/v2/acts/apify~website-content-crawler/runs",
                                "apify_api_ixAWo59VFK8dwdF9wVrQm7TVgYtODM1aRh2d")

scraper.web_scraper("https://blog.neoleads.com")

from flask import Flask, request
import pyngrok.ngrok
import requests

app = Flask(__name__)


@app.route('/webhook', methods=['GET', 'POST'])
def handle_webhook():
    # Process the incoming webhook data
    if request.method == 'POST':
        data = request.json
        print(data)
        response = requests.post(
            url=f"https://api.apify.com/v2/acts/{data['data']['actId']}/run-sync",
            headers=data['headers'],
            json=data['body'],
        )
        print(response)
        return "Webhook received! POST"

    return "Webhook received!"


if __name__ == '__main__':
    # ngrok_tunnel = pyngrok.ngrok.connect(5000)
    # print('Webhook URL:', ngrok_tunnel.public_url + '/webhook')
    # Run Flask app
    app.run(debug=True, port=80)