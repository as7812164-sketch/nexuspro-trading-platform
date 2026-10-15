@echo off
title NexusPro Futures & Deca Terminal
echo ===================================================
echo   ⚡ NEXUSPRO INSTITUTIONAL FUTURES TERMINAL
echo   Format: 100% Bitget Pro Layout
echo   Engine: BB 2.0 ($47,389.77 USDT Historic Model)
echo   Starting Capital: $500.00 across 10 Deca Slots
echo ===================================================
echo Starting server on http://localhost:8080 ...
python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
pause
