from src.assistants.assistant import Assistant
from src.assistants.analyst.FWI import FWI_retrieval
from src.assistants.analyst.history import long_term_fire_history_records
from src.assistants.analyst.incident import recent_fire_incident_data
from src.assistants.analyst.literature import literature_search
from src.assistants.analyst.census import get_census_info
from src.config import client
import streamlit as st
from src.utils import get_openai_response, stream_static_text


class AnalystAssistant(Assistant):
    def __init__(self, config_path, update_assistant, checklist, plan):
        self.checklist = checklist
        self.plan = plan
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "long_term_fire_history_records": long_term_fire_history_records,
            "recent_fire_incident_data": recent_fire_incident_data,
            "fire_weather_index": FWI_retrieval,
            "literature_search": literature_search,
            "census": get_census_info
        }

        stream_text = stream_static_text(self.config['init_message'])
        st.write_stream(stream_text)
        st.session_state.messages.append({"role": "assistant", "content": self.config['init_message']})

    def initialize_instructions(self):
        return self.config["instructions"] + "\n" + self.checklist + "\nHere is your plan to assist your clinet:\n" + self.plan
    
    def get_follow_up(self, thread_id, addtional_message):
        thread_messages = client.beta.threads.messages.list(thread_id).data
        thread_messages = thread_messages[::-1]
        roles = [message.role for message in thread_messages]
        thread_messages = [message.content[0].text.value for message in thread_messages]
        messages = [{"role": "system", "content": f"Here is your overall plan to assist your client:\n{self.plan}\n\n"}] + [{"role": role, "content": content} for role, content in zip(roles, thread_messages)] + addtional_message

        follow_up = get_openai_response(messages)
        
        return follow_up
        

    def decision_point(self, thread_id, user_message = None, tools = []):
        follow_up = ""
        thread_messages = client.beta.threads.messages.list(thread_id).data
        if len(thread_messages) > 0 and thread_messages[0].role == "user":
            user_message = thread_messages[0].content[0].text.value
        if user_message:
            addtional_message = [{"role": "system", "content": "If you can directly respond to the client's questions without the need to retrieve data or literature, you will simply write down: 'Respond to the client's questions.'\n\nIf the client doesn't seem to have a question in mind, it is instead a good idea to proceed with your plan, then you will simply write down: 'Proceed with the plan.'\n\n**Only output** either 'Respond to the client's questions.' or 'Proceed with the plan.'"}]
            follow_up = self.get_follow_up(thread_id, addtional_message)
            #if "Directly respond to the client's questions." in follow_up:
            #    return follow_up, []
        
        addtional_message = [{"role": "system", "content": "First, decide what you would like to do for this step in less than 20 words. Next, identify at most one tool to use for this step: 'fire_weather_index', 'long_term_fire_history_records', 'recent_fire_incident_data', 'literature_search' or `no tool needed`.\n\nFor example, 'Analyze the Fire Weather Index dataset. `fire_weather_index`.' or 'Assess the impact of the rise in recent wildfire activity with some literature search. `literature_search`.' Search for relevant literature on the impact of wildfires on water resources and unpaved roads. `literature_search`.' or 'Develop recommendations to mitigate wildfire risks. `no tool needed`.' or 'Understand local population to see who will be impacted by the risk.' `census`. \n\n**Make sure to output** the tool you would like to use."}]

        available_tools = self.get_follow_up(thread_id, addtional_message)

        follow_up += " " + available_tools
        
        print(follow_up)
        return follow_up, tools
    
    def get_assistant_response(self, user_message=None, thread_id = None):
        message_placeholder = st.empty()
        stream_text = stream_static_text("I'm working diligently on my analysis for you... This may take a bit of time...🧐 Please do not respond yet ...▌")
        message_placeholder.write_stream(stream_text)
        
        tools = self.assistant.tools
        if user_message is not None:
            _ = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )
            self.visualizations = []

        message, tools = self.decision_point(thread_id, user_message, tools)

        _ = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="assistant",
            content=message
        )
        
        stream = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id,
            stream=True,
            instructions=f"Here is the information about your client:\n{self.checklist}\nHere is your overall plan to assist your client: {self.plan}",
            tools = tools
        )
        full_response, run_id, tool_outputs = self.stream_output(stream, message_placeholder)

        return full_response, run_id, tool_outputs
    
    def add_appendix(self, function_response, function_name):
        config = self.config
        if config["available_functions"][function_name]["appendix"]:
            path = config["path"] + "appendix/" + config["available_functions"][function_name]["appendix"]
            with open(path, "r") as f:
                appendix = f.read()
            function_response += appendix
        return function_response
    
    def display_maps(self, maps):
        if maps is None:
            return
        caption, maps = maps
        st.write(caption)
        st.pydeck_chart(maps)

    def display_plots(self, figs):
        if figs is None or len(figs) == 0:
            return
        for fig in figs:
            st.plotly_chart(fig, use_container_width=True)

    def on_tool_call_created(self, tool):
        response = super().on_tool_call_created(tool)
        if type(response) != str:
            response, maps, figs = response
            self.display_maps(maps)
            self.display_plots(figs)
            if maps is not None or len(figs) > 0:
                self.visualizations.append([maps, figs])
        response = self.add_appendix(response, tool.function.name)
        return response


