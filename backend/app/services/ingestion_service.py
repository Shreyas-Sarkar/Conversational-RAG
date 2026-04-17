INGESTION_STAGES = ['uploaded', 'chunking', 'embedding', 'indexing', 'ready']


def build_ingestion_plan(filename: str) -> dict[str, object]:
    return {
        'filename': filename,
        'status': 'uploaded',
        'stages': INGESTION_STAGES
    }


def ingest_document(filename: str) -> dict[str, object]:
    return build_ingestion_plan(filename)
