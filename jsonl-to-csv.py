import json

# We want three columns: AuthorID, AuthorName, Content, and DateTime
with open("./TowaShrug.json", "r", encoding="utf-8") as f:
    for line in f:
        msg = json.loads(line)[0]
        with open("TowaShrug.csv", "a", encoding="utf-8") as file:
            file.write(
                f"{msg['author']['id']},{msg['author']['username']},{msg['content']},{msg['timestamp']}\n"
            )
