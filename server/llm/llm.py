from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain

from typing import Iterable
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessageChunk
from langchain_core.runnables import RunnableGenerator

def setup_llm():
    llm = Ollama(model="llama2")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Your responses are terse."),
        ("user", "{input}")
    ])

    def streaming_parse(chunks: Iterable[BaseMessageChunk]) -> Iterable[str]:
        for chunk in chunks:
            yield chunk

    streaming_parse = RunnableGenerator(streaming_parse)


    chain = prompt | llm | streaming_parse
    return chain
