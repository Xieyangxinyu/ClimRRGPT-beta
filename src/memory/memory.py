from src.config import client, model, chat_history_path

class Profile:
    def __init__(self):
        self.checklist = "Why is the user interested in learning about wildfire and climate change?"
        self.profile_complete = False
        self.profile = ""
        self.initialized = False
        self.plan = ""
        self.messages = []

    
    def write_summary(self):
        #messages = self.messages[2:] + [{"role": "system", "content": f"User Profile Summary: {self.profile}\n\n**User Profile Summary Enhancement Task**\n\nContext: You are a professional consultant with expertise in wildfire risk and climate change. Your objective is to refine and elaborate on the user's profile summary. This summary should be crafted based on the details discussed in the previous conversation.\n\n**Instructions:**\n- Ensure your summary addresses all the points listed in the provided checklist:{self.checklist}.\n- If the user posed any questions during the previous conversation, include and address these questions in your summary.\n- Only output the summary and use the template below:\n\n The user is [user profile information]...\nIn addressing the checklist, the user provided the following insights: [Question]: [Answer]\n[Question]: [Answer]\n...\nApart from the checklist items, the user also inquired about...\n\n"}]
        messages = [{"role": "system", "content": f"User Profile Summary: {self.profile}\n\n**User Profile Summary Enhancement Task**\n\nContext: You are an assistant with expertise in wildfire risk and climate change. Your objective is to refine and elaborate on the user's profile summary. This summary should be crafted based on the details discussed in the following conversation.\n\n**Instructions:**\n- Ensure your summary addresses all the points listed in the provided checklist:{self.checklist}.\n- If the user posed any questions during the previous conversation, include and address these questions in your summary.\n- Only output the summary and use the template below:\n\n The user is [user profile information]..."}] + self.messages[2:]
        self.profile = client.chat.completions.create(
            model=model,
            messages=messages,
        ).choices[0].message.content
        # save profile to chat history
        with open(chat_history_path + "profile.md", "w") as f:
            f.write(self.profile)
    
    
    def create_plan(self):
        prompt_message =  {"role": "system", "content": f"As an expert consultant specializing in wildfire risks and climate change, your role is to assist users with various aspects of wildfire and climate change understanding and mitigation. Here are the only ways that you can help:\n - Interpreting data such as the Fire Weather Index (FWI), long term fire history records, and recent fire incident data.\n- Researching relevant academic papers that could inform your recommendations.\nHere is the user's profile: {self.profile}.\n\n- Create a short step-by-step plan that outlines how to effectively engage with the user in order to address their concerns. The plan should explain the process of extracting relevant data and research papers to inform your recommendations."}

        messages = [prompt_message, {"role": "user", "content": "Tell me about how you plan to assist me in 100 words!"}]
        self.plan = client.chat.completions.create(
            model=model,
            messages=messages,
        ).choices[0].message.content
        # save plan to chat history
        with open(chat_history_path + "plan.md", "w") as f:
            f.write(self.plan)
    
    def checklist_complete(self):
        self.messages = self.messages[:-1]
        self.write_summary()
        if not self.initialized:
            self.initialized = True
            messages = [{"role": "system", 
                        "content": f"You are a professional consultant with expertise in wildfire risk management and the impact of climate change. Your client is seeking your guidance but may not have a comprehensive understanding of wildfire risks and climate change. Your goal is to effectively gather information from the client to assess their specific concerns and informational needs regarding wildfires and climate change. Based on the user's profile and your expertise, develop a checklist of three clarifying questions to ask the client. These questions should be designed to elucidate the client's level of awareness, specific areas of concern, and any particular aspects of wildfire risks and climate change they are interested in exploring. If the user is working on a project, you may ask the location, time or scale. Your output should be limited to these three questions, clearly formulated to maximize the value of the client's responses.\n\nHere is the user's profile: {self.profile}.\n\nOnly output the list of questions."}]
            self.checklist = client.chat.completions.create(
                model=model,
                messages=messages,
            ).choices[0].message.content
            # save checklist to chat history
            with open(chat_history_path + "checklist.md", "w") as f:
                f.write(self.checklist)
        elif not self.profile_complete:
            self.profile_complete = True
            self.create_plan()
        return "Checklist Complete"