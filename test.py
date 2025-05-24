import ollama

response = ollama.generate("qwen3", 'Why is the sky blue?', raw=True)
print(response)