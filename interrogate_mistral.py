import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"

print("Loading Mistral 7B model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16,
    low_cpu_mem_usage=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

print("Model loaded.\n")

def reformulate(sentence, max_new_tokens=150):
    messages = [
        {
            "role": "user",
            "content": (
                "Rewrite the following sentence with better reformulation and correct grammar. "
                "Output multiple proposed sentences, nothing else.\n"
                f"Sentence: {sentence}"
            ),
        }
    ]

    inputs = tokenizer.apply_chat_template(messages, return_tensors="pt", return_dict=True)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=0.7,
        do_sample=True,
        top_p=0.9,
    )

    input_len = inputs["input_ids"].shape[1]
    answer = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
    return answer.strip()

if __name__ == "__main__":
    print("Type a sentence to reformulate it. Type 'exit' to quit.\n")

    while True:
        sentence = input("You: ")

        if sentence.lower() in ["quit", "exit", "bye"]:
            print("Goodbye!")
            break

        if not sentence.strip():
            continue

        result = reformulate(sentence)
        print(f"\nReformulated: {result}\n")
