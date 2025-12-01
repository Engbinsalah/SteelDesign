import streamlit as st
import re

# --- HELPER: LaTeX Formatting ---
def tex_val(val, color="black"):
    """Wraps a value in LaTeX color and bold formatting."""
    return rf"\textcolor{{{color}}}{{\mathbf{{{val}}}}}"

# --- AISC 360-16 EQUATION MAPPING ---
def get_aisc_explanation(check_name, ref, demand, capacity, ratio):
    """
    Returns LaTeX strings with color-coded substitution.
    Colors: Blue for Demand/Capacity, Maroon for Ratio.
    """
    check_name = check_name.upper().strip()
    
    # Format numbers for LaTeX
    d_tex = tex_val(demand, "blue")
    c_tex = tex_val(capacity, "blue")
    r_tex = tex_val(f"{ratio:.3f}", "maroon")

    # 1. TENSION (Chapter D)
    if "TENSILE YIELDING" in check_name:
        return {
            "eq": r"P_n = F_y A_g \quad \text{(Eq. D2-1)}",
            "check": r"\frac{P_u}{\phi_t P_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }
    elif "TENSILE RUPTURE" in check_name:
        return {
            "eq": r"P_n = F_u A_e \quad \text{(Eq. D2-2)}",
            "check": r"\frac{P_u}{\phi_t P_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }

    # 2. COMPRESSION (Chapter E)
    elif "FLEXURAL BUCKLING" in check_name:
        return {
            "eq": r"P_n = F_{cr} A_g \quad \text{(Eq. E3-1)}",
            "check": r"\frac{P_u}{\phi_c P_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }
    elif "FLEXURAL-TORSIONAL" in check_name:
        return {
            "eq": r"P_n = F_{cr} A_g \quad \text{(Eq. E4-1)}",
            "check": r"\frac{P_u}{\phi_c P_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }

    # 3. FLEXURE (Chapter F)
    elif "FLEXURAL YIELDING" in check_name:
        return {
            "eq": r"M_n = M_p = F_y Z_x \quad \text{(Eq. F2-1)}",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }
    elif "LAT TOR BUCK" in check_name: # Lateral Torsional Buckling
        return {
            "eq": r"M_n = C_b [ M_p - (M_p - 0.7 F_y S_x) (\dots) ] \le M_p",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }
    elif "FLANGE LOCAL BUCK" in check_name:
        return {
            "eq": r"\text{Check Compactness } (\lambda = b/t)",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }

    # 4. SHEAR (Chapter G)
    elif "SHEAR" in check_name:
        return {
            "eq": r"V_n = 0.6 F_y A_w C_{v1} \quad \text{(Eq. G2-1)}",
            "check": r"\frac{V_u}{\phi_v V_n} \leq 1.0",
            "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
        }

    # 5. INTERACTION (Chapter H)
    elif "COMBINED" in check_name or "INTERACTION" in check_name:
        if "H1-1a" in ref:
            return {
                "eq": r"\frac{P_r}{P_c} + \frac{8}{9} (\dots) \leq 1.0 \quad \text{(Eq. H1-1a)}",
                "check": r"\text{Interaction Check } (P_r/P_c \ge 0.2)",
                "sub": rf"{r_tex} \leq 1.0"
            }
        else: # Default to H1-1b
            return {
                "eq": r"\frac{P_r}{2P_c} + \left( \frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}} \right) \leq 1.0 \quad \text{(Eq. H1-1b)}",
                "check": r"\text{Interaction Check } (P_r/P_c < 0.2)",
                "sub": rf"{r_tex} \leq 1.0"
            }

    # Default fallback
    return {
        "eq": r"\text{AISC 360-16 Code Provision}",
        "check": r"\frac{\text{Demand}}{\text{Capacity}} \leq 1.0",
        "sub": rf"\frac{{{d_tex}}}{{{c_tex}}} = {r_tex}"
    }

# --- PARSING LOGIC (Preserved) ---
def parse_staad_deep(text):
    data = {"header": {}, "properties": {}, "material": {}, "checks": []}

    mem_match = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", text)
    if mem_match:
        data["header"]["member"] = mem_match.group(1)
        data["header"]["profile"] = mem_match.group(2)
        
    gov_match = re.search(r"Status:\s+(\w+)\s+Ratio:\s+([\d\.]+)\s+.*Ref:\s+(.*)", text)
    if gov_match:
        data["header"]["status"] = gov_match.group(1)
        data["header"]["max_ratio"] = float(gov_match.group(2))
        data["header"]["gov_ref"] = gov_match.group(3).strip()

    check_blocks = re.split(r"\|\s*CHECKS FOR ", text)
    prop_block = check_blocks[0]
    
    fy_match = re.search(r"Fyld:\s+([\d\.]+)", prop_block)
    if fy_match: data["material"]["Fy"] = fy_match.group(1)
    
    area_match = re.search(r"Ag\s*:\s*([\d\.E\+\-]+)", prop_block)
    if area_match: data["properties"]["Ag"] = area_match.group(1)

    regex_check = re.compile(r"\|\s+([A-Z0-9\-\s\(\)]+?)\s+\|\n.*\|.*DEMAND.*CAPACITY.*RATIO.*REFERENCE.*LOC\s+\|\n\|\s+([-\d\.E\+]+)\s+([-\d\.E\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.\d\-]+|Eq\.[\w\.\d\-]+)")
    intermediate_regex = re.compile(r"\|\s+(.*?)\s+:\s+([A-Za-z0-9]+)\s+=\s+([-\d\.E\+]+)\s+([A-Za-z\-\^0-9]+)?\s+(.*)\|")

    for match in regex_check.finditer(text):
        c_name = match.group(1).strip()
        c_dem = float(match.group(2))
        c_cap = float(match.group(3))
        c_rat = float(match.group(4))
        c_ref = match.group(5).strip()
        
        cat = "Other"
        if "SHEAR" in c_name: cat = "Shear (Chapter G)"
        elif "BENDING" in c_name or "FLEXURAL YIELDING" in c_name or "LAT TOR" in c_name or "FLANGE LOCAL" in c_name: cat = "Flexure (Chapter F)"
        elif "COMPRESSION" in c_name or "BUCKLING" in c_name: cat = "Compression (Chapter E)"
        elif "TENSION" in c_name or "TENSILE" in c_name: cat = "Tension (Chapter D)"
        elif "COMBINED" in c_name or "INTERACTION" in c_name: cat = "Interaction (Chapter H)"

        start_index = match.end()
        end_index = text.find("|----------------", start_index)
        sub_text = text[start_index:end_index]
        
        intermediates = []
        for imatch in intermediate_regex.finditer(sub_text):
            val_clean = imatch.group(3).strip()
            # Clean scientific notation for nicer latex (E+00 -> )
            try:
                f_val = float(val_clean)
                if abs(f_val) < 0.001 or abs(f_val) > 10000:
                    val_clean = f"{f_val:.3e}"
                else:
                    val_clean = f"{f_val:.3f}"
            except:
                pass
                
            intermediates.append({
                "symbol": imatch.group(2).strip(),
                "value": val_clean,
                "unit": imatch.group(4).strip() if imatch.group(4) else ""
            })

        data["checks"].append({
            "name": c_name,
            "category": cat,
            "demand": c_dem,
            "capacity": c_cap,
            "ratio": c_rat,
            "ref": c_ref,
            "intermediates": intermediates
        })
        
    return data

# --- STREAMLIT UI ---
st.set_page_config(page_title="STAAD Calc Sheet", layout="centered")

st.markdown("## 🏗️ Structural Calculation Sheet")
st.markdown("*AISC 360-16 LRFD Specification*")

with st.expander("📥 Input Data (Paste STAAD Output)", expanded=True):
    raw_input = st.text_area("Raw Text", height=200, help="Paste from 'Member No' to end of checks.")

if raw_input:
    try:
        data = parse_staad_deep(raw_input)
        
        # 1. Header Summary
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Member:** `{data['header'].get('member','?')}`")
        c1.markdown(f"**Profile:** `{data['header'].get('profile','?')}`")
        
        c2.markdown(f"**Material:** $F_y = {data['material'].get('Fy','?')} ksi$")
        c2.markdown(f"**Area:** $A_g = {data['properties'].get('Ag','?')} in^2$")

        gov_ratio = data['header'].get('max_ratio', 0)
        status = data['header'].get('status', 'UNKNOWN')
        
        # Header Color Logic
        status_tex = r"\textcolor{green}{PASS}" if status == "PASS" else r"\textcolor{red}{FAIL}"
        ratio_tex = tex_val(f"{gov_ratio}", "maroon")
        
        c3.latex(rf"\text{{Status: }} {status_tex}")
        c3.latex(rf"\text{{Gov. Ratio: }} {ratio_tex}")
        st.divider()

        # 2. Render Calculations
        sort_order = ["Tension (Chapter D)", "Compression (Chapter E)", "Flexure (Chapter F)", "Shear (Chapter G)", "Interaction (Chapter H)"]
        present_cats = sorted(list(set(c['category'] for c in data['checks'])), key=lambda x: sort_order.index(x) if x in sort_order else 99)

        for cat in present_cats:
            st.markdown(f"### {cat}")
            
            checks_in_cat = [c for c in data['checks'] if c['category'] == cat]
            
            for check in checks_in_cat:
                if check['ratio'] >= 0.0: # Show all checks
                    with st.container():
                        st.markdown(f"**{check['name']}** (Ref: *{check['ref']}*)")
                        
                        # A. Intermediate Variables (Inputs = GREEN)
                        if check['intermediates']:
                            cols = st.columns(4)
                            for i, var in enumerate(check['intermediates']):
                                with cols[i % 4]:
                                    # LaTeX formatting for variables
                                    # Symbol = Black, Value = Green
                                    unit_tex = rf"\text{{ {var['unit']}}}" if var['unit'] else ""
                                    st.latex(rf"{var['symbol']} = \textcolor{{green}}{{{var['value']}}}{unit_tex}")
                        
                        # B. Formula and Calculation
                        math_data = get_aisc_explanation(check['name'], check['ref'], check['demand'], check['capacity'], check['ratio'])
                        
                        m1, m2 = st.columns([2, 1])
                        with m1:
                            st.latex(math_data['eq'])
                            st.latex(math_data['check'])
                        with m2:
                            st.caption("Substitution")
                            # Demand/Capacity = Blue, Ratio = Maroon
                            st.latex(math_data['sub'])
                            
                        st.markdown("---")

    except Exception as e:
        st.error(f"Error parsing text. Please check the input format. ({e})")
