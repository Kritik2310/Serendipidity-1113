from agents.lab_mapper import run_lab_mapper

lab_input = {
    "subject_id": 10002,
    "hadm_id": 198765
}

output = run_lab_mapper(lab_input)
print(output)