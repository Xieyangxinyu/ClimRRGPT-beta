from src.assistants.profile import ChecklistAssistant
from src.assistants.plan import Plan
from src.assistants.analyst import AnalystAssistant
from src.config import client

class AssistantRouter:
    def __init__(self, name, args={}):
        self.current_thread = client.beta.threads.create()
        self.new_thread = True
        self.assistant_dict = {
            "ChecklistAssistant": [ChecklistAssistant, "src/assistants/profile/config.yml"],
            "Plan": [Plan, "src/assistants/plan/config.yml"],
            "AnalystAssistant": [AnalystAssistant, "src/assistants/analyst/config.yml"]
        }
        Assistant = self.assistant_dict[name][0]
        config_path = self.assistant_dict[name][1]
        self.current_assistant = Assistant(config_path, self.update_assistant, **args)
    
    def update_assistant(self, name, args, new_thread = False):
        Assistant = self.assistant_dict[name][0]
        config_path = self.assistant_dict[name][1]
        self.current_assistant = Assistant(config_path, self.update_assistant, **args)
        if new_thread:
            self.current_thread = client.beta.threads.create()
            self.new_thread = True

    def get_assistant_response(self, user_message: str = None):
        self.new_thread = False
        full_response, run_id, tool_outputs = self.current_assistant.get_assistant_response(user_message, self.current_thread.id)
        if len(tool_outputs):
            full_response += self.current_assistant.respond_to_tool_output(self.current_thread.id, run_id, tool_outputs)
        elif self.new_thread:
            return self.get_assistant_response()
        if self.current_assistant.visualizations:
            full_response = [full_response, self.current_assistant.visualizations]
            self.current_assistant.visualizations = None
        return full_response
    

