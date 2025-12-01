import streamlit as st
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="STAAD Full Design Report", layout="wide")

# --- HELPER FUNCTIONS ---

def format_decimal(val_str):
    """Converts scientific notation to clean decimal strings."""
    try:
        val_str = val_str.strip()
        val = float(val_str)
        if val.is_integer():
            return f"{int(val)}"
        # Format to 3 decimal places, strip trailing zeros
        return f"{val:.3f}".rstrip('0').rstrip('.') if val != 0 else "0"
    except:
        return val_str

def tex_color(text, color):
    """Wraps text in LaTeX color."""
    return rf"\textcolor{{{color}}}{{{text}}}"

def tex_val(label, val, unit="", color="black"):
    """Creates a formatted variable = value unit string."""
    val_clean = format_decimal(val)
    unit_tex = rf"\text{{ {unit}}}" if unit else ""
    # Escape underscores for LaTeX
    label = label.replace("_", r"\_")
    return rf"{label} = \textcolor{{{color}}}{{\mathbf{{{val_clean}}}}}{unit_tex}"

# --- PARSING LOGIC ---

def parse_staad_full(text):
    """
    Parses the text into a list of ordered blocks.
    Returns: List of dicts {'type': '...', 'index': int, 'data': ...}
    """
    blocks = []

    # 1. SLENDERNESS BLOCK
    # Pattern: Header -> Actual -> Allowable
    slen_match = re.search(r"\|\s*COMPRESSION SLENDERNESS", text)
    if slen_match:
        # Look for the lines following the header
        chunk = text[slen_match.end():]
        actual = re.search(r"Actual Slenderness Ratio\s*:\s*([\d\.]+)", chunk)
        allow = re.search(r"Allowable Slenderness Ratio\s*:\s*([\d\.]+)", chunk)
        
        if actual and allow:
            blocks.append({
                "type": "slenderness",
                "index": slen_match.start(),
                "data": {"actual": actual.group(1), "allow": allow.group(1)}
            })

    # 2. SECTION PROPERTIES
    # Pattern: | Ag : val Axx : val ... |
    prop_match = re.search(r"\|\s*SECTION PROPERTIES", text)
    if prop_match:
        start = prop_match.end()
        end = text.find("|-------", start)
        chunk = text[start:end]
        
        # Regex to find Key : Value pairs
        props = re.findall(r"([A-Za-z0-9\+\-]+)\s*:\s*([-\d\.E\+]+)", chunk)
        blocks.append({
            "type": "properties",
            "index": prop_match.start(),
            "data": props # List of tuples (Key, Val)
        })

    # 3. MATERIAL PROPERTIES
    mat_match = re.search(r"\|\s*MATERIAL PROPERTIES", text)
    if mat_match:
        start = mat_match.end()
        end = text.find("|-------", start)
        chunk = text[start:end]
        props = re.findall(r"([A-Za-z]+)\s*:\s*([-\d\.E\+]+)", chunk)
        blocks.append({
            "type": "material",
            "index": mat_match.start(),
            "data": props
        })

    # 4. CLASSIFICATIONS (Compression & Flexure)
    # These are tables with Flange/Web rows
    for class_type in ["COMPRESSION CLASSIFICATION", "FLEXURE CLASSIFICATION"]:
        c_match = re.search(rf"\|\s*{class_type}", text)
        if c_match:
            start = c_match.end()
            end = text.find("|-------", start)
            chunk = text[start:end]
            
            # Find Flange and Web rows
            # Format: Flange: Status Val Val Val Case
            rows = []
            for element in ["Flange", "Web"]:
                row_match = re.search(rf"{element}\s*:\s*(\w+)\s+([0-9\.]+)\s+([0-9\.N/A]+)\s+([0-9\.N/A]+)\s+([\w\.]+)", chunk)
                if row_match:
                    rows.append({
                        "elm": element,
                        "status": row_match.group(1),
                        "lam": row_match.group(2),
                        "lam_p": row_match.group(3),
                        "lam_r": row_match.group(4),
                        "case": row_match.group(5)
                    })
            
            blocks.append({
                "type": "classification",
                "name": class_type.title(),
                "index": c_match.start(),
                "data": rows
            })

    # 5. DESIGN CHECKS (Standard Table Format)
    # Pattern: | NAME | ... | DEMAND CAPACITY RATIO | ...
    check_pattern = re.compile(r"\|\s+([A-Z0-9\-\s\(\)]+?)\s+\|\n.*\|.*DEMAND.*CAPACITY.*RATIO.*REFERENCE.*LOC\s+\|\n\|\s+([-\d\.E\+]+)\s+([-\d\.E\+]+)\s+([\d\.]+)\s+(Cl\.[\w\.\d\-]+|Eq\.[\w\.\d\-]+)")
    
    inter_pattern = re.compile(r"\|\s+(.*?)\s+:\s+([A-Za-z0-9\.]+)\s+=\s+([-\d\.E\+]+)\s+([A-Za-z\-\^0-9]+)?\s+(.*)\|")

    for match in check_pattern.finditer(text):
        block_data = {
            "name": match.group(1).strip(),
            "demand": match.group(2),
            "capacity": match.group(3),
            "ratio": match.group(4),
            "ref": match.group(5).strip(),
            "intermediates": []
        }
        
        # Intermediate Parser
        start_idx = match.end()
        end_idx = text.find("|----------------", start_idx)
        if end_idx != -1:
            chunk = text[start_idx:end_idx]
            for i_match in inter_pattern.finditer(chunk):
                block_data["intermediates"].append({
                    "desc": i_match.group(1).strip(),
                    "sym": i_match.group(2).strip(),
                    "val": i_match.group(3),
                    "unit": i_match.group(4).strip() if i_match.group(4) else "",
                })

        blocks.append({
            "type": "check",
            "index": match.start(),
            "data": block_data
        })

    # 6. INTERACTION CHECK (Special Format)
    # Format: | COMBINED ... | RATIO CRITERIA ... | VAL REF ... |
    # It lacks the "Demand / Capacity" headers in the main row usually
    int_pattern = re.compile(r"\|\s+(COMBINED FORCES.*?)\s+\|\n.*\|.*RATIO.*CRITERIA.*LOC\s+\|\n\|\s+([\d\.]+)\s+(Eq\.[\w\.\-]+)")
    
    for match in int_pattern.finditer(text):
        block_data = {
            "name": match.group(1).strip(),
            "demand": None, # Interaction doesn't always have single demand
            "capacity": None,
            "ratio": match.group(2),
            "ref": match.group(3),
            "intermediates": []
        }
        
        start_idx = match.end()
        end_idx = text.find("|----------------", start_idx)
        if end_idx != -1:
            chunk = text[start_idx:end_idx]
            for i_match in inter_pattern.finditer(chunk):
                block_data["intermediates"].append({
                    "desc": i_match.group(1).strip(),
                    "sym": i_match.group(2).strip(),
                    "val": i_match.group(3),
                    "unit": i_match.group(4).strip() if i_match.group(4) else "",
                })
        
        blocks.append({
            "type": "interaction",
            "index": match.start(),
            "data": block_data
        })

    # Sort all blocks by their appearance in the text
    blocks.sort(key=lambda x: x['index'])
    return blocks

