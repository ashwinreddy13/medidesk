from flask import Blueprint, request, jsonify, session
import re
from services.appointments import get_patient_appointments, get_doctor_appointments
from database.db import get_db

assistant_bp = Blueprint('assistant', __name__, url_prefix='/assistant')

MEDICAL_DISCLAIMER = (
    "⚠️ Medical Guardrail: MediDesk is a demonstration HealthTech clinic management platform using synthetic data. "
    "I cannot diagnose conditions, recommend treatments, or prescribe medication. If you are experiencing a medical emergency, "
    "please call your local emergency services immediately."
)

FAQ_KNOWLEDGE_BASE = [
    {
        'keywords': ['book', 'schedule', 'make appointment', 'how to book'],
        'response': "To book an appointment: Click on 'Book Appointment' in the sidebar or dashboard. Choose your preferred doctor and consultation date. Our server will dynamically check doctor working hours and display open slots. Pick an available slot, enter your reason for visit, and submit! Your appointment will be created in 'Pending' status."
    },
    {
        'keywords': ['pending', 'what is pending', 'status pending'],
        'response': "'Pending' means your appointment request has been securely recorded on the server and is awaiting review and confirmation by your attending doctor."
    },
    {
        'keywords': ['confirmed', 'status confirmed'],
        'response': "'Confirmed' means your doctor has approved your appointment slot. Please arrive on time at the clinic or log in for your consultation."
    },
    {
        'keywords': ['complete', 'completed', 'status completed'],
        'response': "'Completed' indicates that your consultation took place. The attending doctor has filed your digital consultation summary and prescription in your Medical Records."
    },
    {
        'keywords': ['cancel', 'how to cancel'],
        'response': "You can cancel any 'Pending' or 'Confirmed' appointment by visiting the 'Appointments' page and clicking the 'Cancel' button next to the eligible booking."
    },
    {
        'keywords': ['smart appointment', 'best slot', 'find slot', 'recommend'],
        'response': "Try our 'Smart Appointment Finder' under Appointments! Simply select what you're looking for (e.g. Cardiology or General Consultation), preferred timeframe, and time of day. We'll automatically find the earliest and best matching slot."
    },
    {
        'keywords': ['timeline', 'health timeline', 'history'],
        'response': "The Patient Health Timeline provides a chronological view of all your completed clinic visits and verified synthetic medical records with physician notes."
    },
    {
        'keywords': ['privacy', 'security', 'hipaa', 'gdpr', 'safe', 'data'],
        'response': "MediDesk is built with defense-in-depth: strict Role-Based Access Control (RBAC), Anti-IDOR record verification, cryptographically chained SHA-256 audit logs, brute-force login throttling, and zero hardcoded secrets. Check the Privacy Center in your sidebar to learn more."
    },
    {
        'keywords': ['amoxicillin', 'vitamin d', 'metoprolol', 'prescription', 'medication'],
        'response': "In MediDesk's synthetic demo data, medications like Vitamin D3 and Metoprolol represent sample clinical treatments attached to dummy diagnoses. All medical records in this environment are synthetic."
    }
]

CLINICAL_SYMPTOM_TRIGGERS = [
    'pain', 'headache', 'fever', 'chest pain', 'heart attack', 'cough', 'cancer',
    'stroke', 'emergency', 'dying', 'sick', 'vomit', 'nausea', 'infection', 'treat', 'cure', 'diagnose'
]

@assistant_bp.route('/query', methods=['POST'])
def query_assistant():
    """MediDesk AI Clinical Navigator JSON API."""
    data = request.get_json(silent=True) or {}
    user_prompt = data.get('query', '').strip()

    if not user_prompt:
        return jsonify({'response': "Hello! I am your MediDesk Clinical Assistant. Ask me about booking appointments, status explanations, privacy features, or finding the best slot!"})

    lower_prompt = user_prompt.lower()

    # 1. Enforce strict medical safety guardrails
    is_medical_question = any(re.search(rf'\b{re.escape(w)}\b', lower_prompt) for w in CLINICAL_SYMPTOM_TRIGGERS)
    if is_medical_question and not any(w in lower_prompt for w in ['book', 'schedule', 'doctor', 'pending', 'timeline']):
        return jsonify({
            'response': (
                f"{MEDICAL_DISCLAIMER}\n\n"
                "Would you like me to help you book an appointment with one of our specialists (General Consultation, Cardiology, Neurology, or Pediatrics) to have your symptoms evaluated by a doctor?"
            ),
            'suggestion_action': '/patient/book'
        })

    # 2. Check personal appointment query for authenticated user
    if any(q in lower_prompt for q in ['my appointment', 'what appointment', 'upcoming appointment', 'when is my']):
        if 'user_id' not in session:
            return jsonify({'response': "Please log in to your patient account so I can look up your scheduled appointments securely."})
        
        user_role = session.get('user_role')
        if user_role == 'patient':
            appts = get_patient_appointments(session['user_id'])
            active = [a for a in appts if a['status'] in ('Pending', 'Confirmed')]
            if not active:
                return jsonify({
                    'response': "You currently have no active or upcoming appointments scheduled. Would you like to book one?",
                    'suggestion_action': '/patient/book'
                })
            next_one = active[0]
            return jsonify({
                'response': f"You have an upcoming {next_one['status']} appointment with {next_one['doctor_name']} ({next_one['doctor_specialty']}) on {next_one['appointment_date']} at {next_one['appointment_time']}. Reason: '{next_one['reason']}'."
            })
        elif user_role == 'doctor':
            appts = get_doctor_appointments(session['user_id'])
            pending = [a for a in appts if a['status'] == 'Pending']
            return jsonify({
                'response': f"You currently have {len(appts)} total appointments assigned, including {len(pending)} pending confirmation requests."
            })

    # 3. Match against FAQ knowledge base
    for item in FAQ_KNOWLEDGE_BASE:
        if any(kw in lower_prompt for kw in item['keywords']):
            return jsonify({'response': item['response']})

    # 4. Fallback helpful navigation guide
    return jsonify({
        'response': (
            "I'm the MediDesk Assistant! Here are a few things I can assist you with:\n"
            "• Ask: 'How do I book an appointment?'\n"
            "• Ask: 'What does Pending mean?'\n"
            "• Ask: 'What appointments do I have?'\n"
            "• Ask: 'Tell me about MediDesk privacy and security'\n"
            "• Ask: 'How does the Smart Appointment Finder work?'"
        )
    })

