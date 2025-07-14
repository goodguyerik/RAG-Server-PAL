import torch 
import numpy as np
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers.cross_encoder import CrossEncoder
from concurrent.futures import ThreadPoolExecutor

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)

model_path = "./models/cross-electra"

print("CUDA available:", torch.cuda.is_available())
print("GPU count:", torch.cuda.device_count())
device = "cuda" if torch.cuda.is_available() else "cpu"
cross_model = CrossEncoder(model_path, device=device, local_files_only=True)

class ScoreRequest(BaseModel):
    combs: list[tuple[str, str]]
    page_content: list[str]

class ScoreResponse(BaseModel):
    scores: list[float]

@app.post("/score")
async def score(req: ScoreRequest):
    combs = req.combs
    page_content = req.page_content
    
    loop = asyncio.get_running_loop()
    outputs = await loop.run_in_executor(executor, cross_model.predict, combs)

    outputs = outputs.reshape(1, len(page_content))[0].tolist()
    return ScoreResponse(scores=outputs)