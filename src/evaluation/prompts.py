import torch
import random

from utils import *


def evaluate_relevance_in_reference(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Your task is to analyze the relevance of the model's response to the contexts by answering the following questions.",

               "Given this model's response: \n" + llm_response + "\n"
               "(1) Does the response answer the user's last question? The question is '" + previous_query + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(2) Is the response relevant to the user's profession? The profession is '" + user_profile['profession'] + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(3) Is the response relevant to the user's concern? The concern is '" + user_profile['concern'] + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(4) Is the response relevant to the user's location? The location is '" + user_profile['location'] + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(5) Is the response relevant to the user's timeline? The timeline is '" + user_profile['timeline'] + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(6) Is the response relevant to the user's scope? The scope is '" + user_profile['scope'] + "' Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "Please answer these questions one by one and output a Python list of your responses."
              ]
    return message


def evaluate_relevance_in_values_and_recommendations(tool_output, llm_response, user_profile=None, previous_query=None):
    # same as evaluate_relevance_in_reference
    return evaluate_relevance_in_reference(tool_output, llm_response, user_profile, previous_query)


def evaluate_correctness_in_reference(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Your task has two parts, and please respond to them one after the other. "
               "The first task is to extract all the meta-information about papers mentioned in the following '**Tool Outputs**', '**LLM Responses**', and '### References' paragraphs, separately. "
               "You should list information such as author names, titles, DOIs, publications, and reference links (but do not include abstract) in a Python dictionary format. Use paper titles as the keys.\n"
               "The second task is to check if each paper in the dictionaries of '**LLM Responses**' and '### References' can be found in the dictionary of '**Tool Outputs**.' "
               "You should write Python code to verify each key, i.e., paper titles. We only care about Recall but not Precision. "
               "That is to say, for any paper in '**LLM Responses**' and '### References', verify if it exists in the dictionary of '**Tool Outputs**', "
               "and if each attribute like authors, year, doi, publication, and etc, is matched as well. "
               "Note that the author names could be rewritten in a different way.",

               "Following are the texts you need to analyze:\n" + tool_output + '\n' + llm_response,

               "Solely based on this LLM's response, is it true that each paper in the '**LLM Responses**' or '### References' paragraphs can be found in the '**Tool Outputs**' paragraph "
               "and all the information is correct? Answer either 'Yes' or 'No'. "
               "In case of 'Yes', give me the total lengths of the dictionaries of '**LLM Responses**' and '### References' by filling this answer format '0/[Len_of_Dict]', where '0' means zero error. "
               "In case of 'No', provide the number of errors and the total lengths of the dictionaries of '**LLM Responses**' and '### References' by filling this answer format '[Num_of_Errors]/[Len_of_Dict]'."
               "Do NOT provide any other responses."
               ]
    return message


def evaluate_correctness_in_values_and_recommendations(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Given information in the following '**Tool Outputs**' and '**LLM Responses**', step by step identify each important terms or nouns, "
               "and verify each numerical values in the model responses associated with these nouns. "
               "You should write Python codes that inputs the numerical values in '**Tool Outputs**' and '**LLM Responses**' to check deterministically if they are matched.",

               "Following are the texts you need to analyze:\n" + tool_output + '\n' + llm_response,

               "Solely based on this LLM's response, is it true that all important terms, nouns, and numerical value in the '**LLM Responses**' are correct?"
              ]
    return message


def evaluate_entailment_in_reference(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Your task is to list all the points stated in the **LLM Response** section, and verify with the 'Abstract' of the papers in the **Tool Outputs** section. "
               "For each point, you need to further extract only important nouns, technical terms, or facts for evaluation.",

               "Following are the texts you need to analyze: \n" + tool_output + '\n' + llm_response + "\nNow, please answer these two questions:\n"
               "(1) Is there any new factual information only in **LLM Response** but not in any abstracts? You don't need to mention any subjective suggestions. Answer 'Yes', 'No', 'Could be better', or 'Not Applicable.'\n"
               "(2) Is there any contradictory information? Answer 'Yes', 'No', 'Could be better', or 'Not Applicable.'\n"
               "Please answer these questions one by one and output a Python list of your responses."
             ]
    return message


def evaluate_entailment_in_values_and_recommendations(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Your task is to list all the points stated in the **LLM Response** section, and verify with the information in the **Tool Outputs** section. "
               "For each point, you need to further extract only important nouns, technical terms, or facts for evaluation.",

               "Following are the texts you need to analyze: \n" + tool_output + '\n' + llm_response + "\nNow, please answer these two questions:\n"
               "(1) Is there any new factual information only in **LLM Response** but not in any abstracts? You don't need to mention any subjective suggestions. Answer 'Yes', 'No', 'Could be better', or 'Not Applicable.'\n"
               "(2) Is there any contradictory information? Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "Please answer these questions one by one and output a Python list of your responses."
              ]
    return message


def evaluate_accessibility_in_reference(tool_output, llm_response, user_profile=None, previous_query=None):
    message = ["Your task is to analyze the accessibility of the model's response to the human users. "
               "For each question, always answer either 'Yes', 'No', 'Could be better', or 'Not Applicable'",

               "Given this model's response: \n" + llm_response + "\n"
               "(1) Does the response contain too many jargons? Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(2) Does the response provide enough explanation? Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "(3) Does the response contain redundant or useless information? Answer 'Yes', 'No', 'Could be better', or 'Not Applicable'.\n"
               "Please answer these questions one by one and output a Python list of your responses."
              ]
    return message


def evaluate_accessibility_in_values_and_recommendations(tool_output, llm_response, user_profile=None, previous_query=None):
    # same as evaluate_accessibility_in_reference
    return evaluate_accessibility_in_reference(tool_output, llm_response, user_profile, previous_query)
