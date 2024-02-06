# This file contains LLM classes 

import os
import re
import ast
import datetime
from datetime import timedelta
import langchain
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

openai_api_key = os.environ.get('OPENAI_API_KEY')

class ChatBot(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  

    def chatgpt_to_telegram_markdown(self, input_text):
        bold_transformed = input_text.replace('**', '*')

        italics_transformed = ''
        skip_next = False
        for i, char in enumerate(bold_transformed):
            if skip_next:
                skip_next = False
                continue

            if char == '*' and (i == 0 or bold_transformed[i-1] != '*') and (i == len(bold_transformed) - 1 or bold_transformed[i+1] != '*'):
                italics_transformed += '_'
            else:
                italics_transformed += char
                if char == '*':
                    skip_next = True

        return italics_transformed

    def process_message(self, message):
        response = self.invoke(message)['text']
        return self.chatgpt_to_telegram_markdown(response)

class Summarizer(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  
    
    def chatgpt_to_telegram_markdown(self, input_text):
        bold_transformed = input_text.replace('**', '*')

        italics_transformed = ''
        skip_next = False
        for i, char in enumerate(bold_transformed):
            if skip_next:
                skip_next = False
                continue

            if char == '*' and (i == 0 or bold_transformed[i-1] != '*') and (i == len(bold_transformed) - 1 or bold_transformed[i+1] != '*'):
                italics_transformed += '_'
            else:
                italics_transformed += char
                if char == '*':
                    skip_next = True

        return italics_transformed

    def summarize(self, memory):
        messages = memory.buffer_as_messages
        response = self.invoke(messages)['text']
        return self.chatgpt_to_telegram_markdown(response)

class Namer(langchain.chains.llm.LLMChain):
    def __init__(self, llm, prompt, memory, verbose=False):
        super().__init__(llm=llm, prompt=prompt, verbose=verbose, memory=memory)

        self.memory = memory  

    def chatgpt_to_telegram_markdown(self, input_text):
        bold_transformed = input_text.replace('**', '*')

        italics_transformed = ''
        skip_next = False
        for i, char in enumerate(bold_transformed):
            if skip_next:
                skip_next = False
                continue

            if char == '*' and (i == 0 or bold_transformed[i-1] != '*') and (i == len(bold_transformed) - 1 or bold_transformed[i+1] != '*'):
                italics_transformed += '_'
            else:
                italics_transformed += char
                if char == '*':
                    skip_next = True
    
    def name_case(self, case_data):
        response = self.invoke(case_data)['text']
        return self.chatgpt_to_telegram_markdown(response)

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

