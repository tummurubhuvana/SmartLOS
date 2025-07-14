import streamlit as st
import pandas as pd
import requests
import os

# ------------------ CONFIG ------------------
st.set_page_config(page_title="SmartLOS Dashboard", layout="wide")

# ------------------ PAGE NAVIGATION ------------------
page = st.sidebar.radio("Navigation", ["Customer Submission", "Officer Dashboard"])

# ------------------ SESSION STORAGE ------------------
if 'customers' not in st.session_state:
    st.session_state.customers = []

# ------------------ SMART SCORE CALC ------------------
def calculate_smart_score(data):
    score = 300

    if data['repayment_track'] == 'Good':
        score += 100
    elif data['repayment_track'] == 'Average':
        score += 50
    else:
        score += 10

    try:
        income = float(data['income'])
        expenses = float(data['expenses'])
        if income > 0:
            ratio = expenses / income
            if ratio < 0.4:
                score += 100
            elif ratio < 0.6:
                score += 70
            elif ratio < 0.8:
                score += 40
            else:
                score += 10
    except:
        pass

    loans = int(data.get('active_loans', 0))
    if loans == 0:
        score += 50
    elif loans <= 2:
        score += 30
    else:
        score += 10

    job = data.get('job_status', '').lower()
    if job == 'lost':
        score -= 30
    elif job == 'irregular':
        score -= 10
    else:
        score += 30

    reason = data.get('remarks', '').lower()
    if 'salary' in reason or 'job' in reason:
        score += 20

    if 'yes' in data.get('family_backup', '').lower():
        score += 25

    return min(score, 900)

# ------------------ ESTIMATED LOAN CALC ------------------
def estimate_loan_amount(data):
    try:
        income = float(data['income'])
        property_val = float(data.get('property_value', 0))
        backup_score = 1 if 'yes' in data.get('family_backup', '').lower() else 0
        
        base = income * 10  # eligibility is 10x monthly income
        collateral_boost = 0.5 * property_val
        backup_factor = 0.2 * property_val if backup_score else 0
        return round(base + collateral_boost + backup_factor, 2)
    except:
        return 0.0

# ------------------ LLM SUGGESTION ------------------
def ask_llm(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt},
            timeout=60
        )
        return response.json().get("response", "No response from model")
    except:
        return "LLM service unavailable."

# ------------------ PAGE 1: CUSTOMER SUBMISSION ------------------
if page == "Customer Submission":
    st.title("SmartLOS - Customer 360 Loan Evaluation")

    with st.form("customer_form"):
        st.subheader("Upload Documents")
        aadhaar = st.file_uploader("Upload Aadhaar Card")
        pan = st.file_uploader("Upload PAN Card")
        job_letter = st.file_uploader("Upload Job Offer Letter")
        property_doc = st.file_uploader("Upload Property Document (if any)")
        loan_history_doc = st.file_uploader("Upload Previous Loan Repayment History")

        st.subheader("Basic Details")
        name = st.text_input("Customer Name")
        age = st.number_input("Age", 18, 100)
        phone = st.text_input("Phone Number")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        st.subheader("Family Background")
        father = st.text_input("Father's Name")
        father_job = st.text_input("Father's Job")
        mother = st.text_input("Mother's Name")
        mother_job = st.text_input("Mother's Job")

        st.subheader("Credit Profile")
        cibil = st.number_input("CIBIL Score")
        experian = st.number_input("Experian Score")
        credit_issues = st.text_area("Credit History Issues")
        active_loans = st.number_input("Number of Active Loans", 0, 20)
        repayment_track = st.selectbox("Previous Loan Repayment Track", ["Good", "Average", "Poor"])

        st.subheader("Risk Factors")
        job_status = st.selectbox("Job Status", ["Active", "Irregular", "Lost"])
        emergencies = st.text_area("Medical Issues or Emergencies")
        remarks = st.text_area("Remarks on Payment Delays")

        st.subheader("Loan Request")
        loan_needed = st.number_input("Loan Amount Requested (₹)", 1000.0)
        income = st.number_input("Monthly Income (₹)", 0.0)
        expenses = st.number_input("Monthly Expenses (₹)", 0.0)
        savings = st.number_input("Savings Left Monthly (₹)", 0.0)
        family_backup = st.selectbox("Is Family Willing to Support Repayment if Needed?", ["Yes", "No"])
        property_value = st.number_input("Property Value if Any (₹)", 0.0)

        submitted = st.form_submit_button("Submit")

        if submitted:
            new_customer = {
                "name": name,
                "age": age,
                "phone": phone,
                "gender": gender,
                "father": father,
                "father_job": father_job,
                "mother": mother,
                "mother_job": mother_job,
                "cibil": cibil,
                "experian": experian,
                "credit_issues": credit_issues,
                "active_loans": active_loans,
                "repayment_track": repayment_track,
                "job_status": job_status,
                "emergencies": emergencies,
                "remarks": remarks,
                "loan_needed": loan_needed,
                "income": income,
                "expenses": expenses,
                "savings": savings,
                "family_backup": family_backup,
                "property_value": property_value
            }
            st.session_state.customers.append(new_customer)
            st.success("Customer data submitted successfully!")
import streamlit as st
import requests

