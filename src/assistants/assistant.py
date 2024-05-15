from src.utils import get_assistant, create_thread, load_config
from src.config import client
from src.assistants.stream import check_tool_call, manage_tool_call, check_message_delta, get_text_stream, get_text_delta
import json
import streamlit as st
from abc import ABC, abstractmethod

class Assistant(ABC):
    def __init__(self, config_path, update_assistant):
        self.config = load_config(config_path)
        self.function_dict = {}
        self.update_assistant = update_assistant
        self.assistant = get_assistant(self.config, self.initialize_instructions)
        self.assistant.id = self.assistant.id
        self.visualizations = None
    
    @abstractmethod
    def initialize_instructions(self):
        pass
    
    def stream_output(self, stream, message_placeholder):
        tool_outputs = []
        full_response = ''
        streaming = False
        for event in stream:
            if check_tool_call(event):
                message_placeholder.empty()
                tool_outputs += manage_tool_call(event, self.on_tool_call_created)
            if check_message_delta(event):
                text_stream = get_text_stream(event)
                if not streaming:
                    streaming = True
                    message_placeholder.empty()
                for delta in text_stream:
                    text_delta = get_text_delta(delta)
                    full_response += (text_delta or "")
                    message_placeholder.markdown(full_response + "▌")
        run_id = event.data.id
        return full_response, run_id, tool_outputs
    
    def get_assistant_response(self, user_message=None, thread_id = None):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment...🧐▌")
        if thread_id == None:
            thread = create_thread()
            thread_id = thread.id
        
        if user_message:
            _ = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )

        stream = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id,
            stream=True,
        )
        full_response, run_id, tool_outputs = self.stream_output(stream, message_placeholder)
        return full_response, run_id, tool_outputs
    
    def respond_to_tool_output(self, thread_id, run_id, tool_outputs):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment...🧐▌")
        if tool_outputs:
            stream = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=tool_outputs,
                stream=True,
            )
            full_response, _, _ = self.stream_output(stream, message_placeholder)

            with open("chat_history/tools.txt", "a") as f:
                f.write("\n\n\n\n**Tool Outputs**\n")
                f.write(tool_outputs[0]['output'])
                f.write("\n**LLM Response**\n")
                f.write(full_response)
                f.write("\n")
        message_placeholder.empty()
        return full_response

    def on_tool_call_created(self, tool):
        function = self.function_dict.get(tool.function.name)
        function_args = json.loads(tool.function.arguments)
        response = function(**function_args)
        return response
