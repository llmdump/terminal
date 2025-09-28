import json
import colorama
colorama.init(autoreset=True)
llm_color="\x1b[1;38;2;193;198;220;49m"
pipe_color="\x1b[1;38;2;255;255;255;49m"
dump_color="\x1b[1;38;2;71;82;109;49m"
reset_color="\x1b[0;39;49m"
with open("logo.txt") as f:
    raw_logo=f.read()
with open("logo.json") as f:
    sections=json.load(f).get("sections", [])
logo=""
for i in raw_logo.split("\n"):
    logo += f"{llm_color}{i[:sections[0]]}{pipe_color}{i[sections[0]:sections[1]]}{dump_color}{i[sections[1]:]}{reset_color}\n"
