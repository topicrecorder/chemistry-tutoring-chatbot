# iupac_nomenclature.py
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch
import google.generativeai as genai
from transformers import BitsAndBytesConfig

# Load fine-tuned DeepSeek model with quantization
def load_iupac_model():
    base_model_name = "deepseek-ai/deepseek-llm-r1-7b-base"  # Base model
    adapter_path = "C:\\GeminiBot\\checkpoint-250"  # Your adapter path
    
    # Configure 4-bit quantization to reduce memory usage
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load adapter
    model = PeftModel.from_pretrained(model, adapter_path)
    return tokenizer, model

# Generate IUPAC response with DeepSeek
def get_iupac_response(question, tokenizer, model):
    # Set model to evaluation mode
    model.eval()
    
    # Tokenize input
    inputs = tokenizer(
        question, 
        return_tensors="pt",
        max_length=512, 
        truncation=True,
        padding=True
    ).to(model.device)
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1
        )
    
    # Decode and return response
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Translate to Sinhala using Gemini
def translate_to_sinhala(text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Translate this chemistry-related text to Sinhala: {text}"
    response = model.generate_content(prompt)
    return response.text.strip()