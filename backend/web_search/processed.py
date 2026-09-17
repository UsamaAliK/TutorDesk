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