import torch
from tqdm import tqdm
import json
import argparse
import yaml
from src.evaluation.utils import parse_file, parse_user_profile, convert_scores
from src.evaluation.prompts import Prompts
from src.config import client


class Evaluator:
    def __init__(self, args):
        self.args = args
        self.prompts = Prompts()

        # Load the file to evaluate
        with open(args['interaction_file'], 'r') as interaction_file:
            self.interaction_history = []
            for line in interaction_file:
                self.interaction_history.append(json.loads(line))

        self.data_dict = parse_file(self.args['file_name'], self.interaction_history)

        with open(args['user_profile'], 'r') as user_profile_file:
            self.user_profile = user_profile_file.read()
        self.user_profile = parse_user_profile(self.user_profile)

        # Initialize overall scores
        self.scores = {'relevance_score': 0, 'correctness_score': 0, 'entailment_score': 0, 'accessibility_score': 0,
                       'relevance_total': 0, 'correctness_total': 0, 'entailment_total': 0, 'accessibility_total': 0,
                       'relevance_na': 0, 'correctness_na': 0, 'entailment_na': 0, 'accessibility_na': 0}


    def init_assistant(self, model='gpt-4-turbo'):
        # Each evaluation is a separate thread
        assistant = client.beta.assistants.create(
            name="Response Evaluator",
            model=model,
            instructions=messages[0],
            tools=[{"type": "code_interpreter"}]
        )

        thread = client.beta.threads.create()
        return assistant, thread


    def query_assistant(self, assistant_id, thread_id, content):
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread_id
            )
            print(messages)
            return messages
        else:
            print(run.status)
            return None


    def evaluate_single_aspect(self, tool_output, llm_response, data_type, previous_query, aspect):
        if data_type == 'literature':
            messages = getattr(self.prompts, f'evaluate_{aspect}_in_references')(tool_output, llm_response, self.user_profile, previous_query)
        else:
            messages = getattr(self.prompts, f'evaluate_{aspect}_in_values_and_recommendations')(tool_output, llm_response, self.user_profile, previous_query)

        assistant, thread = self.init_assistant(self.args['llm_model'])
        response = self.query_assistant(assistant.id, thread.id, messages[1])
        if response is not None and len(messages) > 2:
            response = self.query_assistant(assistant.id, thread.id, messages[2])
        return response


    def evaluate(self):
        for i, data in tqdm(enumerate(self.data_dict)):
            # Extract each pair of tool output and llm response
            tool_output = data['tool_output']
            llm_response = data['llm_response']
            data_type = data['type']
            previous_query = data['previous_query']

            for aspect in ['relevance', 'correctness', 'entailment', 'accessibility']:
                response = self.evaluate_single_aspect(tool_output, llm_response, data_type, previous_query, aspect)

                score = convert_scores(response)
                self.scores[f'{aspect}_score'] += score[0]
                self.scores[f'{aspect}_total'] += score[1]
                self.scores[f'{aspect}_na'] += score[2]

            print(f"Data {i}/{len(data)}", f"Relevance: {self.scores['relevance_score']}/{self.scores['relevance_total']}({self.scores['relevance_na']})={self.scores['relevance_score']/(self.scores['relevance_total']+1e-6)}",
                  f"Correctness: {self.scores['correctness_score']}/{self.scores['correctness_total']}({self.scores['correctness_na']})={self.scores['correctness_score']/(self.scores['correctness_total']+1e-6)}",
                  f"Entailment: {self.scores['entailment_score']}/{self.scores['entailment_total']}({self.scores['entailment_na']})={self.scores['entailment_score']/(self.scores['entailment_total']+1e-6)}",
                  f"Accessibility: {self.scores['accessibility_score']}/{self.scores['accessibility_total']}({self.scores['accessibility_na']})={self.scores['accessibility_score']/(self.scores['accessibility_total']+1e-6)}")



if __name__ == "__main__":
    print('Torch', torch.__version__)
    # Load hyperparameters
    try:
        with open('config.yaml', 'r') as file:
            args = yaml.safe_load(file)
    except Exception as e:
        print('Error reading the config file')

    # Command-line argument parsing
    parser = argparse.ArgumentParser(description='Command line arguments')
    parser.add_argument('--model', type=str, default=None, help='Set LLM model. Choose from gpt-3.5-turbo, gpt-4-turbo, or gpt-4o')
    parser.add_argument('--file_name', type=str, default=None, help='Set the file name to evaluate')
    parser.add_argument('--user_profile', type=str, default=None, help='Set the file name containing the user profile')
    parser.add_argument('--output_dir', type=str, default="outputs/", help='Set the output directory')
    parser.add_argument('--verbose', dest='verbose', action='store_true', help='Set verbose to True')
    cmd_args = parser.parse_args()

    # Override args from config.yaml with command-line arguments if provided
    args['llm_model'] = cmd_args.model if cmd_args.model is not None else args['llm_model']
    args['file_name'] = cmd_args.file_name if cmd_args.file_name is not None else args['file_name']
    args['user_profile'] = cmd_args.user_profile if cmd_args.user_profile is not None else args['user_profile']
    args['output_dir'] = cmd_args.output_dir if cmd_args.output_dir is not None else args['output_dir']
    args['verbose'] = cmd_args.verbose if cmd_args.verbose is not None else args['verbose']

    # Initialize the evaluation class
    evaluator = Evaluator(args)