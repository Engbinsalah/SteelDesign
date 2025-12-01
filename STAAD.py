import streamlit as st
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="STAAD Calculation Sheet", layout="wide")

# --- HELPER FUNCTIONS ---

def format_decimal(val_str):
    """
    Converts scientific notation strings (1.23E+02) to standard decimals (123.0).
    Returns a string.
    """
    try:
        val = float(val_str)
        # Check if it's an integer effectively
        if val.is_integer():
            return f"{int(val)}"
        # Otherwise show up to 4 decimal places, stripping trailing zeros
        return f"{val:.4f}".rstrip('0').rstrip('.')
    except:
        return val_str

def tex_color(text, color):
    return rf"\textcolor{{{color}}}{{{text}}}"

def get_aisc_equation(name, ref):
    """
    Returns the symbolic equation and the check inequality based on the check name.
    """
    name = name.upper()
    
    # TENSION
    if "TENSILE YIELDING" in name:
        return r"P_n = F_y A_g", r"\frac{P_u}{\phi_t P_n} \leq 1.0"
    if "TENSILE RUPTURE" in name:
        return r"P_n = F_u A_e", r"\frac{P_u}{\phi_t P_n} \leq 1.0"
    
    # COMPRESSION
    if "FLEXURAL BUCKLING" in name or "COMPRESSION" in name:
        return r"P_n = F_{cr} A_g", r"\frac{P_u}{\phi_c P_n} \leq 1.0"
    if "FLEXURAL-TORSIONAL" in name:
        return r"P_n = F_{cr_{ft}} A_g", r"\frac{P_u}{\phi_c P_n} \leq 1.0"
    
    # SHEAR
    if "SHEAR" in name:
        return r"V_n = 0.6 F_y A_w C_v", r"\frac{V_u}{\phi_v V_n} \leq 1.0"
    
    # FLEXURE
    if "FLEXURAL YIELDING" in name:
        return r"M_n = M_p = F_y Z", r"\frac{M_u}{\phi_b M_n} \leq 1.0"
    if "LAT TOR BUCK" in name:
        return r"M_n = C_b [M_p - (M_p - 0.7F_y S_x)(\dots)]", r"\frac{M_u}{\phi_b M_n} \leq 1.0"
    if "FLANGE LOCAL" in name:
        return r"\text{Local Buckling Check}", r"\frac{M_u}{\phi_b M_n} \leq 1.0"
        
    # INTERACTION
    if "COMBINED" in name or "INTERACTION" in name:
        if "H1-1A" in ref.upper():
            return r"\frac{P_r}{P_c} + \frac{8}{9}\left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right)", r"\text{Interaction} \leq 1.0"
        return r"\frac{P_r}{2P_c} + \left(\frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}}\right)", r"\text{Interaction} \leq 1.0"

    # Default
    return r"\text{Capacity Calculation}", r"\text{Demand} \le \text{Capacity}"

# --- PARSING LOGIC ---

def parse_staad_ordered(text):
    data = {
        "header": {},
        "blocks": []
    }

    # 1. Header Extraction
    mem = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", text)
    if mem:
        data["header"]["id"] = mem.group(1)
        data["header"]["profile"] = mem.group(2)
    
    status = re.search(r"Status:\s+(\w+)\s+Ratio:\s+([\d\.]+)", text)
    if status:
        data["header"]["status"] = status.group(1)
        data["header"]["ratio"] = status.group(2)

    # 2. Sequential Block Extraction
    # We look for the "Table Header" of a check (Name, Demand, Capacity...)
    # Regex Breakdown:
    # 1. Name inside pipes
    # 2. Skip headers
    # 3. Capture Demand, Capacity, Ratio, Ref
    
    check_pattern = re.compile(r"\|\s+([A-Z0-9\-\s\(\)]+?)\s+\|\n.*\|.*DEMAND.*CAPACITY.*RATIO.*REFERENCE.*LOC\s+\|\n\|\s+([-\d\.E\+]+)\s+([-\d\.E\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.\d\-]+|Eq\.[\w\.\d\-]+)")
    
    # Intermediate Variable Pattern
    # Matches: | Description : Symbol = Value Unit Ref |
    inter_pattern = re.compile(r"\|\s+(.*?)\s+:\s+([A-Za-z0-9\.]+)\s+=\s+([-\d\.E\+]+)\s+([A-Za-z\-\^0-9]+)?\s+(.*)\|")

    # Use finditer to preserve order
    for match in check_pattern.finditer(text):
        block = {
            "name": match.group(1).strip(),
            "demand": format_decimal(match.group(2)),
            "capacity": format_decimal(match.group(3)),
            "ratio": match.group(4),
            "ref": match.group(5).strip(),
            "intermediates": []
        }

        # Look for intermediate results immediately following this match
        # Start searching from the end of the check row
        start_idx = match.end()
        # Find the next separator line (end of this block)
        end_idx = text.find("|----------------", start_idx)
        
        if end_idx != -1:
            chunk = text[start_idx:end_idx]
            for i_match in inter_pattern.finditer(chunk):
                block["intermediates"].append({
                    "desc": i_match.group(1).strip(),
                    "sym": i_match.group(2).strip(),
                    "val": format_decimal(i_match.group(3)),
                    "unit": i_match.group(4).strip() if i_match.group(4) else "",
                    "ref": i_match.group(5).strip()
                })
        
        data["blocks"].append(block)

    return data

