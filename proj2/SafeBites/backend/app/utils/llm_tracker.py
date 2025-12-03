import time
import os, csv
import logging
from langchain.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)

MODEL_COSTS = {
    "gpt-4o-mini":{"input":1.25, "output":10.00} # per 1M token
}

class LLMUsageTracker(BaseCallbackHandler):
    def __init__(self):
        self.total_cost = 0

    def on_llm_start(self,serialized,prompts, **kwargs):
        self.start_time = time.time()
        self.prompt = prompts[0] if prompts else ""
    
    def on_llm_end(self,response,**kwargs):
        print(response)
        latency = round((time.time() - self.start_time)*1000,2)
        model_name = kwargs.get("invocation_params", {}).get("model", "gpt-4o-mini")
        usage = getattr(response, "llm_output", {}).get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
        logger.info(f"{model_name} {input_tokens} {output_tokens}")
        cost = 0
        if model_name in MODEL_COSTS:
            cost = (
                (input_tokens / 1_000_000) * MODEL_COSTS[model_name]["input"]
                + (output_tokens / 1_000_000) * MODEL_COSTS[model_name]["output"]
            )

        self.total_cost += cost
        os.makedirs("logs",exist_ok=True)
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens" : total_tokens,
            "cost": cost,
            "latency_ms": latency,
        }
        logger.info("Writing the llm usage information to : logs/llm_usage.csv")
        with open("logs/llm_usage.csv","a",newline="") as f:
            writer = csv.DictWriter(f,fieldnames=record.keys())
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(record)