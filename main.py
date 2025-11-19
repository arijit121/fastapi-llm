from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import List, Optional
import os

# Initialize FastAPI
app = FastAPI(title="Qwen2 Chatbot API", version="1.0")

# Load Qwen2-Chat model
print("Loading model... (this may take some time)")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Chat")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-7B-Chat",
    torch_dtype=torch.float16,
    device_map="auto",
)

# Mount static files
# Ensure static directory exists
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Request body structure
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: List[Message] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Construct messages list for chat template
        messages = [msg.dict() for msg in request.history]
        messages.append({"role": "user", "content": request.prompt})

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

        generated_ids = model.generate(
            model_inputs.input_ids,
            max_new_tokens=512
        )
        
        # Extract only the new tokens
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
