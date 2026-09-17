import re




def process_results(search_results):
    processed_results = []

    for result in search_results["results"]:
        processed_results.append({
            "title": result["title"],
            "url": result["url"],
            "content": result["content"],
            "score": result["score"]
        })

    return processed_results


def clean_documents(documents):
    cleaned_documents=[]
    for doc in documents:
        content=doc.page_content.strip()
        if not content:
            continue
        content=clean_text(content)
        if not content:
            continue
        cleaned_documents.append(
            {
            "content":content,
            "source":doc.metadata.get("source")
            }
        )
    return cleaned_documents

def clean_text(text: str) -> str:
    lines=[l.strip() for l in text.splitlines()]
    lines=[l for l in lines if len(l) > 1 and not re.match(r'^[^a-zA-Z]{0,3}$', l)]
    text="\n".join(lines)
    blocks=re.split(r'\n\s*\n', text)
    text=max(blocks, key=lambda b: len(b.split()))
    return re.sub(r'\s+', ' ', text).strip()
