import asyncio
import json
import logging
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from google import genai
from google.genai import types

from .models import Clinic

logger = logging.getLogger(__name__)

# Red-flag keywords that trigger immediate EMERGENCY response (0ms deterministic check)
RED_FLAG_SYMPTOMS = [
    'chest pain',
    'heart attack',
    'stroke',
    "can't breathe",
    'cannot breathe',
    'severe bleeding',
    'unconscious',
    'not breathing',
]

EMERGENCY_RESPONSE = {
    "urgency": "EMERGENCY",
    "badge_color": "red",
    "guidance": "Call 112 or 108 immediately. This may be a life-threatening emergency. Do not wait.",
    "clinical_note": "Chief Complaint: Red-flag emergency symptom detected.\nAssessment: Critical / High Severity (Triage: Emergency, Urgency: Immediate)\nPlan: Immediate emergency medical intervention required. Call 112 / 108 or proceed to the nearest emergency department.",
    "highlight_clinics": True,
}

# Candidate Model Cascade (tried in order with 5-second timeout)
CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

TRIAGE_SYSTEM_PROMPT = """You are a medical triage assistant for Indian patients. Analyze the symptom and respond with a JSON object (no markdown, raw JSON only) with these exact keys:
- urgency: one of "SELF_CARE", "OPD", "EMERGENCY"
- badge_color: "green" for SELF_CARE, "yellow" for OPD, "red" for EMERGENCY
- guidance: practical advice string (2-3 sentences)
- clinical_note: a formatted clinical intake note string (Chief Complaint, Assessment, Plan)
- highlight_clinics: boolean, true only if urgency is EMERGENCY or OPD"""


def clinical_rule_fallback(symptom: str) -> dict:
    """Deterministic rule-based clinical fallback if all AI models fail or time out."""
    s_lower = symptom.lower()

    # High severity keywords (Emergency / Immediate)
    high_keywords = [
        'chest', 'heart', 'breath', 'stroke', 'heavy bleed',
        'bleeding', 'unconscious', 'faint', 'seizure', 'paralysis'
    ]
    # Moderate keywords (OPD / Moderate)
    moderate_keywords = [
        'fever', 'cough', 'pain', 'stomach', 'rash', 'vomit',
        'diarrhea', 'headache', 'throat', 'infection', 'dizzy', 'swelling'
    ]
    # Minor keywords (Self-Care / Low)
    minor_keywords = [
        'burn', 'cut', 'scratch', 'bruise', 'scrape', 'itch', 'mild', 'blister'
    ]

    for kw in high_keywords:
        if kw in s_lower:
            return {
                "urgency": "EMERGENCY",
                "badge_color": "red",
                "guidance": "Call 112 or 108 immediately. Your symptoms indicate a potentially critical condition that requires urgent hospital evaluation.",
                "clinical_note": f"Chief Complaint: {symptom}\nAssessment: High Severity - Emergency (Triage: Emergency, Urgency: Immediate)\nPlan: Seek emergency medical care immediately. Call 112 / 108 or go to the nearest trauma center.",
                "highlight_clinics": True,
            }

    for kw in moderate_keywords:
        if kw in s_lower:
            return {
                "urgency": "OPD",
                "badge_color": "yellow",
                "guidance": "Please visit a nearby outpatient (OPD) clinic or consult a general physician today for timely evaluation and symptom management.",
                "clinical_note": f"Chief Complaint: {symptom}\nAssessment: Moderate Severity - Outpatient (Triage: OPD Consult, Urgency: Moderate)\nPlan: Schedule an outpatient consultation with a doctor. Stay hydrated and rest.",
                "highlight_clinics": True,
            }

    for kw in minor_keywords:
        if kw in s_lower:
            return {
                "urgency": "SELF_CARE",
                "badge_color": "green",
                "guidance": "Apply standard home first-aid: keep the area clean, wash with cool water or apply a sterile dressing. Rest and monitor closely.",
                "clinical_note": f"Chief Complaint: {symptom}\nAssessment: Low Severity - Minor Issue (Triage: Self-Care, Urgency: Low)\nPlan: First-aid and home care. If symptoms persist beyond 48 hours or worsen, consult a doctor.",
                "highlight_clinics": False,
            }

    # Default fallback if no specific keywords matched
    return {
        "urgency": "OPD",
        "badge_color": "yellow",
        "guidance": "We recommend an outpatient consultation (OPD) with a medical professional for an accurate diagnosis and treatment plan.",
        "clinical_note": f"Chief Complaint: {symptom}\nAssessment: Undifferentiated Symptom (Triage: OPD Consult, Urgency: Moderate)\nPlan: Consult an outpatient physician for clinical evaluation. Monitor symptoms.",
        "highlight_clinics": True,
    }


