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
    
    def get_assistant_response(self, user_message=None, thread_id=None):
        if user_message:
            return super().get_assistant_response(user_message = user_message + "\n\nUpon completing the checklist, share your checklist with me to confirm the accuracy of the information.\nWhen you are all done, call the function `checklist_complete()` with your completed checklist.", thread_id = thread_id)
        else:
            return super().get_assistant_response(thread_id = thread_id)
    
    def checklist_complete(self, checklist: str):
        
        if False: #self.checklist == "initial_checklist":
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
            
            self.update_assistant("ChecklistAssistant", args)
            return "Please tell your client that you will ask a few more follow-up questions to ask them for more details."
        
        args = {"checklist": checklist}
        self.update_assistant("Plan", args)
        return "Plan"