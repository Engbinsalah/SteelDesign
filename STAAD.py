import streamlit as st
import re

st.set_page_config(page_title="STAAD Detailed Report", layout="wide")

# --- 1. AISC 360-16 EQUATION LIBRARY ---
# Maps STAAD references (Eq.X-Y) to LaTeX strings
AISC_EQS = {
    # Chapter D (Tension)
    "EQ.D2-1": r"P_n = F_y A_g",
    "EQ.D2-2": r"P_n = F_u A_e",
    "EQ.D3-1": r"A_e = A_n U",
    
    # Chapter E (Compression)
    "EQ.E3-1": r"P_n = F_{cr} A_g",
    "EQ.E3-2": r"F_{cr} = 0.658^{\frac{F_y}{F_e}} F_y",
    "EQ.E3-3": r"F_{cr} = 0.877 F_e",
    "EQ.E3-4": r"F_e = \frac{\pi^2 E}{(L_c/r)^2}",
    "EQ.E4-1": r"P_n = F_{cr} A_g",
    "EQ.E4-2": r"F_e = \left( \frac{\pi^2 E C_w}{(L_{cz})^2} + G J \right) \frac{1}{I_x + I_y}",
    
    # Chapter F (Flexure)
    "EQ.F2-1": r"M_n = M_p = F_y Z_x",
    "EQ.F2-2": r"M_n = C_b [M_p - (M_p - 0.7 F_y S_x)(\frac{L_b - L_p}{L_r - L_p})] \le M_p",
    "EQ.F2-3": r"M_n = F_{cr} S_x",
    "EQ.F2-4": r"F_{cr} = \frac{C_b \pi^2 E}{(L_b/r_{ts})^2} \sqrt{1 + 0.078 \frac{J c}{S_x h_0} (L_b/r_{ts})^2}",
    "EQ.F2-5": r"L_p = 1.76 r_y \sqrt{\frac{E}{F_y}}",
    "EQ.F2-6": r"L_r = 1.95 r_{ts} \frac{E}{0.7 F_y} \sqrt{\frac{J c}{S_x h_0} + \sqrt{(\frac{J c}{S_x h_0})^2 + 6.76 (\frac{0.7 F_y}{E})^2}}",
    "EQ.F2-7": r"r_{ts}^2 = \frac{\sqrt{I_y C_w}}{S_x}",
    "EQ.F2-8A": r"c = 1", # Simplified for doubly symmetric
    "EQ.F6-1": r"M_n = M_p = F_y Z_y \le 1.6 F_y S_y",
    "EQ.F6-2": r"M_n = M_p - (M_p - 0.7 F_y S_y)(\frac{\lambda - \lambda_p}{\lambda_r - \lambda_p})",
    "EQ.F3-1": r"M_n = M_p - (M_p - 0.7 F_y S_x)(\frac{\lambda - \lambda_p}{\lambda_r - \lambda_p})",

    # Chapter G (Shear)
    "EQ.G2-1": r"V_n = 0.6 F_y A_w C_{v1}",
    "EQ.G6-1": r"V_n = 0.6 F_y A_w C_{v2}",
    "EQ.G2-9": r"C_v = 1.0", # Simplified logic often seen

    # Chapter H (Interaction)
    "EQ.H1-1A": r"\frac{P_r}{P_c} + \frac{8}{9} \left( \frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}} \right) \le 1.0",
    "EQ.H1-1B": r"\frac{P_r}{2P_c} + \left( \frac{M_{rx}}{M_{cx}} + \frac{M_{ry}}{M_{cy}} \right) \le 1.0",
}

# --- 2. FORMATTING HELPERS ---
def clean_num(val):
    """Converts 1.234E+02 to 123.4"""
    try:
        f = float(val)
        if f.is_integer(): return f"{int(f)}"
        if abs(f) < 0.001: return f"{f:.3e}" # Keep scientific for tiny numbers
        return f"{f:.3f}".rstrip('0').rstrip('.')
    except:
        return val

def tex_val(sym, val, unit=""):
    """Returns LaTeX string: sym = val unit"""
    unit_str = rf"\text{{ {unit}}}" if unit else ""
    # Make symbol latex friendly (escape underscores)
    sym = sym.replace("_", r"\_")
    return rf"{sym} = \textcolor{{green}}{{\mathbf{{{clean_num(val)}}}}}{unit_str}"

