import ollama

response = ollama.generate("llama3:instruct", 'Why is the sky blue?', raw=True)
print(response)