import socket
import threading
from loguru import logger
import json
import queue
import errno

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
    
def tasker_thread_handler(server_socket, task_queue, llm_chain):
    while True:
        logger.debug("Tasker thread waiting for connection")
        conn, addr = server_socket.accept()
        logger.debug(f"Connection from {addr}")
        flag = False
        while True:
            if flag:
                break
            data = task_queue.get()
            # data = conn.recv(1024).decode()
            # try:
                # data = task_queue.get(timeout=1)
            # except queue.Empty:
            #     logger.debug("Queue was empty")
            #     continue
            # except Exception as e:
            #     logger.debug("Queue was empty")
            #     continue
                
            # if not data:
            #     print('aint no data')
            #     break
            packet = json.loads(data)
            if packet['type'] == 'phrase':
                output = ''
                for chunk in llm_chain.stream(packet['message']):
                    
                    # if '\n' in chunk:
                    #     chunk = chunk.replace('\n', '')
                    #     controller.clear()
                    output += chunk
                    try:
                        # print('wrote', output)
                        data = {"type": "phrase", "message": output}
                        data_string = json.dumps(data)
                        conn.sendall(data_string.encode())
                    except IOError as e:
                        if e.errno == errno.EPIPE:
                            logger.warning("Broken Pipe. Need to reconnect to tasker")
                            flag = True
                            break
                        else:
                            logger.error(e)
                            
                # conn.sendall(data)
            else:
                logger.debug('This packet type has not been implemented')
        conn.close()
        logger.debug('Tasker socket closed')
    logger.debug('tasker thread done')
    
def talon_thread_handler(server_socket, task_queue):
    while True:
        logger.debug("Talon thread waiting for connection")
        conn, addr = server_socket.accept()
        logger.debug(f"Connection from {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                logger.error('Received blank from Talon, or connection was closed and no problem')
                break
            else:
                packet = json.loads(data)
                if packet['type'] == 'phrase':
                    task_queue.put(data)
                else:
                    logger.debug('This packet type has not been implemented yet')
        conn.close()
    logger.debug('talon thread done')
    
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

def main():
    tasker_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # tasker_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tasker_server_socket.bind(('0.0.0.0', 9998))
    tasker_server_socket.listen(1)
    
    talon_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # talon_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    talon_server_socket.bind(('0.0.0.0', 9999))
    talon_server_socket.listen(1)
    
    task_queue = queue.Queue()
    
    llm_chain = setup_llm()
    tasker_thread = threading.Thread(target=tasker_thread_handler, args=(tasker_server_socket, task_queue, llm_chain))
    talon_thread = threading.Thread(target=talon_thread_handler, args=(talon_server_socket, task_queue))
    
    # Start the threads
    tasker_thread.start()
    talon_thread.start()

    # Wait for the threads to finish
    tasker_thread.join()
    talon_thread.join()

    # Close the server socket
    tasker_server_socket.close()
    talon_server_socket.close()



# Start the server
if __name__ == "__main__":
    main()
    logger.debug('Quitting out of main')