def index(request):
    """
    Render the main triage page with clinics data:
    1. Loads from Clinic database model (is_verified=True).
    2. Falls back to clinics.json if the database has 0 records.
    """
    clinics_qs = list(Clinic.objects.filter(is_verified=True).values())

    if clinics_qs:
        clinics = []
        for c in clinics_qs:
            item = dict(c)
            # Ensure compatibility with template card keys
            item["timings"] = item.get("hours") or item.get("timings", "")
            item["maps_link"] = (
                item.get("google_maps_url")
                or item.get("maps_link")
                or f"https://www.google.com/maps/search/?api=1&query={item.get('name', '')}+Bengaluru"
            )
            clinics.append(item)
    else:
        clinics_path = Path(__file__).resolve().parent / 'data' / 'clinics.json'
        try:
            with open(clinics_path, 'r', encoding='utf-8') as f:
                clinics = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            clinics = []

    clinics_json = json.dumps(clinics)
    return render(request, 'portal/index.html', {'clinics_json': clinics_json})


@csrf_exempt
async def triage_api(request):
    """
    Async POST view with:
    1. 0ms deterministic red-flag pre-filter
    2. Multi-model AI cascade (gemini-3.8-flash -> gemini-3.5-flash-lite -> gemini-3.1-flash-lite) with 5s timeout
    3. Deterministic clinical rule fallback on upstream failure (never crashes UI)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)

    symptom = body.get('symptom', '').strip()
    if not symptom:
        return JsonResponse({'error': 'Symptom is required'}, status=400)

    # 1. 0ms Deterministic red-flag pre-filter (before any network or API call)
    symptom_lower = symptom.lower()
    for flag in RED_FLAG_SYMPTOMS:
        if flag in symptom_lower:
            return JsonResponse(EMERGENCY_RESPONSE, status=200)

    # 2. Candidate Model Cascade (gemini-3.8-flash -> gemini-3.5-flash-lite -> gemini-3.1-flash-lite)
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    ai_result = None

    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            for model_name in CANDIDATE_MODELS:
                try:
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model_name,
                            contents=[
                                types.Content(
                                    role="user",
                                    parts=[
                                        types.Part(text=TRIAGE_SYSTEM_PROMPT),
                                        types.Part(text=f"Patient symptom: {symptom}"),
                                    ],
                                )
                            ],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                            ),
                        ),
                        timeout=5.0,
                    )
                    parsed = json.loads(response.text)
                    if isinstance(parsed, dict) and "urgency" in parsed:
                        ai_result = parsed
                        break
                except Exception as model_err:
                    logger.warning(f"Model {model_name} failed ({model_err}). Cascading to next candidate...")
                    continue
        except Exception as client_err:
            logger.warning(f"Gemini client initialization error: {client_err}. Falling back to clinical rules.")

    # If an AI model succeeded, normalize response structure and return
    if ai_result:
        urgency_raw = str(ai_result.get("urgency", "OPD")).upper()
        if "EMERG" in urgency_raw or "IMMEDIATE" in urgency_raw:
            ai_result["urgency"] = "EMERGENCY"
            ai_result["badge_color"] = ai_result.get("badge_color") or "red"
            ai_result["highlight_clinics"] = True
        elif "SELF" in urgency_raw or "LOW" in urgency_raw or "HOME" in urgency_raw:
            ai_result["urgency"] = "SELF_CARE"
            ai_result["badge_color"] = ai_result.get("badge_color") or "green"
            ai_result["highlight_clinics"] = False
        else:
            ai_result["urgency"] = "OPD"
            ai_result["badge_color"] = ai_result.get("badge_color") or "yellow"
            ai_result["highlight_clinics"] = True
        return JsonResponse(ai_result, status=200)

    # 3. Deterministic Rule-Based Fallback (if all AI models fail, time out, 404/503, or offline)
    fallback_result = clinical_rule_fallback(symptom)
    return JsonResponse(fallback_result, status=200)


def login_view(request):
    """Authenticate clinic staff / operators and redirect to home."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm(request)

    return render(request, 'portal/login.html', {'form': form})


def register_view(request):
    """Register a new staff/operator account using standard UserCreationForm and log in."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()

    return render(request, 'portal/register.html', {'form': form})


def logout_view(request):
    """Log out the current user and redirect to home."""
    logout(request)
    return redirect('index')
