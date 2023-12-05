class Template:
    def __init__(self):
        self.location = None
        self.time = None
        self.scale = None
        self.fill_out = False

    def fill_out_template(self, location, time, scale):
        self.location = location
        self.time = time
        self.scale = scale
        return f"Location: {self.location}, Time: {self.time}, Scale: {self.scale}\n"
    
    def template_check(self):
        self.fill_out = True
        return f"Now that you have all the information, you should propose how to address the users' concern.\n"
    
def get_information_about_project(template):
    return f"Location: {template.location}, Time: {template.time}, Scale: {template.scale}"