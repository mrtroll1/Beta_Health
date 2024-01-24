import langchain
import langchain_core
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

class ChatBot(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  

    def process_message(self, message):
        return self.invoke(message)['text']

class Summarizer(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  
    
    def summarize(self, memory):
        messages = memory.buffer_as_messages
        
        return self.invoke(messages)['text']

class Namer(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  
    
    def name_case(self, case_data):

        return self.invoke(case_data)['text']