# --- UI LAYOUT ---

st.markdown("## 📐 AISC 360-16 Design Calculation")
st.markdown("Based on STAAD.Pro Connect Edition Output")

with st.sidebar:
    st.header("Input")
    raw_input = st.text_area("Paste STAAD Output:", height=400)

if raw_input:
    # Parse
    results = parse_staad_ordered(raw_input)
    
    # Header Display
    h = results["header"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Member", h.get('id', '-'))
    c2.metric("Profile", h.get('profile', '-'))
    
    status = h.get('status', 'FAIL')
    ratio = h.get('ratio', '0.0')
    delta_color = "normal" if status == "PASS" else "inverse"
    c3.metric("Governing Ratio", ratio, status, delta_color=delta_color)

    st.divider()

    # Iterate strictly in order found in text
    for i, block in enumerate(results["blocks"]):
        
        # Determine styling
        is_fail = float(block['ratio']) > 1.0
        ratio_color = "red" if is_fail else "maroon"
        
        with st.container():
            # Title Row
            st.subheader(f"{i+1}. {block['name']}")
            st.caption(f"Reference: {block['ref']}")

            col_eq, col_calc = st.columns([1.5, 1])

            # 1. Intermediates (Green Inputs) & Equation
            with col_eq:
                st.markdown("**Variables:**")
                
                # Format intermediates as a Latex Array for alignment
                if block['intermediates']:
                    # We build a LaTeX align block
                    latex_vars = r"\begin{aligned}"
                    for var in block['intermediates']:
                        # Green for Input Values
                        val_display = tex_color(var['val'], "green")
                        unit_display = f"\\text{{ {var['unit']}}}" if var['unit'] else ""
                        # Escape underscore in symbols for latex
                        sym_display = var['sym'].replace("_", "\_")
                        
                        latex_vars += rf"& {sym_display} = {val_display} {unit_display} && \text{{\small ({var['desc']})}} \\"
                    latex_vars += r"\end{aligned}"
                    st.latex(latex_vars)
                else:
                    st.text("No intermediate variables listed.")

                # Symbolic Equation
                eq_sym, eq_check = get_aisc_equation(block['name'], block['ref'])
                st.markdown("**Governing Equation:**")
                st.latex(eq_sym)

            # 2. Final Substitution (Blue Calc / Maroon Ratio)
            with col_calc:
                st.markdown("**Check:**")
                
                # Demand and Capacity in Blue (Calculated)
                d_disp = tex_color(block['demand'], "blue")
                c_disp = tex_color(block['capacity'], "blue")
                r_disp = tex_color(block['ratio'], ratio_color)
                
                # Show the inequality
                st.latex(eq_check)
                
                # Show the substitution
                st.latex(rf"\frac{{{d_disp}}}{{{c_disp}}} = \mathbf{{{r_disp}}}")
                
                if is_fail:
                    st.error("FAIL")
                else:
                    st.success("PASS")
            
            st.divider()

else:
    st.info("👈 Paste the text in the sidebar to generate the report.")
