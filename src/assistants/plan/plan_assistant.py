from src.assistants.assistant import Assistant
from src.config import client
import streamlit as st

class Plan(Assistant):
    def __init__(self, config_path, update_assistant, checklist):
        self.checklist = checklist
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "plan_complete": self.plan_complete,
        }
    
    def initialize_instructions(self):
        return self.config["instructions"] + "\n" + self.checklist
    
    def plan_complete(self, plan: str):
        args = {"checklist": self.checklist,
                "plan": plan}
        self.update_assistant("AnalystAssistant", args, new_thread = True)
        return "Change Thread"
    
    def respond_to_tool_output(self, thread_id, run_id, tool_outputs):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment. ...🧐▌")
        if tool_outputs:
            if tool_outputs[0]['output'] == "Plan":
                tool_outputs[0]['output'] = self.config['dataset_decision'] + '\n' + self.checklist
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs,
                )
                if run.status == 'completed': 
                    messages = client.beta.threads.messages.list(
                        thread_id=thread_id
                    )
                    print(messages.data[0].content[0].text.value)
                run = client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content="Explain to me what your plan is and ask me if I have any questions."
                )
                if run.status == 'completed': 
                    messages = client.beta.threads.messages.list(
                        thread_id=thread_id
                    )
                    print(messages.data[0].content[0].text.value)
                message_placeholder.empty()
                full_response, _, _ = self.get_assistant_response(thread_id=thread_id)
            else:
                message_placeholder.empty()
                full_response = super().respond_to_tool_output(thread_id, run_id, tool_outputs)
        message_placeholder.empty()
        return full_response
