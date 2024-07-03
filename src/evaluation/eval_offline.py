import torch
import numpy as np
from tqdm import tqdm
import os
import json
import random
import re
import argparse
import yaml

import utils
import prompts

# OpenAI ChatGPT API
import openai
from openai import OpenAI


class Evaluator:
    def __init__(self, args):
        self.args = args

        # Load API keys or tokens
        with open('api_keys/openai_key.txt', 'r') as api_key_file:
            self.api_key = api_key_file.read()

        # Load the file to evaluate
        with open(args['interaction_file'], 'r') as interaction_file:
            self.interaction_history = json.load(interaction_file)

        self.data_dict = utils.parse_file(self.args['file_name'], self.interaction_history)

        with open(args['user_profile'], 'r') as user_profile_file:
            self.user_profile = user_profile_file.read()
        self.user_profile = utils.parse_user_profile(self.user_profile)

        # Initialize overall scores
        self.scores = {'relevance_score': 0, 'correctness_score': 0, 'entailment_score': 0, 'accessibility_score': 0}


    def init_assistant(self, model='gpt-4-turbo'):
        # Each evaluation is a separate thread
        client = OpenAI(api_key=self.api_key)
        assistant = client.beta.assistants.create(
            name="Response Evaluator",
            model=model,
            instructions=messages[0],
            tools=[{"type": "code_interpreter"}]
        )

        thread = client.beta.threads.create()
        return client, assistant, thread


    def query_assistant(self, client, assistant_id, thread_id, content):
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
            messages = getattr(prompts, f'evaluate_{aspect}_in_references')(tool_output, llm_response, self.user_profile, previous_query)
        else:
            messages = getattr(prompts, f'evaluate_{aspect}_in_values_and_recommendations')(tool_output, llm_response, self.user_profile, previous_query)

        client, assistant, thread = self.init_assistant(self.args['llm_model'])
        response = self.query_assistant(client, assistant.id, thread.id, messages[1])
        if response is not None and len(messages) > 2:
            response = self.query_assistant(client, assistant.id, thread.id, messages[2])
        return response


    def evaluate(self):
        for data in self.data_dict:
            # Extract each pair of tool output and llm response
            tool_output = data['tool_output']
            llm_response = data['llm_response']
            data_type = data['type']
            previous_query = data['previous_query']

            current_scores = []
            for aspect in ['relevance', 'correctness', 'entailment', 'accessibility']:
                score = self.evaluate_single_aspect(tool_output, llm_response, data_type, previous_query, aspect)
                current_scores.append(score)
                self.scores[f'{aspect}_score'] += score

            print(f"Relevance: {current_scores[0]}, Correctness: {current_scores[1]}, Entailment: {current_scores[2]}, Accessibility: {current_scores[3]}")


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