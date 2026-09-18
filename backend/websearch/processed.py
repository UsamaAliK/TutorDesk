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

    lines = [line.strip() for line in text.splitlines()]

    lines = [
        line
        for line in lines
        if len(line) > 1
        and not re.match(r'^[^a-zA-Z]{0,3}$', line)
    ]

    text = "\n".join(lines)

    return re.sub(r'\s+', ' ', text).strip()

def is_valid_doc(text:str):
    words=text.split()
    if len(words)<=50:
        return False
    return True