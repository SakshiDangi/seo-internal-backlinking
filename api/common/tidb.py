import os
from typing import List, Dict

from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from llama_index.legacy.embeddings import BedrockEmbedding
from llama_index.llms.bedrock import Bedrock
from llama_index.vector_stores.tidbvector import TiDBVectorStore
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

Settings.llm = Bedrock(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    profile_name='neoleads',
    region_name='us-east-1'
)

Settings.embed_model = BedrockEmbedding(
    model="amazon.titan-embed-text-v1",
    profile_name='neoleads',
    region_name='us-east-1'
)

tidbvec = TiDBVectorStore(
    connection_string=os.getenv("TIDB_CONNECTION_STRING"),
    table_name="website_pages_vectors",
    distance_strategy="cosine",
    vector_dimension=1536,
    drop_existing_table=False,
)


def get_session():
    # Create the SQLAlchemy engine
    engine = create_engine(os.getenv('TIDB_CONNECTION_STRING'))

    # Create a session factory
    Session = sessionmaker(bind=engine)

    return Session()


def get_query_engine(filters: List[Dict[str, str]], similarity_top_k: int = 2):
    tidb_vec_index = VectorStoreIndex.from_vector_store(tidbvec)

    metadata_filters = []
    for item in filters:
        metadata_filters.append(
            MetadataFilter(
                **item
            )
        )

    query_engine = tidb_vec_index.as_query_engine(
        filters=MetadataFilters(
            filters=[metadata_filters]
        ),
        similarity_top_k=similarity_top_k,
    )

    return query_engine


def save_row_table(row):
    session = get_session()
    try:
        session.add(row)
        session.commit()
        return row
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_bulk_rows_table(rows):
    session = get_session()
    try:
        session.bulk_save_objects(rows)
        session.commit()
        return rows
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()


def find_rows_table(model, filters):
    session = get_session()
    try:
        query = session.query(model)
        for key, value in filters.items():
            query = query.filter(getattr(model, key) == value)
        result = query.all()
        return result
    except SQLAlchemyError as e:
        raise e
    finally:
        session.close()
