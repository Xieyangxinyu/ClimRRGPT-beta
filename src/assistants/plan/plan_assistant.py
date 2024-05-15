from src.assistants.assistant import Assistant
from src.config import client, model
import streamlit as st
import json

class Plan(Assistant):
    def __init__(self, config_path, update_assistant, checklist):
        self.checklist = checklist
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "plan_complete": self.plan_complete,
        }
        # create an assistant
        self.feedback_assistant = client.beta.assistants.create(
                name="FeedbackAssistant",
                instructions= f"Check the response carefully for correctness and give constructive criticism for how to improve it. The plan assistant only has access to these datasets:\n{self.config['available_datasets']}.\n\n",
                model=model
            )
    
    def initialize_instructions(self):
        return f"{self.config['instructions']}\n{self.config['available_datasets']}\n{self.config['example']}\nHere is the information about your client: {self.checklist}"
    
    def plan_complete(self, plan: str):
        args = {"checklist": self.checklist,
                "plan": plan}
        self.update_assistant("AnalystAssistant", args, new_thread = True)
        return "Change Thread"
    
    
    def get_assistant_response(self, user_message=None, thread_id=None):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment...🧐▌")
        if user_message:
            _ = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=self.assistant.id
        )

        if run.status == 'requires_action':
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                self.on_tool_call_created(tool)
                message_placeholder.empty()
            return "", run.id, []

        while run.status != 'completed':
            pass

        if run.status == 'completed': 
            run_2 = client.beta.threads.runs.create_and_poll(
                thread_id=thread_id,
                assistant_id=self.feedback_assistant.id
            )
            while run_2.status != 'completed':
                pass
            messages = client.beta.threads.messages.list(
                        thread_id=thread_id
                    )
            print(messages.data[0].content[0].text.value)
        
        message_placeholder.empty()
        return super().get_assistant_response(user_message, thread_id)
    
    def respond_to_tool_output(self, thread_id, run_id, tool_outputs):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment...🧐▌")
        if tool_outputs:
            if tool_outputs[0]['output'] == "Plan":
                tool_outputs[0]['output'] = self.config['dataset_decision'] + '\n' + self.checklist
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs,
                )
                while run.status != 'completed':
                    pass
                if run.status == 'completed': 
                    messages = client.beta.threads.messages.list(
                        thread_id=thread_id
                    )
                    print(messages.data[0].content[0].text.value)
                message_placeholder.empty()
                full_response, _, _ = self.get_assistant_response(user_message="Explain to me what your plan is and ask me if I have any questions.",
                                                                  thread_id=thread_id)
            else:
                message_placeholder.empty()
                full_response = super().respond_to_tool_output(thread_id, run_id, tool_outputs)
        message_placeholder.empty()
        return full_response
