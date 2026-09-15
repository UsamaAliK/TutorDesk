from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_docs(docs):
    splitter=RecursiveCharacterTextSplitter(chunk_size=800,chunk_overlap=130)
    return splitter.split_documents(docs)


