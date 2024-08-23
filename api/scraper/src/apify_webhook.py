"""
apify helper functions
"""
import os
from urllib.parse import urlparse

from apify_client import ApifyClient
from llama_index.core import Document, StorageContext, VectorStoreIndex

from common.db_schema import WebsitePages, Website, UserWebsite
from common.schemas import ApifyWebhookData
from common.tidb import save_bulk_rows_table, find_rows_table, save_row_table, tidbvec
from llama_index.core.node_parser import SimpleNodeParser


def get_dataset_items(actor_id, run_id):
    apify_client = ApifyClient(os.getenv("APIFY_API_KEY", "apify_api_x3hGuTH0ffyu1qOYFx8Q97HV4sI9jX2ixG51"))

    # Run the actor synchronously
    run = apify_client.actor(actor_id).last_run()

    # check run id is same as the run id in the request
    if run.get()['id'] != run_id:
        return {"Error": "Run id does not match the run id in the request"}

    # Get the dataset client for the actor run
    dataset_client = run.dataset()

    # Fetch items from the dataset
    items = dataset_client.list_items().items

    return items


def get_markdown_chunks(markdown_text: str) -> list:
    # Initialize the document
    document = Document(text=markdown_text)

    # Initialize a node parser
    node_parser = SimpleNodeParser()

    # Parse the document into nodes (chunks)
    nodes = node_parser.get_nodes_from_documents([document])

    return nodes


def get_domain_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain


def process_apify_webhook(data, user_id=1):
    # validate request body
    webhook_data = ApifyWebhookData(**data)

    # get dataset items
    items = get_dataset_items(
        actor_id=webhook_data.actorId,
        run_id=webhook_data.actorRunId
    )

    # create a website or find the website
    url = items[0]['url']
    domain = get_domain_from_url(url)
    # check if website exists
    website = find_rows_table(Website, {"domain": domain})
    if not len(website):
        # save website
        website = save_row_table(Website(
            name=domain,
            description="",
            domain=domain,
        ))
        save_row_table(UserWebsite(
            user_id=user_id,
            website_id=website.id
        ))
    else:
        website = website[0]

    # for each item, save to db
    rows = []
    for item in items:
        metadata = item['metadata']
        web_content = WebsitePages(
            url=item['url'],
            canonical_url=metadata['canonicalUrl'],
            title=metadata['title'],
            description=metadata.get('description', ""),
            author=metadata.get('author', ""),
            keywords=metadata.get('keywords', ""),
            language_code=metadata['languageCode'],
            text=item['text'],
            markdown=item['markdown'],
            website_id=website.id
        )
        rows.append(web_content)

    pages = save_bulk_rows_table(rows)

    # convert the markdown to chunks
    chunks = []
    for idx, item in enumerate(items):
        metadata = item['metadata']
        website_page = pages[idx]
        nodes = get_markdown_chunks(item['markdown'])
        for node in nodes:
            chunk = Document(
                text=node.text,
                metadata={
                    "website_id": website.id,
                    "website_page_id": website_page.id,
                    "url": item['url'],
                    "title": metadata['title'],
                    "description": metadata.get('description', ""),
                    "language_code": metadata['languageCode'],
                }
            )
            chunks.append(chunk)

    storage_context = StorageContext.from_defaults(vector_store=tidbvec)
    tidb_vec_index = VectorStoreIndex.from_vector_store(tidbvec)
    tidb_vec_index.from_documents(chunks, storage_context=storage_context, show_progress=True)


if __name__ == "__main__":
    print(get_dataset_items("aYG0l9s7dbB7j3gbS", "AV2l9u1VM08cP4vxk"))
