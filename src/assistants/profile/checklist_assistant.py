from src.assistants.assistant import Assistant
from src.config import client, model
import streamlit as st
from src.utils import get_openai_response, stream_static_text


def verify_location_on_map(lat, lon):
    st.session_state.lat = lat
    st.session_state.lon = lon
    st.session_state.location_confirmed = False
    return "Ask the client to confirm the location by clicking the 'Confirm Location' button."

class ChecklistAssistant(Assistant):
    def __init__(self, config_path, update_assistant, checklist=None):
        self.checklist = checklist
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "checklist_complete": self.checklist_complete,
            "checklist_update": self.checklist_update,
            "verify_location_on_map": verify_location_on_map
        }
        if checklist is not None:
            self.init_message_sent = True
        else:
            self.init_message_sent = False

    def initialize_instructions(self):
        if self.checklist is not None:
            check_list = self.checklist
        else:
            check_list = self.config["initial_checklist"]
        return self.config["instructions"] + "\n" + check_list
    
    def get_assistant_response(self, user_message=None, thread_id=None):
        if user_message:
            #return super().get_assistant_response(user_message = user_message + "\n\nUpon completing the checklist, share your checklist with me to confirm the accuracy of the information.\nWhen you are all done, call the function `checklist_complete()` with your completed checklist.", thread_id = thread_id)
            return super().get_assistant_response(user_message = user_message, thread_id = thread_id)
        else:
            if not self.init_message_sent:
                self.add_assistant_message("Let's get started with our first question: What is your professional background?", thread_id)
                self.init_message_sent = True
                stream_text = stream_static_text(self.config['init_message'])
                st.write_stream(stream_text)
                return self.config['init_message'], None, []
            return super().get_assistant_response(thread_id = thread_id)
    

    def checklist_update(self, checklist: str):
        if self.checklist is not None:
            return "Checklist has already been updated."
        message_placeholder = st.empty()
        message_placeholder.markdown("I am coming up with a few follow-up questions. This may take a bit of time...🧐▌")

        follow_up = client.chat.completions.create(
            model=model,
            messages = [
                {"role": "system", "content": self.config["follow_up_instructions"]},
                {"role": "user", "content": checklist}
                ],
            top_p=0.95,
            ).choices[0].message
        
        print(follow_up.content)

        updated_checklist = get_openai_response(
            messages = [
                follow_up,
                {"role": "system", "content": self.config["format_instructions"]}
                ],
        )
        
        # TODO:
        # 1. understand typical concerns of people with a specific type of profession and concern
        # e.g. emergency/hazard mitigation planners are interested in 1/ location 2/ intensity of hazard 3/ probability of hazard 4/ vulnerability of the community impacted by the hazard
        # e.g. community planners are interested in 1/ location of the new community 2/ what risk will the new community face 3/ how to design the community to mitigate the risk
        # e.g. flood plan developers are interested in how wildfire will change the flood risk in the area
        # e.g. land managers ...
        # few shot prompting? generate more questions and filter out the most relevant ones that can be addressed by subsequent data and literature review in the overall experience
        # 2. check if these typical concerns are covered in the checklist
        # 3. if not, ask follow-up questions to check if these concerns should be added to the checklist


        updated_checklist += "\n\nFor each question on the checklist, ask the client if they are interested in addressing it with your assistance today. \n\n**After you confirm the accuracy of all the information, call the function `checklist_complete()` with your completed checklist.**"
        args = {
            "checklist": checklist + "\n" + updated_checklist
        }
        
        self.update_assistant("FollowUpAssistant", args)
        message_placeholder.empty()

        return "Checklist has been updated. Please tell your client that you have come up with a few more follow-up questions and will ask them for more details. Ask the client if they are ready to proceed."
        
    def checklist_complete(self, checklist: str):

        args = {"checklist": checklist}
        self.update_assistant("PlanAssistant", args)
        with open("chat_history/user_profile.txt", "w") as file:
            file.write(checklist)
        return "Plan"