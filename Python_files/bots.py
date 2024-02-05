import os
import re
import ast
import datetime
from datetime import timedelta
import langchain
import langchain_core
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.prompts import HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
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

class Reminder(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  

    def extract_bracket_content(self, s):
        matches = re.findall(r'\{[^{}]*\}', s)

        return ''.join(matches)

    def remove_comments(self, s):
        result = ""
        i = 0
        while i < len(s):
            if s[i] == '#':
                i = s.find('\n', i)
                if i == -1:  
                    break
            else:
                result += s[i]
                i += 1
        return result


    def safe_eval(self, expr):
        try:
            node = ast.parse(expr, mode='eval')
            return eval(compile(node, '<string>', mode='eval'), {"__builtins__": None, "datetime": datetime, "range": range, "timedelta": timedelta})
        except Exception as e:
            print(f"Error evaluating expression: {expr}. Error: {e}")
            return None

    def replace_comprehension(self, match):
        expression, variable, sequence = match.groups()
        full_comprehension = f'[{expression} for {variable} in {self.safe_eval(sequence)}]'
        evaluated_list = self.safe_eval(full_comprehension)
        return str(evaluated_list)

    def comprehension_to_proper(self, input_string):
        comprehension_pattern = r'\[(.+?) for (.+?) in (.+?)\]'
        return re.sub(comprehension_pattern, self.replace_comprehension, input_string)

    def process_output(self, response):
        allowed_names = {"datetime": datetime, "range": range, "timedelta": timedelta}

        formatted_string = self.extract_bracket_content(response)
        formatted_string = self.remove_comments(formatted_string)
        formatted_string = self.comprehension_to_proper(formatted_string)
        formatted_string = formatted_string.replace("'''", "").replace("python", "").replace("```", "")
        formatted_string = formatted_string.replace("\n", "")

        try:
            result_dict = eval(formatted_string, {"__builtins__": None}, allowed_names)
        except Exception as e:
            return e

        return result_dict
        
    def compose_reminders(self, recommendations):
        response = self.invoke(recommendations)['text']
        return response, self.process_output(response)

llm = ChatOpenAI(openai_api_key=openai_api_key, model_name='gpt-4-turbo-preview')  

chat_prompt_russian = ChatPromptTemplate.from_messages(
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

chat_prompt_english = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
            You are a virtual assistant for a doctor. Your task is to receive a complaint or question from a patient and 
            engage in a dialogue with them, asking questions about their problem. Obtain the following information about symptoms: 
            onset, localization, duration, character, relieving/exacerbating factors, temporal pattern, intensity, 
            history of similar diseases/symptoms. Ask many questions to gather many details. Each question should be a separate message. 
            Then, your task is to indicate possible causes for the patient's condition. This message should end with two characters ##. 
            Also, advise simple treatment methods with a known level of evidence. This message should also end with two characters ##. 
            Address the patient formally. If any question or message from the patient does not correspond to the topic of healthcare, 
            remind them of this. Try to write messages that are not too long.
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

summarizer_prompt_russian = ChatPromptTemplate.from_messages(
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


summarizer_prompt_english = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
            You are given a dialogue between an AI assistant and a Human patient. Your task, while preserving all factual details, 
            is to format the information provided by the patient about their condition into text. 
            Your answer should have two sections: Complaints and Preliminary Recommendations. 
            Do not use the words "patient" or "you have" in the text. For example, instead of "The patient complains of a sore throat 
            for three days" or "You have had a sore throat for three days", write "Three days of sore throat." 
            Do not indicate possible causes. Do not ask questions. Use only the symptoms contained in the patient's responses.
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


namer_prompt_russian = ChatPromptTemplate.from_messages(
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

namer_prompt_english = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
            You are given a case - a set of complaints and symptoms of a patient. Your task is to come up with a short name for it. 
            The name should not be longer than three words.
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

reminder_prompt_russian = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""Ты -- ИИ ассистент врача. Твоя задача планировать напоминания. Сегодня у врача был приём
            (сегодняшняя дата тебе дана). Тебе на вход даются рекомендации, которые он дал пациенту, а также даты предстоящих приёмов. 
            Их текст надо адаптировать под напоминания, правильно итерпретируя временные рамки.
            Твоя задача написать текст напоминаний для пациента и указать в днях/часах datetime.timedelta -- время, 
            через которое эти напоминания надо отправить. 
            Твой ответ должен быть в формате python dictionary, где keys - тексты напоминаний, 
            а values - list of timedelta's (одно и тоже можно напоминать несколько раз). 
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

reminder_prompt_english = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
            You are an AI assistant to a doctor. Your task is to plan reminders. Today, the doctor had an appointment (today's date is given). 
            You are given the recommendations he gave to the patient, as well as the dates of upcoming appointments. 
            Their text needs to be adapted for reminders.  
            Your task is to write the text of reminders for the patient and specify in days/hours datetime.timedelta -- 
            the time after which these reminders should be sent. Your answer should be in the format of a python dictionary, 
            where keys are the texts of reminders, and values are lists of timedelta's (the same thing can be reminded several times).
            Please only include the dictionary itself in the answer and do not define any variables outside of it. 
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



