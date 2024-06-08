from openai import OpenAI
client = OpenAI()

thread = client.beta.threads.retrieve("thread_mN7cRIaFBiTFQBo4oAW7t7MK")

thread_messages = client.beta.threads.messages.list(thread.id)

print(thread_messages)
exit()

for message in thread_messages:
    if message.role != 'user':
        client.beta.threads.messages.delete(
            message_id=message.id,
            thread_id=thread.id,
        )
    else:
        break

runs = client.beta.threads.runs.list(
  thread.id
)

for run in runs.data:
    if run.status != "completed":
        if run.status == "running":
            client.beta.threads.runs.cancel(
                thread_id=thread.id,
                run_id=run.id
            )