# ---------------- SMART SCORE CALCULATION ----------------
def calculate_smart_score(customer, all_customers):
    score = 300

    # Repayment track
    track = customer.get('repayment_track', '')
    if track == 'Good':
        score += 100
    elif track == 'Average':
        score += 50
    else:
        score += 10

    # Expenses vs Income
    try:
        income = float(customer.get('income', 0))
        expenses = float(customer.get('expenses', 0))
        if income > 0:
            ratio = expenses / income
            if ratio < 0.4:
                score += 100
            elif ratio < 0.6:
                score += 70
            elif ratio < 0.8:
                score += 40
            else:
                score += 10
    except:
        pass

    # Active loans
    try:
        loans = int(customer.get('active_loans', 0))
        if loans == 0:
            score += 50
        elif loans <= 2:
            score += 30
        else:
            score += 10
    except:
        pass

    # Job status
    job = customer.get('job_status', '').lower()
    if job == 'lost':
        score -= 30
    elif job == 'irregular':
        score -= 10
    elif job == 'active':
        score += 30

    # Remarks on EMI delay
    remarks = customer.get('remarks', '').lower()
    if any(x in remarks for x in ['salary', 'job', 'health']):
        score += 20

    # Family backup support
    if customer.get('family_backup', '').lower() == 'yes':
        score += 25

    # Surname match logic (safe access)
    name = customer.get('name', '')
    surname = name.split()[-1].lower() if name else ''
    for other in all_customers:
        if other.get('name') != name:
            other_name = other.get('name', '')
            other_surname = other_name.split()[-1].lower() if other_name else ''
            if surname and surname == other_surname and other.get('family_backup', '').lower() == 'yes':
                score += 25
                break

    return min(score, 900)

# ---------------- ESTIMATE LOAN AMOUNT ----------------
def estimate_loan(customer):
    try:
        income = float(customer.get('income', 0))
        property_value = float(customer.get('property_value', 0))
        has_backup = customer.get('family_backup', '').lower() == 'yes'

        base = income * 10
        collateral = 0.5 * property_value
        family_boost = 0.2 * property_value if has_backup else 0

        return round(base + collateral + family_boost, 2)
    except:
        return 0.0

# ---------------- LLM Suggestion ----------------
def ask_llm(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt},
            timeout=60
        )
        return response.json().get("response", "No response from model")
    except:
        return "LLM service unavailable"

# ---------------- OFFICER DASHBOARD ----------------
st.title("SmartLOS - Officer Dashboard")

if 'customers' not in st.session_state or len(st.session_state.customers) == 0:
    st.warning("No customer submissions yet. Ask customer to fill Page 1.")
else:
    for idx, cust in enumerate(st.session_state.customers):
        with st.expander(f"Customer: {cust.get('name', 'Unknown')} ({cust.get('phone', '-')})"):
            st.subheader("Basic Details")
            st.write(f"Name: {cust.get('name', '-')}")
            st.write(f"Age: {cust.get('age', '-')}, Gender: {cust.get('gender', '-')}")
            st.write(f"Father: {cust.get('father', '-')} ({cust.get('father_job', '-')}), Mother: {cust.get('mother', '-')} ({cust.get('mother_job', '-')})")

            st.subheader("Credit Info")
            st.write(f"CIBIL Score: {cust.get('cibil', '-')}")
            st.write(f"Experian Score: {cust.get('experian', '-')}")
            st.write(f"Credit Issues: {cust.get('credit_issues', '-')}")
            st.write(f"Active Loans: {cust.get('active_loans', '-')}")
            st.write(f"Repayment Track: {cust.get('repayment_track', '-')}")

            st.subheader("Loan Request")
            st.write(f"Loan Requested: ₹{cust.get('loan_needed', 0)}")
            st.write(f"Monthly Income: ₹{cust.get('income', 0)}")
            st.write(f"Monthly Expenses: ₹{cust.get('expenses', 0)}")
            st.write(f"Savings: ₹{cust.get('savings', 0)}")
            st.write(f"Property Value: ₹{cust.get('property_value', 0)}")
            st.write(f"Family Backup: {cust.get('family_backup', '-')}")

            st.subheader("Risks & Remarks")
            st.write(f"Job Status: {cust.get('job_status', '-')}")
            st.write(f"Medical Emergencies: {cust.get('emergencies', '-')}")
            st.write(f"Remarks: {cust.get('remarks', '-')}")

            st.subheader("Evaluation")

            smart_score = calculate_smart_score(cust, st.session_state.customers)
            estimated_loan = estimate_loan(cust)

            st.metric("Smart Score", f"{smart_score} / 900")
            st.metric("Estimated Eligible Loan", f"₹{estimated_loan}")

            # Final System Recommendation
            decision = "Reject"
            if smart_score >= 750 and estimated_loan >= cust.get('loan_needed', 0):
                decision = "Approve"
            elif smart_score >= 600:
                decision = "Hold"

            st.markdown(f"**System Recommendation:** `{decision}`")

            st.subheader("LLM Suggestion")
            prompt = (
                f"A customer with CIBIL {cust.get('cibil')}, income ₹{cust.get('income')}, expenses ₹{cust.get('expenses')}, "
                f"has {cust.get('active_loans')} active loans, repayment track '{cust.get('repayment_track')}', "
                f"job status '{cust.get('job_status')}' requests a loan of ₹{cust.get('loan_needed')}. "
                "Suggest whether to approve, hold, or reject."
            )
            st.info(ask_llm(prompt))

            st.subheader("Officer Final Action")
            st.radio(f"Decision for {cust.get('name', 'customer')}", ["Approve", "Hold", "Reject"], key=f"action_{idx}")
