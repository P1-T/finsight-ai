from app.api.schemas import Ticker
from app.config import Settings
from app.rag.pinecone_store import PineconeFilingStore, citation_from_hit, metric_payload_from_hits


class FakeDocuments:
    def __init__(self):
        self.upsert_calls = []
        self.search_kwargs = None
        self.delete_kwargs = None

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def search(self, **kwargs):
        self.search_kwargs = kwargs
        return {"matches": [{"_id": "a", "chunk_text": "evidence"}]}

    def delete(self, **kwargs):
        self.delete_kwargs = kwargs


class FakeIndex:
    def __init__(self):
        self.documents = FakeDocuments()


class FakeClient:
    def __init__(self):
        self.index_value = FakeIndex()

    def describe_index(self, name):
        return type("IndexDescription", (), {"host": "https://pinecone.example", "status": {"ready": True}})()

    def index(self, **kwargs):
        return self.index_value


def test_document_batches_respect_integrated_embedding_limit() -> None:
    store = PineconeFilingStore(Settings(pinecone_api_key="test"))
    store.client = FakeClient()
    docs = [{"_id": str(index), "chunk_text": "filing chunk"} for index in range(100)]
    store.ingest(Ticker.AAPL, "accession", docs)
    assert [len(call["documents"]) for call in store.client.index_value.documents.upsert_calls] == [96, 4]


def test_search_and_citation_extract_real_document_fields() -> None:
    store = PineconeFilingStore(Settings(pinecone_api_key="test"))
    store.client = FakeClient()
    assert store.search(Ticker.NVDA, "risk factors") == [{"_id": "a", "chunk_text": "evidence"}]
    assert store.client.index_value.documents.search_kwargs["namespace"] == "NVDA"

    hit = {"_id": "fact", "fields": {"metrics_json": "{\"revenue\": 10}"}}
    assert metric_payload_from_hits([hit]) == {"revenue": 10}
    assert citation_from_hit({"fields": {"chunk_text": "text", "section": "Item 1", "citation_url": "https://www.sec.gov/Archives/edgar/data/1/a.htm"}}) == {
        "text": "text", "section": "Item 1", "url": "https://www.sec.gov/Archives/edgar/data/1/a.htm"
    }


def test_search_parser_supports_rest_hits_shape() -> None:
    assert PineconeFilingStore._hits({"result": {"hits": [{"_id": "rest-doc"}]}}) == [{"_id": "rest-doc"}]
