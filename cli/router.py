PREFERRED = {
    "bugs":     ["qwen3-coder", "qwen3", "deepseek-r1","codellama", "llama"],
    "security": ["qwen3-coder", "deepseek-r1", "qwen3", "codellama", "llama"],
    "full":     ["qwen3-coder", "deepseek-r1", "qwen3", "codellama","llama"],
}
def select_model(mode: str, available: list[str]) -> str:
    if not available:
        return "codellama"
    
    for pref in PREFERRED.get(mode, []):
        for model in available:
            if model.startswith(pref):
                return model
                
    return available[0]