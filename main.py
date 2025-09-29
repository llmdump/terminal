import json
import colorama
import math
colorama.init(autoreset=True)
start=(105, 120, 250)
end=(76, 200, 229)
def get_gradient(steps,n):

    ans=[0,0,0]
    t=n/(steps-1)
    ans[0]=math.floor((1-t)*start[0]+t*end[0])
    ans[1]=math.floor((1-t)*start[1]+t*end[1])
    ans[2]=math.floor((1-t)*start[2]+t*end[2])
    return f"\x1b[1;38;2;{ans[0]};{ans[1]};{ans[2]};49m"
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
    for index,j in enumerate(i):
        logo+=get_gradient(len(i),index)+j
    logo+="\n"+reset_color
print(logo)