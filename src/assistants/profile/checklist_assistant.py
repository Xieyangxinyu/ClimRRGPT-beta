from src.assistants.assistant import Assistant
from src.config import client, model
import streamlit as st

class ChecklistAssistant(Assistant):
    def __init__(self, config_path, update_assistant, checklist="initial_checklist"):
        self.checklist = checklist
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "checklist_complete": self.checklist_complete,
        }

    def initialize_instructions(self):
        check_list = self.config["initial_checklist"]
        if self.checklist != "initial_checklist":
            check_list = self.checklist
        return self.config["instructions"] + "\n" + check_list
    
    def checklist_complete(self, checklist: str):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment. ...🧐▌")
        if self.checklist == "initial_checklist":
            follow_up = client.chat.completions.create(
                model=model,
                messages = [
                    {"role": "system", "content": self.config["follow_up_instructions"]},
                    {"role": "user", "content": checklist}
                    ]
                ).choices[0].message
            
            print(follow_up.content)

            updated_checklist = client.chat.completions.create(
                model=model,
                messages = [
                    follow_up,
                    {"role": "user", "content": self.config["format_instructions"]}
                    ]
                ).choices[0].message.content
            
            print(updated_checklist)
            args = {
                "checklist": checklist + '\n' + updated_checklist
            }
            message_placeholder.empty()
            self.update_assistant("ChecklistAssistant", args)
            return "Please tell your client that you will ask a few more follow-up questions to ask them for more details."
        
        args = {"checklist": checklist}
        message_placeholder.empty()
        self.update_assistant("Plan", args)
        return "Plan"