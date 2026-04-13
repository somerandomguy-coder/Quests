Use this prompt to generate a markdown quest file for the Quests app.

Goal:
Create a markdown document containing multiple quests that can be imported directly into the app.
The output must follow the exact schema and formatting rules below.

Formatting rules:
- Each quest must start with a title line in this exact format: `# QUEST: <quest name>`
- Separate every quest block with a line containing only `---`
- Use plain markdown bullet points for fields
- Supported fields are:
  - `Description`
  - `Difficulty`
  - `Reward`
  - `Deadline`
  - `Recurrence`
  - `Tags`
  - `Important Level`
- Field names are case-insensitive, but keep the spelling above for consistency
- Do not invent any other field names
- Do not wrap values in code fences or JSON

Schema rules:
- `Description`: optional free text
- `Difficulty`: required integer, must be `1`, `2`, or `3`
- `Reward`: optional positive integer XP value, for example `50 XP`
- `Deadline`: optional date in ISO format `YYYY-MM-DD`
- `Recurrence`: optional, must be one of `daily`, `weekly`, or `monthly`
- `Tags`: optional comma-separated list, for example `study, work, deep-focus`
- `Important Level`: optional integer from `0` to `100`

Quality rules:
- Every quest name must be unique inside the same file
- Keep quests realistic and actionable
- Prefer short, concrete descriptions
- Mix task difficulty and importance values so the importer and mission sorter have variety
- If no deadline is needed, omit the deadline field entirely
- If no recurrence is needed, omit the recurrence field entirely
- If no tags are needed, omit the tags field entirely

Template:
# QUEST: Example quest name
- Description: One or two sentences describing the task.
- Difficulty: 2
- Reward: 50 XP
- Deadline: 2026-04-20
- Tags: study, work
- Important Level: 80

---

Example with recurrence:
# QUEST: Water the plants
- Description: Check the indoor plants and water only the dry ones.
- Difficulty: 1
- Reward: 10 XP
- Recurrence: weekly
- Tags: home, routine
- Important Level: 35

When responding:
- Output only the markdown file contents
- Do not explain the format
- Do not add intro text
- Do not add commentary after the last quest
