def format_citation(source: dict[str, object]) -> dict[str, object]:
    return {
        'chunk_id': source.get('chunk_id'),
        'document_id': source.get('document_id'),
        'filename': source.get('filename'),
        'page_number': source.get('page_number'),
        'chunk_index': source.get('chunk_index'),
        'similarity': source.get('similarity'),
        'chunk_text': source.get('chunk_text')
    }
