import ollama
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
        raise NotImplementedError("OpenAI is not implemented yet")
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
                    if "<think>" in response:
                        # add small text display of thinking process
                        message_placeholder.markdown("LLM is thinking...")
                        if "</think>" in response:
                            # response comes after </think>
                            response = response.split("</think>")[1]
                            message_placeholder.markdown(response)
                    else:
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