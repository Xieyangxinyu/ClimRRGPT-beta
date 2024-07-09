import os
import json
import yaml
import argparse
from src.evaluation.utils import parse_current_entry


def score_formatting(sum_, length):
    return f"{sum_/length:.4f}({sum_}/{length})"

def extract_expert_score(interaction_history):
    expert_score = {
        "relevance": [],
        "entailment": [],
        "accessibility": []
    }

    score_map = {
        "Yes": 1,
        "No": 0,
        "Could be better": 0.5,
    }

    for aspect in expert_score.keys():
        for entry in interaction_history:
            parsed_entry = parse_current_entry(entry, aspect)
            # remove 'Not Applicable' from the list
            parsed_entry = [score_map[x] for x in parsed_entry if x != 'Not Applicable']
            expert_score[aspect] += parsed_entry

    print_message = f"Expert scores: \nRelevance: {score_formatting(sum(expert_score['relevance']), len(expert_score['relevance']))}\nEntailment: {score_formatting(sum(expert_score['entailment']), len(expert_score['entailment']))}\nAccessibility:{score_formatting(sum(expert_score['accessibility']), len(expert_score['accessibility']))}"

    print(print_message)
    return expert_score

for case in ["Beaverton_mitigation_policy", "Chicago_fire", "Mora_county_mitigation", "Virginia_forest"]:

    with open(f"{case}/interaction.jsonl", 'r') as interaction_file:
        interaction_history = []
        for line in interaction_file:
            interaction_history.append(json.loads(line))

    expert_score = extract_expert_score(interaction_history)
    