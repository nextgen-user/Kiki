from ast import literal_eval
x="""[
  {
    "response": "Okay, I understand. I will remember the objects and locations in your house.",
    "direction": "NONE",
    "STEPS": "NONE"
  }
]"""
print(literal_eval((x))[0]['response'])