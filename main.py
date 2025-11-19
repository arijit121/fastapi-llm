from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import List
import os

app = FastAPI(title="Qwen2 Chatbot API", version="1.0")

print("Loading model...")

MODEL_ID = "Qwen/Qwen2-7B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
)

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: List[Message] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
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

        new_tokens = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0]

        return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
