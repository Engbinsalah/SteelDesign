import streamlit as st
import re
import pandas as pd

# --- AISC 360-16 EQUATION MAPPING ---
def get_aisc_explanation(check_name, ref, demand, capacity, ratio):
    """
    Returns a dictionary with LaTeX strings for the Formula and the Substitution
    based on the check name and reference code.
    """
    check_name = check_name.upper().strip()
    
    # 1. TENSION (Chapter D)
    if "TENSILE YIELDING" in check_name:
        return {
            "eq": r"P_n = F_y A_g \quad \text{(Eq. D2-1)}",
            "check": r"\frac{P_u}{\phi_t P_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }
    elif "TENSILE RUPTURE" in check_name:
        return {
            "eq": r"P_n = F_u A_e \quad \text{(Eq. D2-2)}",
            "check": r"\frac{P_u}{\phi_t P_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }

    # 2. COMPRESSION (Chapter E)
    elif "FLEXURAL BUCKLING" in check_name:
        # Distinguish between Elastic (Euler) and Inelastic buckling roughly based on context,
        # but STAAD outputs the final Pn. We show the general governing logic.
        return {
            "eq": r"P_n = F_{cr} A_g \quad \text{(Eq. E3-1)}",
            "check": r"\frac{P_u}{\phi_c P_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }
    elif "FLEXURAL-TORSIONAL" in check_name:
        return {
            "eq": r"P_n = F_{cr} A_g \quad \text{(Eq. E4-1)}",
            "check": r"\frac{P_u}{\phi_c P_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }

    # 3. FLEXURE (Chapter F)
    elif "FLEXURAL YIELDING" in check_name:
        return {
            "eq": r"M_n = M_p = F_y Z_x \quad \text{(Eq. F2-1)}",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }
    elif "LAT TOR BUCK" in check_name: # Lateral Torsional Buckling
        return {
            "eq": r"M_n = C_b \left[ M_p - (M_p - 0.7 F_y S_x) \left( \frac{L_b - L_p}{L_r - L_p} \right) \right] \le M_p",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }
    elif "FLANGE LOCAL BUCK" in check_name:
        return {
            "eq": r"\text{Check Compactness } (\lambda = b/t) \text{ vs } \lambda_p, \lambda_r \quad \text{(Cl. F3)}",
            "check": r"\frac{M_u}{\phi_b M_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }

    # 4. SHEAR (Chapter G)
    elif "SHEAR" in check_name:
        return {
            "eq": r"V_n = 0.6 F_y A_w C_{v1} \quad \text{(Eq. G2-1)}",
            "check": r"\frac{V_u}{\phi_v V_n} \leq 1.0",
            "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
        }

    # 5. INTERACTION (Chapter H)
    elif "COMBINED" in check_name or "INTERACTION" in check_name:
        # Check if Pr/Pc >= 0.2 (Eq H1-1a) or < 0.2 (Eq H1-1b)
        # We can infer from the reference string usually
        if "H1-1a" in ref:
            return {
                "eq": r"\frac{P_r}{P_c} + \frac{8}{9} \left( \frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}} \right) \leq 1.0 \quad \text{(Eq. H1-1a)}",
                "check": r"\text{Interaction Check } (P_r/P_c \ge 0.2)",
                "sub": rf"\mathbf{{{ratio:.3f}}} \leq 1.0"
            }
        else: # Default to H1-1b
            return {
                "eq": r"\frac{P_r}{2P_c} + \left( \frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}} \right) \leq 1.0 \quad \text{(Eq. H1-1b)}",
                "check": r"\text{Interaction Check } (P_r/P_c < 0.2)",
                "sub": rf"\mathbf{{{ratio:.3f}}} \leq 1.0"
            }

    # Default fallback
    return {
        "eq": r"\text{AISC 360-16 Code Provision}",
        "check": r"\frac{\text{Demand}}{\text{Capacity}} \leq 1.0",
        "sub": rf"\frac{{{demand}}}{{{capacity}}} = \mathbf{{{ratio:.3f}}}"
    }

# --- PARSING LOGIC ---
def parse_staad_deep(text):
    """
    Parses the text to extract header info, member properties, and every detailed check block.
    """
    data = {
        "header": {},
        "properties": {},
        "material": {},
        "checks": []
    }

    # 1. Header Info
    mem_match = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", text)
    if mem_match:
        data["header"]["member"] = mem_match.group(1)
        data["header"]["profile"] = mem_match.group(2)
        
    gov_match = re.search(r"Status:\s+(\w+)\s+Ratio:\s+([\d\.]+)\s+.*Ref:\s+(.*)", text)
    if gov_match:
        data["header"]["status"] = gov_match.group(1)
        data["header"]["max_ratio"] = float(gov_match.group(2))
        data["header"]["gov_ref"] = gov_match.group(3).strip()

    # 2. Extract Sections based on STAAD Headers
    # We split by specific STAAD separators to isolate blocks
    check_blocks = re.split(r"\|\s*CHECKS FOR ", text)
    
    # The first block contains properties, the rest are checks
    prop_block = check_blocks[0]
    
    # Parse Properties (Simple extraction of key values)
    fy_match = re.search(r"Fyld:\s+([\d\.]+)", prop_block)
    if fy_match: data["material"]["Fy"] = fy_match.group(1)
    
    area_match = re.search(r"Ag\s*:\s*([\d\.E\+\-]+)", prop_block)
    if area_match: data["properties"]["Ag"] = area_match.group(1)
    
    iz_match = re.search(r"Ixx\s*:\s*([\d\.E\+\-]+)", prop_block)
    if iz_match: data["properties"]["Ix"] = iz_match.group(1)

    # 3. Iterate through Check Blocks (Tension, Compression, Shear, etc.)
    for block in check_blocks[1:]:
        # Identify the Category title (the text immediately following "CHECKS FOR ")
        # In the split, the title is actually consumed, so we need to infer or look at the previous split.
        # Actually, let's use a regex iterator to find the blocks + titles.
        pass 
    
    # Alternative robust parsing for check tables:
    # Look for the specific pattern: | Check Name | ... | DEMAND ... | ... | values |
    
    # Regex explanation:
    # 1. Capture the Check Name (e.g. "TENSILE YIELDING") inside pipes
    # 2. Skip lines until we find the numerical row
    # 3. Capture Demand, Capacity, Ratio, Reference, LC, Loc
    
    regex_check = re.compile(r"\|\s+([A-Z0-9\-\s\(\)]+?)\s+\|\n.*\|.*DEMAND.*CAPACITY.*RATIO.*REFERENCE.*LOC\s+\|\n\|\s+([-\d\.E\+]+)\s+([-\d\.E\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.\d\-]+|Eq\.[\w\.\d\-]+)")
    
    intermediate_regex = re.compile(r"\|\s+(.*?)\s+:\s+([A-Za-z0-9]+)\s+=\s+([-\d\.E\+]+)\s+([A-Za-z\-]+)?\s+(.*)\|")

    # We iterate over the full text to find these tables
    for match in regex_check.finditer(text):
        c_name = match.group(1).strip()
        c_dem = float(match.group(2))
        c_cap = float(match.group(3))
        c_rat = float(match.group(4))
        c_ref = match.group(5).strip()
        
        # Determine Category for display grouping
        cat = "Other"
        if "SHEAR" in c_name: cat = "Shear (Chapter G)"
        elif "BENDING" in c_name or "FLEXURAL YIELDING" in c_name or "LAT TOR" in c_name or "FLANGE LOCAL" in c_name: cat = "Flexure (Chapter F)"
        elif "COMPRESSION" in c_name or "BUCKLING" in c_name: cat = "Compression (Chapter E)"
        elif "TENSION" in c_name or "TENSILE" in c_name: cat = "Tension (Chapter D)"
        elif "COMBINED" in c_name or "INTERACTION" in c_name: cat = "Interaction (Chapter H)"

        # Attempt to find Intermediate Results associated with this check
        # We look at the text immediately following this match until the next dashed line
        start_index = match.end()
        end_index = text.find("|----------------", start_index)
        sub_text = text[start_index:end_index]
        
        intermediates = []
        for imatch in intermediate_regex.finditer(sub_text):
            intermediates.append({
                "desc": imatch.group(1).strip(),
                "symbol": imatch.group(2).strip(),
                "value": imatch.group(3).strip(),
                "unit": imatch.group(4).strip() if imatch.group(4) else "",
                "ref": imatch.group(5).strip()
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
st.markdown("### AISC 360-16 LRFD Specification")

with st.expander("📥 Paste STAAD Output Here", expanded=True):
    raw_input = st.text_area("Raw Text", height=200, help="Paste the text starting from 'Member No'")

if raw_input:
    try:
        data = parse_staad_deep(raw_input)
        
        # 1. Header Summary
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Member:** `{data['header'].get('member','?')}`")
        c1.markdown(f"**Profile:** `{data['header'].get('profile','?')}`")
        
        c2.markdown(f"**Material Yield ($F_y$):** `{data['material'].get('Fy','?')} ksi`")
        c2.markdown(f"**Area ($A_g$):** `{data['properties'].get('Ag','?')} in²`")

        gov_ratio = data['header'].get('max_ratio', 0)
        status = data['header'].get('status', 'UNKNOWN')
        color = "green" if status == "PASS" else "red"
        
        c3.markdown(f"**Governing Ratio:** :{color}[**{gov_ratio}**]")
        c3.markdown(f"**Limit State:** `{data['header'].get('gov_ref','?')}`")
        st.markdown("---")

        # 2. Render Calculations in Logic Order
        # Group by category to make it look like a report
        
        # Order: Tension -> Compression -> Flexure -> Shear -> Interaction
        sort_order = ["Tension (Chapter D)", "Compression (Chapter E)", "Flexure (Chapter F)", "Shear (Chapter G)", "Interaction (Chapter H)"]
        
        # Get unique categories present
        present_cats = sorted(list(set(c['category'] for c in data['checks'])), key=lambda x: sort_order.index(x) if x in sort_order else 99)

        for cat in present_cats:
            st.markdown(f"### {cat}")
            
            checks_in_cat = [c for c in data['checks'] if c['category'] == cat]
            
            for check in checks_in_cat:
                # Logic to determine if this check is significant (Ratio > 0.01) or just show all
                # For a calc sheet, we usually show everything that isn't zero.
                if check['ratio'] >= 0.0:
                    with st.container():
                        st.markdown(f"**{check['name']}** (Ref: *{check['ref']}*)")
                        
                        # A. Intermediate Variables (The "givens" for this equation)
                        if check['intermediates']:
                            cols = st.columns(len(check['intermediates']) if len(check['intermediates']) < 4 else 4)
                            for i, var in enumerate(check['intermediates']):
                                with cols[i % 4]:
                                    st.caption(f"{var['symbol']}")
                                    st.markdown(f"`{var['value']} {var['unit']}`")
                        
                        # B. The Formula and Calculation
                        math_data = get_aisc_explanation(check['name'], check['ref'], check['demand'], check['capacity'], check['ratio'])
                        
                        m1, m2 = st.columns([2, 1])
                        with m1:
                            st.latex(math_data['eq'])
                            st.latex(math_data['check'])
                        with m2:
                            st.write("Substitution:")
                            st.latex(math_data['sub'])
                            
                        # C. Divider for readability
                        st.markdown("---")

    except Exception as e:
        st.error(f"Error parsing text: {e}")
        st.info("Make sure you copy the FULL block from 'Member No' down to the last check.")