# --- 3. PARSING LOGIC ---
def parse_block_logic(text):
    blocks = []
    
    # We define a "Check Block" pattern
    # It starts with | HEADER |
    # Then has DEMAND/CAPACITY row
    # Then has Intermediate Results
    
    # Split raw text by the dashed line preceding a Header
    # Regex to find Check Headers: | CHECKS FOR ... | or just | COMPRESSION... |
    
    # Strategy: Find every occurrence of the DEMAND/CAPACITY pattern, 
    # then scan backwards for the Title, and forwards for the intermediates.
    
    # 1. Find the Main Result Row (Demand/Cap/Ratio/Ref)
    main_row_regex = re.compile(r"\|\s+([-\d\.E\+]+)\s+([-\d\.E\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.\-]+|Eq\.[\w\.\-]+|Table[\w\.]+)?\s+([\d]+)\s+([\d\.]+)\s+\|")
    
    # 2. Find Intermediate Rows
    # Format: | Description : Symbol = Value Unit Ref |
    # Regex Groups: 1:Desc, 2:Sym, 3:Val, 4:Unit(Opt), 5:Ref(Opt)
    inter_regex = re.compile(r"\|\s+(.*?)\s+:\s+([A-Za-z0-9/]+)\s+=\s+([-\d\.E\+]+)\s+([A-Za-z]+)?\s*([A-Za-z\.\-0-9]+)?\s*\|")

    lines = text.split('\n')
    
    current_block = None
    
    for i, line in enumerate(lines):
        # A. Check for Title (Line before a dashed line usually, or surrounded by pipes)
        # Crude Title finder: Uppercase text inside pipes, no numbers
        if re.match(r"\|\s+[A-Z\s\-]+\s+\|$", line):
            if "DEMAND" not in line and "Intermediate" not in line:
                # Close previous block if exists
                if current_block: blocks.append(current_block)
                current_block = {
                    "title": line.strip("| ").strip(),
                    "main": None,
                    "intermediates": []
                }
                continue

        # B. Check for Main Result Row
        m = main_row_regex.search(line)
        if m and current_block:
            current_block["main"] = {
                "demand": m.group(1),
                "capacity": m.group(2),
                "ratio": m.group(3),
                "ref": m.group(4) if m.group(4) else ""
            }
            continue

        # C. Check for Intermediate Rows
        # Only parse intermediates if we are "inside" a block (after the title)
        if current_block and "Intermediate Results" not in line and "----" not in line:
            im = inter_regex.search(line)
            if im:
                current_block["intermediates"].append({
                    "desc": im.group(1).strip(),
                    "sym": im.group(2).strip(),
                    "val": im.group(3),
                    "unit": im.group(4) if im.group(4) else "",
                    "ref": im.group(5) if im.group(5) else ""
                })

    if current_block: blocks.append(current_block)
    return blocks

# --- 4. STREAMLIT UI ---

st.markdown("### 📘 STAAD Detailed Calculation Pad")
st.markdown("_Showing all intermediate steps with AISC 360-16 References_")

with st.sidebar:
    st.header("Input Data")
    raw_input = st.text_area("Paste STAAD Output:", height=500)

if raw_input:
    # Header Info
    mem_match = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", raw_input)
    if mem_match:
        c1, c2 = st.columns(2)
        c1.metric("Member", mem_match.group(1))
        c2.metric("Profile", mem_match.group(2))
    st.divider()

    # Parse
    blocks = parse_block_logic(raw_input)
    
    for block in blocks:
        # Filter out blocks that are just headers or empty
        if not block['main'] and not block['intermediates']:
            continue
            
        with st.container():
            # TITLE
            st.markdown(f"#### {block['title']}")
            
            # MAIN RESULT ROW (If exists)
            if block['main']:
                m = block['main']
                # Determine colors
                r_val = float(m['ratio'])
                r_color = "maroon" if r_val <= 1.0 else "red"
                
                # Create a summary box
                cols = st.columns(4)
                cols[0].markdown("**Reference**")
                cols[0].caption(m['ref'])
                
                cols[1].markdown("**Demand ($P_u/M_u$)**")
                cols[1].latex(rf"\textcolor{{blue}}{{{clean_num(m['demand'])}}}")
                
                cols[2].markdown("**Capacity ($\phi R_n$)**")
                cols[2].latex(rf"\textcolor{{blue}}{{{clean_num(m['capacity'])}}}")
                
                cols[3].markdown("**Ratio**")
                cols[3].latex(rf"\textcolor{{{r_color}}}{{\mathbf{{{m['ratio']}}}}}")

            # INTERMEDIATE DETAILS
            if block['intermediates']:
                st.markdown("---")
                st.caption("Detailed Calculation Steps:")
                
                for step in block['intermediates']:
                    # Grid Layout: Description | Value | Equation from Code
                    c_desc, c_val, c_eq = st.columns([1.5, 1, 1.5])
                    
                    # 1. Description
                    c_desc.markdown(f"**{step['desc']}**")
                    
                    # 2. Value (Green)
                    c_val.latex(tex_val(step['sym'], step['val'], step['unit']))
                    
                    # 3. Equation (Lookup from Ref)
                    ref_key = step['ref'].upper()
                    if ref_key in AISC_EQS:
                        c_eq.latex(rf"\text{{{step['ref']}}}: \quad " + AISC_EQS[ref_key])
                    elif step['ref']:
                         c_eq.caption(f"Ref: {step['ref']}")
                
            st.divider()

else:
    st.info("Paste your STAAD output in the sidebar to generate the detailed report.")
