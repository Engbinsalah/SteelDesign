import streamlit as st
import re
import pandas as pd

def parse_staad_output(text):
    """
    Parses the raw text output from STAAD.Pro (AISC 360-16).
    Returns a dictionary of structured data.
    """
    data = {
        "member_no": "N/A",
        "profile": "N/A",
        "governing_ratio": 0.0,
        "governing_ref": "N/A",
        "status": "UNKNOWN",
        "checks": []
    }

    # 1. Parse Header Information
    member_match = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", text)
    if member_match:
        data["member_no"] = member_match.group(1)
        data["profile"] = member_match.group(2)

    gov_match = re.search(r"Status:\s+(\w+)\s+Ratio:\s+([\d\.]+)\s+.*Ref:\s+(Cl\.[\w\.]+)", text)
    if gov_match:
        data["status"] = gov_match.group(1)
        data["governing_ratio"] = float(gov_match.group(2))
        data["governing_ref"] = gov_match.group(3)

    # 2. Parse Specific Checks
    # We look for the pattern: | Check Name | ... | DEMAND CAPACITY ... | ... | val val val ... |
    # This is a simplified regex strategy to catch standard STAAD table blocks
    
    # Split text into pages/sections to handle duplicates
    sections = text.split("*****************************************************")
    
    # Regex to find check blocks. 
    # Captures: Check Name, Reference, Demand, Capacity, Ratio
    # Note: STAAD formatting varies, we try to catch the line with numerical results
    
    check_pattern = re.compile(r"\|\s+([A-Z\s\-]+)\s+\|\n.*\|.*DEMAND.*CAPACITY.*RATIO.*REFERENCE.*\n\|\s+([\d\.E\-\+]+)\s+([\d\.E\-\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.]+)")
    
    for match in check_pattern.finditer(text):
        check_name = match.group(1).strip()
        demand = float(match.group(2))
        capacity = float(match.group(3))
        ratio = float(match.group(4))
        ref = match.group(5)
        
        # Determine Check Type for Icon/Grouping
        category = "Other"
        if "SHEAR" in check_name: category = "Shear"
        elif "BENDING" in check_name or "FLEXURAL YIELDING" in check_name: category = "Flexure"
        elif "COMPRESSION" in check_name or "BUCKLING" in check_name: category = "Compression"
        elif "TENSION" in check_name or "TENSILE" in check_name: category = "Tension"
        elif "INTERACTION" in check_name or "COMBINED" in check_name: category = "Combined"

        data["checks"].append({
            "name": check_name,
            "demand": demand,
            "capacity": capacity,
            "ratio": ratio,
            "ref": ref,
            "category": category
        })

    return data

def get_formula_latex(category, ref):
    """
    Returns a LaTeX string explaining the check based on the reference.
    """
    if "G1" in ref or "G2" in ref:
        return r"\frac{V_u}{\phi_v V_n} \le 1.0"
    elif "F2" in ref or "F6" in ref:
        return r"\frac{M_u}{\phi_b M_n} \le 1.0"
    elif "E3" in ref or "E4" in ref:
        return r"\frac{P_u}{\phi_c P_n} \le 1.0"
    elif "D2" in ref:
        return r"\frac{P_u}{\phi_t P_n} \le 1.0"
    elif "H1" in ref:
        return r"\frac{P_r}{P_c} + \frac{8}{9}\left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right) \le 1.0"
    else:
        return r"\text{Ratio} = \frac{\text{Demand}}{\text{Capacity}}"

# --- Streamlit App Layout ---

st.set_page_config(page_title="STAAD Check Viewer", layout="wide")

st.title("📘 STAAD.Pro Result Interpreter")
st.markdown("Paste your raw STAAD **AISC 360-16** text output below to generate a clean calculation sheet.")

# Sidebar for Input
with st.sidebar:
    st.header("Input Data")
    raw_text = st.text_area("Paste STAAD Output Text:", height=600, help="Copy the text starting from 'Member No' down to the end of the checks.")
    
    parse_btn = st.button("Generate Calculation Sheet", type="primary")

# Main Content
if raw_text:
    try:
        data = parse_staad_output(raw_text)
        
        # --- Header Section ---
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Member", data['member_no'])
        c2.metric("Profile", data['profile'])
        
        status_color = "normal"
        if data['status'] == "PASS": status_color = "normal" 
        else: status_color = "inverse"
        
        c3.metric("Status", data['status'], delta_color=status_color)
        c4.metric("Max Ratio", f"{data['governing_ratio']:.3f}", f"Gov: {data['governing_ref']}")
        
        st.divider()

        # --- Governing Check Highlight ---
        st.subheader("🏁 Governing Limit State")
        
        # Find the check object that matches the governing info
        gov_check = next((item for item in data["checks"] if abs(item["ratio"] - data["governing_ratio"]) < 0.0001), None)
        
        if gov_check:
            st.info(f"The design is controlled by **{gov_check['name']}** ({gov_check['ref']}).")
            
            gc1, gc2 = st.columns([1, 2])
            with gc1:
                st.markdown(f"**Demand ($R_u$):** `{gov_check['demand']}`")
                st.markdown(f"**Capacity ($\phi R_n$):** `{gov_check['capacity']}`")
                st.markdown(f"**Ratio:** `{gov_check['ratio']}`")
            with gc2:
                st.latex(get_formula_latex(gov_check['category'], gov_check['ref']))
                st.latex(rf"\frac{{{gov_check['demand']}}}{{{gov_check['capacity']}}} = \mathbf{{{gov_check['ratio']}}}")
        else:
            st.warning("Could not automatically match the governing ratio to a specific check block. See detailed list below.")

        # --- Detailed Checks ---
        st.subheader("📝 Detailed Calculation Checks")
        
        # Group by category
        categories = ["Shear", "Flexure", "Compression", "Tension", "Combined", "Other"]
        tabs = st.tabs(categories)
        
        for i, cat in enumerate(categories):
            with tabs[i]:
                cat_checks = [c for c in data["checks"] if c["category"] == cat]
                
                if not cat_checks:
                    st.caption(f"No {cat} checks found in input.")
                    continue
                
                for check in cat_checks:
                    with st.expander(f"{check['name']} (Ref: {check['ref']}) - Ratio: {check['ratio']}", expanded=True):
                        col_math, col_vals = st.columns([2, 1])
                        
                        with col_math:
                            st.markdown("##### Governing Equation")
                            st.latex(get_formula_latex(check['category'], check['ref']))
                            
                        with col_vals:
                            st.markdown("##### Values")
                            # Dynamic symbol selection based on category
                            sym_d, sym_c = "R_u", "R_n"
                            if cat == "Shear": sym_d, sym_c = "V_u", "\phi V_n"
                            if cat == "Flexure": sym_d, sym_c = "M_u", "\phi M_n"
                            if cat == "Compression": sym_d, sym_c = "P_u", "\phi P_n"
                            if cat == "Tension": sym_d, sym_c = "P_u", "\phi P_n"

                            st.write(f"${sym_d} = {check['demand']}$")
                            st.write(f"${sym_c} = {check['capacity']}$")
                            
                            ratio_delta = None
                            if check['ratio'] > 1.0: ratio_delta = "-FAIL"
                            st.metric("Utilization Ratio", check['ratio'], delta=ratio_delta, delta_color="inverse")

    except Exception as e:
        st.error(f"Error parsing text. Please ensure you pasted the full STAAD output block. Debug info: {e}")
else:
    st.info("👈 Paste your STAAD result text in the sidebar to begin.")
