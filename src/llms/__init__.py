import ollama
from src.config import model, client
from abc import ABC, abstractmethod
import streamlit as st

class ChatCompletion(ABC):
    def __init__(self, **args):
        pass

    @abstractmethod
    def get_response(self, messages, options, content = True, stream = False):
        pass


class OpenAI(ChatCompletion):
    def __init__(self, **args):
        super().__init__(**args)

    def get_response(self, **args):
        pass

class OpenSourceModels(ChatCompletion):
    def __init__(self, model, **args):
        super().__init__(**args)
        self.model = model

    def get_response(self, messages, options, content = True, stream = False, stream_handler = None):
        if stream:
            stream = ollama.chat(model=self.model, messages=messages, stream=stream, options=options)
            response = ''
            if stream_handler:
                response = stream_handler(stream)
            else:
                message_placeholder = st.empty()
                for chunk in stream:
                    response += chunk['message']['content']
                    message_placeholder.markdown(response)
            return response
        else:
            if content:
                return ollama.chat(model=self.model, messages=messages, options=options)['message']['content']
            else:
                return ollama.chat(model=self.model, messages=messages, options=options)

class OpenSourceVisionModels(ChatCompletion):
    # TODO
    def __init__(self, model, **args):
        super().__init__(**args)
        self.model = model

    def get_response(self, messages, options, content = True, stream = False, stream_handler = None):
        if stream:
            stream = ollama.chat(model=self.model, messages=messages, stream=stream, options=options)
            response = ''
            if stream_handler:
                response = stream_handler(stream)
            else:
                message_placeholder = st.empty()
                for chunk in stream:
                    response += chunk['message']['content']
                    message_placeholder.markdown(response)
            return response
        else:
            if content:
                return ollama.chat(model=self.model, messages=messages, options=options)['message']['content']
            else:
                return ollama.chat(model=self.model, messages=messages, options=options)


class OpenSourceCodingModels(ChatCompletion):
    # TODO
    def __init__(self, model, **args):
        super().__init__(**args)
        self.model = model

    def get_response(self, messages, options, content = True, stream = False, stream_handler = None):
        if stream:
            stream = ollama.chat(model=self.model, messages=messages, stream = stream, options=options)
            response = ''
            if stream_handler:
                response = stream_handler(stream)
            else:
                message_placeholder = st.empty()
                for chunk in stream:
                    response += chunk['message']['content']
                    message_placeholder.markdown(response)
            return response
        else:
            if content:
                return ollama.chat(model=self.model, messages=messages, options=options)['message']['content']
            else:
                return ollama.chat(model=self.model, messages=messages, options=options)