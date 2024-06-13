from src.assistants.assistant import Assistant
from src.config import client, model
import streamlit as st


def verify_location_on_map(lat, lon):
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.location_confirmed = False
    return "Ask the client to confirm the location by clicking the 'Confirm Location' button."

class ChecklistAssistant(Assistant):
    def __init__(self, config_path, update_assistant, checklist="initial_checklist"):
        self.checklist = checklist
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "checklist_complete": self.checklist_complete,
            "verify_location_on_map": verify_location_on_map
        }

    def initialize_instructions(self):
        check_list = self.config["initial_checklist"]
        if self.checklist != "initial_checklist":
            check_list = self.checklist
        return self.config["instructions"] + "\n" + check_list
    
    def get_assistant_response(self, user_message=None, thread_id=None):
        if user_message:
            #return super().get_assistant_response(user_message = user_message + "\n\nUpon completing the checklist, share your checklist with me to confirm the accuracy of the information.\nWhen you are all done, call the function `checklist_complete()` with your completed checklist.", thread_id = thread_id)
            return super().get_assistant_response(user_message = user_message, thread_id = thread_id)
        else:
            return super().get_assistant_response(thread_id = thread_id)
    
    def checklist_complete(self, checklist: str):
        
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
            # TODO:
            # 1. understand typical concerns of people with a specific type of profession and concern
            # e.g. emergency/hazard mitigation planners are interested in 1/ location 2/ intensity of hazard 3/ probability of hazard 4/ vulnerability of the community impacted by the hazard
            # e.g. community planners are interested in 1/ location of the new community 2/ what risk will the new community face 3/ how to design the community to mitigate the risk
            # e.g. flood plan developers are interested in how wildfire will change the flood risk in the area
            # e.g. land managers ...
            # few shot prompting? generate more questions and filter out the most relevant ones that can be addressed by subsequent data and literature review in the overall experience
            # 2. check if these typical concerns are covered in the checklist
            # 3. if not, ask follow-up questions to check if these concerns should be added to the checklist


            print(updated_checklist)
            args = {
                "checklist": checklist + '\n' + updated_checklist
            }
            
            self.update_assistant("ChecklistAssistant", args)
            return "Please tell your client that you will ask a few more follow-up questions to ask them for more details. When you are done with the follow-up questions, call the function `checklist_complete()` with the updated checklist."
        
        
        args = {"checklist": checklist}
        self.update_assistant("PlanAssistant", args)
        with open("chat_history/checklist.txt", "w") as file:
            file.write(checklist)
        return "Plan"