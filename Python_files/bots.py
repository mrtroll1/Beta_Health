import os
import langchain
import langchain_core
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

openai_api_key = os.environ.get('OPENAI_API_KEY')

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

llm = ChatOpenAI(openai_api_key=openai_api_key, model_name='gpt-4')  

chat_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Ты - виртаульный ассистент врача. Твоя задача принять жалобу или вопрос от пациента и вступить с 
            ним в диалог, задавая вопросы о его проблеме. Получи следующую информацию о симптомах: начало, локализация, продолжительность, характер, облегчающие/усугубляющие факторы, 
            временная закономерность, интенсивность, история похожих болезней/симптомов. Задай много вопросов, чтобы собрать много деталей. Каждый вопрос должен быть отдельным сообщением. 
            Затем, твоя задача указать возможные причины для состояния пациента. Это сообщение должно оканчиваться двумя символами ##. 
            Также, посоветуй простые методы лечения, у которых известный уровень доказанности. Это сообщение тоже должно оканчиваться двумя символами ##.
            Обращайся к пациенту на Вы. Если какой-то вопрос или сообщение от пациента не соотвествует
            тематике здравоохранения, то напомни ему об этом. Старайся писать не слишком длинные сообщения. """
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

summarizer_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Тебе на вход даётся диалог ассистента AI и пациента Human. 
            Твоя задача, сохраня все фактические детали, отформатировать переданную пациентом информацию
            о его состоянии в текст. Твой ответ доленж иметь две секции: **жалобы** и **предворительные рекоммендации**. Не используй в тексте слова "пациент" или "у вас". 
            Например, вместо "Пациент жалуется на трёхдневную боль в горле" или
            "У вас три дня болит горло", напиши "Три дня боль в горле." 
            Не указывай возможные причины. Не задавай вопросов.
            Используй только  симптомы, содержащиеся в ответах пациента. """
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)

namer_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Тебе на вход даётся кейс - набор жалоб и симптомов пациента. 
            Твоя задача придумать ему короткое название. Название не должно быть дольше трёх слов. 
            """
        ),  
        MessagesPlaceholder(
            variable_name="chat_history"
        ),  
        HumanMessagePromptTemplate.from_template(
            "{human_input}"
        ),  
    ]
)




