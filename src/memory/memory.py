from src.config import client, model

class Profile:
    def __init__(self):
        self.checklist = "Why is the user interested in learning about wildfires?"
        self.profile_complete = False
        self.summary = ""
        self.initialized = False
        self.plan = ""
        self.messages = []

    
    def write_summary(self):
        messages = self.messages[2:] + [{"role": "system", "content": f"User Profile Summary: {self.summary}\n\nYou're a professional consultant specializing in wildfire risk and climate change. Your task is to improve the user profile summary based on the previous conversation. Make sure your summary answer every question in checklist and **if the user asked you questions in the previous conversation, include these questions in your summary**. **Checklist**:{self.checklist}. Only output the summary. Use the template:\n\n The user is [user profile information]...\n[Question 1]: [Answer]\n[Question 2]: [Answer]\n...\nBesides things on the checklist, the user asked about ...\n\n"}]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        ).choices[0].message.content
        self.summary = response
    
    def create_plan(self):
        prompt_message =  {"role": "system", "content": f"As an expert consultant specializing in wildfire management, your role is to assist users with various aspects of wildfire understanding and mitigation. Here's how you can help:\n - Interpreting data such as the Fire Weather Index (FWI), long term fire history records, and recent fire incident data.\n- Researching relevant academic papers that could inform your recommendations.\nHere is the user's profile: {self.summary}.\n\n- In 100 words, create a short step-by-step plan that outlines how to effectively engage with the user in order to address their concerns. The plan should explain the process of extracting relevant data and research papers to inform your recommendations. "}

        messages = [prompt_message, {"role": "user", "content": "Tell me about how you plan to assist me in 100 words!"}]
        self.plan = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=1
        ).choices[0].message.content
    
    def checklist_complete(self):
        self.messages = self.messages[:-1]
        self.write_summary()
        if not self.initialized:
            self.initialized = True
            messages = [{"role": "system", 
                        "content": f"You're a professional consultant specializing in wildfire risk and climate change. Your task is to gather information from the user, i.e. your client, to understand what their concerns are and what they want to know about wildfires. Keep in mind that you know wildfire risks while your client do not.\n{self.summary}\nCreate a checklist of 3 questions to ask the user. If the user is working on a project that could be impacted by wildfire, ask about the specifics of their project (for example, location, timeline etc). Only output the questions."}]
            self.checklist = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=1
            ).choices[0].message.content
        elif not self.profile_complete:
            self.profile_complete = True
            self.create_plan()
        return "Checklist Complete"