# --- UI LAYOUT ---

st.markdown("## 🏗️ STAAD.Pro Detailed Calculation Sheet")
st.markdown("*AISC 360-16 LRFD*")

with st.sidebar:
    st.header("Input")
    raw_input = st.text_area("Paste Full STAAD Output:", height=600)

if raw_input:
    # 0. HEADER INFO
    # Parse Top Level info (Member, Forces)
    mem = re.search(r"Member No:\s+(\d+)\s+Profile:\s+([\w\d]+)", raw_input)
    status = re.search(r"Status:\s+(\w+)\s+Ratio:\s+([\d\.]+)", raw_input)
    
    # Header Metrics
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    if mem:
        c1.metric("Member No", mem.group(1))
        c2.metric("Profile", mem.group(2))
    if status:
        s_color = "normal" if status.group(1) == "PASS" else "inverse"
        c3.metric("Status", status.group(1), delta_color=s_color)
        c4.metric("Max Ratio", status.group(2))
    st.divider()

    # PROCESS BLOCKS
    blocks = parse_staad_full(raw_input)
    
    for block in blocks:
        
        # --- A. SLENDERNESS ---
        if block['type'] == 'slenderness':
            with st.container():
                st.subheader("📏 Compression Slenderness")
                d = block['data']
                actual = float(d['actual'])
                allow = float(d['allow'])
                
                k1, k2 = st.columns(2)
                k1.latex(tex_val(r"KL/r_{actual}", actual, "", "blue"))
                k2.latex(tex_val(r"KL/r_{limit}", allow, "", "green"))
                
                # Visual Bar
                st.progress(min(actual/allow, 1.0))
                if actual > allow:
                    st.error("Slenderness Limit Exceeded")
                st.divider()

        # --- B. PROPERTIES (Material or Section) ---
        elif block['type'] in ['properties', 'material']:
            with st.container():
                title = "🧱 Section Properties" if block['type'] == 'properties' else "⚙️ Material Properties"
                st.subheader(title)
                
                # Display in a grid
                items = block['data']
                cols = st.columns(4)
                for i, (key, val) in enumerate(items):
                    with cols[i % 4]:
                        # Inputs are Green
                        st.latex(tex_val(key, val, "", "green"))
                st.divider()

        # --- C. CLASSIFICATIONS ---
        elif block['type'] == 'classification':
            with st.container():
                st.subheader(f"📋 {block['name']}")
                
                # Create a clean table for Classifications
                # Header
                h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 1, 2])
                h1.markdown("**Element**")
                h2.markdown(r"$\lambda$")
                h3.markdown(r"$\lambda_p$")
                h4.markdown(r"$\lambda_r$")
                h5.markdown("**Result**")
                
                for row in block['data']:
                    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])
                    c1.write(row['elm'])
                    c2.latex(tex_color(format_decimal(row['lam']), "blue"))
                    c3.latex(tex_color(format_decimal(row['lam_p']), "green"))
                    c4.latex(tex_color(format_decimal(row['lam_r']), "green"))
                    
                    res_color = "red" if "Slender" in row['status'] and "Non" not in row['status'] else "black"
                    c5.markdown(f":{res_color}[{row['status']}] ({row['case']})")
                st.divider()

        # --- D. DESIGN CHECKS ---
        elif block['type'] == 'check':
            d = block['data']
            
            with st.container():
                st.markdown(f"#### {d['name']}")
                st.caption(f"Ref: {d['ref']}")

                left, right = st.columns([2, 1])
                
                with left:
                    # Intermediate Inputs (Green)
                    if d['intermediates']:
                        st.markdown("**Parameters:**")
                        latex_str = r"\begin{aligned}"
                        for var in d['intermediates']:
                            latex_str += rf"& {var['sym']} = \textcolor{{green}}{{{format_decimal(var['val'])}}} \text{{ {var['unit']}}} \\"
                        latex_str += r"\end{aligned}"
                        st.latex(latex_str)
                
                with right:
                    st.markdown("**Utilization:**")
                    # Demand/Cap (Blue), Ratio (Maroon)
                    dem = tex_color(format_decimal(d['demand']), "blue")
                    cap = tex_color(format_decimal(d['capacity']), "blue")
                    rat = tex_color(d['ratio'], "maroon" if float(d['ratio']) <= 1.0 else "red")
                    
                    st.latex(rf"\text{{Demand}} = {dem}")
                    st.latex(rf"\text{{Capacity}} = {cap}")
                    st.latex(rf"\text{{Ratio}} = \mathbf{{{rat}}}")
                
                st.divider()

        # --- E. INTERACTION ---
        elif block['type'] == 'interaction':
            d = block['data']
            with st.container():
                st.markdown(f"#### {d['name']}")
                st.caption(f"Ref: {d['ref']}")
                
                # Similar logic but Interaction often lacks single demand/cap
                left, right = st.columns([2, 1])
                
                with left:
                    if d['intermediates']:
                        latex_str = r"\begin{aligned}"
                        for var in d['intermediates']:
                            # Distinguish inputs vs calculated capacities in interaction
                            # Usually Pn/Mn in interaction are Capacities (Blue), but here listed as intermediates
                            # We will keep green for consistency of "variables listed below"
                            latex_str += rf"& {var['sym']} = \textcolor{{green}}{{{format_decimal(var['val'])}}} \text{{ {var['unit']}}} \\"
                        latex_str += r"\end{aligned}"
                        st.latex(latex_str)

                with right:
                    st.markdown("**Interaction Eq:**")
                    rat = tex_color(d['ratio'], "maroon" if float(d['ratio']) <= 1.0 else "red")
                    st.latex(rf"\text{{Result}} = \mathbf{{{rat}}}")

                st.divider()

else:
    st.info("👈 Paste the STAAD output text in the sidebar.")
