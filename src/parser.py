import re


def parse_markdown_quests(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Split the file by the horizontal rule ---
    quest_blocks = content.split('---')
    parsed_quests = []

    for block in quest_blocks:
        # Extract the Title (Anything after # QUEST:)
        name_match = re.search(r'# QUEST:\s*(.*)', block)
        if not name_match:
            continue
            
        name = name_match.group(1).strip()
        
        # Extract metadata using simple splits or regex
        # This is safer than counting lines!
        desc = re.search(r'\*\*Description\*\*:\s*(.*)', block)
        diff = re.search(r'\*\*Difficulty\*\*:\s*(\d+)', block)
        xp = re.search(r'\*\*Reward\*\*:\s*(\d+)', block)

        quest_data = {
            "name": name,
            "description": desc.group(1).strip() if desc else "",
            "difficulty": int(diff.group(1)) if diff else 1,
            "reward_xp": int(xp.group(1)) if xp else 10
        }
        parsed_quests.append(quest_data)

    return parsed_quests

# file_path = r'/home/nam/Documents/git-repos/quests/src/example.md'
# quests = parse_markdown_quests(file_path)
# print(quests)

