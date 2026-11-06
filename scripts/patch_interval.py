file_path = r"C:\Users\power\.gemini\antigravity\scratch\nexuspro_trading_platform\static\js\app.js"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('let currentInterval = "15m";', 'let currentInterval = "1h";')
text = text.replace(
    "if (symParam) currentSymbol = symParam.toUpperCase();",
    "if (symParam) currentSymbol = symParam.toUpperCase();\nconst tfParam = urlParams.get('tf') || urlParams.get('interval');\nif (tfParam) currentInterval = tfParam.toLowerCase();"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("[OK] Set default interval to 1h and enabled tf/interval URL parameter")
