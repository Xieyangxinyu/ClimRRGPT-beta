from src.assistants.assistant import Assistant
from src.assistants.analyst.FWI import fire_weather_index
from src.assistants.analyst.history import long_term_fire_history_records
from src.assistants.analyst.incident import recent_fire_incident_data
from src.assistants.analyst.literature import literature_search
from src.config import client, model
import streamlit as st

class AnalystAssistant(Assistant):
    def __init__(self, config_path, update_assistant, checklist, plan):
        self.checklist = checklist
        self.plan = plan
        super().__init__(config_path, update_assistant)
        self.function_dict = {
            "long_term_fire_history_records": long_term_fire_history_records,
            "recent_fire_incident_data": recent_fire_incident_data,
            "fire_weather_index": fire_weather_index,
            "literature_search": literature_search
        }

    def initialize_instructions(self):
        return self.config["instructions"] + "\n" + self.checklist + "\nHere is your plan to assist your clinet:\n" + self.plan
    
    def get_follow_up(self, thread_id, addtional_message):
        thread_messages = client.beta.threads.messages.list(thread_id)
        thread_messages = thread_messages.data
        thread_messages = thread_messages[::-1]
        roles = [message.role for message in thread_messages]
        thread_messages = [message.content[0].text.value for message in thread_messages]
        messages = [{"role": "system", "content": f"Here is your overall plan to assist your client:\n{self.plan}\n\n"}] + [{"role": role, "content": content} for role, content in zip(roles, thread_messages)] + addtional_message

        follow_up = client.chat.completions.create(
            model=model,
            messages = messages
            ).choices[0].message.content
        return follow_up
        

    def decision_point(self, thread_id, user_message = None, tools = []):
        if user_message:
            addtional_message = [{"role": "system", "content": "If you can directly respond to the client's questions, you will simply write down: 'Directly respond to the client's questions.'\n\nIf the client doesn't seem to have a question in mind, it is instead a good idea to proceed with your plan, then you will simply write down: 'Proceed with the plan.'\n\n**Only output** either 'Directly respond to the client's questions.' or 'Proceed with the plan.'"}]
            follow_up = self.get_follow_up(thread_id, addtional_message)
            print(follow_up)
            if "Directly respond to the client's questions." in follow_up:
                return follow_up, []
        addtional_message = [{"role": "system", "content": "First, decide what you would like to do for this step in less than 20 words. Next, identify a single tool to use for this step: 'fire_weather_index', 'long_term_fire_history_records', 'recent_fire_incident_data', or 'literature_search'.\n\nFor example, 'Analyze the Fire Weather Index dataset. `fire_weather_index`.' or 'Assess the impact of the rise in recent wildfire activity with some literature search. `literature_search`.' or 'Develop recommendations to mitigate wildfire risks with some literature search. `literature_search`.' \n\n**Only output** the tool you would like to use."}]
        follow_up = self.get_follow_up(thread_id, addtional_message)
        try:
            chosen_tool = follow_up.split("`")[1].split("`")[0]
            tools = [tool for tool in tools if tool.function.name == chosen_tool]
        except:
            tools = []
        print(follow_up)

        return follow_up, tools
    
    def get_assistant_response(self, user_message=None, thread_id = None):
        message_placeholder = st.empty()
        message_placeholder.markdown("Let me think about that for a moment...🧐▌")

        tools = self.assistant.tools
        if user_message:
            _ = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )

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
    
    def display_plots(self, figs):
        self.visualizations = figs
        for fig in figs:
            st.plotly_chart(fig, use_container_width=True)

    def on_tool_call_created(self, tool):
        response = super().on_tool_call_created(tool)
        if type(response) != str:
            response, figs = response
            self.display_plots(figs)
        response = self.add_appendix(response, tool.function.name)
        return response


